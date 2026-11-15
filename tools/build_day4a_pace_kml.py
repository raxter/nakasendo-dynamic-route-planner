"""Day 4 Course A pacing markers for Google My Maps (owner's request, 15 Nov 2026).

A marker every km plus the schedule's waypoints, each with the time to be there at a chosen pace:
  walking time = pace × km + 15 min per 100 m climbed (the planner's rule; heights from GSI's 10 m DEM tiles, as in
  build_elev.py), plus fixed stops: Tsumago, Nagiso (buy the picnic lunch), and lunch at the Yogawa village headman's house
  (the guide's "picnic spot with a covered shelter", 14:00–14:30 in its schedule). Walk Japan's own schedule times are in each
  waypoint's description for comparison.

The track: Walk Japan's own route map (the owner's Google My Maps copy, "Self-guided Nakasendo Wayfarer", from the Route
Booklet QR code), saved git-ignored at .cache/walkjapan_mymap.kml; get it with
  curl -L -o .cache/walkjapan_mymap.kml "https://www.google.com/maps/d/kml?mid=12UGlGkwcBPp5QVDwn7sAF99ue5Y_klg&forcekml=1"
Course A = the end of its "Day 3" line from Maruya Inn + "Day 4 Morning" + "Day 4 Afternoon". Output is markers only (Walk
Japan's line stays in their map: import this as an extra layer there). Places © OpenStreetMap contributors.

Run from the repo root:  python3 tools/build_day4a_pace_kml.py [--pace 20] [--leave 7:45]
Writes kml/day4A_pace_targets.kml and prints the timetable.
"""
import argparse, math, sys, xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools")); import build_elev as be   # GSI heights (cached tiles)
ap = argparse.ArgumentParser(); ap.add_argument("--pace", type=float, default=20); ap.add_argument("--leave", default="7:45")
ap.add_argument("--climb", type=float, default=15, help="minutes per 100 m climbed"); A = ap.parse_args()
hm = lambda s: int(s.split(":")[0]) * 60 + int(s.split(":")[1])
fm = lambda m: f"{int(round(m)) // 60}:{int(round(m)) % 60:02d}"

WJ = ROOT / ".cache/walkjapan_mymap.kml"
if not WJ.exists(): sys.exit(f"missing {WJ.relative_to(ROOT)}: see the curl line at the top of this script")
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
NS = "{http://www.opengis.net/kml/2.2}"
lines = {pm.findtext(NS + "name"): [[float(v) for v in c.split(",")[:2]][::-1] for c in pm.find(".//" + NS + "LineString/" + NS + "coordinates").text.split()]
         for pm in ET.parse(WJ).getroot().iter(NS + "Placemark") if pm.find(".//" + NS + "LineString") is not None}
d3 = with_km(lines["Day 3"]); _, k0 = project(d3, MARUYA)
G = with_km([MARUYA] + [q[:2] for q in d3 if q[2] > k0] + lines["Day 4 Morning"] + lines["Day 4 Afternoon"]); TOTAL = G[-1][2]
def at(km):
    for a, c in zip(G, G[1:]):
        if km <= c[2]:
            f = (km - a[2]) / ((c[2] - a[2]) or 1); return [a[0] + f * (c[0] - a[0]), a[1] + f * (c[1] - a[1])]
    return G[-1][:2]

# heights every 100 m, lightly smoothed, → metres climbed so far
KS = [i / 10 for i in range(int(TOTAL * 10) + 1)] + [TOTAL]
H = [be.height(*at(k)) for k in KS]
SM = [sum(H[max(0, i - 2):i + 3]) / len(H[max(0, i - 2):i + 3]) for i in range(len(H))]
UP, DN = [0.0], [0.0]
for i in range(1, len(SM)): UP.append(UP[-1] + max(0, SM[i] - SM[i - 1])); DN.append(DN[-1] + max(0, SM[i - 1] - SM[i]))
def look(arr, km):
    for i in range(1, len(KS)):
        if km <= KS[i]: f = (km - KS[i - 1]) / ((KS[i] - KS[i - 1]) or 1); return arr[i - 1] + f * (arr[i] - arr[i - 1])
    return arr[-1]

# (where, label, OSM position, stop minutes, Walk Japan's time, note, style)
WAY = [
    ("Maruya Inn", MARUYA, 0, "leave 8:30", "Day 4 Course A: O-tsumago → Nagiso → Yogawa-michi → Nenoue Pass → Nojiri. Walk Japan's breakfast is 7:30: ask for it earlier.", "go"),
    ("Tsumago", [35.5790, 137.5950], 15, "9:00–9:45", "You saw Tsumago on Day 3, so a short stop. (Waki-honjin opens 9:00, ¥800.)", "town"),
    ("Nagiso Stn · buy picnic lunch", [35.5988, 137.6084], 30, "10:45–11:45", "LAST EXIT: trains from here (Course B ends here). Behind time? Take Course B. Buy the picnic lunch nearby.", "exit"),
    ("Momosuke Bridge (optional)", [35.60088, 137.60695], 0, "optional", "Wooden suspension bridge (1922), a short detour, inside the Nagiso stop time.", "opt"),
    ("Midono-juku → Yogawa-michi climb", [35.6088, 137.61156], 0, "12:15–12:30", "After Midono post town (三留野宿) the climb up the Yogawa-michi (与川道) starts. No transport until Nojiri.", "town"),
    ("Shozensawa stream", [35.6218, 137.63455], 0, "", "正善沢, the Yogawa / Midono boundary.", "pt"),
    ("Picnic lunch · Yogawa headman's house", [35.63206, 137.64166], 30, "14:00–15:00", "与川村庄屋屋敷: the likely 'picnic spot with a covered shelter' (not named in the guide).", "lunch"),
    ("Nenoue Pass (top, 840 m)", [35.65318, 137.65511], 0, "15:45–16:00", "根の上峠, the high point. Sunset 16:40, dark ≈17:08.", "pass"),
    ("Nojiri Stn", [35.67317, 137.63651], 0, "17:00 · train 17:26", "Train 17:26 Nojiri → Kiso-Fukushima (38 min, ¥420; earlier one 14:52), arrive 18:04, then taxi (~¥900) or walk ~1 km to Iwaya Inn. Donguri Café if you're here before 16:45.", "exit"),
]
WAY = [(n, ll, stop, wj, note, sty, 0.0 if i == 0 else TOTAL if i == len(WAY) - 1 else project(G, ll)[1]) for i, (n, ll, stop, wj, note, sty) in enumerate(WAY)]
def arrive(km):   # clock time you get to km (before any stop there)
    t = hm(A.leave) + km * A.pace + look(UP, km) * A.climb / 100
    return t + sum(w[2] for w in WAY if w[6] < km - 1e-6)
# Decision deadlines for the last train that gets you to Kiso-Fukushima before 19:00: it's the same train from either end,
# 17:16 from Nagiso = 17:26 from Nojiri (arrive 18:04). "Go by": the latest time to be here and still reach Nojiri by 17:20
# (with the stops still to come: Tsumago, Nagiso, lunch). "Back by": the latest time to be here and still walk back
# to Nagiso by 17:10 (today's downhills count as climbs on the way back; snack, don't stop for lunch).
NAG_KM = next(w[6] for w in WAY if w[0].startswith("Nagiso")); LUNCH_KM = next(w[6] for w in WAY if w[0].startswith("Picnic"))
rise = lambda arr, a, b: look(arr, b) - look(arr, a)
go_by = lambda x: hm("17:20") - ((TOTAL - x) * A.pace + rise(UP, x, TOTAL) * A.climb / 100
                                 + sum(w[2] for w in WAY if w[6] >= x - 1e-6))   # the stops still to come (one you're at, too)
back_mins = lambda x: (x - NAG_KM) * A.pace + rise(DN, NAG_KM, x) * A.climb / 100
back_by = lambda x: hm("17:10") - back_mins(x)
TURN_KM = next(k / 100 for k in range(int(NAG_KM * 100), int(TOTAL * 100)) if back_by(k / 100) <= go_by(k / 100))   # past here, carrying on is quicker
def decide(x, short):
    if x < NAG_KM - 1e-6: return (f" · go by {fm(go_by(x))}" if short else
        f"Go by {fm(go_by(x))}: be here by then to do Course A and catch the 17:26 at Nojiri (else Course B: train from Nagiso).")
    if x <= TURN_KM: return (f" · go by {fm(go_by(x))} · back by {fm(back_by(x))}" if short else
        f"Go by {fm(go_by(x))}: here by then → carry on to Nojiri for the 17:26.\nBack by {fm(back_by(x))}: here by then → you can still walk back to Nagiso for the 17:16 (same train, Kiso-Fukushima 18:04; snack, don't stop for lunch).\nLater than both → next trains reach Kiso-Fukushima ≈19:05: phone Iwaya Inn about dinner.")
    return (f" · go by {fm(go_by(x))} · no turning back" if short else
        f"Go by {fm(go_by(x))}: here by then → Nojiri for the 17:26. Past km {TURN_KM:.1f} carrying on is always quicker than turning back. Later → next train ≈18:29 (≈19:05 at Kiso-Fukushima): phone Iwaya Inn.")
EVENTS = []
for n, ll, stop, wj, note, sty, km in WAY:
    a = arrive(km); when = f"{fm(a)}–{fm(a + stop)}" if stop else fm(a)
    if km == 0: when = f"leave {fm(a)}"
    dec = "" if km >= TOTAL - 1e-6 else "\n\n" + decide(km, False)
    EVENTS.append((km, f"{when} {n}", ll, f"{note}{dec}\n\nkm {km:.1f} of {TOTAL:.1f} · {round(look(H, km))} m.\nWalk Japan's schedule here: {wj or '—'}.", sty))
for k in range(1, int(TOTAL) + 1):
    EVENTS.append((k, f"{fm(arrive(k))} · km {k}{decide(k, True)}", at(k), f"Planned: {fm(arrive(k))} (at {A.pace:g} min/km + {A.climb:g} min per 100 m climbed, leaving {A.leave}). Height {round(look(H, k))} m.\n\n{decide(k, False)}", "pace"))
EVENTS.sort(key=lambda e: e[0])

# Two colours, written the way Google My Maps exports its own pins (icon-1899-RRGGBB + StyleMap), so they survive an import:
# waypoints orange, km pace checks yellow (Walk Japan's map already uses blue for the Day 3/4 line, red/green for start/end).
# Each marker also carries a "Type" column, for My Maps' "Style by data column" if the colours don't come through.
COL = {"Waypoint": "E65100", "Pace check": "FFD600"}
TYPE = lambda sty: "Pace check" if sty == "pace" else "Waypoint"
def style(rgb):
    abgr = "ff" + rgb[4:6] + rgb[2:4] + rgb[0:2]; sid = f"icon-1899-{rgb}"
    one = lambda kind, lab: (f'<Style id="{sid}-{kind}"><IconStyle><color>{abgr}</color><scale>1</scale>'
                             f'<Icon><href>https://www.gstatic.com/mapspro/images/stock/503-wht-blank_maps.png</href></Icon>'
                             f'<hotSpot x="32" xunits="pixels" y="64" yunits="insetPixels"/></IconStyle><LabelStyle><scale>{lab}</scale></LabelStyle></Style>')
    return (one("normal", 0) + one("highlight", 1) +
            f'<StyleMap id="{sid}"><Pair><key>normal</key><styleUrl>#{sid}-normal</styleUrl></Pair><Pair><key>highlight</key><styleUrl>#{sid}-highlight</styleUrl></Pair></StyleMap>')
kml = ['<?xml version="1.0" encoding="UTF-8"?>', '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>',
       f'<name>Day 4A · {A.pace:g} min/km · leave {A.leave}</name>',
       f'<description>Times at {A.pace:g} min/km + {A.climb:g} min per 100 m climbed, on Walk Japan\'s Course A track ({TOTAL:.1f} km, ≈{UP[-1]:.0f} m of climbing), with stops at Tsumago, Nagiso and lunch. Places © OpenStreetMap contributors (ODbL); heights GSI.</description>',
       *[style(c) for c in COL.values()]]
for km, name, ll, desc, sty in EVENTS:
    kml.append(f'<Placemark><name>{escape(name)}</name><description>{escape(desc)}</description><styleUrl>#icon-1899-{COL[TYPE(sty)]}</styleUrl>'
               f'<ExtendedData><Data name="Type"><value>{TYPE(sty)}</value></Data></ExtendedData>'
               f'<Point><coordinates>{ll[1]:.6f},{ll[0]:.6f},0</coordinates></Point></Placemark>')
kml.append('</Document></kml>')
(ROOT / "kml/day4A_pace_targets.kml").write_text("\n".join(kml), encoding="utf-8")
print(f"{TOTAL:.2f} km, climb ≈{UP[-1]:.0f} m, walking {TOTAL * A.pace + UP[-1] * A.climb / 100:.0f} min + stops {sum(w[2] for w in WAY)} min")
for km, name, *_ in EVENTS: print(f"  km {km:5.2f}  {name}")
print(f"turn point km {TURN_KM:.2f}"); print("wrote kml/day4A_pace_targets.kml")
