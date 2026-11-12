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
        await b.close(); sys.exit(1 if errs or r[0] != "d4" else 0)
asyncio.run(main())
