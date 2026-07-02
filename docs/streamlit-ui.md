# Streamlit UI (v0.7)

## 실행

```bash
cd "mini pjt"
streamlit run streamlit_app.py
```

> `python streamlit_app.py`는 자동으로 `streamlit run`으로 재실행됩니다.

## 탭 구성

| 순서 | 탭 | 역할 |
|------|-----|------|
| 1 | ▶ 실행 | **Newsletter Orchestrator** (LangGraph) · 소스 선택 · Workflow 상태 |
| 2 | 📋 기사 검토 | **통합 HITL** — RSS · 등록소스 · Tavily 웹검색 모두 `02_review/` |
| 3 | 📰 뉴스레터 | draft 생성 · Preview · 발행 확정 |
| 4 | 📦 아카이브 | `05_newsletter_archive` · `06_newsletter_used` |
| 5 | ⚙️ 운영콘솔 | Discovery staging · quality gate 로그 · IETF Radar · Tool 로그 |

### 제거된 탭 (v0.7)

| 이전 | 변경 |
|------|------|
| 🔍 웹검색 후보 | **제거** — Tavily는 Orchestrator에서 자동 `02_review` 생성 |
| ✅ 1차 검토 | **📋 기사 검토**로 통합 |
| 📡 IETF Radar | **⚙️ 운영콘솔**로 이동 (standards_context, 뉴스레터 기사 HITL 대상 아님) |

## 실행 — Newsletter Orchestrator

1. `sources.yaml` 소스 표 + multiselect
2. **▶ 수집 + HITL 큐** — `run_orchestrator_workflow(mode="collect")`
3. **▶ Draft 생성** — `mode="draft"`
4. **▶ 전체 실행** — `mode="full"`
5. **Workflow 상태** — vault 실시간 집계 · `step_status` · run_id · draft_path

### Orchestrator 버튼

| 버튼 | mode | Graph node까지 |
|------|------|----------------|
| 수집 + HITL 큐 | `collect` | collect → expansion_search → standards_radar → first_review → threshold_routing → END |
| Draft 생성 | `draft` | → editor_prepare → … → draft_created |
| 전체 실행 | `full` | collect ~ draft (승인 기사 있을 때) |

### 수집 흐름 (v0.7)

```
01_raw/{source_id}/     ─┐
01_raw/expansion/       ─┤→ review_script → 02_review/
                         ↓
               기사 검토 탭 (단일 HITL)
```

- Tavily 결과도 **staging 없이** `01_raw/expansion/`에 저장 후 `review_script` 처리
- Gate 제외 로그: `logs/discovery/` (운영콘솔)

## 기사 검토 (통합 HITL)

RSS · 등록소스 · Tavily 결과를 모두 `02_review/` 기준으로 검토합니다.  
UI 점수는 **`review_score`** 중심 (`discovery_score`는 운영콘솔·상세 메타만).

### 검토 큐

| 큐 | 조건 |
|----|------|
| 승인 대기 | `hitl_route = approval_pending` (review_score ≥ 0.80) |
| 추가 검토 | `hitl_route = needs_human_review` (0.55 ~ 0.80 또는 gate/bias) |
| 재수집 필요 | `recollect_required = true` |
| 전체 (미발행) | `is_published = false` |
| 기발행 차단 | registry 매칭 — 승인 불가 표시 |

### 필터

| 필터 | 옵션 |
|------|------|
| 출처 유형 | 전체 / 등록소스 / 웹검색 / Vendor / Standards |
| 카테고리 | 9 + Other |
| 최소 importance | 0~5 |
| 검색어 | 제목·본문·요약 |
| 고급 | bias_risk · source_id / source_name |

### 목록 라벨 예

```
★4 · 0.86 · RSS · APNIC — 제목
★3 · 0.72 · Web · expansion/routing_ops — 제목
★4 · 0.80 · Vendor · Kentik — 제목
```

### 승인 / 반려

| 액션 | 결과 |
|------|------|
| ✅ 승인 | `03_approved/` |
| ❌ 반려 | `99_rejected/` |

## 운영콘솔

| 섹션 | 내용 |
|------|------|
| Expansion raw | `01_raw/expansion/` 건수 · gate 제외 · 저점수 |
| Expansion 목록 | Tavily raw 미리보기 (`discovery_score`는 디버그용) |
| Quality gate 제외 | `logs/discovery/search_discarded.jsonl` 최근 사유 |
| IETF Radar | WG 컨텍스트 · Radar Preview · 재실행 버튼 |
| Tool 로그 | Orchestrator 실행 시 `logs/tool_runs.jsonl` 집계 |

## 뉴스레터 생성

1. Approved / Draft / Published 메트릭
2. **뉴스레터 생성 (draft)** — `run_orchestrator_workflow(mode="draft")`
3. Draft Preview · **발행 확정** (`publish_newsletter()`)

발행은 Graph 밖 — Streamlit 수동 처리. 입력은 **`03_approved`만**.

## Sidebar

- Vault 건수 (Raw · **Expansion** · Review · Approved · Newsletter · IETF Radar)
- MVP 상한 · Last Run · Recent Tool (Orchestrator 실행 시)

## 타임아웃

| 스크립트 | 초 |
|----------|-----|
| `fetch_script.py` | 1200 |
| `review_script.py` | 3600 |
| `standards_radar_script.py` | 300 |
| `newsletter_orchestrator.py` (full) | subprocess 내부 |
