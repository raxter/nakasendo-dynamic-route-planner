# Nakasendo Dynamic Route Planner: handoff for Claude

You are picking up a project built in an earlier Claude session. This file is the whole briefing, so read it before you change anything.

## 1. The trip and the people

- **Tour:** Walk Japan, *Self-Guided Nakasendo Wayfarer*, 13–19 Nov 2026, from Ena to Tokyo.
  - Day 1 is arrival only. The walks are Days 2–7.
  - Day 4 has two routes: Course A (23 km over Nenoue Pass) and Course B (8 km to Nagiso).
- **Group:** three adults, a mum and two grown-up siblings. One of them may struggle to walk.
- **Getting out early:** the duck-out options are **buses and trains. Taxis are a last resort** (rural area, often unavailable).
- **The owner** reads everything on a **phone, often a low-DPI one, sometimes a tablet**.
  - Keep phone layouts map-first.
  - On a tablet or square screen the page must **fit without scrolling**.
  - **Nothing may judder.** The option cards keep a fixed height, and `tools/tests/sweep.py` checks it.
- **Style:** *Japanese-cute and cheerful, funny, but serious data.*
  - The walkers are a **mum squirrel in a pin, wearing a kasa hat, facing right, plus two trailing adult squirrels**.
  - The two trailing squirrels both wear **green** gear: a scarf and a backpack.
- **Default walking pace:** 30 min/km, plus 15 min per 100 m of climbing, plus a 45-min lunch where a day has `lunchKm`.

## 2. What's in this repo

| Path | What it is |
|---|---|
| `src/planner.html` | **Source of truth.** The self-contained planner with the hand-drawn SVG "sketch map". It is also published as a Claude artifact (see §6). |
| `src/live_addon.js` | The live-map mode: a Leaflet map, a GPS blue dot, and "set position & time to here". It's spliced into the page at build time. |
| `tools/build_live.py` | Builds `index.html` = `src/planner.html` + `src/live_addon.js` + Leaflet from cdnjs. It uses exact-string anchors, so if an anchor moves, the build fails loudly. |
| `tools/build_paths.py` | Builds the real walking paths from OpenStreetMap (see §4 "Paths") into `data/trail_paths.json` and the `TRAIL-PATHS` block in `src/planner.html`. Raw OSM downloads are cached in `.cache/` (git-ignored); `--refresh` re-downloads. |
| `index.html` | **Built output, served by GitHub Pages. Never edit it by hand.** |
| `tools/tests/sweep.py` | Regression test: every day × every 7 min. Fails on any JS error or on card-height judder. |
| `tools/tests/test_live.py` | Live-map test with mocked GPS (near Tsumago) and clock (16 Nov 11:20 JST). It needs `npm i leaflet@1.9.4`. |
| `docs/*.pdf` | Printable trail and duck-out guides: one in English, one with English and Japanese side by side. They're static and were made in the earlier session; the generator isn't included. |
| `data/trail_data.json` | Per-day stops, ETAs at 30 min/km, zones and journeys, exported from the planner for the PDFs. |
| `kml/*.kml` + `tools/build_kml.py` | Google My Maps imports for inns and sub-stops. **These use the old pace assumptions.** |
| `.nojekyll` | Stops GitHub Pages from running Jekyll. |

## 3. First job: host it on GitHub Pages

1. Put these files at the **repo root** on the default branch (`main`), keeping this folder layout.
2. Rebuild and test:
   ```bash
   pip install playwright && python -m playwright install chromium   # if needed
   python3 tools/build_live.py
   python3 tools/tests/sweep.py              # sketch planner
   python3 tools/tests/sweep.py index.html   # built live page (same sweep)
   npm i leaflet@1.9.4 && python3 tools/tests/test_live.py
   ```
3. Commit and push.
4. Turn on Pages from `main` / root, using either route:
   - **CLI:** `gh api -X POST repos/OWNER/REPO/pages -f "source[branch]=main" -f "source[path]=/"`. Use `PUT` instead if Pages already exists.
   - **Web:** Settings → Pages → Deploy from a branch → `main` / `/ (root)`.
5. Pages needs a **public** repo on free plans. The owner already accepts that the planner is public.
6. Give the owner the URL, `https://OWNER.github.io/REPO/`. Tell them to open it on their phone, tap **🗺️**, and allow location.

## 4. How the planner works (src/planner.html)

It's one inline `<script>`, with sections marked `/* ---------- name ---------- */`. Everything is in minutes-since-midnight (`hm("7:00")` → 420, `fmt(m)` back; `fmt` adds "(after midnight)" past 24:00).

### Data

- **`P`:** coordinates as `[lat, lng]`.
- **`DEP`:** departure lists per stop, built with `L("7:02 8:00 …")` or `every(from, to, step)`.
  - **Gotcha:** `L` is the planner's timetable parser, which is why Leaflet is aliased to `LF`.
- **`DAYS`:**
  - Keys: `d2 d3 d4A d4B d5 d6 d7`. `d.key` is `d4` for both Day 4 courses. `ORDER` lists the chips.
  - Each day has `walkStart`, an optional `lunchKm`, an optional `transfer`, and `pts`.
  - Each entry in `pts` is `pt(km, ll, name, kind, up, down, hop)`:
    - `kind` is `stop`, `pass` or `end`. A `pass` means a no-exit section.
    - `hop` is the duck-out: `{mode, to, toLL, ride, deps, est, weather, at, atName, extraKm, freqNote}`.
    - `at` means the bus leaves from somewhere off the trail, e.g. Karuizawa Stn, `extraKm` away.
    - `est: true` marks an estimate; the UI shows ≈.
- **`TRAIL_ENC` / `TRAIL`:** generated by `tools/build_paths.py` (don't hand-edit the block between the `TRAIL-PATHS` markers). One Google-encoded polyline per stop-to-stop stretch, per `DAYS` key (`d.id`, e.g. `d4A`).
- **`TOUR`:** the pre-planned tour transport legs. `NODES` are stations and `INNS` are the inns.

### State

`S = {day, course, pace, km, t, starts:{}, walkOver:{}, txt, txtScale, paths, sky, base}`. The look settings `paths` (`"walk"` | `"straight"`), `txtScale`, `sky` (daylight band on/off) and `base` (live-map background) are remembered in `localStorage` (`nakasendo.look`); see `PREFS`.

- **`startOf(d)`:** when you leave the inn, i.e. the ▲ on the time rail.
- **`transferOf(d)`:** the morning tour transfer.
  - Day 5: a taxi, 25 min.
  - Day 6: a van to Kiso-Fukushima (45 min), then the next train to Yabuhara (20 min).
- **`walkStartOf(d)`:** when walking actually begins. It's `S.walkOver` if set (by "I'm here…"), else the transfer arrival, else `startOf`.
- **`journeyOf(d)`:** timed segments of the planned transport, used to put the squirrels on the train or van.
  - Morning (`grp:"am"`) and evening (`grp:"pm"`) trips. Evening trips are:
    - Day 4B: Nagiso → Kiso-Fukushima.
    - Day 4A: Nojiri → Kiso-Fukushima.
    - Day 6: Narai → Shiojiri → Nagano → Karuizawa.
    - Day 7: Yokokawa → Takasaki → Tokyo.
  - It ends with a `done` "at the inn" segment.

### Walking model

`walkBetween`, `walkBack` (descents count as climbs on the way back), `T(d, km, pace)` and `Pos(d, t, pace)` (which handles lunch).

Precedence:
- Moving the time moves the position.
- Dragging the squirrels changes the time.
- Changing the pace keeps the position and changes the time.
- Moving the ▲ start keeps the position.

### Paths (route geometry)

- **`geomOf(d)`** gives the day's line as `[{ll, km}]`: the `TRAIL` polylines when `S.paths === "walk"`, else just the stops. Each stretch is stretched so its ends sit at the stops' km, so **the stops' km stay the truth for timing**; the path only changes where things are drawn.
- Everything that draws or snaps uses it: `llAt`, `sliceLL` / `routeSlice`, `lineLL`, `nearestOn` (dragging), `snapToDay` (live), the day fits and the trailing squirrels.
- **Where the paths come from** (`tools/build_paths.py`): the shortest way along the OSM 中山道 route relations (美濃, 木曽路, 信濃, the whole route, and 旧中山道 east of Usui). Stations that sit off the old road get a short foot-routed connector. Anything else (Day 5 on the Kaida Plateau) uses OSM foot routing via routing.openstreetmap.de, falling back to the bike profile after a big detour, and to a straight line if nothing believable is found (Kaida Info Centre → Kaida Shisho). The script prints each stretch's length against the itinerary km; check those numbers, and look at the result on a map, after any rebuild.
- **Attribution is required** (ODbL): the legend's "trail © OpenStreetMap", the ☰ menu note, the info sheet and the Leaflet attribution all carry it.

### Daylight band

- `skyAt(d, t)` maps a time to the colour of the light (`SKY_STOPS`: night navy, dawn pink ≈6:15, pale day, amber in the afternoon, orange at sunset, purple at dusk, navy after dark). `skySamples(d)` samples the day's walk with `T(d, km, pace)`, so the band moves with pace and start time.
- Sketch: `skyBand()` smooths the samples, draws Catmull-Rom/Bézier pieces into the separate `#sky` SVG under `#map`, and CSS blurs it. `#map` has no background rect any more; the paper colour comes from `.mapwrap`.
- Live: polylines in a `sky` Leaflet pane (z 300) that CSS blurs (`.skypane`).

### Escape zones

These colour the wide band under the route.

- **`zonesOf`** is the geographic layer. Within a stretch containing a `pass` between two exits, the zone is `back` (yellow) while walking back is quicker, and `commit` (red-orange) after the point of no return. Otherwise it's `go` (green).
- **`timedZones`** adds time, using the nearest stop ahead and behind and when you'd reach each:
  - Neither has a departure left → `nobus` (burgundy `#8e1b3a`).
  - Only the stop ahead has one → `commit`.
  - Only the stop behind has one → `back`.
  - A walk that ends at an inn with no `hop` counts as OK ahead.

### Options

`compute()` returns `{fwd, back}`, each with `walk, arr, dep, dep2, wait`.
- `back.off` hides the turn-back option when walking on is quicker.
- `noBus` is set when no departure is left. It hides the arc, the tags and (for back) the route.

### Rendering

- **`render()`:** draws the SVG.
  - Layers: other days, tour legs, today's zones, the walked part, ahead/back routes and ride arcs (`hopLine`), stops, `tag()` lines for the next two departures, then the squirrels and the `rideIcon` vehicle.
  - Labels go through `addLabel` → `placeLabels`, a collision placer. It has time-ordered stacks, leader lines and a halo.
  - Labels have no bubbles. Option stops read `"➡️ Name"` in colour plus a black `" · arrive @ hh:mm 🚃"` tail.
  - Map text has 3 states (`S.txt`: 0 shown, 1 hidden, 2 faded 50% – default) and a size of 50/75/100% (`S.txtScale`, default 50%). Full-strength text draws above the squirrels; faded text draws below them.
- **`renderText()`:** the status line, badges, the two option cards (`optHTML`) and the tip.
- **`renderRail()`:** time-rail ticks for leave/walk start, finish, sunset 🌇 and dark 🌙, with spread labels.
- **Controls:**
  - The day chips scroll sideways on phones, with ‹ › chevrons.
  - Day 4 has a course toggle.
  - The **"📍 I'm here…"** dropdown (`hereAt`): Now, then 15-min times. It keeps the position, sets the clock, and back-solves the walk start.
  - The **▲** marker is draggable.
  - Map buttons: zoom, fit today, whole trip, text visibility (👁️ shown / hidden / faded), text size (50/75/100%) and **☰**. The ☰ menu has the path style (walking path / straight lines) and the daylight band on/off, plus, on the built page only (injected by `build_live.py`), the live-map background.

### Live mode (src/live_addon.js)

- **Map:** Leaflet is aliased as **`LF`**. The background is picked in ☰ (`setBase`, `BASES`): **Quiet** (default), Pale, Topo, Aerial (all GSI) or OSM. Attribution is required, and it's already in place.
- **Quiet** is drawn by hand from GSI's vector tiles (`experimental_bvmap`, CORS-open). `mvtDecode` is a small built-in Mapbox Vector Tile reader, so no extra library is needed. `quietDraw` paints only `contour` (50 m index lines darker), `waterarea` and `river` onto canvas tiles, and adds `label` features with `annoCtg` 210/220 (villages, hamlets) as Leaflet markers in the `qlabels` pane, but only if they're within 1.2 km of any day's path (`nearTrail`). Names show as romaji from the kana reading (`romaji()`, simplified Hepburn without macrons) plus the kanji.
- **`drawLive()`:** redraws the overlays (zones, stops with tooltips, tour legs, inns, the draggable squirrel marker that snaps to the trail, the GPS dot and its accuracy circle). It runs at the end of every `render()`.
- **`setHere(ll)`:** the blue-dot popup button.
  1. Snap to the nearest trail of any day (`snapAnyDay`).
  2. Set the time to now.
  3. Keep the start time and solve the pace: `(now − walkStart − climbMinutes − lunch) / km`.
  4. If the result falls outside 12–60 min/km, or you're at or before the start, fall back to `hereAt` (move the start instead) and say so in a toast.
- **Trail geometry** is the shared `geomOf` line (see "Paths"). If the owner ever supplies the real Walk Japan GPX tracks, they beat the OSM paths. Don't scrape them from elsewhere.

## 5. Making updates

0. If you move a stop or add one, re-run `python3 tools/build_paths.py` (it reads `DAYS` from the planner) and check its report.
1. Edit **`src/planner.html`** for planner changes, or **`src/live_addon.js`** for live-map-only changes.
2. `python3 tools/build_live.py`.
3. Run both sweeps, plus `test_live.py` if you touched live mode. Look at screenshots at **390×844 (phone)** and **1000×1000 (square tablet)**.
4. Commit with a clear message and push. Pages redeploys in about a minute.

Rules and lessons:
- Keep every option card the same height; the sweep enforces it. Use single-line ellipses rather than letting text wrap.
- Flag new estimated times with `est:true` / ≈. Don't present guesses as timetable facts.
- Times are JST minutes. The owner's phone will be on JST during the trip.
- Don't add taxis as a duck-out except as a clearly labelled last resort.
- Keep the squirrel art consistent: the mum pin with her kasa, the two trailing squirrels in green, and the vehicle icons with heads in the windows.

## 6. The Claude artifact copy

- The sketch planner is also live as a public Claude artifact at https://claude.ai/artifact/UDCorA8nSLtETrTVqudNxi.
- The artifact host blocks map tiles, Leaflet and geolocation, so the live mode works **only** on GitHub Pages.
- A Claude Code session can't update that artifact. If the owner wants it kept in step, they paste `src/planner.html` into a claude.ai chat that has the artifact tools and ask for it to be republished. Otherwise the GitHub Pages link is the one to use.

## 7. Known uncertainties (in the app as ≈)

- **Estimated times:** the Ena trains; the Ochiai and Kaida Info Centre buses; the Nojiri, Yabuhara and Narai trains; Kiso-Fukushima northbound; and the Shinano / shinkansen connection waits.
- **Tour pick-up times** (assumed to be the leave time) and transfer durations. If the owner gets the real times from Walk Japan, put them in `DAYS[..].transfer` / `KF_NORTH`.
- **Stop positions:** Nenoue Pass (根の上峠), Torii Pass (鳥居峠) and Sakamoto-juku (坂本宿) were moved to their OpenStreetMap positions in Nov 2026. Nenoue Pass had been about 5 km off, on the wrong side of the Kiso river. Course A goes over it by the Yogawa-michi.
- **Day 4A km split:** the mapped path puts Nenoue Pass about 9.8 km after Nagiso Stn and 4.2 km before Nojiri. The planner still says 6 + 9 km (pass at 14 km, `lunchKm:14`). The total of 23 km is unchanged. Ask the owner before changing it.
- **Day 5 paths** are OSM routing guesses, not a mapped trail. The PDFs, `data/trail_data.json` and the KML files predate the path work and still use the old stop positions.
- **Aka Bus at Usui Pass:** it only runs down the pass and is cancelled in fog (`weather:true`).
