"""CLI 진입점.

기본 실행: 예시 도서(『차별하는 데이터』)를 분류해 결과를 출력.
    python src/run.py

JSON 파일로 다른 도서를 넣으려면:
    python src/run.py path/to/book.json
"""

from __future__ import annotations

import json
import sys

from pipeline import classify_book
from schema import BookInput

# 제안서에 등장한 애매한 예시 도서
_SAMPLE = BookInput(
    title="차별하는 데이터",
    author="(번역서)",
    toc=["데이터 편향", "알고리즘 차별", "사회 불평등"],
    is_translation=True,
    keywords=["데이터", "차별", "알고리즘", "사회"],
)


def _load_book(path: str) -> BookInput:
    with open(path, encoding="utf-8") as f:
        return BookInput(**json.load(f))


def main() -> None:
    book = _load_book(sys.argv[1]) if len(sys.argv) > 1 else _SAMPLE

    print(f"\n📖 분류 대상: 「{book.title}」\n")
    result, cases = classify_book(book)

    print("🔎 검색된 유사 사례:")
    if cases:
        for c in cases:
            print(f"   - 「{c.title}」 → {c.call_number} ({c.category}) [유사도 {c.similarity}]")
    else:
        print("   (없음)")

    print("\n📚 청구기호 후보:")
    for i, cand in enumerate(result.candidates, 1):
        print(f"\n  [{i}] {cand.call_number}  {cand.category}  (적합도 {cand.confidence:.2f})")
        print(f"      근거: {cand.reasoning}")
        if cand.similar_refs:
            print(f"      참고 사례: {', '.join(cand.similar_refs)}")

    if result.candidates:
        top = result.candidates[0]
        print(f"\n✅ 추천(사서 검토 필요): {top.call_number} {top.category}\n")


if __name__ == "__main__":
    main()
