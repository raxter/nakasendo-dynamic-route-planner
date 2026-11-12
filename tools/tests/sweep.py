"""Regression sweep: every day × every 7 minutes. Fails on any JS error or if the option-card height changes (judder).
Run from repo root: python3 tools/tests/sweep.py [page]   (default: src/planner.html)"""
import asyncio, sys
from pathlib import Path
from playwright.async_api import async_playwright
ROOT = Path(__file__).resolve().parents[2]
PAGE = (ROOT / (sys.argv[1] if len(sys.argv) > 1 else "src/planner.html")).as_uri()
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={"width":1000,"height":1000})
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.route("https://**/*", lambda r: r.abort())          # offline: fonts/leaflet not needed for the sketch map
        await pg.goto(PAGE); await pg.wait_for_timeout(300)
        hs = set()
        for day in ["d2","d3","d4","d5","d6","d7"]:
            await pg.click(f'.chip[data-d="{day}"]')
            for t in range(360, 1201, 7):
                await pg.eval_on_selector('#time', f'el => {{ el.value = {t}; el.dispatchEvent(new Event("input")); }}')
                hs.add(await pg.evaluate("() => document.getElementById('fwd').offsetHeight"))
        print("card heights", hs, "errors", errs[:3])
        await b.close()
        sys.exit(1 if errs or len(hs) != 1 else 0)
asyncio.run(main())
