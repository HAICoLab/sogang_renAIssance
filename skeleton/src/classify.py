"""③ 분류 후보 생성 + 근거 설명 단계 (Claude).

이 파이프라인에서 유일하게 Claude API를 호출하는 곳.
(도서 서지 + 검색된 유사 사례)를 주고 복수의 청구기호 후보 + 판단 근거를
구조화(JSON schema)로 강제해 받아온다.
"""

from __future__ import annotations

import anthropic

from config import MAX_TOKENS, MODEL
from schema import BookInput, ClassificationResult, SimilarCase

_client = anthropic.Anthropic()

# 안정적인 시스템 프롬프트 → 프롬프트 캐싱 대상 (반복 분류 시 비용/지연 절감)
_SYSTEM = """당신은 대학 도서관의 숙련 사서를 돕는 도서 분류 보조 에이전트입니다.
신규 도서의 서지 정보와, 기존 장서에서 검색된 유사 분류 사례가 주어집니다.

당신의 임무:
- DDC(듀이십진분류) 기준으로 이 도서에 적합한 청구기호 후보를 1~3개 제시합니다.
- 각 후보마다 적합도(confidence, 0~1)와 '왜 이 청구기호인가'에 대한 판단 근거를 답니다.
- 근거에는 도서의 핵심 주제 판단과, 참고한 유사 사례를 함께 언급합니다.
- 동일 도서라도 관점에 따라 여러 분류가 가능함을 인정하고, 애매한 경우 복수 후보를 제시합니다.
- 최종 결정은 사람 사서가 하므로, 단정하지 말고 판단을 도울 근거를 충실히 제공합니다.
후보는 적합도 내림차순으로 정렬합니다."""


def _format_cases(cases: list[SimilarCase]) -> str:
    if not cases:
        return "(검색된 유사 사례 없음)"
    lines = []
    for c in cases:
        line = f"- 「{c.title}」 → {c.call_number} ({c.category}), 유사도 {c.similarity}"
        if c.librarian_note:
            line += f"\n  · 사서 메모: {c.librarian_note}"
        lines.append(line)
    return "\n".join(lines)


def _build_prompt(book: BookInput, cases: list[SimilarCase]) -> str:
    return f"""[분류 대상 도서]
- 제목: {book.title}
- 저자: {book.author or "미상"}
- 목차/주제: {", ".join(book.toc) or "-"}
- 출판사: {book.publisher or "-"}
- 번역서 여부: {"예" if book.is_translation else "아니오"}
- 키워드: {", ".join(book.keywords) or "-"}

[기존 장서에서 검색된 유사 분류 사례]
{_format_cases(cases)}

위 정보를 바탕으로 청구기호 후보와 판단 근거를 제시하세요."""


def classify(book: BookInput, cases: list[SimilarCase]) -> ClassificationResult:
    """도서 + 유사 사례 → 청구기호 후보 목록(근거 포함)."""
    response = _client.messages.parse(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        thinking={"type": "adaptive"},
        system=[
            {"type": "text", "text": _SYSTEM, "cache_control": {"type": "ephemeral"}}
        ],
        messages=[{"role": "user", "content": _build_prompt(book, cases)}],
        output_format=ClassificationResult,
    )
    return response.parsed_output
