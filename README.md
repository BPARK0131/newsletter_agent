# IP Network Newsletter Agent

Obsidian Vault 기반 IP Network 기술 동향 뉴스레터 MVP.

## 문서

**[docs/README.md](docs/README.md)** — 전체 문서 목록·빠른 시작

| 문서 | 설명 |
|------|------|
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

## 실행

```bash
pip install -r requirements.txt
# 프로젝트 루트에 .env 생성 (변수 목록: docs/setup-and-operations.md)
streamlit run streamlit_app.py
```

## Streamlit 탭 (v0.7)

| 탭 | 역할 |
|----|------|
| ▶ 실행 | Orchestrator 수집 · Workflow 상태 |
| 📋 기사 검토 | RSS · 등록소스 · Tavily **통합 HITL** |
| 📰 뉴스레터 | draft · 발행 확정 |
| 📦 아카이브 | archive · used |
| ⚙️ 운영콘솔 | Discovery staging · IETF Radar · Tool 로그 |

## Vault

[ vault/README.md ](vault/README.md)
