# IP Network Newsletter Agent

Multi-Agent + LangGraph + Obsidian Vault 기반 IP Network 기술 동향 뉴스레터 Agent MVP.

---

## [1] 프로젝트 설명

IP Network 영역(Backbone, DCI, Data Center Network, IP Security, NetDevOps, 표준화 등)의 기술 동향은 RSS, 벤더 블로그, IETF API, 오픈 웹 등 여러 채널에 분산되어 있어 담당자가 매번 직접 수집·분류·요약해야 하는 부담이 큽니다.

본 프로젝트는 **역할별 Multi-Agent**가 협업하고, **LangGraph Newsletter Orchestrator**가 전체 흐름을 조율하여 IP Network 뉴스레터 초안까지 자동 생성하는 **데모 가능한 MVP**입니다. Agent 간 산출물은 Obsidian Vault(`01_raw` → `02_review` → `03_approved` → `04_newsletter`)를 **공유 Artifact Store**로 교환하며, 사람 검수(HITL)와 기발행 차단(registry)을 통해 품질을 보장합니다.

### 주요 구성

| 역할 | 구현 | 산출물 |
|------|------|--------|
| **Research Agent** | RSS/API/blog_index/Tavily 수집 | `vault/01_raw/` |
| **Analysis Agent** | LLM 1차 리뷰 (요약·분류·편향·중요도) | `vault/02_review/` |
| **Threshold HITL** | review_score 기반 큐 분류 (LLM 없음) | `hitl_route` 메타 |
| **Human Agent (HITL)** | Streamlit **기사 검토** 탭 승인/반려 | `vault/03_approved/` |
| **Standards Radar Agent** | IETF datatracker WG 동향 | `vault/04_newsletter/ietf_radar.md` |
| **Editor** | Orchestrator editor node → 뉴스레터 draft | `vault/04_newsletter/draft/` |
| **Newsletter Orchestrator** | 단일 LangGraph (`newsletter_orchestrator.py`) | `output/pipeline_runs/` |

### 파이프라인 흐름

```
sources.yaml
  → 수집(collect) → Tavily 보강(expansion) → IETF Radar
  → LLM 1차 리뷰 → threshold HITL 큐
  → (Streamlit 사람 승인) → approved
  → Editor draft 생성 → (Streamlit 발행 확정) → published + registry
```

### 기술 스택

Python · LangGraph · LangChain (OpenAI) · Streamlit · Obsidian Vault (Markdown) · feedparser · Tavily (선택)

상세 설계: [docs/architecture.md](docs/architecture.md) · [docs/project-overview.md](docs/project-overview.md)

---

## [2] 프로젝트 실행 방법

### 사전 요구사항

- Python 3.10+
- OpenAI API Key (필수)
- Tavily API Key (선택 — 웹 검색 보강 시)

### 1. 설치

```bash
cd "mini pjt"
pip install -r requirements.txt
```

### 2. 환경 변수 설정

프로젝트 루트에 `.env` 파일을 생성합니다. (`.env.example` 참고)

```env
OPENAI_API_KEY=sk-...
# OBSIDIAN_VAULT_PATH=...   # 선택 — 미설정 시 프로젝트 vault/ 자동 사용
# TAVILY_API_KEY=tvly-...   # 선택
```

### 3. Streamlit UI 실행 (권장)

```bash
streamlit run streamlit_app.py
```

브라우저에서 아래 순서로 시연할 수 있습니다.

1. **📥 데이터 수집** — Orchestrator 수집 (RSS + Tavily → `02_review/` HITL 큐 생성)
2. **📋 기사 검토** — RSS·Tavily 통합 HITL 승인/반려
3. **📰 뉴스레터** — Draft 생성 및 Preview → 발행 확정 (`published/` + registry 업데이트)
4. **📦 아카이브** — 발행 호별 보관 · 사용된 승인 기사
5. **⚙️ 운영콘솔** — Discovery gate 로그 · IETF Radar · Tool 로그 (선택)

### 4. CLI (Orchestrator 직접 실행)

```bash
# 수집 ~ threshold HITL 큐
python newsletter_orchestrator.py --mode collect

# approved 기사 → draft 생성
python newsletter_orchestrator.py --mode draft

# 전체 파이프라인
python newsletter_orchestrator.py --mode full

# 특정 소스만 수집
python newsletter_orchestrator.py --sources apnic_blog --mode collect
```

### 5. 개별 Agent 스크립트 (선택)

```bash
python fetch_script.py --source apnic_blog    # Research Agent
python review_script.py                       # Analysis Agent
python standards_radar_script.py              # IETF Radar
```

### 6. Vault 초기화 (주의: 데이터 삭제)

```bash
python reset_vault.py --dry-run   # 삭제 대상 미리보기
python reset_vault.py             # 실제 삭제
```

운영·환경 변수 상세: [docs/setup-and-operations.md](docs/setup-and-operations.md)

---

## 문서

**[docs/README.md](docs/README.md)** — 전체 문서 목록·빠른 시작

| 문서 | 설명 |
|------|------|
| [docs/ip-newsletter-agent-confluence.md](docs/ip-newsletter-agent-confluence.md) | **일반 사용자 공유용** (Confluence 붙여넣기용) |
| [docs/project-overview.md](docs/project-overview.md) | 프로젝트 개요 |
| [docs/assignment-spec.md](docs/assignment-spec.md) | **과제 설명서** |
| [docs/assignment-review.md](docs/assignment-review.md) | **과제 검토** |
| [docs/architecture.md](docs/architecture.md) | 아키텍처 |
| [docs/vault-structure.md](docs/vault-structure.md) | Vault·draft/published |
| [docs/streamlit-ui.md](docs/streamlit-ui.md) | Streamlit v0.7 · 통합 HITL |
| [docs/newsletter-pipeline.md](docs/newsletter-pipeline.md) | 뉴스레터·표준 맥락 |
| [docs/changelog.md](docs/changelog.md) | 변경 이력 |
| [docs/project-structure.md](docs/project-structure.md) | **Python 패키지 구조** |

## 코드 구조

Python 구현은 `ipn_agent/` 패키지에 역할별로 정리되어 있습니다.  
CLI 명령(`python fetch_script.py` 등)은 루트 wrapper로 **기존과 동일**하게 동작합니다.

```
ipn_agent/
├── core/          tool_logger, mvp_limits
├── registry/      article·published registry
├── vault/         vault_utils, reset_vault
├── collect/       fetch, extract, discovery
├── review/        runner, metadata, hitl
├── orchestrator/  workflow, editor, pipeline
├── standards/     IETF radar
└── ui/            streamlit_utils
```

상세: [docs/project-structure.md](docs/project-structure.md)

## Streamlit 탭 (v0.8)

| 탭 | 역할 |
|----|------|
| 📥 데이터 수집 | Orchestrator 수집 · 진행 상황 |
| 📋 기사 검토 | RSS · 등록소스 · Tavily **통합 HITL** |
| 📰 뉴스레터 | draft · 발행 확정 |
| 📦 아카이브 | archive · used |
| ⚙️ 운영콘솔 | Discovery staging · IETF Radar · Tool 로그 |

## Vault

[ vault/README.md ](vault/README.md)
