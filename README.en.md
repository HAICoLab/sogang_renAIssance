# Sogang renAIssance

<p align="right">
  <a href="./README.md">한국어</a> |
  <a href="./README.en.md">English</a>
</p>

**Sogang renAIssance** is the official repository for the project  
**“A Librarian–AI Collaborative Agent for Library Classification Number Decision Support.”**

The project was developed by undergraduate students in the 
**English Language and Literature program, Department of English, Sogang University**.

The goal of the project is to develop a **human–AI collaborative decision-support system**
that assists librarians in determining appropriate library classification numbers.

Rather than fully automating the classification process,
the system retrieves similar cataloging cases, generates classification candidates,
and provides supporting evidence and explanations for each candidate.
The final classification decision remains with the librarian,
following a **Human-in-the-Loop** design philosophy.

## Award

🏆 **Excellence Award**  
Sogang University Student Competition

---

## Team

All members are from the
**English Language and Literature program, Department of English, Sogang University**.

- **Team Leader:** Goeun Nam (남고은)
- **Team Member:** Soyoung Cho (조소영)
- **Team Member:** Seowoo Lee (이서우)
- **Team Member:** Hyunjae Kim (김현재)
- **Faculty Advisor:** Yoonseok Heo (허윤석)

## Project Overview

### Project Topic
**A Librarian–AI Collaborative Agent for Library Classification Number Decision Support**

### Objectives

- Retrieve similar cataloging cases based on bibliographic metadata
- Generate candidate classification numbers using AI
- Provide supporting evidence and explanations for each candidate
- Support librarians through a Human-in-the-Loop decision-making workflow
- Accumulate classification cases and reasoning as reusable knowledge assets

---

## Repository Structure

| Directory | Description |
| --- | --- |
| [`crawler/`](./crawler) | Metadata crawler for books in Sogang University Loyola Library |
| [`skeleton/`](./skeleton) | Initial working skeleton and baseline implementation of the librarian–AI collaboration system |
| [`lib_copilot/`](./lib_copilot) | Core Library Copilot implementation developed by the student team |
| [`library-cataloging-demo/`](./library-cataloging-demo) | Web-based demonstration system used for the competition presentation |

---

## System Concept

This project is not designed to fully automate library classification.

Instead, it follows a **human–AI collaboration paradigm** in which the AI system
provides candidate classification numbers and supporting evidence,
while the librarian remains responsible for the final decision.

The overall workflow is:

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

---

## Components

### `crawler/`

A data collection module for retrieving bibliographic metadata from
Sogang University Loyola Library.

### `skeleton/`

An initial **working skeleton / baseline implementation**
based on [`skeleton/docs/prototype_design.md`](./skeleton/docs/prototype_design.md).

Given bibliographic metadata, the system retrieves similar cataloging cases
and generates candidate classification numbers together with supporting evidence.

See [`skeleton/README.md`](./skeleton/README.md) for detailed instructions.

### `lib_copilot/`

Core implementation of the Library Copilot system developed by the student team.

Original repository:

[https://github.com/lilmosy/lib_copilot](https://github.com/lilmosy/lib_copilot)

The code is included in this repository as part of the official project archive.

### `library-cataloging-demo/`

A web-based demonstration system developed for the competition presentation
and live system demonstration.

---

## Collaboration Guidelines

- The `main` branch should remain in a working state.
- Development should be conducted in `feature/<feature-name>` branches.
- Changes should be merged through Pull Requests.
- Commit messages should use component prefixes when appropriate.
  - Example: `[crawler] ...`
  - Example: `[demo] ...`
  - Example: `[model] ...`
- Large datasets, model weights, API keys, and credentials should not be committed directly to the repository.

---


