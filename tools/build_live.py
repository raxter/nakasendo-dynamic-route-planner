"""Build index.html (the GitHub Pages live-map page) from src/planner.html + src/live_addon.js.
Run from the repo root:  python3 tools/build_live.py"""
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
src = (ROOT / "src/planner.html").read_text(encoding="utf-8")
addon = (ROOT / "src/live_addon.js").read_text(encoding="utf-8")
s = src
def rep(a, b):
    global s
    assert s.count(a) == 1, f"anchor not found exactly once ({s.count(a)}): {a[:70]}"
    s = s.replace(a, b)
rep('<title>Nakasendo Dynamic Route Planner</title>', '''<title>Nakasendo Dynamic Route Planner · live map</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<script>window.LF = window.L;   /* the planner uses L() for its timetables, so Leaflet is LF */</script>''')
rep('    <svg id="map" role="img"', '''    <div id="lmap" hidden></div>
    <div id="liveToast" class="livetoast" role="status" hidden></div>
    <svg id="map" role="img"''')
rep('''      <button type="button" id="ztrip" aria-label="Show whole trip" title="Whole trip">🗾</button>''',
    '''      <button type="button" id="ztrip" aria-label="Show whole trip" title="Whole trip">🗾</button>
      <button type="button" id="zlive" aria-label="Live map with your location" title="Live map with your location">🗺️<small>Live</small></button>
      <button type="button" id="zgps" aria-label="Show my location" title="Show my location" hidden>🎯</button>''')
rep("</style>", '''  #lmap{position:absolute;inset:0;z-index:1;isolation:isolate;background:#e9e4da}
  .legend{z-index:5}.zoom{z-index:6}
  /* the live/sketch switch says what it does, so the way back from the live map is obvious */
  .zoom #zlive{width:auto;min-width:36px;align-self:flex-end;padding:0 7px;display:flex;align-items:center;gap:3px;white-space:nowrap}
  .zoom #zlive small{font-size:11px;font-weight:800}
  .zoom #zlive.on{background:#fff4d6;border-color:#e5a83a}
  .legend.live{bottom:22px}
  .sq-icon{background:none;border:none;font-size:16px;line-height:18px;text-align:center;user-select:none;-webkit-user-select:none;-webkit-touch-callout:none}
  .elv-mark i{position:absolute;left:-4px;top:-4px;width:8px;height:8px;border-radius:50%;background:#fffdf8;border:1.6px solid #7a5c3e;box-sizing:border-box}
  .elv-mark.top i{left:-6px;top:-7px;width:0;height:0;border:6px solid transparent;border-bottom:10px solid #7a5c3e;border-top:0;border-radius:0;background:none}
  .elv-mark span{position:absolute;left:6px;top:-14px;white-space:nowrap;font-family:inherit;font-size:9px;font-weight:800;line-height:1;color:#5b4330;background:rgba(255,253,248,.8);border:1px solid #d8c6b0;border-radius:6px;padding:1px 3px}
  .elv-mark.top span{border-color:#7a5c3e}
  .elv-mark:not(.top) i{display:none}
  .elv-mark:not(.top):not(.stop) span{left:-14px;top:-18px}
  .elv-mark.stop span{left:9px;top:-19px;border-color:#b79b7c}
  .live-tip{font:inherit;font-size:11.5px;font-weight:700;color:#3b2f2a;padding:2px 6px;border-radius:8px}
  .live-tip.f{color:#2e8b3e;border-color:#2e8b3e}.live-tip.b{color:#c0700a;border-color:#e08a12}.live-tip.faded{opacity:.5 !important}
  .live-pop{font:inherit;font-size:13px;line-height:1.4}.live-pop .fine{font-size:11px;color:#7a6a5e}
  .live-set{appearance:none;margin:6px 0 4px;border:2px solid #1a73e8;background:#1a73e8;color:#fff;border-radius:999px;padding:6px 12px;font:inherit;font-weight:800;font-size:13px;cursor:pointer}
  .livetoast{position:absolute;left:50%;top:64px;transform:translateX(-50%);z-index:6;max-width:min(92%,520px);background:#2b231e;color:#fff;border-radius:14px;padding:8px 12px;font-size:12.5px;line-height:1.35;box-shadow:0 4px 14px rgba(0,0,0,.2)}
  .leaflet-container{font:inherit}
  .skypane{opacity:.4}   /* no CSS blur here: suspected of blanking the map on some Android phones */
  .qlab-icon{background:none;border:none}
  .qlab{position:absolute;transform:translate(-50%,-50%);white-space:nowrap;font-size:11.5px;font-weight:800;color:#7a5a40;text-shadow:0 0 2px #fbf6ec,0 0 4px #fbf6ec,0 0 6px #fbf6ec}
  .qlab small{font-size:10px;font-weight:700;color:#9a8270}
</style>''')
rep('$("zday").onclick = () => { fitDay(); render(); };', '$("zday").onclick = () => { if (LIVE) { LMAP.fitBounds(LF.latLngBounds(lineLL(D())).pad(.15)); return; } fitDay(); render(); };')
rep('$("ztrip").onclick = () => { fitTrip(); render(); };', r'''$("ztrip").onclick = () => { if (LIVE) { LMAP.fitBounds(LF.latLngBounds(ORDER.flatMap(k => lineLL(dayObj(k)))).pad(.05)); return; } fitTrip(); render(); };
$("zin").onclick = () => { if (LIVE) { LMAP.zoomIn(); return; } zoomAt([W/2,H/2], 1.5); };
$("zout").onclick = () => { if (LIVE) { LMAP.zoomOut(); return; } zoomAt([W/2,H/2], 1/1.5); };
$("zlive").onclick = () => { setLive(!LIVE); $("legend").classList.toggle("live", LIVE); };
$("zgps").onclick = () => { geoStart(); if (GEO) { LMAP.setView(GEO.ll, Math.max(LMAP.getZoom(), 15)); } else liveToast("Finding you… allow location if your browser asks."); };''')
rep("  renderText(fwd, back);\n  renderWx();\n}", "  renderText(fwd, back);\n  renderWx();\n  if (LIVE && !LDRAG) drawLive();\n}")
rep("/* ---------- start ---------- */", addon + "\n/* ---------- start ---------- */")
rep('''      <div class="mrow"><span>🌗 Daylight band</span>''', '''      <div class="mrow"><span>🗺️ Live map</span><div class="toggle" id="mBase" role="group" aria-label="Live map background"><button type="button" data-v="quiet">Quiet</button><button type="button" data-v="pale">Pale</button><button type="button" data-v="topo">Topo</button><button type="button" data-v="photo">Aerial</button><button type="button" data-v="osm">OSM</button></div></div>
      <div class="mrow"><span>🌗 Daylight band</span>''')
rep('''      <div class="fine">The daylight band shades''', '''      <div class="fine" id="mStat">Map tiles: open 🗺️ to check.</div>
      <div class="fine">The daylight band shades''')
rep('''const menuShow = on => { $("menu").hidden = !on; menuSync(); };''', '''const menuShow = on => { $("menu").hidden = !on; menuSync(); if (on && typeof statusLine === "function") statusLine(); };''')
rep('''  $("lgSky").hidden = !S.sky;''', '''  $("lgSky").hidden = !S.sky; document.querySelectorAll("#mBase button").forEach(b => b.setAttribute("aria-pressed", b.dataset.v === S.base ? "true" : "false"));''')
rep('''document.querySelectorAll("#mSky button").forEach(b => b.onclick''', '''document.querySelectorAll("#mBase button").forEach(b => b.onclick = () => { S.base = b.dataset.v; savePrefs(); menuSync(); if (LIVE) setBase(S.base); });
document.querySelectorAll("#mSky button").forEach(b => b.onclick''')
rep('<h2>How this works</h2>', '''<h2>How this works</h2>
      <p><b>🗺️ Live map:</b> swaps the sketch for a real map with your location as a blue dot. Pick its background in <b>☰</b>: <b>Quiet</b> shows only contours, lakes, rivers and the villages near the trail (from GSI's vector map); Pale, Topo and Aerial are GSI maps, and OSM is OpenStreetMap. Tap the dot → <b>Set position &amp; time to here</b>: the squirrels jump to the nearest point on the trail, the clock jumps to now, today's start time stays put and the pace is worked out from how far you've come. The trail line comes from OpenStreetMap (or straight lines, from ☰), so on the ground follow the signposts and your Walk Japan notes.</p>''')
rep('<input type="range" id="pace" min="12" max="45"', '<input type="range" id="pace" min="12" max="60"')
(ROOT / "index.html").write_text(s, encoding="utf-8")
print("built index.html", len(s), "bytes")
