"""도서관 분류 Copilot — 시연용 웹 UI (Streamlit).

실행:
    streamlit run app.py

기존 CLI 파이프라인(src/)을 그대로 재사용한다. 새 로직은 없고, classify_book()의
결과를 사람이 보기 좋게 화면에 배치하기만 한다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# src/ 모듈은 `from pipeline import ...` 식의 평면 임포트를 쓰므로 경로에 추가한다.
SRC = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(SRC))

from pipeline import classify_book  # noqa: E402
from schema import BookInput  # noqa: E402

st.set_page_config(page_title="도서관 분류 Copilot", page_icon="📚", layout="centered")

# ── 시연용 예시 도서 프리셋 ──────────────────────────────────────
PRESETS: dict[str, dict] = {
    "차별하는 데이터 (애매한 사례)": {
        "title": "차별하는 데이터",
        "author": "(번역서)",
        "toc": "데이터 편향, 알고리즘 차별, 사회 불평등",
        "publisher": "",
        "is_translation": True,
        "keywords": "데이터, 차별, 알고리즘, 사회",
    },
    "파이썬 딥러닝 입문": {
        "title": "파이썬 딥러닝 입문",
        "author": "김철수",
        "toc": "신경망 기초, 텐서플로, 이미지 분류, 모델 배포",
        "publisher": "한빛미디어",
        "is_translation": False,
        "keywords": "파이썬, 딥러닝, 신경망, 머신러닝",
    },
    "조선왕조실록 읽기": {
        "title": "조선왕조실록 읽기",
        "author": "이영희",
        "toc": "조선 건국, 세종의 치세, 임진왜란, 실록의 편찬",
        "publisher": "역사비평사",
        "is_translation": False,
        "keywords": "조선, 역사, 왕조, 실록",
    },
    "빈 양식 (직접 입력)": {
        "title": "",
        "author": "",
        "toc": "",
        "publisher": "",
        "is_translation": False,
        "keywords": "",
    },
}


def _split(text: str) -> list[str]:
    """쉼표로 구분된 문자열 → 리스트(빈 항목 제거)."""
    return [t.strip() for t in text.split(",") if t.strip()]


# ── 헤더 ─────────────────────────────────────────────────────────
st.title("📚 도서관 분류 Copilot")
st.caption(
    "신규 도서의 서지 정보를 입력하면 → 유사 사례를 검색하고 → "
    "청구기호 후보와 판단 근거(XAI)를 제시합니다. **최종 판단은 사람 사서가 합니다.**"
)

# ── 입력 폼 ──────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("예시 도서")
    preset_name = st.selectbox("빠르게 불러오기", list(PRESETS.keys()))
    st.caption("고른 예시가 아래 입력란에 채워집니다. 값을 바꿔도 됩니다.")

preset = PRESETS[preset_name]

with st.form("book_form"):
    title = st.text_input("제목", value=preset["title"], placeholder="예: 차별하는 데이터")
    col1, col2 = st.columns(2)
    with col1:
        author = st.text_input("저자", value=preset["author"])
    with col2:
        publisher = st.text_input("출판사", value=preset["publisher"])
    toc = st.text_area("목차 / 주요 주제 (쉼표로 구분)", value=preset["toc"])
    keywords = st.text_area("키워드 (쉼표로 구분)", value=preset["keywords"])
    is_translation = st.checkbox("번역서", value=preset["is_translation"])
    submitted = st.form_submit_button("🔍 분류하기", use_container_width=True, type="primary")

# ── 실행 & 결과 ──────────────────────────────────────────────────
if submitted:
    if not title.strip():
        st.warning("제목을 입력해 주세요.")
        st.stop()

    book = BookInput(
        title=title.strip(),
        author=author.strip() or None,
        toc=_split(toc),
        publisher=publisher.strip() or None,
        is_translation=is_translation,
        keywords=_split(keywords),
    )

    with st.spinner("유사 사례 검색 후 Claude가 청구기호 후보를 분석 중…"):
        result, cases = classify_book(book)

    # ① 검색된 유사 사례
    st.subheader("🔎 검색된 유사 사례")
    if cases:
        for c in cases:
            note = f" · _{c.librarian_note}_" if c.librarian_note else ""
            st.markdown(
                f"- **「{c.title}」** → `{c.call_number}` ({c.category}) "
                f"— 유사도 `{c.similarity}`{note}"
            )
    else:
        st.info("겹치는 유사 사례를 찾지 못했습니다.")

    st.divider()

    # ② 청구기호 후보
    st.subheader("📚 청구기호 후보")
    if not result.candidates:
        st.error("후보를 생성하지 못했습니다.")
        st.stop()

    for i, cand in enumerate(result.candidates, 1):
        rank = "✅ 추천" if i == 1 else f"대안 {i - 1}"
        with st.container(border=True):
            st.markdown(f"**[{rank}]  `{cand.call_number}`  {cand.category}**")
            st.progress(
                min(max(cand.confidence, 0.0), 1.0),
                text=f"적합도 {cand.confidence:.2f}",
            )
            st.markdown(cand.reasoning)
            if cand.similar_refs:
                st.caption("참고 사례: " + ", ".join(cand.similar_refs))

    top = result.candidates[0]
    st.success(f"추천 청구기호(사서 검토 필요): **{top.call_number}  {top.category}**")
