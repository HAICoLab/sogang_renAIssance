# library-cataloging-demo

실제 대학도서관 편목(cataloging) 업무 화면을 그대로 재현한 데모입니다. 사서가 신착도서에
청구기호(KDC/DDC ▼h)를 부여할 때 거치는 화면 흐름(종합목록 조회 → 서지 확인 → 편목 → AI 후보
추천)을 실제 서강대 장서 DB와 lib_copilot LLM 파이프라인으로 구동합니다.

- 프론트엔드: `library_system.html` (순수 HTML/CSS/JS, 빌드 없음)
- 백엔드: `library_biblio_server.py` (표준 라이브러리만 사용하는 로컬 HTTP 서버)

## 화면 구성
- **종합목록** — KERIS 종합목록(union catalog) 검색 창. 기본값으로 검색하면 의도적으로
  "결과 없음" 상태를 보여준다(신착도서가 아직 어디에도 없다는 것을 보여주는 데모 시나리오).
- **서지** — 서강대 실제 장서 DB(`/api/biblio`)를 서명·저자·청구기호·키워드·ISBN·제어번호로
  검색하는 화면.
- **편목** — 아직 청구기호가 없는 신착도서 대기열. 각 건을 열면 MARC 편집기와 함께 AI가
  추천하는 청구기호 후보(신뢰도 점수·근거·인용도서 포함)를 확인할 수 있고, 후보별로
  암묵지 메모를 남길 수 있다. 편목 대기열에 있는 책은 서지검색 결과에서 자기 자신이
  나오지 않도록 제외된다.
- **기각사례** — 과거에 AI 추천 청구기호가 사서의 최종 판단과 달랐던 사례 모음.

## 실행 준비
1. 이 저장소를 클론합니다.
2. `lib_copilot` 저장소(https://github.com/lilmosy/lib_copilot)를 이 폴더 안에 `lib_copilot/`이라는 이름으로 클론합니다.
   ```
   git clone https://github.com/lilmosy/lib_copilot
   ```
3. `data/sogang_db_final.db` (서강대 장서 DB, 약 1.36GB, 용량 문제로 이 저장소에는 미포함)를 `data/` 폴더에 넣어주세요. 파일은 담당자에게 별도로 요청하세요.
4. 서버 실행:
   ```
   python3 library_biblio_server.py
   ```
   기본 포트: 8934 (`http://localhost:8934`)

## API
- `GET /api/biblio?field=청구기호|서명|저자|키워드|ISBN|제어번호&q1=..&q2=..`
  — 서지 탭/편목 내 서지검색 창에서 쓰는 실 DB 조회.
- `GET /api/classify?case=<lib_copilot/experiment/data/scenarios 파일명>`
  — 편목 대기열의 신착도서에 대한 AI 청구기호(▼h) 후보 추천. lib_copilot의
  `pipeline.classify_book`을 그대로 호출하며(수정 없음), 실제 LLM 호출이라 건당
  15~20초가 걸린다. 결과는 케이스당 `lru_cache`로 1회만 계산되고, 서버를 재시작하면
  캐시가 초기화된다.

## 알아두면 좋은 점
- `run_classify_LIVE`는 실제 LLM 호출이라 완전히 결정적이지 않다 — 서버를 재시작한 뒤
  같은 케이스를 다시 돌리면 인용도서·근거 문구가 조금씩 달라질 수 있다.
- `case10_bilingual`(이중언어자) 케이스는 데모 발표용으로 후보 순서·점수를
  `FORCE_BILINGUAL_ORDER` 스위치(`library_biblio_server.py`)로 고정해뒀다. 필요 없으면
  `False`로 바꾸면 원래 라이브 결과로 돌아간다.
