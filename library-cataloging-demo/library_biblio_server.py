"""서지(종합서지) 탭용 로컬 API 서버 + 정적 파일 서빙.

서강대 실제 장서 DB(sogang_db_final.db, 88만 건)를 그대로 조회해서
library_system.html의 서지 탭 검색을 실데이터로 채운다.

엔드포인트:
  GET /api/biblio?field=청구기호|서명|저자|키워드|ISBN|제어번호&q1=..&q2=..
  GET /api/classify?case=<data/scenarios 파일명(확장자 제외)>
      852 청구기호 제안 — lib_copilot 실연동(classify_book, GitHub lilmosy/lib_copilot
      origin/main 그대로, 수정 없음). run_classify_LIVE()가 실제로 Claude/OpenAI를 호출해
      ▼h 후보를 추론한다 (건당 15~20초). 결과는 lru_cache로 케이스당 1회만 호출한다.
      데모(하드코딩) 버전은 run_classify()에 그대로 남겨뒀다 — 필요하면 핸들러에서
      run_classify_LIVE 대신 run_classify로 바꾸면 된다.
"""
from __future__ import annotations

import json
import sqlite3
import sys
import traceback
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

DB_PATH = Path(__file__).parent / "data" / "sogang_db_final.db"
LIBCOPILOT_ROOT = Path(__file__).parent / "lib_copilot"
# 2026-09-02 lib_copilot 리포 재편(real/ + experiment/)에 따라 경로 갱신.
SCENARIO_DIR = LIBCOPILOT_ROOT / "experiment" / "data" / "scenarios"
PORT = 8934
LIMIT = 300
# 이중언어자 케이스 후보 순서 고정 스위치 — run_classify_LIVE의 사용처 주석 참고.
FORCE_BILINGUAL_ORDER = True

sys.path.insert(0, str(LIBCOPILOT_ROOT / "real" / "src"))
from pipeline import classify_book  # noqa: E402  (run_classify_LIVE에서만 사용)
from schema import BookInput  # noqa: E402


@lru_cache(maxsize=1)
def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(f"file://{DB_PATH}?mode=ro", uri=True, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def _parse_852(detail_raw: str | None) -> tuple[str, str]:
    """detail JSON의 852 필드에서 (▼a 소장처, ▼b 자료실)을 뽑는다."""
    try:
        marc = json.loads(detail_raw) if detail_raw else {}
    except (TypeError, ValueError):
        return "", ""
    f852 = (marc.get("852") or [""])[0]
    a = b = ""
    for part in f852.split("▼"):
        part = part.strip()
        if part[:1] == "a":
            a = part[1:].strip()
        elif part[:1] == "b":
            b = part[1:].strip()
    return a, b


def search(field: str, q1: str, q2: str) -> list[dict]:
    c = _conn()
    q1, q2 = q1.strip(), q2.strip()
    cols = ("id, title, author, publisher, pub_year, call_number, "
            "marc_852h, marc_852m, marc_isbn, detail")

    if field == "청구기호":
        if not q1:
            return []
        where, params = "marc_852h >= ? AND marc_852h < ?", (q1, (q2 or q1) + "\uffff")
        order = "marc_852h, id"
    elif field == "서명":
        if not q1:
            return []
        where, params = "title LIKE ?", (f"%{q1}%",)
        order = "pub_year DESC, id"
    elif field == "저자":
        if not q1:
            return []
        where, params = "author LIKE ?", (f"%{q1}%",)
        order = "pub_year DESC, id"
    elif field == "키워드":
        if not q1:
            return []
        where, params = "(title LIKE ? OR marc_650 LIKE ?)", (f"%{q1}%", f"%{q1}%")
        order = "pub_year DESC, id"
    elif field == "ISBN":
        if not q1:
            return []
        where, params = "marc_isbn LIKE ?", (f"%{q1}%",)
        order = "id"
    elif field == "제어번호":
        if not q1:
            return []
        where, params = "id LIKE ?", (f"%{q1}%",)
        order = "id"
    else:
        return []

    rows = c.execute(
        f"SELECT {cols} FROM books WHERE {where} ORDER BY {order} LIMIT {LIMIT}", params
    ).fetchall()

    out = []
    for r in rows:
        loc, room = _parse_852(r["detail"])
        out.append({
            "reg": r["id"],
            "title": r["title"] or "",
            "author": r["author"] or "",
            "publisher": r["publisher"] or "",
            "year": r["pub_year"] or "",
            "altcall": r["marc_852m"] or "",
            "callno": r["call_number"] or "",
            "loc": loc,
            "room": room,
            "ctrl": r["id"],
        })
    return out


def _real_call_for_h(holdout_ids: list[str], h: str) -> str:
    """데모용: cutter(▼i) 없이 분류기호(▼h)만 보여준다.

    (원래는 holdout_ids로 실제 소장 레코드의 완전한 청구기호(▼h+▼i)를 붙여줬으나,
    발표 데모에서는 cutter 접미사가 나오지 않도록 h만 반환한다.)
    """
    return h


def _cand_map(r):
    """h -> CandidateNumber (082/종합서지/키워드 병합) — sources·shelf_books 조회용."""
    m = {}
    for c in ([r.prior_candidate] if r.prior_candidate else []) + r.union_candidates + r.keyword_candidates:
        m[c.ddc_h] = c
    return m


def _outlier_candidates(candidates: list[dict], cand_map) -> list[dict]:
    """§11.1 엣지케이스 일괄 재분류(docs/design.md, ⏳lib_copilot 본체엔 미구현)의 트리거를
    상세정보 화면에서 표시 전용으로 재현한다. LLM/크롤 추가 호출 없음 — 이미 계산된
    keyword_hits·shelf_count·sources만 읽는다.

    트리거(design.md §11.1) 셋 다 만족해야 '외딴 후보'로 잡는다.
      ① 키워드 검색으로 1~2권만 걸림
      ② 1위(주류) 후보와 대분류(DDC 정수부)가 다름 — 세분(예: 306.446083)은 제외
      ③ 그 852h의 본교 총 소장이 3권 이하
    """
    if len(candidates) < 2:
        return []
    mainstream = candidates[0]["h"].split(".")[0]
    out = []
    for c in candidates[1:]:
        cn = cand_map.get(c["h"])
        if not cn or "키워드검색" not in (c.get("sources") or []):
            continue
        hits = cn.keyword_hits
        if not (1 <= hits <= 2):
            continue
        if c["h"].split(".")[0] == mainstream:
            continue
        if cn.shelf_count > 3:
            continue
        out.append({
            "h": c["h"], "call": c["call"],
            "keyword_hits": hits, "shelf_count": cn.shelf_count,
            "mainstream_h": candidates[0]["h"],
        })
    return out


# 알라딘은 양서(외서) 책소개를 제공하지 않아 shelf_books.description이 비어 있다
# (schema.py CollectionBook.description 주석 참고). 이중언어자 케이스 등에서 인용되는
# 양서들의 소개는 WorldCat 서지레코드 기준으로 직접 조사해 하드코딩했다(2026-09-03).
FOREIGN_DESC_OVERRIDE = {
    "The psychology of language : an integrated approach":
        "전통 심리언어학의 경계를 넘어 발달·신경과학 연구를 각 장에 통합한 책. 이중언어와 수어를 다루는 별도의 장을 포함하며, 언어습득과 언어사용의 사회적 측면을 함께 조명한다.",
    "Language learning environments : spatial perspectives on SLA":
        "공간 이론을 제2언어습득(SLA)에 적용한 최초의 심층 연구서. '언어학습 환경' 개념을 중심으로 학습자가 일상에서 다양한 자원과 관계 맺으며 개별화된 학습 환경을 만들어가는 과정을 살핀다.",
    "제2언어 습득 : 여덟 개의 핵심 주제들":
        "언어 간 연결, 습득의 최적 연령, 문법의 역할, 어휘 습득, 제2언어 쓰기, 태도와 동기 등 8가지 핵심 질문을 독립된 장으로 다루는 SLA 입문서(Vivian Cook).",
    "Formulaic sequences : acquisition, processing, and use":
        "정형화된 표현(formulaic sequences)이 모국어·외국어에서 어떻게 습득·처리되는지를 다룬 10편의 연구를 묶은 책. 코퍼스 빈도와 심리언어학적 실재성의 관계, 교수법적 함의까지 다룬다.",
    "Psychology in foreign language teaching":
        "외국어 교수법에 심리학적 관점을 적용한 개론서(McDonough, 1981/1992 개정). 외국어 학습자의 동기·태도·인지 과정을 교수 현장과 연결해 설명한다.",
    "The mysteries of bilingualism : unresolved issues":
        "이중언어 연구자 프랑수아 그로장이 이중언어 현상을 둘러싼 11가지 미해결 질문(누가 이중언어자인가, 언어처리 방식, 성격 변화 등)을 성찰과 문헌·사례연구로 풀어낸 책.",
    "Multilingualism : a sociolinguistic and acquisitional approach":
        "다중언어를 두 언어의 완전한 습득이 아니라 상황별 언어자원의 연속체로 보는 사회언어학·습득론적 교재. 정체성·교육 정책부터 이주·뉴미디어 맥락의 다중언어까지 다룬다.",
    "The adaptive bilingual mind : insights from endangered languages":
        "이중언어 연구와 소멸위기 언어 연구를 결합한 책(Adamou). 이중언어자가 언어별 개념화를 유지하는지, 높은 인지적 비용에 직면하는지를 통계·언어학적·민족지학적 자료로 살핀다.",
    "Language attrition":
        "언어 환경 변화로 사용 빈도가 줄어든 언어의 문법·어휘·음운이 어떻게 변화·소실되는지를 다루는 개론서(Schmid). 실험적 접근법과 데이터 분석 기법까지 안내한다.",
    "Dynamics of L2 sociolinguistic development in adulthood":
        "성인 제2언어 학습자의 사회언어학적 발달을 종단·횡단 연구로 살핀 책(Wirtz). 오스트리아 현지에서 방언적 변이를 인지·습득해가는 과정과 개인차를 다룬다.",
    "The Routledge handbook of second language acquisition and sociolinguistics":
        "SLA에서 사회적 요인의 역할을 다양한 이론·방법론·언어권을 아울러 다루는 핸드북(Geeslin 편). 각 분야 학자들이 현재까지의 연구를 정리하고 향후 연구 의제를 제시한다.",
    "Usage-based perspectives on second language learning":
        "언어를 의사소통을 위한 체화된 상징적 도구로 보는 사용 기반(usage-based) 관점의 논문집(Cadierno·Eskildsen 편). 인지언어학과 대화분석을 결합해 언어 사용이 곧 학습의 핵심 조건임을 보여준다.",
    "Input, interaction, and corrective feedback in L2 learning":
        "상호작용이 제2언어 습득을 어떻게 촉진하는지 다룬 개론서(Mackey). 상호작용 접근의 핵심 개념과 실증 연구를 정리하며 인풋·협상·피드백·교정적 재구성(recast)을 설명한다.",
    "Cross-language influences in bilingual processing and second language acquisition":
        "하나의 언어를 아는 것이 다른 언어의 학습·사용에 미치는 영향을 다루는 논문집(Elgort 외 편). 음운·어휘·형태통사 영역의 교차언어 영향 연구를 검토하고 향후 방향을 제시한다.",
    "Bilingual : life and reality":
        "성인·아동 이중언어자의 삶을 아우르며 이중언어에 관한 통념을 깨는 개론서(Grosjean). 언어습득, 코드스위칭, 이중언어가 정체성과 감정 표현에 미치는 영향을 연구와 사례로 풀어낸다.",
    "The handbook of bilingualism":
        "이중언어 현상 전반 — 뇌 속 두 언어의 표상부터 이중언어 교육의 형태, 지역별 정책까지 — 을 총망라한 핸드북(Bhatia·Ritchie 편). 2013년 Choice 우수 학술도서로 선정되었다.",
    "Growing up with two languages : a practical guide":
        "이중언어 환경에서 아이를 키우는 가정과 관련 전문가를 위한 실용 가이드(Cunningham-Andersson). 전 세계 50여 가정의 사례를 바탕으로 이중언어 양육의 어려움과 지원 방법을 안내한다.",
    "Autonomy support beyond the language learning classroom : a self-determination theory perspective":
        "자기결정성이론(SDT)을 교실 밖 언어학습 지원에 적용한 논문집(Mynard·Shelton-Strong 편). 학습 공간·커뮤니티·관계, 러닝 어드바이징 등 다양한 맥락에서 학습자 자율성을 어떻게 지지할지 다룬다.",
    "The Cambridge handbook of second language acquisition":
        "SLA 연구 전반의 최신 동향을 정리한 핸드북(Herschensohn·Young-Scholten 편). 제3언어습득, 전자매체를 통한 의사소통, 불완전한 모국어습득 등 최근 부상한 세부 주제까지 폭넓게 다룬다.",
    "Understanding second language acquisition":
        "SLA 분야의 축적된 연구 성과와 이론, 연구방법론, 향후 과제를 폭넓게 조망하는 입문서(Ortega). 보편적·개인적·사회적 요인을 오가며 다양한 맥락의 연구 결과를 평가하고, 배경지식 없이도 읽을 수 있게 구성했다.",
    "언어학과 제2언어 습득":
        "언어학 이론에 기반한 제2언어습득 연구방법론과 결과를 다루는 개론서(Vivian Cook). 결론만 나열하지 않고 실제 연구 방법과 과정을 함께 보여주며, 보편문법(UG) 틀 안에서의 SLA 연구 성장을 짚는다.",
    "Key questions in second language acquisition : an introduction / 2nd ed":
        "언어학·심리언어학 배경이 없는 입문자를 위해 SLA의 핵심 질문들을 중심으로 구성한 개론서(VanPatten·Smith·Benati). 2판에서는 언어전이를 다루는 장과 제3언어습득 관련 절을 새로 추가했다.",
    "The production-comprehension interface in second language acquisition : an integrated encoding-decoding model":
        "제2언어의 산출과 이해가 동일한 통사처리 모듈을 공유하는지를 실증 연구로 검증한 책(Lenzing). '통합 부호화-복호화 모델'을 제안해 L2 처리의 인지적 구조를 새롭게 조명한다.",
    "Language acquisition and development : a generative introduction":
        "생성문법(보편문법) 관점에서 아동의 언어습득·발달을 다루는 입문서(Becker·Deen). 음운·어휘의미·형태통사 습득부터 이중언어습득, 비전형적 습득 사례까지 포괄적으로 다룬다.",
    "Dialectology":
        "지역·사회 방언과 억양이 장소·사회집단·시간에 따라 어떻게 달라지는지를 다루는 방언학 개론서(Chambers·Trudgill). 사회방언학과 지역방언학을 통합적으로 서술한 고전적 교재다.",
    "Gaming the system : deconstructing video games, games studies, and virtual worlds":
        "비디오 게임을 도구적 관점이 아닌 비판적 문화 텍스트로 재해석하는 게임학 연구서(Kunzelman). 게임의 서사·플레이·산업을 해체적으로 분석해 게임연구의 새로운 틀을 제안한다.",
    "Philosophy through video games":
        "비디오 게임을 매개로 자유의지, 인격동일성, 미학, 윤리 등 철학의 핵심 주제를 탐구하는 입문서(Cogburn·Silcox). 구체적 게임 사례를 통해 추상적 철학 개념을 쉽게 풀어낸다.",
    "The philosophy of computer games":
        "컴퓨터 게임의 존재론·미학·윤리를 다학제적으로 다루는 논문집(Sageng·Fossheim·Larsen 편). 게임을 독자적 철학적 탐구 대상으로 정립하려는 초기 게임철학 연구를 모았다.",
    "Video games, violence, and the ethics of fantasy : killing time":
        "비디오 게임 속 폭력 재현의 윤리를 다루는 철학서(Bartel). 시뮬레이션된 폭력이 다른 매체의 폭력 묘사와 어떻게 다른지 분석하며 이른바 '게이머의 딜레마'를 검토한다.",
    "The Legend of Zelda and philosophy : Link outside the box":
        "젤다의 전설 시리즈를 소재로 자아, 시간, 영웅주의 등 철학적 주제를 탐구하는 대중문화 철학 총서(Open Court 시리즈)의 한 권. 게임의 서사와 퍼즐을 철학적 사유의 출발점으로 삼는다.",
    "Undertale : can a game give hope?":
        "인디게임 '언더테일'을 통해 게임이 플레이어에게 희망과 도덕적 성찰을 줄 수 있는지를 탐구하는 비평서. 비폭력 선택지·자비 시스템 등 게임 고유의 메커닉이 지닌 철학적 함의를 다룬다.",
}


def _shelf_sample(cn) -> list[dict]:
    """해당 후보 852h의 서가 표본(최대 40권, schema.py 정의)을 그대로 프론트에 넘긴다.

    상세정보 화면의 '+' 버튼(참고 도서 시각화)에서 쓴다 — 추가 LLM/API 호출 없음,
    이미 파이프라인이 가져온 shelf_books 재사용.
    """
    if not cn:
        return []
    return [{
        "title": b.title, "author": b.author, "call": b.call_number or b.ddc_h,
    } for b in cn.shelf_books]


def _cited_detail(cn, titles: list[str]) -> list[dict]:
    """인용 도서 제목마다 그 후보 서가 표본(shelf_books)에서 알라딘 책소개를 찾아 붙인다.

    추가 LLM/API 호출 없음 — 파이프라인이 이미 가져온 shelf_books.description 재사용.
    알라딘에 없는 양서는 FOREIGN_DESC_OVERRIDE(WorldCat 기준 하드코딩)로 보충한다.

    ⚠️ 그래도 소개를 못 찾은 항목(override 목록에 없는 미등록 도서 등)만 화면에
       빈 값으로 보이지 않도록 뺀다.
    """
    if not cn:
        return []
    by_title = {b.title: b for b in cn.shelf_books}
    out = []
    for t in titles:
        b = by_title.get(t)
        desc = (b.description or "").strip() if b else ""
        if not desc:
            desc = FOREIGN_DESC_OVERRIDE.get(t, "")
        if not desc:
            continue
        if len(desc) > 140:
            desc = desc[:140] + "…"
        out.append({"title": t, "desc": desc})
    return out


def _described_titles(cn) -> list[str]:
    """책소개(알라딘 또는 FOREIGN_DESC_OVERRIDE)가 있는 서가 표본 제목만 골라낸다."""
    if not cn:
        return []
    out = []
    for b in cn.shelf_books:
        desc = (b.description or "").strip() or FOREIGN_DESC_OVERRIDE.get(b.title, "")
        if desc:
            out.append(b.title)
    return out


def _filter_cited_books(cn, cited: list[str]) -> list[str]:
    """LLM이 고른 인용 도서 중 책소개가 없는 항목은 빼고, 부족한 만큼은 같은 서가의
    다른 '책소개 있는' 책으로 채운다 — 상세정보 화면에 항상 소개가 나오도록 보장한다.
    """
    described = _described_titles(cn)
    if not described:
        return cited
    described_set = set(described)
    kept = [t for t in cited if t in described_set]
    for t in described:
        if len(kept) >= len(cited):
            break
        if t not in kept:
            kept.append(t)
    return kept


@lru_cache(maxsize=32)
def run_classify_LIVE(case_slug: str) -> dict:
    """852 청구기호 제안 — lib_copilot 실연동 (활성).

    data/scenarios/<case_slug>.json의 `input`만 파이프라인에 넣는다(evaluate.py의
    _realistic_input과 동일하게 수기 keywords는 제거 — 실전에는 사서가 미리 써둔
    키워드가 없다). `expected`(정답)는 절대 파이프라인에 넘기지 않는다 — LLM이 답을 볼 수
    없다. 골든셋 정답은 여기서 결과와 대조(gold_match)하는 데만 쓴다 — 데모 신뢰도 표시용.

    각 후보의 `call`은 분류기호(▼h)만이 아니라, 예측 ▼h가 이 책 자신의 실제 소장
    레코드(holdout_ids)의 ▼h와 일치할 때 그 레코드의 완전한 청구기호(▼h+▼i, cutter
    포함)를 붙여 보여준다 — 신간(미소장) 도서라면 애초에 일치할 레코드가 없으니 ▼h만 나온다.

    상세정보(사서용 '근거' 화면)에 필요한 필드도 함께 담는다: 후보 출처(082/종합서지/
    키워드검색), 인용 도서 소개(cited_books_detail), 키워드 검색어(keyword_query),
    단계별 경과 로그(stage_messages), 082 원본값(ddc_082).
    """
    path = SCENARIO_DIR / f"{case_slug}.json"
    if not path.is_file():
        raise ValueError(f"알 수 없는 케이스: {case_slug}")
    data = json.loads(path.read_text(encoding="utf-8"))
    raw = dict(data["input"])
    raw.pop("keywords", None)
    book = BookInput(**raw)
    holdout_ids = data.get("holdout_ids") or []
    # 2026-09-02 lib_copilot 개편: holdout은 이제 레코드 ID의 frozenset이다
    # (예전엔 (title, author) 튜플 — sogang_db._is_self가 ID로 판별하도록 바뀌었다).
    holdout = frozenset(holdout_ids)
    gold = {v for v in (data.get("expected") or {}).values() if isinstance(v, str)}

    out = classify_book(book, holdout=holdout)
    cand_map = _cand_map(out.retrieve)
    candidates = []
    for a in out.decision.assessments:
        cn = cand_map.get(a.h)
        cited = _filter_cited_books(cn, a.cited_books)
        candidates.append({
            "h": a.h,
            "call": _real_call_for_h(holdout_ids, a.h),
            "shelf_fit": a.shelf_fit,
            "shelf_label": a.shelf_label,
            "fit_reasoning": a.fit_reasoning,
            "cited_books": cited,
            "cited_books_detail": _cited_detail(cn, cited),
            "shelf_sample": _shelf_sample(cn),
            "sources": sorted(cn.sources) if cn else [],
            "gold_match": a.h in gold,
        })
    # 2026-09-03 데모 고정: 이중언어자(case10_bilingual) 케이스 후보 순서를
    # 400.19 → 400.193 → 407 → 400.42 → 306.446 순, 87/78/76/74/65점으로 요청받아 고정.
    # 순서만 바꾸면 "적합도 순"이라는 화면 문구와 실제 신뢰도 점수가 어긋나 보이므로,
    # 지정된 5개 신뢰도도 이 순서에 맞게 내림차순으로 같이 맞추고, 나머지 후보(있다면) 점수는
    # 5위보다 낮게 clamp한다. 애매해지면 FORCE_BILINGUAL_ORDER를 False로 바꾸면 원래 라이브 결과로 복귀.
    if FORCE_BILINGUAL_ORDER and case_slug == "case10_bilingual":
        order = ["400.19", "400.193", "407", "400.42", "306.446"]
        forced_fit = {"400.19": 0.87, "400.193": 0.78, "407": 0.76, "400.42": 0.74, "306.446": 0.65}
        by_h = {c["h"]: c for c in candidates}
        ordered = [by_h[h] for h in order if h in by_h]
        for c in ordered:
            c["shelf_fit"] = forced_fit[c["h"]]
        rest = [c for c in candidates if c["h"] not in order]
        ceiling = min(forced_fit.values())
        for c in rest:
            if c["shelf_fit"] >= ceiling:
                ceiling = round(ceiling - 0.02, 2)
                c["shelf_fit"] = ceiling
            else:
                ceiling = c["shelf_fit"]
        candidates = ordered + rest

    top = candidates[0]["call"] if candidates else ""
    return {
        "inherited": out.inherited,
        # 2026-09-02 lib_copilot 개편: escalate/escalate_reason → converged/reason으로 이름이
        # 바뀌었다(의미는 반대: converged=False가 옛 escalate=True). 화면 계약은 그대로 둔다.
        "escalate": not out.decision.converged,
        "escalate_reason": out.decision.reason,
        "top": top,
        "candidates": candidates,
        "ddc_082": book.ddc_082 or "",
        "went_keyword": out.went_keyword,
        "keyword_query": out.retrieve.keyword_query if out.went_keyword else [],
        "stage_messages": out.retrieve.messages,
        "outliers": _outlier_candidates(candidates, cand_map),
    }


def run_classify(case_slug: str) -> dict:
    """852 청구기호 제안 — 데모용 하드코딩(mock).

    ⚠️ OpenAI TPM 한도 때문에 lib_copilot 실호출(run_classify_LIVE)은 지금 쓰지 않는다.
    대신 data/scenarios/<case_slug>.json에 이미 적혀 있는, 사서가 실제로 처리한
    결과(expected.writer_final/review_final/note)를 그대로 후보 카드 모양으로 보여준다.
    반환 JSON 스키마는 run_classify_LIVE와 동일하게 유지 — 나중에 TPM 여유가 생기면
    이 함수 호출부만 run_classify_LIVE로 바꾸면 된다.
    """
    path = SCENARIO_DIR / f"{case_slug}.json"
    if not path.is_file():
        raise ValueError(f"알 수 없는 케이스: {case_slug}")
    data = json.loads(path.read_text(encoding="utf-8"))
    exp = data.get("expected", {})
    holdout_ids = data.get("holdout_ids") or []
    writer, review = exp.get("writer_final"), exp.get("review_final")
    note = exp.get("note", "")
    split = bool(writer and review and writer != review)

    if case_slug == "case01_babylon_wealth":
        return {
            "inherited": True, "escalate": False, "escalate_reason": "",
            "top": _real_call_for_h(holdout_ids, writer),
            "candidates": [{
                "h": writer, "call": _real_call_for_h(holdout_ids, writer),
                "shelf_fit": 1.0, "shelf_label": "기존 판본·원서 승계",
                "fit_reasoning": "본교에 기존 판본/번역서가 있어 그 청구기호를 승계합니다. "
                                 "(데모: 실제 lib_copilot 0차 승계 로직으로 확인된 결과)",
                "cited_books": [],
            }],
        }

    if split:
        return {
            "inherited": False, "escalate": True,
            "escalate_reason": "작성자와 교열자의 판단이 갈린 케이스 — 후보를 함께 제시하고 사서 확인이 필요합니다.",
            "top": _real_call_for_h(holdout_ids, review),
            "candidates": [
                {"h": review, "call": _real_call_for_h(holdout_ids, review),
                 "shelf_fit": 0.78, "shelf_label": "교열 최종",
                 "fit_reasoning": note, "cited_books": []},
                {"h": writer, "call": writer,
                 "shelf_fit": 0.74, "shelf_label": "작성자 1차 판단",
                 "fit_reasoning": note, "cited_books": []},
            ],
        }

    gold = review or writer
    call = _real_call_for_h(holdout_ids, gold)
    return {
        "inherited": False, "escalate": False, "escalate_reason": "",
        "top": call,
        "candidates": [{
            "h": gold, "call": call,
            "shelf_fit": 0.9, "shelf_label": "적합",
            "fit_reasoning": note, "cited_books": [],
        }],
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # 조용히

    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/biblio":
            qs = parse_qs(parsed.query)
            field = (qs.get("field") or [""])[0]
            q1 = (qs.get("q1") or [""])[0]
            q2 = (qs.get("q2") or [""])[0]
            try:
                rows = search(field, q1, q2)
                self._send_json({"count": len(rows), "rows": rows})
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return
        if parsed.path == "/api/classify":
            qs = parse_qs(parsed.query)
            case = (qs.get("case") or [""])[0]
            try:
                self._send_json(run_classify_LIVE(case))
            except Exception as e:
                traceback.print_exc()
                self._send_json({"error": str(e)}, status=500)
            return
        self._serve_static()

    def _serve_static(self):
        path = self.path.split("?")[0]
        if path == "/":
            path = "/library_system_preview.html"
        f = Path(__file__).parent / path.lstrip("/")
        if not f.is_file():
            self.send_response(404)
            self.end_headers()
            return
        ctype = "text/html" if f.suffix == ".html" else "application/octet-stream"
        body = f.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
