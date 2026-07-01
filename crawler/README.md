# 서강대 로욜라도서관 도서 메타데이터 크롤러

서강대학교 로욜라도서관(`https://library.sogang.ac.kr`)의 **소장자료(도서)** 메타데이터를
검색 결과 페이지에서 수집해 CSV로 저장하는 크롤러입니다.

수집 필드: `제목, 저자, 출판사, 출판년, 청구기호, 자료유형, 총서명, 소장처, 대출상태, 서지ID, 상세URL`

---

## 1. 빠른 시작

```bash
# (최초 1회) 가상환경 + 패키지
conda create -y -n sgl_crawl python=3.12
conda run -n sgl_crawl pip install requests beautifulsoup4 lxml pandas

# 실행
conda run -n sgl_crawl python crawler.py
# 결과: output/books.csv
```

검색어/건수만 바꾸려면 `config.py`의 `KEYWORDS`, `TARGET_TOTAL`을 수정하면 됩니다.

> **로그인 불필요** — 검색 결과와 청구기호는 비로그인 공개 정보입니다.
> **Playwright/브라우저 불필요** — 검색 결과가 서버 렌더링 HTML이라 `requests`만으로 충분합니다.

---

## 2. 동작 원리 (이걸 알아야 확장이 쉽다)

### 2.1 검색 URL 구조
```
https://library.sogang.ac.kr/search/toc/result?st=KWRD&si=TOTAL&q=<검색어>&pn=<페이지>
```
| 파라미터 | 의미 | 값 |
|---|---|---|
| `st` | 검색 타입 | `KWRD`(키워드). 그 외 `TITL`(서명), `AUTH`(저자), `PUBL`(출판사) 등 |
| `si` | 검색 범위 | `TOTAL`(전체) |
| `q`  | 검색어 | URL 인코딩됨 |
| `pn` | 페이지 번호 | 1부터. **한 페이지 10건 고정** |

### 2.2 HTML 구조
- 검색 결과 한 페이지에 `ul.resultList > li.items` 가 **10개**.
- 각 `li` 안은 `<dl>`의 `dt`(라벨) / `dd`(값) 쌍 구조.
  `crawler.py`의 `_label_map()`이 `dt`(예: "저자") → 바로 뒤 `dd`(값)로 매핑합니다.
- **청구기호는 서지 레벨이 아니라 "소장처 정보"의 `[대괄호]` 안**에 들어있습니다.
  한 책에 소장본이 여러 개면 청구기호도 여러 개라서 `MULTI_SEP`(기본 ` | `)으로 합칩니다.
- 상세 페이지 ID(서지ID)는 상세 링크 `/search/detail/CATTOC...`에서 추출합니다.

### 2.3 중복 제거
검색어가 달라도 같은 책이 나올 수 있으므로 **서지ID 기준**으로 전역 중복 제거합니다
(`crawl()`의 `seen` 집합).

---

## 3. 대량 크롤링으로 확장하기

100건짜리 데모를 수천~수만 건으로 키울 때 고려할 점과 구체적 수정 방법입니다.

### 3.1 "무엇을 모을지" 전략 — 가장 먼저 정할 것
도서관 검색은 **검색어 기반**이라, 장서 전체를 그냥 순회하는 API는 공개돼 있지 않습니다.
대량 수집을 하려면 "넓게 훑는 검색 축"을 정해야 합니다. 선택지:

1. **주제어/분류 키워드 대량 투입** (가장 현실적)
   - `KEYWORDS`에 수백 개의 주제어를 넣고 각 검색어에서 깊은 페이지까지 수집.
   - 예: KDC/DDC 주제명, 학과명, 전공 키워드 리스트 등.
2. **저자/출판사 축으로 순회**
   - `st=AUTH` 또는 `st=PUBL`로 바꿔 저자/출판사 목록을 순회.
3. **청구기호(분류기호) 구간 브라우징**
   - 청구기호 앞자리(예: `005`, `610`)를 키워드처럼 넣어 분야별로 긁기.

> ⚠️ 어떤 방식이든 **검색어당 결과 상한**이 있습니다. 관측상 한 검색어의 페이지는
> 수십~수백 페이지(예: "파이썬" = 93페이지 ≈ 930건)로 잘립니다. 즉 검색어 하나로
> 전체를 다 못 가져오니, **검색어를 잘게 쪼개 합집합**을 만드는 게 핵심입니다.

### 3.2 페이지 상한 늘리기
`config.py`:
```python
TARGET_TOTAL = 50000          # 목표 건수
MAX_PAGES_PER_KEYWORD = 100   # 검색어당 페이지 상한 (10건/페이지 → 최대 1000건)
KEYWORDS = [ ... 수백 개 ... ]
```
검색어당 quota(`math.ceil(TARGET_TOTAL/len(KEYWORDS))`)도 자동으로 커집니다.
검색어 하나에서 최대한 깊게 긁고 싶으면 quota 로직을 "검색어당 N페이지 전부"로 바꾸세요.

### 3.3 ⭐ 체크포인트 / 재개 (대량의 필수 기능)
수만 건은 중간에 끊길 수 있습니다. **이어받기**가 없으면 처음부터 다시 긁어야 합니다.
권장 변경:
- 수집 결과를 한 번에 메모리에 쌓지 말고 **줄 단위로 즉시 파일에 append**(JSONL 권장).
- 이미 처리한 `서지ID`와 `(검색어, pn)` 진행 위치를 별도 파일에 기록.
- 재시작 시 그 파일들을 읽어 `seen`을 복원하고 마지막 위치부터 재개.

```python
# 개념 예시 (crawler.py에 통합)
import json, os
SEEN_FILE = "output/seen_ids.txt"
JSONL = "output/books.jsonl"

seen = set(open(SEEN_FILE).read().split()) if os.path.exists(SEEN_FILE) else set()
fout = open(JSONL, "a", encoding="utf-8")
fseen = open(SEEN_FILE, "a")

def emit(rec):
    if rec["서지ID"] in seen: return
    seen.add(rec["서지ID"])
    fout.write(json.dumps(rec, ensure_ascii=False) + "\n"); fout.flush()
    fseen.write(rec["서지ID"] + "\n"); fseen.flush()
```
마지막에 JSONL → CSV로 변환(`pandas.read_json(..., lines=True).to_csv(...)`)하면 됩니다.

### 3.4 ⭐ 예의 있는 속도 + 재시도 (차단 방지)
대량 요청 시 서버 부담/차단을 피하는 게 중요합니다.
- **요청 간격**: `DELAY_SEC`를 0.5~1.0초 이상 유지. 야간/주말 위주 권장.
- **지터(jitter)**: 고정 간격 대신 약간의 랜덤(예: `0.5~1.2초`)을 섞으면 자연스럽습니다.
- **재시도/백오프**: 일시적 5xx/타임아웃은 점증 대기 후 재시도.

```python
import random, time, requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def make_session():
    s = requests.Session()
    retry = Retry(total=5, backoff_factor=1.0,
                  status_forcelist=[429,500,502,503,504],
                  allowed_methods=["GET"])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s

def polite_sleep():
    time.sleep(random.uniform(config.DELAY_SEC, config.DELAY_SEC + 0.6))
```
> **동시요청(병렬/멀티스레드)은 피하세요.** 속도를 위해 동시 연결을 늘리면 차단 위험이
> 급증합니다. 단일 스레드 + 적절한 딜레이가 대량 수집에선 더 안전하고 결국 더 빠릅니다.

### 3.5 로깅 & 진행 상황
`print` 대신 `logging`으로 바꾸고 파일에도 남기면 장시간 작업 추적이 쉽습니다.
실패한 `(검색어, pn)`은 별도 `errors.log`에 적어 나중에 재수집하세요.

### 3.6 저장 포맷
- 수천 건까지: CSV로 충분.
- 수만 건 이상 또는 재개/질의가 잦으면: **SQLite** 권장.
  `서지ID`를 PRIMARY KEY로 두면 중복 삽입이 자동으로 무시(`INSERT OR IGNORE`)돼
  체크포인트가 사실상 공짜로 해결됩니다.

### 3.7 데이터 정제 (선택)
- 청구기호 칸에 `보관서고` 같은 **소장 위치 문구가 섞이는** 경우가 있습니다.
  실제 청구기호는 보통 `숫자.숫자 + 저자기호` 패턴이라, 정규식으로 필터링하면 깔끔해집니다.
- 일부 책은 저자 필드가 비어 있습니다(편저/기관 저자 등). 정상입니다.
- ISBN·페이지수·주제어가 필요하면 상세페이지(`상세URL`)를 추가로 요청해 파싱하세요
  (요청 수가 책 수만큼 늘어나니 딜레이를 더 보수적으로).

---

## 4. 권장 작업 순서 (대량 수집 체크리스트)

1. [ ] 수집 전략 결정 (3.1) — 검색어 목록/축을 충분히 크게 준비
2. [ ] `config.py`에서 `TARGET_TOTAL`, `MAX_PAGES_PER_KEYWORD`, `DELAY_SEC` 상향
3. [ ] 체크포인트/재개 로직 추가 (3.3)
4. [ ] 재시도·백오프·지터 추가 (3.4)
5. [ ] 로깅 + 에러 파일 (3.5)
6. [ ] 소규모(수백 건)로 시험 → CSV/DB 결과 검수
7. [ ] 본 수집 실행 (야간 권장), 중간 점검
8. [ ] 정제 후 최종 산출물 생성 (3.7)

---

## 5. 에티켓 & 주의

- 이 데이터는 본인 학습/연구 목적의 **메타데이터 수집**을 전제로 합니다.
- 도서관 시스템에 과도한 부하를 주지 않도록 **느린 속도 · 단일 연결**을 지키세요.
- 사이트의 `robots.txt`와 이용약관을 존중하고, 대량 수집 전 도서관에
  공식 데이터 제공(예: 오픈 API / 정보공개 요청) 가능 여부를 문의하는 것도 좋은 방법입니다.
- 로그인 자격증명은 코드에 하드코딩하지 말고 환경변수/별도 설정으로 분리하세요
  (이 크롤러는 로그인이 필요 없습니다).

---

## 6. 파일 구성

```
sgl_crawling/
├── crawler.py      # 크롤러 본체 (requests + BeautifulSoup)
├── config.py       # 검색어 / 목표건수 / 딜레이 설정
├── output/
│   └── books.csv   # 결과
├── recon/          # 사이트 구조 분석에 썼던 정찰 스크립트 (삭제 가능)
└── README.md
```
