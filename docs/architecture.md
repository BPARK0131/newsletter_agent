# 아키텍처

## 전체 파이프라인 (v0.7)

```
[sources.yaml]
      │
      └─ newsletter_orchestrator.py (단일 LangGraph)
            load_sources → collect → expansion_search → standards_radar
            → first_review → threshold_routing → END
            (draft mode: load_approved → filter_published → editor_* → draft_created)
      │
      ▼
 vault/01_raw/ (RSS + expansion) → review_script → 02_review/ → (통합 HITL) → 03_approved/ → draft/
      │
      ▼
 Streamlit publish_newsletter() → published/ + registry + 06_used/
```

### Tavily Discovery (collect 단계)

Orchestrator `expansion_search` node → `fetch_script.run_expansion_search()`:

```
Tavily Result → discovery_score → apply_tavily_quality_gate()
  → 01_raw/expansion/{category}/
  → (Orchestrator 후반) review_script → 02_review/
```

Gate 제외·저점수 로그: `logs/discovery/*.jsonl` (vault 밖)

### IETF Radar (Standards Radar Agent)

뉴스 수집·리뷰 파이프라인과 **분리된 reference 전용** 흐름이다. 상세 역할: [assignment-spec.md §10.3](./assignment-spec.md#103-ietf-radar-standards-radar-agent--역할-정의)

```
ietf_datatracker API (WG 5개)
        │
        ▼
fetch_script.collect_api()  →  01_raw/ietf_datatracker/*.md
        │                        (review_script SKIP — standards_signal)
        ▼
standards_radar_script.py   →  04_newsletter/ietf_radar.md
        │
        ├─ 운영콘솔: Radar 전체 Preview
        └─ draft: standards_linker_node → 기사별 standards_context만
```

| 항목 | 내용 |
|------|------|
| Agent | Standards Radar Agent (`ipn_agent.standards.radar`) |
| Collect | Orchestrator `collect` 시 `ietf_datatracker` 자동 포함 |
| HITL | ❌ — 기사 검토 큐 대상 아님 |
| LLM | ❌ — `wg_radar` + 키워드 룰 Linker |

| 게이트 조건 | 동작 |
|-------------|------|
| discovery_score < min | 제외 |
| 본문 < 500자 | 제외 |
| URL/registry 중복 | 제외 |
| thin body / bias high / 날짜 불확실 | `needs_human_review` 라우트 |

## 단일 Orchestrator — `newsletter_orchestrator.py`

| 항목 | 내용 |
|------|------|
| State | `NewsletterWorkflowState` (`newsletter_workflow_state.py`) |
| Graph | `build_newsletter_workflow()` → `newsletter_app` |
| 실행 | `run_newsletter_workflow(mode=collect\|draft\|full)` |
| 로그 | `output/pipeline_runs/{run_id}/state.json`, `events.jsonl` |

### Editor node (Orchestrator 내부)

| Node | 역할 | 구현 |
|------|------|------|
| `editor_prepare` | approved 경로 검증·입력 기사 count | `newsletter_editor.prepare_newsletter_context()` |
| `editor_generate` | analysis → standards_linker → hitl → editor | `newsletter_editor.generate_newsletter_draft()` |
| `editor_quality_check` | draft 품질·파일 존재 확인 | `newsletter_editor.refine_newsletter_draft()` |
| `draft_created` | run 완료 마킹 | — |

Editor 핵심 로직은 **`newsletter_editor.py`**에 분리. Orchestrator node가 직접 호출한다.

### NewsletterWorkflowState 원칙

- 기사 **원문 본문 저장 금지** — metadata·path·hash만
- LLM에 전체 state 통째 전달 금지
- threshold · registry · dedupe는 **LLM 없음**

## 진입점

| 경로 | 용도 | LangGraph |
|------|------|-----------|
| **`newsletter_orchestrator.py`** | Streamlit 기본 · CLI | ✅ 단일 Graph |
| `research_review_agent.py` | 레거시 Collect & Analyze | ❌ subprocess |
| `newsletter_agent_skeleton.app` | Chat UI / langgraph.json | ✅ deprecated Editor subgraph |
| `pipeline_graph.py` | deprecated wrapper | → orchestrator re-export |

## threshold HITL (`hitl_routing.py`)

| review_score | hitl_route | Streamlit |
|--------------|------------|-----------|
| ≥ 0.80 | `approval_pending` | 승인 대기 |
| 0.55 ~ 0.80 | `needs_human_review` | 추가 검토 |
| < 0.55 | `rejected` | 자동 제외 (`99_rejected/`) |

`approved`는 Streamlit 사람 승인만.

## 기발행 차단 (`published_registry.py`)

- `vault/registry/published_articles.json`
- 이중 차단: HITL 목록 + `filter_published_articles` node

## Graph 밖 (Streamlit)

- **기사 검토** 탭 — 통합 HITL 승인/반려 (RSS · Tavily · Vendor)
- `publish_newsletter()` 발행 확정
- **운영콘솔** — Expansion raw · gate 로그 · IETF Radar · Tool 로그

## Review 메타 정규화 (`review_metadata.py`)

RSS / Tavily / Vendor 공통 `02_review` frontmatter:

| 필드 | 설명 |
|------|------|
| `source_type` | rss · tavily · manual · ietf · vendor |
| `origin` | curated_source · open_web_search · standards_context |
| `trust_level` | high · medium · low |
| `review_score` | UI 주 점수 |
| `discovery_score` | Tavily 품질 보조 (운영콘솔) |
| `hitl_route` | approval_pending · needs_human_review · rejected |
| `is_published` | registry 차단 플래그 |

## Multi-Agent vs Orchestrator

| 구분 | 이 프로젝트 |
|------|-------------|
| Agent 경계 | fetch / review / radar — **별도 스크립트** (subprocess wrapper) |
| Artifact Store | Obsidian Vault + published registry |
| **Orchestration** | **`newsletter_orchestrator.py` 단일 StateGraph** |
| Editor 로직 | `newsletter_editor.py` (함수) + Orchestrator editor node |
| HITL | threshold routing + Streamlit **기사 검토** (단일 단계) |

Vault는 **Agent handoff·HITL·발행 이력**을 담는 공유 저장소입니다.
