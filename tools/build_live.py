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
      <button type="button" id="zlive" aria-label="Live map with your location" title="Live map with your location">🗺️</button>
      <button type="button" id="zgps" aria-label="Show my location" title="Show my location" hidden>🎯</button>''')
rep("</style>", '''  #lmap{position:absolute;inset:0;z-index:1;isolation:isolate;background:#e9e4da}
  .zoom,.legend{z-index:5}
  .legend.live{bottom:22px}
  .sq-icon{background:none;border:none;font-size:16px;line-height:18px;text-align:center}
  .live-tip{font:inherit;font-size:11.5px;font-weight:700;color:#3b2f2a;padding:2px 6px;border-radius:8px}
  .live-tip.f{color:#2e8b3e;border-color:#2e8b3e}.live-tip.b{color:#c0700a;border-color:#e08a12}.live-tip.faded{opacity:.5 !important}
  .live-pop{font:inherit;font-size:13px;line-height:1.4}.live-pop .fine{font-size:11px;color:#7a6a5e}
  .live-set{appearance:none;margin:6px 0 4px;border:2px solid #1a73e8;background:#1a73e8;color:#fff;border-radius:999px;padding:6px 12px;font:inherit;font-weight:800;font-size:13px;cursor:pointer}
  .livetoast{position:absolute;left:50%;top:10px;transform:translateX(-50%);z-index:6;max-width:min(92%,520px);background:#2b231e;color:#fff;border-radius:14px;padding:8px 12px;font-size:12.5px;line-height:1.35;box-shadow:0 4px 14px rgba(0,0,0,.2)}
  .leaflet-container{font:inherit}
</style>''')
rep('$("zday").onclick = () => { fitDay(); render(); };', '$("zday").onclick = () => { if (LIVE) { LMAP.fitBounds(LF.latLngBounds(D().pts.map(p => p.ll)).pad(.15)); return; } fitDay(); render(); };')
rep('$("ztrip").onclick = () => { fitTrip(); render(); };', r'''$("ztrip").onclick = () => { if (LIVE) { LMAP.fitBounds(LF.latLngBounds(ORDER.flatMap(k => dayObj(k).pts.map(p => p.ll))).pad(.05)); return; } fitTrip(); render(); };
$("zlive").onclick = () => { setLive(!LIVE); $("legend").classList.toggle("live", LIVE); };
$("zgps").onclick = () => { geoStart(); if (GEO) { LMAP.setView(GEO.ll, Math.max(LMAP.getZoom(), 15)); } else liveToast("Finding you… allow location if your browser asks."); };''')
rep("  renderText(fwd, back);\n}", "  renderText(fwd, back);\n  if (LIVE && !LDRAG) drawLive();\n}")
rep("/* ---------- start ---------- */", addon + "\n/* ---------- start ---------- */")
rep('<h2>How this works</h2>', '''<h2>How this works</h2>
      <p><b>🗺️ Live map:</b> swaps the sketch for a real Japanese topographic map (GSI, or OpenStreetMap / aerial photo from the layer button) with your location as a blue dot. Tap the dot → <b>Set position &amp; time to here</b>: the squirrels jump to the nearest point on the trail, the clock jumps to now, today's start time stays put and the pace is worked out from how far you've come. The trail is drawn as straight lines between stops, so follow the signposts and the map's own paths on the ground.</p>''')
rep('<input type="range" id="pace" min="12" max="45"', '<input type="range" id="pace" min="12" max="60"')
(ROOT / "index.html").write_text(s, encoding="utf-8")
print("built index.html", len(s), "bytes")
