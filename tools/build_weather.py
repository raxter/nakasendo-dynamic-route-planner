"""Save the weather forecast for the trip into the planner (run on request; no live weather calls from the page).

For each walking day it samples the route (every ~0.75 km), the day's planned rides and the inns, buckets those
points into ~3 km cells, and fetches an hourly forecast for each cell for that date (JST):

  1. Open-Meteo (api.open-meteo.com): hourly for all days, one request per day. Free, no key, CC BY 4.0.
  2. If that fails (it rate-limits per IP): MET Norway Locationforecast (api.met.no), free, CC BY 4.0.
     It's hourly for the first ~2.5 days, then 6-hour blocks, which are spread over their hours.

Writes data/weather.json and the WEATHER block in src/planner.html (between the WEATHER markers).
Then run: python3 tools/build_live.py, and commit + push.

Run from the repo root:   python3 tools/build_weather.py [--metno]
Needs Python Playwright (to read the days from the planner) and network access.
"""
import datetime as dt, json, math, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLANNER = ROOT / "src/planner.html"
OUT = ROOT / "data/weather.json"
JST = dt.timezone(dt.timedelta(hours=9))
UA = {"User-Agent": "nakasendo-route-planner-weather/1.0"}
CELL = 0.03                                   # degrees (~3 km)

def get(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r: return r.read()
        except Exception as e:
            err = e; print(f"  … {url[:70]} failed ({e})", file=sys.stderr); time.sleep(3 * (i + 1))
    raise err

def points_from_planner():
    """{date: [[lat, lng], ...]}: route samples, rides and inns for every walking day"""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page()
        pg.route("https://**/*", lambda r: r.abort())
        pg.goto(PLANNER.as_uri())
        out = pg.evaluate("""() => { const out = {};
          Object.values(DAYS).forEach(d => { const iso = dayISO(d), pts = out[iso] = out[iso] || [];
            for (let km = 0; km <= total(d) + 1e-6; km += 0.75) pts.push(llAt(d, km));
            pts.push(llAt(d, total(d)));
            journeyOf(d).forEach(g => [g.a, ...(g.via || []), g.b].forEach(q => pts.push(q)));
            if (d.skip) [d.skip.fromLL, ...(d.skip.via || []), d.skip.toLL].forEach(q => pts.push(q));
            for (let h = 0; h < 24; h++) pts.push(whereAt(d, h*60 + 30)); });
          return out; }""")
        b.close(); return out

def cells(pts):
    seen = {}
    for la, lo in pts:
        k = (round(la / CELL) * CELL, round(lo / CELL) * CELL)
        seen.setdefault(k, [la, lo])           # keep a real route point as the cell's location
    return [[round(v[0], 4), round(v[1], 4)] for v in seen.values()]

def open_meteo(iso, pts):
    q = {"latitude": ",".join(str(p[0]) for p in pts), "longitude": ",".join(str(p[1]) for p in pts),
         "hourly": "weather_code,temperature_2m,precipitation,precipitation_probability", "timezone": "Asia/Tokyo", "start_date": iso, "end_date": iso}
    js = json.loads(get("https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(q)))
    js = js if isinstance(js, list) else [js]
    return [{"c": w["hourly"]["weather_code"], "t": [None if v is None else round(v) for v in w["hourly"]["temperature_2m"]],
             "mm": w["hourly"]["precipitation"], "p": w["hourly"]["precipitation_probability"]} for w in js], "1h"

SYM = {"clearsky": 0, "fair": 1, "partlycloudy": 2, "cloudy": 3, "fog": 45, "lightrain": 61, "rain": 63, "heavyrain": 65,
       "lightrainshowers": 80, "rainshowers": 81, "heavyrainshowers": 82, "lightsleet": 66, "sleet": 67, "heavysleet": 67,
       "lightsleetshowers": 85, "sleetshowers": 85, "heavysleetshowers": 86, "lightsnow": 71, "snow": 73, "heavysnow": 75,
       "lightsnowshowers": 85, "snowshowers": 85, "heavysnowshowers": 86}
def sym_code(s):
    s = re.sub(r"_(day|night|polartwilight)$", "", s or "")
    return 95 if "thunder" in s else SYM.get(s, -1)

def metno_point(iso, la, lo):
    js = json.loads(get(f"https://api.met.no/weatherapi/locationforecast/2.0/complete?lat={la:.4f}&lon={lo:.4f}")); time.sleep(0.3)
    ts = [(dt.datetime.fromisoformat(e["time"].replace("Z", "+00:00")), e["data"]) for e in js["properties"]["timeseries"]]
    c, t, mm, pp, res = [], [], [], [], "1h"
    day0 = dt.datetime.fromisoformat(iso).replace(tzinfo=JST)
    for h in range(24):
        H = day0 + dt.timedelta(hours=h)
        temp = None; code = -1; rain = None; prob = None
        # temperature: interpolate between the instants around H
        before = [x for x in ts if x[0] <= H]; after = [x for x in ts if x[0] >= H]
        if before and after:
            (t0, d0), (t1, d1) = before[-1], after[0]; a = d0["instant"]["details"]["air_temperature"]; b2 = d1["instant"]["details"]["air_temperature"]
            f = 0 if t1 == t0 else (H - t0) / (t1 - t0); temp = round(a + (b2 - a) * f)
        exact = [x for x in ts if x[0] == H and "next_1_hours" in x[1]]
        if exact:
            n = exact[0][1]["next_1_hours"]; code = sym_code(n["summary"]["symbol_code"]); rain = n["details"].get("precipitation_amount", 0); prob = n["details"].get("probability_of_precipitation")
        else:
            blk = [x for x in ts if x[0] <= H < x[0] + dt.timedelta(hours=6) and "next_6_hours" in x[1]]
            if blk:
                n = blk[-1][1]["next_6_hours"]; code = sym_code(n["summary"]["symbol_code"]); rain = round(n["details"].get("precipitation_amount", 0) / 6, 2); prob = n["details"].get("probability_of_precipitation"); res = "6h"
        c.append(code); t.append(temp); mm.append(rain); pp.append(None if prob is None else round(prob))
    return {"c": c, "t": t, "mm": mm, "p": pp}, res

def main():
    force_metno = "--metno" in sys.argv
    by_day = points_from_planner(); days = {}; sources = set()
    for iso, pts in sorted(by_day.items()):
        cs = cells(pts); rows = None; src = "Open-Meteo.com"
        if not force_metno:
            try: rows, res = open_meteo(iso, cs); sources.add(src)
            except Exception as e: print(f"{iso}: Open-Meteo failed ({e}); using MET Norway", file=sys.stderr)
        if rows is None:
            got = [metno_point(iso, *p) for p in cs]; rows = [g[0] for g in got]
            res = "6h" if any(g[1] == "6h" for g in got) else "1h"; src = "MET Norway"; sources.add(src)
        days[iso] = {"src": src, "res": res, "pts": cs, "c": [r["c"] for r in rows], "t": [r["t"] for r in rows], "p": [r["p"] for r in rows],
                     "mm": [[None if v is None else round(v, 1) for v in r["mm"]] for r in rows]}
        wet = sum(1 for r in rows for h in range(7, 18) if (r["c"][h] or -1) >= 51)
        print(f"{iso}: {src}, {len(cs)} cells, {res}, wet cell-hours 7–17h: {wet}")
    data = {"updated": dt.datetime.now(JST).strftime("%Y-%m-%dT%H:%M+09:00"), "source": " + ".join(sorted(sources)), "days": days}
    OUT.write_text(json.dumps(data, separators=(",", ":")))
    block = ("/* WEATHER:BEGIN generated by tools/build_weather.py (forecast saved on request; CC BY 4.0, see source). Don't edit by hand. */\n"
             f"const WEATHER = {json.dumps(data, separators=(',', ':'))};\n/* WEATHER:END */")
    src = PLANNER.read_text(encoding="utf-8"); pat = re.compile(r"/\* WEATHER:BEGIN.*?/\* WEATHER:END \*/", re.S)
    assert len(pat.findall(src)) == 1, "WEATHER markers not found exactly once in src/planner.html"
    PLANNER.write_text(pat.sub(lambda m: block, src), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} and the WEATHER block ({len(block)} bytes), source {data['source']}, as of {data['updated']}")

if __name__ == "__main__": main()
