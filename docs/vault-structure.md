# Vault 구조

Obsidian에서 **Open folder as vault**로 `vault/` 폴더를 엽니다.

> Agent 산출물·HITL 큐·발행 스냅샷은 모두 이 vault 아래 Markdown으로 교환합니다.  
> Quality gate **제외 로그**만 vault 밖 `mini pjt/logs/discovery/`에 둡니다.

## 폴더 트리

```
vault/
├── 01_raw/                    Phase 1 — collect (fetch + Tavily expansion)
│   ├── {source_id}/           RSS · API · blog_index 등록 소스
│   │   └── YYYY-MM-DD-title.md
│   └── expansion/             Tavily quality gate 통과분
│       └── {category_id}/
│           └── YYYY-MM-DD-title.md
│
├── 02_review/                 Phase 2 — review_script.py LLM 리뷰 + **통합 HITL 큐**
│   └── YYYY-MM-DD__source_id__title-slug.md
│
├── 03_approved/               HITL 승인 (Streamlit **기사 검토** 탭)
│
├── 04_newsletter/             Phase 4 — 뉴스레터 · IETF Radar
│   ├── draft/                 Agent 생성·재생성 (발행 후 삭제)
│   ├── published/             발행 확정 스냅샷 (불변)
│   └── ietf_radar.md          표준화 Radar (기사 HITL 대상 아님)
│
├── 05_newsletter_archive/     발행 호별 영구 아카이브
│   └── {issue_date}/
│
├── 06_newsletter_used/        발행에 사용된 승인 기사
│   └── {issue_date}/
│
├── registry/                  기발행 registry
│   └── published_articles.json
│
└── 99_rejected/               HITL 반려 · threshold 자동 제외
```

### vault 밖 (운영 로그)

```
mini pjt/logs/
├── tool_runs.jsonl            Tool 실행 로그 (Streamlit)
└── discovery/
    ├── search_discarded.jsonl   Tavily gate 제외·중복·저점수
    └── search_low_score.jsonl   score 3 ~ min_score-1
```

---

## Phase · 스크립트 매핑

| Vault | 생성 주체 | 소비 주체 |
|-------|-----------|-----------|
| `01_raw/` | `fetch_script.py` (RSS/API/blog + `--expansion-search`) | `review_script.py`, `standards_radar_script.py` |
| `02_review/` | `review_script.py` | Streamlit 기사 검토, threshold routing |
| `03_approved/` | HITL 승인 | Newsletter Orchestrator (draft) |
| `04_newsletter/` | Newsletter Agent / Orchestrator | Streamlit 발행 |
| `registry/` | `publish_newsletter()` | Collect·Draft 중복 차단 |
| `99_rejected/` | HITL 반려 · auto-reject | — |

---

## 상태 전이

```
[RSS/API/blog]  fetch  →  01_raw/{source_id}/
[Tavily]        expansion_search + quality gate  →  01_raw/expansion/{category}/

01_raw/**  ── review_script ──►  02_review/
                                      │
                                      ├── threshold ──► approval_pending / needs_human_review
                                      ├── score < 0.55 ──► 99_rejected
                                      │
                                      ├── HITL 승인 ──► 03_approved/
                                      └── HITL 반려 ──► 99_rejected/

03_approved/  ── draft pipeline ──►  04_newsletter/draft/
                                         │
                                         └── 발행 ──► published/
                                                      + 05_archive/
                                                      + 06_used/{issue}/
                                                      + registry/
                                                      (draft 삭제, 01_raw URL 마킹)
```

### Tavily Discovery (collect 단계)

```
Tavily Search
  → discovery_score (1~5)
  → apply_tavily_quality_gate()
  → 01_raw/expansion/{category}/     ← raw만 저장
  → (Orchestrator 후반) review_script
  → 02_review/
  → Streamlit 기사 검토
```

Gate 제외 사유: `logs/discovery/search_discarded.jsonl`  
저점수 기록: `logs/discovery/search_low_score.jsonl`

---

## `01_raw/` 상세

| 하위 경로 | source_name 예 | 수집 방식 |
|-----------|----------------|-----------|
| `apnic_blog/` | `apnic_blog` | RSS |
| `ietf_datatracker/` | `ietf_datatracker` | API (Radar 신호, 일반 HITL 제외 가능) |
| `tmforum_newsroom/` | `tmforum_newsroom` | blog_index |
| `expansion/routing_ops/` | `expansion/routing_ops` | Tavily expansion_search |

파일명: `{published_date}-{title-slug}.md`  
리뷰 파일명: `{date}__{source_id}__{title-slug}.md` (`/` in source_id → `__`)

---

## URL 중복 방지

검사 대상 Phase: `01_raw`, `02_review`, `03_approved`, `06_newsletter_used`, `99_rejected`

| 단계 | 동작 |
|------|------|
| **fetch / discovery** | vault 전역 canonical URL → 있으면 SKIP |
| **review** | 동일 URL이 review/approved/used → SKIP |
| **발행** | `01_raw` 동일 URL에 `newsletter_used_in` 마킹 |

---

## registry (`registry/published_articles.json`)

발행된 기사 hash·URL·title registry. Draft·Collect에서 기발행 제외.

- `publish_newsletter()` — 발행 시 등록
- `sync_registry_from_used_folder()` — `06_used` 백필

---

## 환경 변수

```
OBSIDIAN_VAULT_PATH=C:/path/to/mini pjt/vault
```

미설정 시 프로젝트 내 `vault/` 기본 사용 (`get_vault_path()`가 하위 폴더 자동 생성).

---

## reset_vault.py Phase

| Phase | 폴더 / 대상 |
|-------|-------------|
| `01` | `01_raw/` |
| `02` | `02_review/` |
| `03` | `03_approved/` |
| `04` | `04_newsletter/` |
| `05` | `05_newsletter_archive/` |
| `06` | `06_newsletter_used/` |
| `registry` | `registry/published_articles.json` |
| `99` | `99_rejected/` |

Gate 로그는 vault가 아니므로 `reset_vault.py` 대상이 아닙니다. 필요 시 `logs/discovery/`를 직접 삭제하세요.
