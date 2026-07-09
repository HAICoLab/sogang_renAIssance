# Sogang Librarian Copilot

도서관 분류 의사결정을 위한 사서-AI 협업 에이전트 (v0 워킹 스켈레톤).

신규 도서의 서지 정보를 입력하면 → 유사 사례를 검색하고 → 복수의 청구기호 후보와
판단 근거(XAI)를 제시한다. 최종 판단은 사람 사서가 한다.

## 이 스켈레톤은 어떻게 만들어졌나

이 코드는 [`docs/prototype_design.md`](docs/prototype_design.md) 설계서를 바탕으로 **바이브코딩(vibe coding)**으로 구현되었다.
즉, 사람이 한 줄씩 직접 타이핑한 것이 아니라 설계 문서를 맥락으로 주고 AI와 대화하며 파이프라인을 세워 나갔다.

- **출발점:** `docs/prototype_design.md` — 입력(서지정보) → 출력(청구기호 후보 + 근거)이 끝까지 관통하는 가장 얇은 파이프라인 설계서.
- **결과물:** 이 `skeleton/` 폴더 전체 (analyze → retrieve → classify 파이프라인 + CLI + 웹 UI).

> 학생 여러분은 **여기서 시작해서** 각자의 버전을 만들어 보고, 이 스켈레톤과 비교해 보세요.
> 설계서(`docs/prototype_design.md`)를 먼저 읽으면 "왜 이렇게 만들었는지" 판단 배경을 이해할 수 있다.

## 아키텍처 (v0)

```
BookInput ──analyze──▶ Analysis ──retrieve──▶ [SimilarCase] ──classify──▶ ClassificationResult
          (휴리스틱)             (키워드 검색)              (Claude, 구조화 출력)
```

| 모듈 | 역할 | v0 구현 | 이후 고도화 |
|------|------|---------|------------|
| `analyze.py` | 의미 분석 | 키워드 추출(휴리스틱) | Claude 주제 추출 |
| `retrieve.py` | 사례 검색(RAG) | 키워드 겹침 top-k | pgvector 임베딩 유사도 |
| `classify.py` | 후보 생성 + 근거 | **Claude 호출** (구조화 출력) | 프롬프트/캐싱 고도화 |
| `pipeline.py` | 배선 | 세 단계 연결 | — |

> v0에서 API를 쓰는 곳은 `classify.py` 한 군데뿐. 나머지는 순수 파이썬.

## 실행

Python 3.12 기준. miniconda로 전용 환경을 만들어 실행한다.

```bash
conda create -n librarian_baseline python=3.12 -y
conda activate librarian_baseline
pip install -r requirements.txt
cp .env.example .env      # 그리고 ANTHROPIC_API_KEY 입력

python src/run.py                 # 예시 도서(『차별하는 데이터』) 분류 (CLI)
python src/run.py path/to/book.json   # 임의 도서 (BookInput 형식 JSON)

streamlit run app.py              # 웹 UI로 실행 (브라우저에서 입력·결과 확인)
```

## 데이터

- `data/collection.json` — 기존 장서(검색 대상). DDC 청구기호 + 일부 사서 메모(암묵지 시드).

## 로드맵

- **v0** 휴리스틱 스켈레톤 ← 현재
- **v1** retrieve 임베딩 기반(진짜 RAG)
- **v2** classify 근거 품질/캐싱 고도화
- **v3** Supabase(PostgreSQL + pgvector) 연동
- **v4** 사서 피드백 저장 (Tacit Knowledge Repository 순환)
- **v5** React 웹 UI
