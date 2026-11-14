"""Live-map test with mocked GPS + clock. Needs Leaflet locally: `npm i leaflet@1.9.4` in the repo root (node_modules is git-ignored).
Run from repo root after tools/build_live.py:  python3 tools/tests/test_live.py"""
import asyncio, datetime, sys
from pathlib import Path
from playwright.async_api import async_playwright
ROOT = Path(__file__).resolve().parents[2]
LJS = (ROOT / "node_modules/leaflet/dist/leaflet.js").read_text(); LCSS = (ROOT / "node_modules/leaflet/dist/leaflet.css").read_text()
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width":390,"height":844}, is_mobile=True, has_touch=True, timezone_id="Asia/Tokyo",
                                  geolocation={"latitude":35.5900, "longitude":137.6010, "accuracy":25}, permissions=["geolocation"])
        pg = await ctx.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        async def route(r):
            u = r.request.url
            if "leaflet.min.js" in u: await r.fulfill(body=LJS, content_type="application/javascript")
            elif "leaflet.min.css" in u: await r.fulfill(body=LCSS, content_type="text/css")
            else: await r.abort()                                       # map tiles are blocked in the sandbox: grey map is expected
        await pg.route("https://**/*", route)
        await pg.clock.set_fixed_time(datetime.datetime(2026,11,16,11,20, tzinfo=datetime.timezone(datetime.timedelta(hours=9))))
        await pg.goto((ROOT / "index.html").as_uri()); await pg.wait_for_timeout(400)
        await pg.click('.chip[data-d="d4"]'); await pg.click("#zlive"); await pg.wait_for_timeout(800)
        await pg.evaluate("() => { LLAYER.eachLayer(l => { if (l.getPopup && l.getPopup()) l.openPopup(); }); }"); await pg.wait_for_timeout(200)
        await pg.click(".live-set"); await pg.wait_for_timeout(300)
        r = await pg.evaluate("() => [S.day, S.km.toFixed(2), fmt(S.t), S.pace, fmt(startOf(D())), document.getElementById('liveToast').textContent]")
        print(r, errs); await pg.screenshot(path=str(ROOT / "live_test.png"))
        # drag the squirrels well off the trail: mid-drag they must still sit on it (within 30 m)
        bb = await pg.locator(".leaflet-marker-icon.leaflet-marker-draggable").first.bounding_box()
        x0, y0 = bb["x"] + bb["width"] * .3, bb["y"] + bb["height"] * .45   # mum herself (the icon is wide for the height badge)
        await pg.mouse.move(x0, y0); await pg.mouse.down(); await pg.mouse.move(x0 - 120, y0 + 60, steps=8)
        off = await pg.evaluate("() => { let m; LLAYER.eachLayer(l => { if (l.dragging && l.dragging.enabled()) m = l; }); const p = m.getLatLng(); return snapAnyDay([p.lat, p.lng]).dist; }")
        # a GPS fix arriving mid-drag (every second or so on a real phone) must not drop the squirrels from under the finger
        assert await pg.evaluate("() => LDRAG"), "the drag never started (missed the squirrels?)"
        km0 = await pg.evaluate("() => S.km"); await ctx.set_geolocation({"latitude": 35.5905, "longitude": 137.6015, "accuracy": 20}); await pg.wait_for_timeout(300)
        await pg.mouse.move(x0 - 40, y0 - 80, steps=6)
        held = await pg.evaluate("km0 => [LDRAG, Math.abs(S.km - km0) > 0.01]", km0)
        await pg.mouse.up(); print("mid-drag distance from trail (m):", round(off, 1), "| drag survives a GPS fix:", held)
        # drag mum off the end of the walk onto the planned evening train: she must hop on (vehicle shown, clock on the ride)
        await pg.evaluate("() => { setFromPos(total(D())); sync(); render(); const j = journeyOf(D()).find(g => g.kind === 'ride'); LMAP.fitBounds([j.a, j.b], {padding:[90,90]}); }"); await pg.wait_for_timeout(400)
        sx, sy, tx, ty = await pg.evaluate("""() => { const r = document.getElementById('lmap').getBoundingClientRect(), j = journeyOf(D()).find(g => g.kind === 'ride');
            const a = LMAP.latLngToContainerPoint(llAt(D(), total(D()))), m = LMAP.latLngToContainerPoint(alongPoly([j.a, ...(j.via || []), j.b], .5)); return [a.x + r.left, a.y + r.top, m.x + r.left, m.y + r.top]; }""")
        bb = await pg.locator(".leaflet-marker-icon.leaflet-marker-draggable").first.bounding_box()
        gx, gy = bb["x"] + 26, bb["y"] + 50
        await pg.mouse.move(gx, gy); await pg.mouse.down(); await pg.mouse.move(gx + tx - sx, gy + ty - sy, steps=12)
        ride = await pg.evaluate("() => { const js = segAt(D(), S.t); return js ? js.kind : 'walk'; }")
        await pg.mouse.up(); print("dragged onto the evening train:", ride, errs)
        await b.close(); sys.exit(1 if errs or r[0] != "d4" or off > 30 or held != [True, True] or ride != "ride" else 0)
asyncio.run(main())
