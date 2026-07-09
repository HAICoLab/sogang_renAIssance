"""파이프라인 배선: 입력 → 분석 → 검색 → 후보 생성 → 결과.

각 단계는 순수 함수라 하나씩 실제 구현으로 교체해도 이 배선은 그대로다.
"""

from __future__ import annotations

from analyze import analyze
from classify import classify
from retrieve import retrieve
from schema import BookInput, ClassificationResult, SimilarCase


def classify_book(book: BookInput) -> tuple[ClassificationResult, list[SimilarCase]]:
    """신규 도서 한 건을 끝까지 관통시켜 분류 결과를 만든다.

    반환: (분류 결과, 근거로 사용된 유사 사례)
    """
    analysis = analyze(book)          # ① 의미 분석
    cases = retrieve(analysis)        # ② 사례 검색 (RAG)
    result = classify(book, cases)    # ③ 후보 생성 + 근거 (Claude)
    return result, cases
