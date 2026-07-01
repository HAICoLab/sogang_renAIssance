"""
Recon v2: directly hit the holdings search (소장자료검색) result page and capture
the internal API that returns book records (incl. call number / 청구기호).
Run: conda run -n sgl_crawl python recon/recon_toc.py "파이썬"
"""
import sys, json, pathlib
from playwright.sync_api import sync_playwright

QUERY = sys.argv[1] if len(sys.argv) > 1 else "파이썬"
OUT = pathlib.Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)
BASE = "https://library.sogang.ac.kr"
URL = f"{BASE}/search/toc/result?st=KWRD&si=TOTAL&q={QUERY}"

captured = []

def is_asset(url):
    return any(b in url.lower() for b in
               (".png",".jpg",".jpeg",".gif",".svg",".css",".woff",".ttf",".ico",
                "google","analytics","gtm","kakaocdn","daumcdn","deep-fountain"))

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(locale="ko-KR")
        page = ctx.new_page()

        def on_response(resp):
            url = resp.url
            if is_asset(url):
                return
            ct = resp.headers.get("content-type","")
            if "json" in ct or url.lower().endswith((".do",".json")) or "/api" in url.lower():
                rec = {"url": url, "method": resp.request.method, "status": resp.status, "ct": ct}
                try:
                    rec["post_data"] = resp.request.post_data
                except Exception:
                    rec["post_data"] = None
                try:
                    rec["body"] = resp.json()
                except Exception:
                    try: rec["body"] = resp.text()[:4000]
                    except Exception: rec["body"] = "<unreadable>"
                captured.append(rec)
                print(f"[{resp.status}] {resp.request.method} {url}")

        page.on("response", on_response)
        print("== goto:", URL)
        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(5000)
        print("final url:", page.url)

        # dump the rendered result HTML for inspection
        (OUT / "toc_result.html").write_text(page.content(), encoding="utf-8")
        page.screenshot(path=str(OUT / "toc_result.png"), full_page=True)
        (OUT / "toc_captured_api.json").write_text(
            json.dumps(captured, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"== captured {len(captured)} responses ==")

        # try to grab the first detail link
        links = page.eval_on_selector_all(
            "a[href*='detail'], a[href*='Detail']",
            "els => [...new Set(els.map(e=>e.href))].slice(0,5)")
        (OUT / "toc_detail_links.json").write_text(
            json.dumps(links, ensure_ascii=False, indent=2), encoding="utf-8")
        print("detail links sample:", links)
        browser.close()

if __name__ == "__main__":
    main()
