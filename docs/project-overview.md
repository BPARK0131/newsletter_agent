# 프로젝트 개요

## 한 줄 요약

**Multi-Agent + Obsidian Vault + Newsletter Orchestrator (단일 LangGraph)**로 IP Network 기술 동향을 수집·검수·뉴스레터화하는 MVP.

## 목표

1. **Research** — RSS/API/blog_index 소스 자동 수집
2. **Analysis** — LLM 1차 리뷰 (요약·분류·편향·중요도)
3. **Threshold HITL** — score 기반 큐 분류 (`ipn_agent.review.hitl`)
4. **HITL** — Streamlit **기사 검토** 탭 사람 최종 승인 (RSS · Tavily 통합)
5. **Editor** — Orchestrator editor node → draft Markdown
6. **Standards Context** — IETF Radar + 기사별 표준 맥락

## MVP 범위

- **`newsletter_orchestrator.py`** — 수집~draft **단일 StateGraph** (v0.8, 유일한 진입점)
- **`ipn_agent.collect.discovery`** — Tavily quality gate → 02_review 자동 생성
- **`ipn_agent.review.metadata`** — 02_review frontmatter 정규화
- **`ipn_agent.orchestrator.editor`** — Editor prepare/generate/refine 함수
- Chat UI / 이메일 / HTML 변환은 최종 범위 제외 (미구현으로 종료)

## 산출물

| 산출물 | 경로 |
|--------|------|
| Raw 기사 | `vault/01_raw/` |
| LLM 리뷰 | `vault/02_review/` |
| 승인 기사 | `vault/03_approved/` |
| draft | `vault/04_newsletter/draft/` |
| 발행본 | `vault/04_newsletter/published/` |
| 기발행 registry | `vault/registry/published_articles.json` |
| Workflow 로그 | `output/pipeline_runs/{run_id}/` |
| Tool 로그 | `logs/tool_runs.jsonl` |

## 카테고리 (9 + Other)

Routing/Internet Operations · Backbone/Backhaul · Transport/DCI · DataCenter Network · IP Security · NetDevOps · AI Network/Autonomous Network · Standards/Architecture · Other
