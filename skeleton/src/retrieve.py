"""② 사례 기반 검색 단계 (RAG).

v0: collection.json을 로드해 키워드 겹침 점수로 top-k를 고른다 (API/임베딩 없음).
이후 고도화: pgvector 임베딩 유사도 검색으로 교체 (이 함수 시그니처는 유지).
"""

from __future__ import annotations

import json
import re
from functools import lru_cache

from config import COLLECTION_PATH, TOP_K
from schema import Analysis, SimilarCase


@lru_cache(maxsize=1)
def _load_collection() -> list[dict]:
    with open(COLLECTION_PATH, encoding="utf-8") as f:
        return json.load(f)


def _terms_of(book: dict) -> set[str]:
    """장서 한 건에서 매칭용 용어 집합을 만든다."""
    raw = list(book.get("keywords", []))
    raw += re.findall(r"[0-9A-Za-z가-힣]+", book.get("title", ""))
    raw += re.findall(r"[0-9A-Za-z가-힣]+", book.get("category", ""))
    return {t.lower() for t in raw if len(t) > 1}


def retrieve(analysis: Analysis, top_k: int = TOP_K) -> list[SimilarCase]:
    """분석 용어와 장서를 비교해 유사 사례 top-k 반환."""
    query = {t.lower() for t in analysis.terms}
    if not query:
        return []

    scored: list[tuple[float, dict]] = []
    for book in _load_collection():
        book_terms = _terms_of(book)
        if not book_terms:
            continue
        overlap = len(query & book_terms)
        if overlap == 0:
            continue
        # Jaccard 유사도로 정규화(0~1)
        similarity = overlap / len(query | book_terms)
        scored.append((similarity, book))

    scored.sort(key=lambda x: x[0], reverse=True)

    return [
        SimilarCase(
            title=book["title"],
            call_number=book["call_number"],
            category=book["category"],
            similarity=round(sim, 3),
            librarian_note=book.get("librarian_note"),
        )
        for sim, book in scored[:top_k]
    ]
