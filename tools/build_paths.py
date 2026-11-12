"""Build the real walking paths for the planner from OpenStreetMap.

For every stretch between two stops of a day it finds the shortest way along the
OSM-mapped Nakasendo (中山道 hiking/foot route relations). Where the walk leaves the
old road (or a stop is too far from it) it falls back to OSM foot routing
(routing.openstreetmap.de, FOSSGIS OSRM "foot" profile).

The result is written to data/trail_paths.json and injected into src/planner.html
between the TRAIL-PATHS markers as Google-encoded polylines (one per stretch).
The stops' km values stay the source of truth for timing: the drawn path is just
stretched to fit them.

Run from the repo root:   python3 tools/build_paths.py [--refresh]
then                      python3 tools/build_live.py
Data © OpenStreetMap contributors, ODbL. Needs Python Playwright (to read DAYS
from the planner) and network access to an Overpass server and the router.
"""
import heapq, json, math, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLANNER = ROOT / "src/planner.html"
CACHE = ROOT / ".cache"            # git-ignored: raw OSM downloads
OUT = ROOT / "data/trail_paths.json"
RELATIONS = [11198696, 10128790, 11919089, 54496, 2195916]   # 中山道 美濃 / 木曽路 / 信濃 / whole route / 旧中山道 (Usui east)
OVERPASS = ["https://maps.mail.ru/osm/tools/overpass/api/interpreter", "https://overpass-api.de/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter"]
ROUTER = "https://routing.openstreetmap.de/routed-foot/route/v1/foot/"
UA = {"User-Agent": "nakasendo-route-planner-build/1.0"}
MAX_SNAP_M = 1500                  # a stop further than this from the mapped Nakasendo → foot-route the whole stretch
BRIDGE_M = 40                      # join way ends that OSM left this close but unconnected
SIMPLIFY_M = 5                     # Douglas-Peucker tolerance
# stretches that are known not to follow the old road: always foot-route them ("day:index" of the stretch's first stop)
FORCE_ROUTER = set()

def get(url, data=None, tries=6):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers=UA)
            with urllib.request.urlopen(req, timeout=200) as r: return r.read()
        except Exception as e:
            print(f"  … {url[:60]} failed ({e}); retry {i+1}", file=sys.stderr); time.sleep(10 * (i + 1))
    raise SystemExit(f"could not fetch {url}")

def overpass_geom(refresh):
    f = CACHE / "nakasendo_relations.json"
    if f.exists() and not refresh: return json.loads(f.read_text())
    CACHE.mkdir(exist_ok=True)
    q = f"[out:json][timeout:150];relation(id:{','.join(map(str, RELATIONS))});out geom;"
    for url in OVERPASS:
        try:
            raw = get(url + "?" + urllib.parse.urlencode({"data": q}), tries=3); js = json.loads(raw); break
        except (SystemExit, ValueError): continue
    else: raise SystemExit("no Overpass server answered")
    f.write_text(json.dumps(js)); return js

def days_from_planner():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page()
        pg.route("https://**/*", lambda r: r.abort())
        pg.goto(PLANNER.as_uri())
        days = pg.evaluate("() => Object.fromEntries(Object.entries(DAYS).map(([k,d]) => [k, d.pts.map(p => ({km:p.km, ll:p.ll, name:p.name}))]))")
        b.close(); return days

def metres(a, b):
    kx = 111320 * math.cos(math.radians((a[0] + b[0]) / 2))
    return math.hypot((a[1] - b[1]) * kx, (a[0] - b[0]) * 110540)

def length(line): return sum(metres(line[i], line[i + 1]) for i in range(len(line) - 1))

def build_graph(js):
    adj = {}
    for rel in js["elements"]:
        for m in rel["members"]:
            g = m.get("geometry")
            if m["type"] != "way" or not g: continue
            pts = [(round(q["lat"], 7), round(q["lon"], 7)) for q in g]
            for a, b in zip(pts, pts[1:]):
                if a == b: continue
                w = metres(a, b); adj.setdefault(a, {})[b] = w; adj.setdefault(b, {})[a] = w
    # the relations' ways don't always share nodes: bridge loose ends to anything within BRIDGE_M
    grid = {}
    for n in adj: grid.setdefault((int(n[0] * 2000), int(n[1] * 2000)), []).append(n)
    for n in [n for n in adj if len(adj[n]) == 1]:
        gx, gy = int(n[0] * 2000), int(n[1] * 2000)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for m in grid.get((gx + dx, gy + dy), []):
                    if m != n and m not in adj[n] and metres(n, m) <= BRIDGE_M:
                        w = metres(n, m); adj[n][m] = w; adj[m][n] = w
    return adj

def nearest(adj, ll):
    best = min(adj, key=lambda n: metres(n, ll)); return best, metres(best, ll)

def dijkstra(adj, s, t):
    dist, prev, pq = {s: 0}, {}, [(0, s)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == t: break
        if d > dist[u]: continue
        for v, w in adj[u].items():
            nd = d + w
            if nd < dist.get(v, 1e18): dist[v] = nd; prev[v] = u; heapq.heappush(pq, (nd, v))
    if t not in dist: return None
    out = [t]
    while out[-1] != s: out.append(prev[out[-1]])
    return out[::-1]

def router(a, b, profile="foot"):
    base = ROUTER if profile == "foot" else ROUTER.replace("foot", profile)
    url = f"{base}{a[1]},{a[0]};{b[1]},{b[0]}?overview=full&geometries=geojson"
    js = json.loads(get(url)); time.sleep(1)
    if js.get("code") != "Ok": return None
    return [(c[1], c[0]) for c in js["routes"][0]["geometry"]["coordinates"]]

def connector(p, q):
    """walk from a stop that sits off the old road (e.g. a station) to the nearest point on it, and back"""
    d = metres(p, q)
    if d < 60: return [tuple(p), tuple(q)]
    r = router(p, q)
    return [tuple(p)] + (r if r and length(r) < 3 * d + 300 else []) + [tuple(q)]

def simplify(line, tol):
    if len(line) < 3: return line
    lat0 = line[0][0]; kx = 111320 * math.cos(math.radians(lat0))
    xy = [((q[1] - line[0][1]) * kx, (q[0] - lat0) * 110540) for q in line]
    keep = [False] * len(line); keep[0] = keep[-1] = True; stack = [(0, len(line) - 1)]
    while stack:
        i, j = stack.pop(); ax, ay = xy[i]; bx, by = xy[j]; vx, vy = bx - ax, by - ay; L2 = vx * vx + vy * vy or 1e-9
        best, bi = -1, -1
        for k in range(i + 1, j):
            px, py = xy[k]; f = max(0, min(1, ((px - ax) * vx + (py - ay) * vy) / L2))
            dd = math.hypot(px - ax - f * vx, py - ay - f * vy)
            if dd > best: best, bi = dd, k
        if best > tol: keep[bi] = True; stack += [(i, bi), (bi, j)]
    return [q for q, k in zip(line, keep) if k]

def encode(line):
    out, plat, plon = [], 0, 0
    for lat, lon in line:
        ilat, ilon = round(lat * 1e5), round(lon * 1e5)
        for v in (ilat - plat, ilon - plon):
            v = ~(v << 1) if v < 0 else v << 1
            while v >= 0x20: out.append(chr((0x20 | (v & 0x1f)) + 63)); v >>= 5
            out.append(chr(v + 63))
        plat, plon = ilat, ilon
    return "".join(out)

def main():
    refresh = "--refresh" in sys.argv
    days = days_from_planner(); adj = build_graph(overpass_geom(refresh))
    print(f"Nakasendo graph: {len(adj)} nodes")
    result, report = {}, []
    for key, pts in days.items():
        segs = []
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]; nominal = (b["km"] - a["km"]) * 1000
            line, src, note = None, "router", ""
            if f"{key}:{i}" not in FORCE_ROUTER:
                (na, da), (nb, db) = nearest(adj, a["ll"]), nearest(adj, b["ll"])
                note = f"off-trail {da:.0f}/{db:.0f} m"
                if max(da, db) <= MAX_SNAP_M and na != nb:
                    path = dijkstra(adj, na, nb)
                    if path:
                        cand = connector(a["ll"], na) + path[1:-1] + connector(nb, b["ll"])
                        if 0.55 * nominal <= length(cand) <= 1.7 * nominal + 500: line, src = cand, "nakasendo"
                        else: note += f", trail way {length(cand)/1000:.1f} km rejected"
            if line is None:
                line = router(a["ll"], b["ll"])
                if line and length(line) > 1.6 * nominal + 500:      # the foot router took a long detour:
                    bike = router(a["ll"], b["ll"], "bike")          # the bike profile sticks to the direct lanes
                    if bike and length(bike) < length(line): line, src = bike, "router(bike)"
                if not line or length(line) > 1.6 * nominal + 500: line, src = [], "straight"   # no believable path: keep it straight
            line = [tuple(a["ll"])] + list(line) + [tuple(b["ll"])]
            line = simplify(line, SIMPLIFY_M)
            report.append(f"{key:4} {a['name'][:22]:22} → {b['name'][:22]:22} {src:12} {length(line)/1000:5.1f} km (itinerary {nominal/1000:4.1f}) {len(line)} pts  {note}")
            segs.append(line)
        result[key] = segs
    print("\n".join(report))
    OUT.write_text(json.dumps({"source": "© OpenStreetMap contributors (ODbL), built by tools/build_paths.py",
                               "days": {k: [[[round(x, 5) for x in q] for q in s] for s in v] for k, v in result.items()}}, separators=(",", ":")))
    enc = {k: [encode(s) for s in v] for k, v in result.items()}
    block = ("/* TRAIL-PATHS:BEGIN generated by tools/build_paths.py from OpenStreetMap (© OpenStreetMap contributors, ODbL). Don't edit by hand. */\n"
             f"const TRAIL_ENC = {json.dumps(enc, separators=(',', ':'))};\n/* TRAIL-PATHS:END */")
    src = PLANNER.read_text(encoding="utf-8")
    pat = re.compile(r"/\* TRAIL-PATHS:BEGIN.*?/\* TRAIL-PATHS:END \*/", re.S)
    assert len(pat.findall(src)) == 1, "TRAIL-PATHS markers not found exactly once in src/planner.html"
    PLANNER.write_text(pat.sub(lambda m: block, src), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} and the TRAIL block in src/planner.html ({len(block)} bytes)")

if __name__ == "__main__": main()
