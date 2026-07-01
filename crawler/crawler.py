"""
서강대 로욜라도서관 소장자료(도서) 메타데이터 크롤러.

- 소장자료검색 결과 페이지가 서버 렌더링 HTML이라 requests + BeautifulSoup만으로 충분.
- 로그인 불필요(검색결과/청구기호 공개).
- 여러 검색어로 나눠 수집하고 같은 책(서지ID 기준)은 중복 제거.

실행: conda run -n sgl_crawl python crawler.py
"""
import re
import csv
import time
import math
import pathlib
import requests
from bs4 import BeautifulSoup

import config

BASE = "https://library.sogang.ac.kr"
SEARCH = BASE + "/search/toc/result"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/148.0.0.0 Safari/537.36"),
}

CALLNO_RE = re.compile(r"\[([^\]]+)\]")          # 소장처 텍스트 안의 [청구기호]
BIBID_RE = re.compile(r"/search/detail/(\w+)")    # 상세 링크에서 서지ID


def _label_map(li):
    """<dl> 안의 dt(라벨) -> 바로 뒤 dd(값) 매핑. dd가 없는 라벨은 제외."""
    m = {}
    for dt in li.select("dl > dt.title"):
        nxt = dt.find_next_sibling()
        if nxt and nxt.name == "dd":
            m[dt.get_text(strip=True)] = nxt
    return m


def _clean(text):
    return re.sub(r"\s+", " ", (text or "")).strip()


def parse_item(li):
    """검색결과 <li> 한 건을 dict로 파싱."""
    m = _label_map(li)

    # 서명 + 상세 링크 + 서지ID
    title_dd = m.get("서명")
    title, detail_url, bibid = "", "", ""
    if title_dd:
        a = title_dd.find("a", href=True)
        if a:
            title = _clean(a.get_text())
            href = a["href"].split("?")[0]
            detail_url = BASE + href
            mb = BIBID_RE.search(href)
            bibid = mb.group(1) if mb else ""

    author = _clean(m["저자"].get_text()) if "저자" in m else ""
    publisher = _clean(m["출판사"].get_text()) if "출판사" in m else ""
    pubyear = _clean(m["출판년"].get_text()) if "출판년" in m else ""
    series = _clean(m["총서명"].get_text()) if "총서명" in m else ""
    mat_type = _clean(m["자료유형"].get_text()) if "자료유형" in m else ""

    # 소장처 정보: 위치/청구기호/대출상태가 여러 개일 수 있음
    locations, call_numbers, statuses = [], [], []
    hold = m.get("소장처 정보")
    if hold:
        for loc in hold.select("p.location"):
            full = _clean(loc.get_text(" "))
            status_el = loc.select_one(".availableBtn")
            status = _clean(status_el.get_text()) if status_el else ""
            # 위치 텍스트 = 전체에서 [청구기호]와 상태 문구 제거
            place = full
            cn = CALLNO_RE.search(full)
            if cn:
                call_numbers.append(_clean(cn.group(1)))
                place = place.replace("[" + cn.group(1) + "]", "")
            if status:
                place = place.replace(status, "")
            place = _clean(place)
            if place:
                locations.append(place)
            if status:
                statuses.append(status)

    sep = config.MULTI_SEP
    return {
        "서지ID": bibid,
        "제목": title,
        "저자": author,
        "출판사": publisher,
        "출판년": pubyear,
        "청구기호": sep.join(dict.fromkeys(call_numbers)),  # 중복 제거, 순서 유지
        "자료유형": mat_type,
        "총서명": series,
        "소장처": sep.join(locations),
        "대출상태": sep.join(statuses),
        "상세URL": detail_url,
    }


def fetch_page(session, keyword, pn):
    params = {"st": "KWRD", "si": "TOTAL", "q": keyword, "pn": pn}
    r = session.get(SEARCH, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")


def crawl():
    n_kw = len(config.KEYWORDS)
    quota = math.ceil(config.TARGET_TOTAL / n_kw)  # 검색어당 목표
    seen = set()
    rows = []

    with requests.Session() as session:
        for keyword in config.KEYWORDS:
            if len(rows) >= config.TARGET_TOTAL:
                break
            got = 0
            print(f"\n[검색어] {keyword!r} (목표 {quota}건)")
            for pn in range(1, config.MAX_PAGES_PER_KEYWORD + 1):
                if got >= quota or len(rows) >= config.TARGET_TOTAL:
                    break
                soup = fetch_page(session, keyword, pn)
                items = soup.select("ul.resultList li.items")
                if not items:
                    print(f"  p{pn}: 결과 없음 -> 다음 검색어")
                    break
                for li in items:
                    rec = parse_item(li)
                    if not rec["제목"]:
                        continue
                    key = rec["서지ID"] or (rec["제목"], rec["저자"])
                    if key in seen:
                        continue
                    seen.add(key)
                    rec["검색어"] = keyword
                    rows.append(rec)
                    got += 1
                    if got >= quota or len(rows) >= config.TARGET_TOTAL:
                        break
                print(f"  p{pn}: 누적 {len(rows)}건 (이 검색어 {got}건)")
                time.sleep(config.DELAY_SEC)

    return rows


def save_csv(rows):
    out = pathlib.Path(config.OUTPUT_CSV)
    out.parent.mkdir(parents=True, exist_ok=True)
    cols = ["검색어", "제목", "저자", "출판사", "출판년", "청구기호",
            "자료유형", "총서명", "소장처", "대출상태", "서지ID", "상세URL"]
    with out.open("w", newline="", encoding="utf-8-sig") as f:  # utf-8-sig: Excel 한글 호환
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    return out


def main():
    rows = crawl()
    out = save_csv(rows)
    print(f"\n완료: {len(rows)}건 저장 -> {out.resolve()}")
    # 청구기호가 비어있는 건수 리포트
    no_cn = sum(1 for r in rows if not r["청구기호"])
    print(f"청구기호 누락: {no_cn}건 / {len(rows)}건")


if __name__ == "__main__":
    main()
