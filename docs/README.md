# IP Network Newsletter Agent — 문서

Obsidian Vault 기반 IP Network 기술 동향 뉴스레터 MVP 프로젝트 문서 모음입니다.

## 빠른 시작

```bash
cd "mini pjt"
pip install -r requirements.txt
# .env는 로컬에서 직접 생성 — docs/setup-and-operations.md 참고
streamlit run streamlit_app.py
```

## 문서 목록

| 문서 | 내용 |
|------|------|
| [ip-newsletter-agent-confluence.md](./ip-newsletter-agent-confluence.md) | **일반 사용자 공유용** — Confluence 붙여넣기용 소개·사용 가이드 |
| [project-overview.md](./project-overview.md) | 프로젝트 목표·범위·MVP 정의 |
| [assignment-spec.md](./assignment-spec.md) | **과제 설명서** |
| [assignment-review.md](./assignment-review.md) | **과제 검토 보고서** |
| [architecture.md](./architecture.md) | **Newsletter Orchestrator** · Tavily 자동 파이프라인 |
| [vault-structure.md](./vault-structure.md) | Obsidian Vault·registry·통합 Review 메타 |
| [streamlit-ui.md](./streamlit-ui.md) | Streamlit v0.8 · 통합 HITL · 운영콘솔 |
| [newsletter-pipeline.md](./newsletter-pipeline.md) | editor prepare/generate/refine · 발행 |
| [setup-and-operations.md](./setup-and-operations.md) | `newsletter_orchestrator.py` 실행 |
| [project-structure.md](./project-structure.md) | **ipn_agent/** Python 패키지 구조 |
| [changelog.md](./changelog.md) | 반영 이력 (v0.1 → v0.8) |
| [sources-checklist.md](./sources-checklist.md) | `sources.yaml` 소스 검증 |
| [agent-coding-guide.md](./agent-coding-guide.md) | LangGraph 코딩 가이드 |
| [legacy-design-notes.md](./legacy-design-notes.md) | 초기 기획안 → docs 통합 |

## 코드 ↔ 문서 매핑

> 파일 위치: [project-structure.md](./project-structure.md)

| 스크립트 (CLI wrapper) | 패키지 모듈 | 역할 |
|------------------------|-------------|------|
| **`newsletter_orchestrator.py`** | `ipn_agent.orchestrator.workflow` | 단일 LangGraph |
| `fetch_script.py` | `ipn_agent.collect.fetch` | Phase 1 수집 |
| `review_script.py` | `ipn_agent.review.runner` | Phase 2 LLM Review |
| `standards_radar_script.py` | `ipn_agent.standards.radar` | IETF Radar |
| `research_review_agent.py` | `ipn_agent.orchestrator.research_agent` | 레거시 subprocess |
| `reset_vault.py` | `ipn_agent.vault.reset` | Vault 초기화 |
| `streamlit_app.py` | `ipn_agent.ui.*` + vault | HITL UI |

| 패키지 | 역할 |
|--------|------|
| `ipn_agent.orchestrator.editor` | Editor prepare / generate / refine |
| `ipn_agent.orchestrator.state` | `NewsletterWorkflowState` |
| `ipn_agent.collect.discovery` | Tavily quality gate → 02_review |
| `ipn_agent.review.metadata` | 02_review frontmatter 정규화 |
| `ipn_agent.review.hitl` | threshold HITL (rule) |
| `ipn_agent.registry.published` | 기발행 hash registry |
| `ipn_agent.vault.utils` | Vault/HITL/발행/registry |

## Vault 바로가기

[vault/README.md](../vault/README.md)
