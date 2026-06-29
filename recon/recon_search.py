"""
Recon script: open Sogang library, run a search, capture internal API (XHR/fetch) calls.
Goal is purely investigative -- find which endpoints return book data (JSON?) and what fields they carry.
Run: conda run -n sgl_crawl python recon/recon_search.py "검색어"
"""
import sys
import json
import pathlib
from playwright.sync_api import sync_playwright

QUERY = sys.argv[1] if len(sys.argv) > 1 else "python"
OUT = pathlib.Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)

BASE = "https://library.sogang.ac.kr"

captured = []


def is_interesting(url: str) -> bool:
    bad = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".css", ".woff", ".woff2",
           ".ttf", ".ico", ".js", "google", "analytics", "gtm", "facebook")
    return not any(b in url.lower() for b in bad)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(locale="ko-KR",
                                  user_agent=("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                                              "Chrome/148.0.0.0 Safari/537.36"))
        page = ctx.new_page()

        def on_response(resp):
            url = resp.url
            ct = resp.headers.get("content-type", "")
            if not is_interesting(url):
                return
            if "json" in ct or "/api" in url.lower() or "search" in url.lower():
                rec = {"url": url, "status": resp.status, "content_type": ct, "method": resp.request.method}
                body = None
                if "json" in ct:
                    try:
                        body = resp.json()
                    except Exception:
                        try:
                            body = resp.text()[:2000]
                        except Exception:
                            body = "<unreadable>"
                rec["body_preview"] = (json.dumps(body, ensure_ascii=False)[:3000]
                                       if body is not None else None)
                captured.append(rec)
                print(f"[{resp.status}] {resp.request.method} {url}")

        page.on("response", on_response)

        print(f"== Opening homepage, searching for: {QUERY} ==")
        page.goto(BASE, wait_until="networkidle", timeout=60000)

        # Dump search-related inputs on the page
        inputs = page.eval_on_selector_all(
            "input, button[type=submit], form",
            "els => els.map(e => ({tag:e.tagName, type:e.type||'', name:e.name||'', "
            "id:e.id||'', placeholder:e.placeholder||'', action:e.action||''}))")
        (OUT / "homepage_inputs.json").write_text(
            json.dumps(inputs, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"saved homepage_inputs.json ({len(inputs)} elements)")

        # Try to locate a search box and submit a query
        try:
            box = page.locator("input[type=text], input[type=search]").first
            box.click(timeout=5000)
            box.fill(QUERY)
            box.press("Enter")
            page.wait_for_timeout(6000)
            print("current url after search:", page.url)
            (OUT / "after_search_url.txt").write_text(page.url, encoding="utf-8")
        except Exception as e:
            print("search box interaction failed:", e)

        page.wait_for_timeout(2000)
        page.screenshot(path=str(OUT / "search_result.png"), full_page=True)
        (OUT / "captured_api.json").write_text(
            json.dumps(captured, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n== captured {len(captured)} interesting responses -> out/captured_api.json ==")
        browser.close()


if __name__ == "__main__":
    main()
