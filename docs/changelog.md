# 변경 이력

프로젝트 MVP 개발 중 반영된 주요 변경 사항입니다.

---

## v0.7 — HITL 승인 흐름 통일 + Tavily 자동 파이프라인

### HITL UX

- **웹검색 후보** 탭 제거 — Tavily 2단계 HITL (후보 + 1차 검토) 해소
- **기사 검토** 탭 — RSS · 등록소스 · Tavily 모두 `02_review/` 통합 HITL
- **운영콘솔** 탭 신설 — staging · gate 로그 · IETF Radar · Tool 로그
- Streamlit 탭: **실행 → 기사 검토 → 뉴스레터 → 아카이브 → 운영콘솔**

### Tavily 자동 처리

- `ipn_agent/collect/discovery.py` — quality gate → `01_raw/expansion/` → LLM Review → `02_review/`
- `00_discovery/candidates/` — UI 메인 검토 대상 아님, `auto_processed` staging만
- RSS보다 엄격한 quality gate (본문 길이 · URL/registry 중복 · bias · 날짜)

### Review 메타 통일

- `ipn_agent/review/metadata.py` — `source_type`, `origin`, `review_score`, `hitl_route` 등 통합 frontmatter
- UI 점수: **`review_score` 중심** · `discovery_score`는 운영콘솔·상세 메타

### Streamlit

- `render_article_review_tab()` — 검토 큐 · 출처 유형 필터 · source_type badge 라벨
- `render_ops_console_tab()` — staging 집계 · 제외 사유 jsonl · IETF Radar
- Sidebar Discovery → **Staging** 라벨

### 문서 · 패키지

- `docs/` v0.7 갱신 (streamlit-ui, vault-structure, architecture, changelog)
- **`ipn_agent/` 패키지 구조** — flat root `.py` → 역할별 서브패키지, CLI wrapper 유지 (`docs/project-structure.md`)

---

## v0.6 — Newsletter Orchestrator 단일 Graph + Editor node 통합

### 구조 개편

- `pipeline_graph.py` → **`newsletter_orchestrator.py`** (메인 LangGraph 진입점)
- `pipeline_state.py` → **`newsletter_workflow_state.py`** (`NewsletterWorkflowState`)
- **`newsletter_editor.py`** — `prepare_newsletter_context()` · `generate_newsletter_draft()` · `refine_newsletter_draft()`
- Editor node 분리: `editor_prepare` → `editor_generate` → `editor_quality_check` → `draft_created`
- `pipeline_graph.py` / `run_pipeline()` — deprecated wrapper 유지
- `newsletter_agent_skeleton.py` — Editor subgraph Chat UI용, `run_newsletter()` → orchestrator/editor wrapper

### Streamlit

- **Newsletter Orchestrator** 버튼을 기본 경로로 지정
- Collect & Analyze → 레거시 expander로 이동
- Workflow 상태에 editor quality 표시

### 문서

- `docs/` v0.6 전면 갱신 (assignment-spec v1.6, architecture, orchestrator 등)

---

## v0.5 — Pipeline StateGraph · threshold HITL · published registry

### Pipeline StateGraph (`pipeline_graph.py`)

- 수집 → Discovery → Radar → Review → **threshold routing** → HITL 대기 → approved 필터 → editor draft
- 기존 스크립트는 **Graph node wrapper**로 감싸 subprocess 호출 유지
- `PipelineState` — metadata·path만 저장 (원문 본문 state 미저장)
- 실행 모드: `collect` | `draft` | `full`
- 로그: `output/pipeline_runs/{run_id}/state.json`, `events.jsonl`

### 신규 모듈

| 파일 | 역할 |
|------|------|
| `pipeline_state.py` | `PipelineState`, `ArticleRef`, count 헬퍼 |
| `pipeline_graph.py` | 전체 LangGraph StateGraph |
| `hitl_routing.py` | score threshold 라우팅 (LLM 없음) |
| `published_registry.py` | `vault/registry/published_articles.json` hash 중복 차단 |
| `pipeline_articles.py` | vault md → `ArticleRef` 스캔 |
| `pipeline_logging.py` | run state·events 저장 |
| `pipeline_hitl_apply.py` | `02_review` frontmatter 갱신, auto-reject 이동 |

### Threshold HITL

- `importance_score` 1~5 → `review_score` (0.0~1.0)
- ≥ 0.80 → `approval_pending` (자동 approved **없음**)
- 0.55 ~ 0.80 → `needs_human_review`
- < 0.55 → `rejected` → `99_rejected/`
- 최종 `approved`는 Streamlit 사람 승인만

### 기발행 차단 (`published_registry.py`)

- registry: `vault/registry/published_articles.json`
- 중복 판정: `article_id`, `normalized_url_hash`, `content_hash`, `title_hash`+`source`
- 이중 차단: HITL 진입 전 + draft 생성 직전
- `publish_newsletter()` — 발행 시 registry 등록 + `06_used` 동기화

### Streamlit

- **Pipeline Collect / Draft / Full** 버튼 (수집/리뷰 탭)
- Pipeline count·run_id 표시
- HITL 탭: 승인 대기 / 추가 검토 / 기발행 차단 / 승인 완료 구분

### Newsletter

- `run_newsletter_from_pipeline()` — 지정 approved 경로만 요약 기반 draft (기존 CLI 유지)

### 토큰 최적화 원칙

- State·LLM 프롬프트에 기사 원문 전체 금지
- dedupe / threshold / registry는 rule 기반
- review·editor 결과 파일 캐시 재사용

### 문서

- `docs/` 전면 갱신 (architecture, vault, streamlit, assignment-spec 등)

---
### 발행 lifecycle (`publish_newsletter`)

- 발행 확정 시 `draft/` **삭제**
- `03_approved` → `06_newsletter_used/{issue_date}/` **이동**
- draft frontmatter: `included_urls`, `included_approved_files`
- Streamlit 발행 **확인 체크박스**

### URL 중복 방지 (`article_registry.py`)

- `canonical_url()` — query/fragment 제거
- fetch: vault 전역 URL 존재 시 raw SKIP
- review: 02/03/06에 URL 있으면 SKIP
- 발행: `01_raw`에 `newsletter_used_in` 마킹

### Streamlit

- **📦 아카이브** 탭 분리 (05_archive + 06_used)
- 뉴스레터 탭: Draft/Published만
- Sidebar Used 건수

### reset_vault

- Phase `06` — `06_newsletter_used/`

### 문서

- `docs/vault-structure.md`, `newsletter-pipeline.md`, `streamlit-ui.md` 갱신

---

## v0.3 — Streamlit 재구성 + IETF 기사별 맥락 + 발행 관리

### Streamlit v0.3

- 탭 순서: **Sources & Analyze → IETF Radar → HITL Review → Newsletter**
- Vault Admin / Agent Console 탭 제거
- Sidebar: Vault 상태, MVP 상한, Last Run, Recent Tool
- Sources & Analyze: pandas 소스 표, Collect & Analyze Orchestrator 연동
- `use_container_width` → `width="stretch"` (Streamlit deprecation 대응)

### Orchestrator

- `research_review_agent.py` 추가
- 순서: fetch → standards_radar → review

### Tool 로깅

- `tool_logger.py` → `logs/tool_runs.jsonl`
- 각 Agent 스크립트 `log_tool_event()` 연동
- Streamlit Aggregate Tool 상태 표시

### HITL / Vault

- `vault_utils.py`: 승인 → `03_approved`, 반려 → `99_rejected`
- `parse_review_body`, `load_sources_from_yaml`
- `ietf_radar.md` Newsletter 카운트 제외

### review_script 안정화

- Windows Unicode `_safe_print`, stdout UTF-8
- Streamlit Analysis 타임아웃 3600초
- `newsletter_candidate` → 25~45자 헤드라인 (`normalize_newsletter_headline`)
- 섹션명 `# 뉴스레터 헤드라인`

### MVP 상한 (`mvp_limits.py`)

- `MVP_MAX_ARTICLES_PER_SOURCE`, `MVP_MAX_REVIEW`, `MVP_REVIEW_SEED`
- 후보 필터 → shuffle → 상한 처리

### 뉴스레터 출력

- 카드형 Markdown (`_format_article_card`)
- `03_approved` frontmatter/리뷰 메타 재사용
- `CategoryType` 확장 (Routing/Internet Operations 등)

### IETF Radar — 기사별 표준 맥락

- `ietf_radar.md` 하단 append **제거**
- `ArticleAnalysis.standards_context` optional 필드
- `standards_linker_node` (LLM 없음, 키워드 룰)
- 그래프: analysis → (hitl) → standards_linker → editor
- Streamlit Newsletter 탭: Radar 전체 섹션 제거, IETF Radar 탭 유지

### 다크모드

- `inject_theme_css()` + `.ipn-theme-card` 클래스
- WG 카드, HITL 메타, Tool 로그 카드 테마 변수 적용

### 발행 관리 (draft / published)

- `04_newsletter/draft/` — Agent 생성
- `04_newsletter/published/` — 발행 스냅샷
- `publish_newsletter()` frontmatter (`status`, `published_at`, `issue_date`)
- Streamlit: Draft / Published 분리 UI
- 레거시 루트 `*-newsletter.md` 호환

| 발행 관리 (draft / published) | ✅ |

### 문서

- `docs/` 폴더 — assignment-spec · assignment-review 포함
- 루트 `IP_Newsletter_Agent_*.md` → docs stub

---

## v0.2 — Streamlit HITL MVP

- Streamlit HITL Review 탭
- Obsidian Vault 연동
- fetch / review / newsletter skeleton 기본 파이프라인

---

## v0.1 — 초기 스켈레ton

- `sources.yaml`, `fetch_script.py`, `review_script.py`
- `newsletter_agent_skeleton.py` LangGraph 골격
- Vault `01_raw` ~ `04_newsletter` 기본 구조

---

## 미구현 / P2 백로그

- [ ] `review_script` frontmatter `standards_related` 사전 태깅
- [ ] draft vs published diff UI
- [ ] PDF/HTML export, 구독자 발송
- [ ] RAG — `published/`만 인덱싱
- [ ] SQLite 메타 인덱스 (vault md + registry 동기화)
- [ ] Editor Orchestrator + Chat UI
- [ ] `llm_usage.jsonl` token 집계 UI
