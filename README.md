# Sogang renAIssance <p align="right">
  <a href="./README.md">한국어</a> |
  <a href="./README.en.md">English</a>
</p>




**팀 Sogang renAIssance**는 서강대학교 학생 공모전에서 진행한  
**「도서관 분류기호 결정을 위한 사서-AI 협업 에이전트」** 프로젝트의 공식 저장소입니다.

본 프로젝트는 **[2026년 서강대학교 생성형 AI기반 아이디어 공모전](https://contest.sogang.ac.kr/)**에서 **우수상**을 수상하였습니다. 

본 프로젝트는 서강대학교 영문학부 영미어문전공 학생들이 참여하여 수행하였으며,  
도서관 장서의 분류기호 결정 과정을 지원하기 위한 **LibCowork: 사서-AI 협업형 의사결정 지원 시스템**을 구현하는 것을 목표로 합니다.

이 시스템은 도서의 서지정보와 유사 분류 사례를 바탕으로 분류기호 후보를 제시하고,  
각 후보에 대한 판단 근거와 관련 정보를 제공함으로써 사서의 전문적인 의사결정을 지원합니다.  
최종 분류 결정은 AI가 자동으로 수행하는 것이 아니라, **사서가 판단의 주체로 남는 Human-in-the-Loop 구조**를 지향합니다.  

## Team

모든 팀원은 **서강대학교 영문학부 영미어문전공** 소속입니다.

- **팀장:** 남고은
- **팀원:** 조소영
- **팀원:** 이서우
- **팀원:** 김현재
- **지도교수:** 허윤석

---

## Project Overview

### 주제
**도서관 분류기호 결정을 위한 사서-AI 협업 에이전트**

### 주요 목표

- 도서 서지정보 및 기존 분류 사례 기반의 유사 사례 검색
- AI 기반 분류기호 후보 생성
- 후보별 판단 근거 및 설명 제공
- 사서의 최종 판단을 지원하는 Human-in-the-Loop 의사결정 구조 구현
- 분류 과정에서 생성되는 판단 근거와 사례의 축적을 통한 지식 자산화

---

## Repository Structure

| 디렉토리 | 설명 |
| --- | --- |
| [`crawler/`](./crawler) | 서강대학교 로욜라도서관 도서 메타데이터 수집을 위한 크롤러 |
| [`skeleton/`](./skeleton) | 사서-AI 협업 분류 시스템의 초기 워킹 스켈레톤 및 baseline 구현 |
| [`lib_copilot/`](./lib_copilot) | 학생 팀에서 개발한 Library Copilot 구현 코드 |
| [`library-cataloging-demo/`](./library-cataloging-demo) | 공모전 발표 및 시연을 위해 개발한 웹 기반 데모 |

---

## System Concept

본 프로젝트는 도서 분류 업무를 완전히 자동화하는 시스템이 아니라,
**AI가 후보와 근거를 제시하고 사서가 최종 결정을 내리는 협업형 시스템**을 지향합니다.

기본적인 처리 흐름은 다음과 같습니다.

```text
Bibliographic Metadata
        ↓
Similar Case Retrieval
        ↓
Classification Candidate Generation
        ↓
Evidence & Explanation
        ↓
Librarian Review
        ↓
Final Classification Decision
```

AI는 기존 장서와 유사 사례를 검색하고 분류기호 후보를 제안하며,
각 후보에 대해 관련 사례와 판단 근거를 함께 제공합니다.

---

## Components

### `crawler/`

서강대학교 로욜라도서관 장서의 메타데이터를 수집하기 위한 데이터 수집 모듈입니다.

### `skeleton/`

[`skeleton/docs/prototype_design.md`](./skeleton/docs/prototype_design.md)를 기반으로 구현한
초기 **working skeleton / baseline**입니다.

서지정보를 입력하면 유사 사례를 검색하고,
분류기호 후보와 판단 근거를 제시합니다.

자세한 실행 방법은 [`skeleton/README.md`](./skeleton/README.md)를 참고하세요.

### `lib_copilot/`

학생 팀에서 개발한 Library Copilot의 주요 구현 코드입니다.

Original repository:

[https://github.com/lilmosy/lib_copilot](https://github.com/lilmosy/lib_copilot)

본 저장소에는 프로젝트의 공식 결과물 관리를 위해 해당 코드를 포함하고 있습니다.

### `library-cataloging-demo/`

공모전 발표 및 라이브 시연을 위해 개발한 웹 기반 데모입니다.

---

## Collaboration Guidelines

- `main` 브랜치는 항상 실행 가능한 상태를 유지합니다.
- 기능 개발은 `feature/<feature-name>` 브랜치에서 진행합니다.
- 변경사항은 Pull Request를 통해 병합합니다.
- 커밋 메시지는 가능하면 컴포넌트 이름을 접두어로 사용합니다.
  - 예: `[crawler] ...`
  - 예: `[demo] ...`
  - 예: `[model] ...`
- 대용량 데이터, 모델 가중치, API key 및 credential은 저장소에 직접 포함하지 않습니다.

---

## Award

🏆 **Excellence Award (우수상)**  
Sogang University Student Competition

---

## Acknowledgement

본 프로젝트는 서강대학교 학생 공모전의 일환으로 수행되었습니다.

Repository maintained by **HAI CoLab, Sogang University**.
