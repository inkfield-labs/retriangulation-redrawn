"""Selection race check: a story whose partners fetch is slow must not draw over a newer selection.

Holds the partners/PP301.json request for 1.5 s, starts story 4 (Merrick to Snowdon), selects Sca Fell (PP92) 200 ms
later, releases the request, then expects Sca Fell's panel with no story box and no pair line.

Usage:  python -I scripts/check_race.py [URL]      (default http://localhost:8766/; exits non-zero on failure)
Needs:  pip install playwright && python -m playwright install --only-shell chromium
Writes: nothing
"""
import sys

from playwright.sync_api import sync_playwright


def main(url):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        held = []
        page.route("**/partners/PP301.json", lambda route: held.append(route))
        page.goto(url)
        page.wait_for_function("window.mapReady === true", timeout=120_000)
        page.evaluate("() => { story(3); }")  # not awaited: evaluate would wait for the held fetch
        page.wait_for_timeout(200)
        page.evaluate("() => { select('PP92', false); }")
        page.wait_for_timeout(1300)
        assert len(held) == 1, "the PP301 partners request was not held"
        held[0].continue_()
        page.wait_for_timeout(1500)
        got = page.evaluate("""({name: document.getElementById('d-name').textContent,
                                 story_hidden: document.getElementById('d-story').hidden,
                                 pair_lines: map.getSource('pair').serialize().data.type === 'Feature' ? 1 : 0,
                                 hash: location.hash})""")
        browser.close()
    ok = got == {"name": "Sca Fell", "story_hidden": True, "pair_lines": 0, "hash": "#PP92"}
    print(("PASS " if ok else "FAIL ") + str(got))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8766/")
