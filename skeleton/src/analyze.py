"""① 의미 분석 단계.

v0: 서지 정보에서 핵심 용어를 뽑는 휴리스틱 (API 호출 없음).
이후 고도화: Claude로 주제/학문분야 추출 + 임베딩.
"""

from __future__ import annotations

import re

from schema import Analysis, BookInput

# 검색 신호가 약한 조사/불용어 (v0 최소 목록)
_STOPWORDS = {"의", "를", "을", "이", "가", "은", "는", "와", "과", "에", "for", "the", "of", "a"}


def _tokenize(text: str) -> list[str]:
    """한글/영문/숫자 토큰만 남긴다."""
    tokens = re.findall(r"[0-9A-Za-z가-힣]+", text)
    return [t for t in tokens if len(t) > 1 and t.lower() not in _STOPWORDS]


def analyze(book: BookInput) -> Analysis:
    """도서 서지 정보 → 검색용 핵심 용어 집합."""
    terms: list[str] = []
    terms += book.keywords
    terms += book.toc
    terms += _tokenize(book.title)

    # 중복 제거(입력 순서 유지)
    seen: set[str] = set()
    unique: list[str] = []
    for t in terms:
        key = t.lower()
        if key not in seen:
            seen.add(key)
            unique.append(t)

    return Analysis(terms=unique)
