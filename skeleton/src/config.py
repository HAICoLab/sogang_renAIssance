"""파이프라인 설정. 모델·경로 등 한 곳에서 관리."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # 프로젝트 루트의 .env에서 ANTHROPIC_API_KEY 등을 읽어옴

# LLM 모델 — 교체하려면 이 줄만 수정 (예: "claude-sonnet-4-6")
MODEL = os.environ.get("LIBRARIAN_MODEL", "claude-opus-4-8")

# classify 단계 최대 출력 토큰
MAX_TOKENS = 4000

# RAG 검색에서 가져올 유사 사례 수
TOP_K = 5

# 데이터 경로
PROJECT_ROOT = Path(__file__).resolve().parent.parent
COLLECTION_PATH = PROJECT_ROOT / "data" / "collection.json"
