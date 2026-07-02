# 소스 정합성 검증 체크리스트

> **최종 업데이트:** 2026-07-02 (v0.8 레거시 경로 정리)  
> **상태:** ✅ 확인 | ❌ 문제 | ⚠️ 부분 | ⬜ 미확인

## 0. 코드-YAML 정합성

| 항목 | 상태 | 비고 |
|------|------|------|
| `newsletter_orchestrator.py` | ✅ | 단일 LangGraph, 유일한 진입점 |
| `ipn_agent.collect.discovery` | ✅ | Tavily quality gate → 02_review |
| `ipn_agent.review.metadata` | ✅ | 02_review frontmatter 정규화 |
| `ipn_agent.orchestrator.editor` | ✅ | Editor prepare/generate/refine |
| `ipn_agent.review.hitl` — threshold HITL | ✅ | v0.5+ |
| `ipn_agent.registry.published` — hash 차단 | ✅ | v0.5+ |
| Vault `registry/published_articles.json` | ✅ | v0.5+ |
| `pipeline_graph.py` / `newsletter_agent_skeleton.py` | 🗑️ 삭제됨 | v0.8 — [changelog.md](./changelog.md) 참고 |

## 1. 소스 검증 (Tier 1~3)

> 상세 소스별 RSS/API/blog_index 테스트는 `sources.yaml` + 수동 fetch로 확인.

| source_id | Tier | 상태 | 비고 |
|-----------|------|------|------|
| `apnic_blog` | 1 | ✅ | 최소 동작 조합 |
| `ripe_labs` | 1 | ✅ | |
| `ietf_datatracker` | ref | ✅ | Radar 전용 |

## 7. 파이프라인 E2E

| 단계 | 명령 | 산출물 |
|------|------|--------|
| Collect | Orchestrator `mode=collect` | `01_raw/`, `02_review/`, `ietf_radar.md` |
| Tavily gate | `expansion_search` + `discovery.py` | `01_raw/expansion/`, `logs/discovery/` |
| Threshold | `threshold_routing` node | `hitl_route`, `99_rejected/` |
| HITL | Streamlit **기사 검토** (통합) | `03_approved/` |
| Draft | Orchestrator `mode=draft` | `04_newsletter/draft/` |
| Publish | Streamlit 발행 확정 | `published/`, `registry/`, `06_used/` |

## 9. 변경 이력 (요약)

| 버전 | 내용 |
|------|------|
| v0.8 | 레거시 경로 삭제(`pipeline_graph.py` 등) · 문서 동기화 |
| v0.7 | 통합 HITL · Tavily 자동 파이프라인 · 운영콘솔 |
| v0.6 | `newsletter_orchestrator.py` 단일 Graph · editor node 3분리 |
| v0.5 | threshold HITL · published registry |
| v0.4 | 발행 lifecycle · archive 탭 |

전체: [changelog.md](./changelog.md)
