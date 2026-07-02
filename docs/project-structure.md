# 프로젝트 구조 (v0.8)

Python 코드는 `ipn_agent/` 패키지 아래 역할별로 정리되어 있습니다.  
CLI·Streamlit 진입점은 **프로젝트 루트**에 thin wrapper로 유지합니다 (기존 명령 호환).

> v0.8에서 deprecated 상태였던 `pipeline_graph.py` · `newsletter_agent_skeleton.py`(Chat UI subgraph) · `langgraph.json`을 실제로 삭제했습니다. `newsletter_orchestrator.py`가 유일한 진입점입니다. 상세: [changelog.md](./changelog.md)

## 디렉터리 트리

```
mini pjt/
├── streamlit_app.py          # Streamlit UI 진입점
├── sources.yaml              # 수집 소스·expansion_search 설정
├── requirements.txt
├── .env                      # 로컬 전용 (Git 제외)
│
├── ipn_agent/                 # 메인 Python 패키지
│   ├── paths.py               # PROJECT_DIR (루트 기준 경로)
│   ├── core/                  # 공통 유틸
│   │   ├── tool_logger.py
│   │   └── mvp_limits.py
│   ├── registry/              # URL·발행 중복 registry
│   │   ├── article.py
│   │   └── published.py
│   ├── vault/                 # Obsidian Vault I/O
│   │   ├── utils.py
│   │   └── reset.py
│   ├── collect/                # Phase 1 — 수집·Discovery
│   │   ├── fetch.py
│   │   ├── extract.py
│   │   └── discovery.py
│   ├── review/                 # Phase 2 — LLM Review·HITL 메타
│   │   ├── runner.py
│   │   ├── metadata.py
│   │   └── hitl.py
│   ├── orchestrator/           # LangGraph Workflow·Editor
│   │   ├── workflow.py         # Newsletter Orchestrator StateGraph
│   │   ├── state.py            # NewsletterWorkflowState
│   │   ├── editor.py           # prepare/generate/refine
│   │   ├── newsletter.py       # editor node 함수 (analysis/standards_linker/editor)
│   │   ├── articles.py
│   │   ├── hitl_apply.py
│   │   ├── logging.py
│   │   └── research_agent.py   # Collect Orchestrator (레거시 subprocess)
│   ├── standards/               # IETF Radar
│   │   └── radar.py
│   └── ui/                      # Streamlit 공통
│       └── streamlit_utils.py
│
├── fetch_script.py            # CLI wrapper → ipn_agent.collect.fetch
├── review_script.py           # CLI wrapper → ipn_agent.review.runner
├── standards_radar_script.py
├── newsletter_orchestrator.py
├── research_review_agent.py
├── reset_vault.py
│
├── vault/                    # Obsidian Vault (데이터)
├── logs/                     # tool_runs.jsonl
├── output/pipeline_runs/     # Orchestrator run 스냅샷
└── docs/                     # 문서
```

## 모듈 ↔ 역할

| 패키지 | 역할 |
|--------|------|
| `ipn_agent.core` | Tool 로그, MVP 상한 |
| `ipn_agent.registry` | URL 중복·기발행 hash registry |
| `ipn_agent.vault` | Vault read/write, HITL approve/reject, 발행 |
| `ipn_agent.collect` | RSS/Tavily fetch, 본문 추출, Discovery pipeline |
| `ipn_agent.review` | LLM Review, review frontmatter, threshold routing |
| `ipn_agent.orchestrator` | Newsletter Orchestrator (LangGraph), Editor |
| `ipn_agent.standards` | IETF Radar |
| `ipn_agent.ui` | Streamlit 헬퍼 (Orchestrator 실행, Tool 로그) |

## `ipn_agent.orchestrator` 내부 구성

| 모듈 | 역할 |
|------|------|
| `workflow.py` | `build_newsletter_workflow()` — load_sources ~ draft_created 단일 StateGraph |
| `state.py` | `NewsletterWorkflowState`, count 집계 헬퍼 |
| `newsletter.py` | `obsidian_loader_node` · `analysis_node` · `standards_linker_node` · `hitl_node` · `editor_node` + Pydantic 모델(`RawArticle`, `ArticleAnalysis`, `NewsletterOutput`) |
| `editor.py` | `prepare_newsletter_context()` · `generate_newsletter_draft()` · `refine_newsletter_draft()` — `newsletter.py` 노드를 순차 호출 |
| `articles.py` | vault md → `ArticleRef` 스캔 (raw/review/approved 병합) |
| `hitl_apply.py` | threshold 라우팅 결과를 `02_review` frontmatter에 반영 |
| `logging.py` | `output/pipeline_runs/{run_id}/state.json`, `events.jsonl` |
| `research_agent.py` | `research_review_agent.py`가 사용하는 레거시 subprocess 오케스트레이션 |

## 실행 (변경 없음)

```bash
streamlit run streamlit_app.py
python newsletter_orchestrator.py --mode collect
python fetch_script.py --source apnic_blog
python review_script.py
```

내부 구현은 `ipn_agent.*`를 import하지만, **문서·Orchestrator subprocess는 루트 wrapper 경로**를 그대로 사용합니다.

## import 예시

```python
from ipn_agent.vault.utils import get_vault_path, list_review_items
from ipn_agent.orchestrator.workflow import run_newsletter_workflow
from ipn_agent.review.metadata import source_type_badge
```

## 경로 기준

`ipn_agent.paths.PROJECT_DIR` = `mini pjt/` ( `sources.yaml`, `vault/`, `logs/` 위치 )
