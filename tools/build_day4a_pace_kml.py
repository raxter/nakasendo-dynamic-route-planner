"""Day 4 Course A pacing markers for Google My Maps (owner's request, 15 Nov 2026).

Targets come from Walk Japan's Course A schedule (O-tsumago → Nagiso → Yogawa-michi → Nenoue Pass → Nojiri);
places from OpenStreetMap. In-between "pace" markers are interpolated between the schedule's times (≈).

The track: Walk Japan's own route map (the owner's Google My Maps copy, "Self-guided Nakasendo Wayfarer"), if it's
saved at .cache/walkjapan_mymap.kml (git-ignored; get it with
  curl -L -o .cache/walkjapan_mymap.kml "https://www.google.com/maps/d/kml?mid=12UGlGkwcBPp5QVDwn7sAF99ue5Y_klg&forcekml=1").
Course A = the end of its "Day 3" line from Maruya Inn + "Day 4 Morning" + "Day 4 Afternoon". With it the output is
markers only (Walk Japan's line stays in their map: import this as an extra layer there); without it, the planner's
Day 4A OSM path is used and drawn. Writes kml/day4A_pace_targets.kml.
Run from the repo root: python3 tools/build_day4a_pace_kml.py   (needs Python Playwright without the Walk Japan file)
"""
import math, xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
WJ = ROOT / ".cache/walkjapan_mymap.kml"
MARUYA = [35.5647, 137.5930]
def mdist(a, b):
    k = math.cos(math.radians((a[0] + b[0]) / 2)); return math.hypot((a[0] - b[0]) * 111320, (a[1] - b[1]) * 111320 * k)
def with_km(line):
    out = [[*line[0], 0.0]]
    for a, b in zip(line, line[1:]): out.append([*b, out[-1][2] + mdist(a, b) / 1000])
    return out
def project(line, ll):   # (metres off, km along) for the nearest point of a [lat, lng, km] line
    best = (1e9, 0.0)
    for a, b in zip(line, line[1:]):
        k = math.cos(math.radians(a[0])); vx, vy = (b[1] - a[1]) * k, b[0] - a[0]; px, py = (ll[1] - a[1]) * k, ll[0] - a[0]
        f = max(0.0, min(1.0, (px * vx + py * vy) / ((vx * vx + vy * vy) or 1e-18))); q = [a[0] + f * vy, a[1] + f * (b[1] - a[1])]
        d = mdist(q, ll)
        if d < best[0]: best = (d, a[2] + f * (b[2] - a[2]))
    return best
if WJ.exists():
    NS = "{http://www.opengis.net/kml/2.2}"
    lines = {pm.findtext(NS + "name"): [[float(v) for v in c.split(",")[:2]][::-1] for c in pm.find(".//" + NS + "LineString/" + NS + "coordinates").text.split()]
             for pm in ET.parse(WJ).getroot().iter(NS + "Placemark") if pm.find(".//" + NS + "LineString") is not None}
    d3 = with_km(lines["Day 3"]); _, k0 = project(d3, MARUYA)
    G = with_km([MARUYA] + [q[:2] for q in d3 if q[2] > k0] + lines["Day 4 Morning"] + lines["Day 4 Afternoon"]); SRC = "Walk Japan's route map"
else:
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(); pg.route("https://**/*", lambda r: r.abort()); pg.goto((ROOT / "src/planner.html").as_uri())
        G = pg.evaluate("() => { S.paths = 'walk'; return geomOf(DAYS.d4A).map(g => [g.ll[0], g.ll[1], g.km]); }"); b.close()
    SRC = "the planner's OSM path"
TOTAL = G[-1][2]

def at(km):   # [lat, lng] on the path at this planner km
    for a, c in zip(G, G[1:]):
        if km <= c[2]:
            f = (km - a[2]) / ((c[2] - a[2]) or 1); return [a[0] + f * (c[0] - a[0]), a[1] + f * (c[1] - a[1])]
    return G[-1][:2]
hm = lambda s: int(s.split(":")[0]) * 60 + int(s.split(":")[1])
fm = lambda m: f"{int(m) // 60}:{int(round(m)) % 60:02d}"

# (km, time used for pacing in between, label, where, notes, style)  times are the guide's; ranges kept in the label
CHECK = [
    (0.0,   "8:30",  "8:30 Leave Maruya Inn", [35.5647, 137.5930], "Breakfast 7:30. Day 4 Course A: O-tsumago → Nagiso → Yogawa-michi → Nenoue Pass → Nojiri.", "go"),
    (2.0,   "9:00",  "9:00–9:45 Tsumago post town", [35.5790, 137.5950], "Waki-honjin museum opens 9:00 (¥800; closed 2nd/4th Thursday). Guide: no more than an hour here. Leave by 9:45.", "town"),
    (5.9,   "10:52", "10:45–11:00 Nagiso Stn · buy picnic lunch", [35.5988, 137.6084], "LAST EXIT: trains from here (Course B ends here). Buy the picnic lunch nearby. Leave 11:30–11:45.", "exit"),
    (6.1,   None,    "Optional · Momosuke Bridge", [35.60088, 137.60695], "Wooden suspension bridge (1922) over the Kiso river, a short detour from Nagiso.", "opt"),
    (7.1,   "12:22", "12:15–12:30 Midono-juku → start Yogawa-michi climb", [35.6088, 137.61156], "After Midono post town (三留野宿), climb the Yogawa-michi (与川道). From here there's no transport until Nojiri. Running late here? Think about Course B (train from Nagiso).", "town"),
    (10.23, None,    "Shozensawa stream (Yogawa / Midono boundary)", [35.6218, 137.63455], "正善沢. On the way up the Yogawa valley.", "pt"),
    (11.97, "14:15", "14:00–14:30 Picnic lunch ≈ Yogawa village headman's house", [35.63206, 137.64166], "Guide: picnic lunch spot with a covered shelter at 14:00–14:30; this is the likely spot (与川村庄屋屋敷), not named in the guide. Leave 14:30–15:00.", "lunch"),
    (15.8,  "15:52", "15:45–16:00 Nenoue Pass (top)", [35.65318, 137.65511], "根の上峠, the high point (~840 m). Sunset 16:40, dark ≈17:08: don't linger.", "pass"),
    (19.95, "17:00", "17:00 Nojiri Stn · train 17:26 (or 14:52)", [35.67317, 137.63651], "Donguri Café if you arrive before 16:45. Train 17:26 Nojiri → Kiso-Fukushima (38 min, ¥420), arrive 18:04; the earlier 14:52 if exceptionally fast. Then taxi (~¥900, 3–5 min) or walk ~1 km to Iwaya Inn. Dinner 19:00.", "exit"),
]
CHECK = [(project(G, ll)[1] if i else 0.0, t, name, ll, note, sty) for i, (_, t, name, ll, note, sty) in enumerate(CHECK)]
CHECK[-1] = (TOTAL, *CHECK[-1][1:])
DEPART = {"9:00": "9:45", "10:52": "11:37", "14:15": "14:45"}   # arrive → leave (range middles) for pacing the next stretch   # leave times (range middles) for pacing the next stretch
anchors = []
for km, t, *_ in CHECK:
    if t: anchors.append((km, hm(t)))
    if t in DEPART: anchors.append((km, hm(DEPART[t])))
def t_at(km):
    for (k0, t0), (k1, t1) in zip(anchors, anchors[1:]):
        if k0 <= km <= k1 and k1 > k0: return t0 + (km - k0) / (k1 - k0) * (t1 - t0)
PACE = [8.0, 9.0, 10.5, 12.5, 13.5, 14.5, 16.5, 18.0]
STY = {"go": "ff3d8b2e", "town": "ff1f6fd6", "exit": "ff12a7f5", "opt": "ffb0b0b0", "pt": "ff8a6a5a", "lunch": "ff7a2ae0", "pass": "ff2a2ad6", "pace": "ff3d8b2e"}

pm = []
for km, t, name, ll, note, sty in CHECK:
    if t is None and sty == "pt": name = f"≈{fm(t_at(km))} {name}"
    pm.append((name, ll, f"{note}\n\nkm {km:.1f} of {TOTAL:.1f} on {SRC}.", sty))
for km in PACE:
    pm.append((f"≈{fm(t_at(km))} pace check · km {km:g}", at(km), f"Interpolated from the Walk Japan schedule: to stay on it, be here around {fm(t_at(km))}.", "pace"))

def style(k, col):
    return (f'<Style id="{k}"><IconStyle><color>{col}</color><scale>{0.8 if k == "pace" else 1.1}</scale>'
            f'<Icon><href>https://maps.google.com/mapfiles/kml/paddle/wht-blank.png</href></Icon></IconStyle><LabelStyle><scale>0.9</scale></LabelStyle></Style>')
kml = ['<?xml version="1.0" encoding="UTF-8"?>', '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>',
       '<name>Day 4 Course A · pace targets (Mon 16 Nov)</name>',
       '<description>Times from Walk Japan\'s Course A schedule; ≈ markers are interpolated. Places © OpenStreetMap contributors (ODbL).</description>',
       *[style(k, c) for k, c in STY.items()],
       ]
if not WJ.exists():   # no Walk Japan map: draw the planner's path so the markers have a line to sit on
    kml += ['<Style id="route"><LineStyle><color>ff3d8b2e</color><width>4</width></LineStyle></Style>',
            f'<Placemark><name>Day 4 Course A walking path ({TOTAL:.0f} km)</name><styleUrl>#route</styleUrl><LineString><tessellate>1</tessellate><coordinates>',
            " ".join(f"{g[1]:.6f},{g[0]:.6f},0" for g in G), '</coordinates></LineString></Placemark>']
for name, ll, desc, sty in pm:
    kml.append(f'<Placemark><name>{escape(name)}</name><description>{escape(desc)}</description><styleUrl>#{sty}</styleUrl>'
               f'<Point><coordinates>{ll[1]:.6f},{ll[0]:.6f},0</coordinates></Point></Placemark>')
kml.append('</Document></kml>')
out = ROOT / "kml/day4A_pace_targets.kml"; out.write_text("\n".join(kml), encoding="utf-8")
for (name, ll, *_), in zip(pm): print(f"{name}   ({project(G, ll)[0]:.0f} m off the track)")
print("track:", SRC, f"{TOTAL:.2f} km")
print("wrote", out.relative_to(ROOT))
