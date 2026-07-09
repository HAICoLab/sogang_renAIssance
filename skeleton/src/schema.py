"""파이프라인 전 구간에서 오가는 데이터 계약(스키마).

각 모듈(analyze/retrieve/classify)은 여기 정의된 타입만 주고받는다.
내부 구현이 바뀌어도(휴리스틱→LLM, 키워드→벡터) 이 계약은 그대로 유지되는 것이 목표.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── ① 입력 ────────────────────────────────────────────────
class BookInput(BaseModel):
    """분류 대상 신규 도서의 서지 정보."""

    title: str
    author: str | None = None
    toc: list[str] = Field(default_factory=list, description="목차 / 주요 주제")
    publisher: str | None = None
    is_translation: bool = False
    keywords: list[str] = Field(default_factory=list)
    isbn: str | None = None


# ── ② 중간 결과물 ─────────────────────────────────────────
class Analysis(BaseModel):
    """의미 분석 결과 (v0: 키워드 휴리스틱 / 이후: LLM 주제 추출)."""

    terms: list[str] = Field(description="검색에 사용할 핵심 용어들")


class SimilarCase(BaseModel):
    """RAG 사례 검색 결과 한 건 (기존 장서/과거 분류 사례)."""

    title: str
    call_number: str
    category: str
    similarity: float = Field(description="0~1, 입력 도서와의 유사도")
    librarian_note: str | None = None


# ── ③ 출력 ────────────────────────────────────────────────
class Candidate(BaseModel):
    """청구기호 후보 하나 + 판단 근거(XAI)."""

    call_number: str = Field(description="DDC 청구기호, 예: 303.48")
    category: str = Field(description="분류 항목명, 예: 사회학")
    confidence: float = Field(description="적합도 0~1")
    reasoning: str = Field(description="왜 이 청구기호인지에 대한 판단 근거")
    similar_refs: list[str] = Field(
        default_factory=list, description="근거가 된 유사 도서 제목들"
    )


class ClassificationResult(BaseModel):
    """분류 결과: 복수 후보를 적합도 순으로 담는다."""

    candidates: list[Candidate] = Field(description="적합도 내림차순 후보 목록")
