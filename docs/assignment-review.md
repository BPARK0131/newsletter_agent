# Multi-Agent 기반 IP Network 기술 동향 뉴스레터 Agent — 과제 검토 보고서

> **작성 목적:** Day 8 해커톤 제출 전 과제 명세서의 기술 적합성·완결성·리스크를 검토한다.  
> **검토 기준:** LangGraph 8일 코스 패턴, 해커톤 시간 제약, 시연 가능성  
> **갱신:** v0.7 통합 HITL · Tavily 자동 파이프라인 (2026-07-01)  
> **관련:** [assignment-spec.md](./assignment-spec.md) · [changelog.md](./changelog.md)

---

## 1. 과제 개요 검토

### 1.1 방향성 판정: 적합 ✅

| 평가 항목 | 판정 | 근거 |
|-----------|------|------|
| 현실 업무 문제 연결 | ✅ 적합 | 정보 수집·분류·편향 검토 Pain Point 명확 |
| MVP 범위 설정 | ✅ 적합 | 운영 시스템이 아닌 Agent·HITL·뉴스레터 시연에 초점 |
| 해커톤 시간 내 완성 가능성 | ✅ 달성 | collect → HITL → Orchestrator draft 파이프라인 동작 |
| Day 1~7 패턴 적용 | ✅ 적용 | StateGraph, Structured Output, HITL, LLM-as-Judge, Tool 로깅 |

---

## 2. 기술 구조 검토 (v0.6 구현 기준)

### 2.1 Multi-Agent 구성 — ✅ 단일 Newsletter Orchestrator

```
[배치] research_review_agent.py (레거시)
  fetch → expansion → standards_radar → review

[Newsletter Orchestrator] newsletter_orchestrator.py (v0.6)
  load_sources → collect → expansion_search → standards_radar → first_review
  → threshold_routing → human_review_wait
  → load_approved → filter_published
  → editor_prepare → editor_generate → editor_quality_check → draft_created

[Editor 함수] newsletter_editor.py
  prepare_newsletter_context → generate_newsletter_draft → refine_newsletter_draft

[Editor subgraph — deprecated] newsletter_agent_skeleton.py app
  analysis → standards_linker → editor → draft/  (Chat UI 전용)

(Human) Streamlit HITL + 발행 확정 → published/ + registry/
```

| 구성요소 | 역할 | 상태 |
|----------|------|------|
| `fetch_script.py` | Research Agent | ✅ |
| `research_review_agent.py` | Collect Orchestrator (subprocess, 레거시) | ✅ |
| `newsletter_orchestrator.py` | **단일 Newsletter Orchestrator** (v0.6) | ✅ |
| `newsletter_editor.py` | Editor prepare/generate/refine | ✅ |
| `newsletter_workflow_state.py` | `NewsletterWorkflowState` | ✅ |
| `hitl_routing.py` | threshold HITL 라우팅 | ✅ |
| `published_registry.py` | 기발행 hash 차단 | ✅ |
| `review_script.py` | Analysis Agent (1차) | ✅ |
| `standards_radar_script.py` | Standards Radar | ✅ |
| `standards_linker_node` | 기사별 IETF 맥락 | ✅ |
| `newsletter_agent_skeleton.py` | Editor subgraph (Chat UI, deprecated) | ✅ |
| `pipeline_graph.py` | deprecated → orchestrator wrapper | ✅ |
| `streamlit_app.py` | HITL + Orchestrator UI | ✅ |
| Chat UI | LangGraph dev | ⬜ |

**판정:** collect~draft가 **단일 StateGraph**로 통합됐고, Editor는 함수+node 3분할로 시연·추적이 명확하다.

### 2.2 Structured Output — ✅ 반영 완료

| 모델 | 용도 | 파일 |
|------|------|------|
| `ReviewResult` | 1차 리뷰 | `review_script.py` |
| `RawArticle` | 로더 출력 | `newsletter_agent_skeleton.py` |
| `ArticleAnalysis` | 2차 분석 + `standards_context` | `newsletter_agent_skeleton.py` |
| `NewsletterOutput` | 최종 뉴스레터 | `newsletter_agent_skeleton.py` |
| `BiasJudge` | LLM-as-Judge | `analysis_node` |

`CategoryType` 9카테고리 + `Other` — `sources.yaml`과 동기화됨.

### 2.3 Vault Artifact Store — ✅ 확장

| 경로 | 역할 |
|------|------|
| `01_raw/` | 수집 원문 |
| `02_review/` | LLM 1차 리뷰 |
| `03_approved/` | HITL 승인 |
| `99_rejected/` | HITL 반려 |
| `04_newsletter/draft/` | Orchestrator 생성·재생성 |
| `04_newsletter/published/` | 발행 스냅샷 |
| `registry/published_articles.json` | 기발행 hash registry |
| `04_newsletter/ietf_radar.md` | IETF Radar 전체 |
| `output/pipeline_runs/` | Orchestrator state·events |

### 2.4 IETF 표준 맥락 — ✅ v0.3 설계 적합

| 방식 | 판정 |
|------|------|
| Radar 전체를 뉴스레터 하단 append | ❌ 제거 — 노이즈·중복 |
| `standards_linker_node` 기사별 연결 | ✅ 룰 기반, LLM 비용 없음 |
| IETF Radar 탭에서 전체 Preview | ✅ HITL/Newsletter와 역할 분리 |

### 2.5 Fallback — ✅ 적합

`load_sample_node` + `sample_articles.json` + Streamlit `fallback_used` 표시.

---

## 3. 데이터 수집 검토

### 3.1 소스 선정 — ✅ 사전 테스트 반영

Tier 1~3 + IETF reference 소스가 `sources.yaml`에 등록되어 있고, [sources-checklist.md](./sources-checklist.md)로 검증한다.

**최소 동작 조합:** `apnic_blog` + Orchestrator collect + HITL 1건 승인 + Orchestrator draft

### 3.2 MVP 상한 — ✅ 시연 안정화

`mvp_limits.py` — `MVP_MAX_ARTICLES_PER_SOURCE`, `MVP_MAX_REVIEW`, `MVP_REVIEW_SEED`

---

## 4. UI 구성 검토

### 4.1 Streamlit v0.7 — ✅ 적합

| 탭 | 검토 결과 |
|----|-----------|
| 실행 | **Newsletter Orchestrator** · Workflow 상태 |
| 기사 검토 | **통합 HITL** — RSS · Tavily · threshold 큐 · 출처 필터 |
| 뉴스레터 | Orchestrator draft/published + registry 연동 발행 |
| 아카이브 | 05_archive + 06_used |
| 운영콘솔 | Discovery staging · gate 로그 · IETF Radar · Tool 로그 |

**다크모드:** `inject_theme_css()` 적용 — WG 카드·HITL 메타 가독성 해결.

### 4.2 Chat UI — ⬜ 미구현 (리스크 낮음)

보조 시연 채널. Streamlit v0.7만으로 Multi-Agent·통합 HITL·뉴스레터 시연 가능.
시간 있을 때 `langgraph.json` + deprecated Editor subgraph 연결.

---

## 5. 개발 우선순위 검토 (실적)

| 순서 | 기능 | 상태 |
|------|------|------|
| 1 | `sources.yaml` | ✅ |
| 2 | Research + Analysis Agent | ✅ |
| 3 | Standards Radar + Linker | ✅ |
| 4 | Editor (함수 + Orchestrator node) | ✅ |
| 5 | Streamlit HITL | ✅ |
| 6 | Streamlit v0.6 + Orchestrator | ✅ |
| 7 | draft/published 발행 + registry | ✅ |
| 8 | Tool 로깅 + MVP 상한 | ✅ |
| 9 | `docs/` 문서 체계 | ✅ |
| 10 | **Newsletter Orchestrator** (v0.6) | ✅ |
| 11 | Chat UI | ⬜ |

---

## 6. 패턴 적용 검토

| 패턴 | 명세서 계획 | 구현 | 판정 |
|------|-----------|------|------|
| Structured Output | Pydantic 3모델+ | ReviewResult 포함 | ✅ |
| RAG / 샘플 fallback | load_sample | `load_sample_node` | ✅ |
| 도구 다중 호출 | fetch + Tavily | `fetch_script` + `tavily_node` | ✅ |
| HITL | 승인/반려 | Streamlit + `vault_utils` | ✅ |
| Multi-Agent | StateGraph | 배치 Agent + Orchestrator | ✅ |
| LLM-as-Judge | 편향 검토 | review + analysis_node | ✅ |
| Rule-based linker | (v0.3) | standards_linker_node | ✅ |
| Newsletter Orchestrator | (v0.6) | newsletter_orchestrator.py | ✅ |
| Editor node 분리 | (v0.6) | newsletter_editor.py | ✅ |
| Threshold HITL | (v0.5) | hitl_routing.py | ✅ |
| Published registry | (v0.5) | published_registry.py | ✅ |

---

## 7. 실패하면 안 되는 케이스

| No | 케이스 | v0.6 동작 | 판정 |
|----|--------|-----------|------|
| 1 | 무관 문서 | `category: Other` → editor 제외 | ✅ |
| 2 | 벤더 편향 | `bias_flag`, `bias_note`, HITL | ✅ |
| 3 | 수집 실패 | `load_sample_node`, `fallback_used` | ✅ |
| 4 | IETF를 뉴스처럼 혼재 | `standards_signal` skip + Radar 분리 | ✅ |
| 5 | 기발행 기사 재사용 | `published_registry` hash 이중 차단 | ✅ |

---

## 8. 산출물 체크리스트 (2026-07-01)

| 산출물 | 필수 | 상태 |
|--------|------|------|
| `fetch_script.py` | ✅ | ✅ |
| `review_script.py` | ✅ | ✅ |
| `standards_radar_script.py` | ✅ | ✅ |
| `research_review_agent.py` | ✅ | ✅ |
| `newsletter_orchestrator.py` | ✅ | ✅ |
| `newsletter_editor.py` | ✅ | ✅ |
| `newsletter_agent_skeleton.py` | ✅ | ✅ |
| `pipeline_graph.py` (deprecated) | ✅ | ✅ |
| `published_registry.py` | ✅ | ✅ |
| `streamlit_app.py` (v0.6) | ✅ | ✅ |
| `vault_utils.py` | ✅ | ✅ |
| `sources.yaml` | ✅ | ✅ |
| `docs/` (명세·검토·아키텍처) | ✅ | ✅ |
| `sample_articles.json` | ✅ | ✅ |
| `langgraph.json` + Chat UI | ✅ | ⬜ |
| 발표 시나리오 | ✅ | 🟡 docs 기반 정리 가능 |

---

## 9. 디렉토리 구조 (현행)

```
class/mini pjt/
├── docs/
│   ├── assignment-spec.md      # 과제 설명서 v1.6
│   ├── assignment-review.md    # ← 본 문서
│   ├── architecture.md
│   └── ...
├── newsletter_orchestrator.py  # 단일 LangGraph (v0.6)
├── newsletter_editor.py
├── newsletter_workflow_state.py
├── pipeline_graph.py           # deprecated wrapper
├── streamlit_app.py
├── vault/
└── output/pipeline_runs/
```

---

## 10. 리스크·완화

| 리스크 | 영향 | 완화 |
|--------|------|------|
| RSS/API 수집 실패 | collect 빈 결과 | sample fallback + Orchestrator count 표시 |
| LLM 비용·지연 | 시연 타임아웃 | MVP 상한 · `--sources` 제한 |
| Chat UI 미구현 | 보조 시연 불가 | Streamlit v0.6으로 충분 시연 가능 |
| State vs Vault 불일치 | draft 실패 | `NewsletterWorkflowState`는 path만 · Vault가 source of truth |

---

## 11. 최종 판정

| 항목 | 판정 |
|------|------|
| 과제 적합성 | ✅ Day 8 LangGraph 해커톤 목표와 일치 |
| 기술 완결성 | ✅ collect~draft~발행 E2E 동작 |
| 시연 가능성 | ✅ Orchestrator 단계·count·HITL·registry 설명 가능 |
| 문서 정합성 | ✅ v0.6 docs 동기화 |
| 잔여 리스크 | 🟡 Chat UI만 미구현 (필수 아님) |

### 체크리스트 (제출 전)

- [x] **newsletter_orchestrator.py 단일 StateGraph (v0.6)**
- [x] **newsletter_editor.py editor node 3분할**
- [x] threshold HITL + published registry
- [x] Streamlit 6탭 + Orchestrator UI
- [x] `docs/` v0.6 갱신
- [ ] Chat UI (선택)

---

*본 검토 보고서는 Day 8 해커톤 기술 적합성 확인용. v0.7 (2026-07-01). 위치: `docs/assignment-review.md`*
