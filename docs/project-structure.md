# 프로젝트 구조 (v0.7)

Python 코드는 `ipn_agent/` 패키지 아래 역할별로 정리되어 있습니다.  
CLI·Streamlit 진입점은 **프로젝트 루트**에 thin wrapper로 유지합니다 (기존 명령 호환).

## 디렉터리 트리

```
mini pjt/
├── streamlit_app.py          # Streamlit UI 진입점
├── sources.yaml              # 수집 소스·expansion_search 설정
├── requirements.txt
├── .env                      # 로컬 전용 (Git 제외)
│
├── ipn_agent/                # 메인 Python 패키지
│   ├── paths.py              # PROJECT_DIR (루트 기준 경로)
│   ├── core/                 # 공통 유틸
│   │   ├── tool_logger.py
│   │   ├── mvp_limits.py
│   │   └── text_normalize.py
│   ├── registry/             # URL·발행 중복 registry
│   │   ├── article.py
│   │   └── published.py
│   ├── vault/                # Obsidian Vault I/O
│   │   ├── utils.py
│   │   └── reset.py
│   ├── collect/              # Phase 1 — 수집·Discovery
│   │   ├── fetch.py
│   │   ├── extract.py
│   │   └── discovery.py
│   ├── review/               # Phase 2 — LLM Review·HITL 메타
│   │   ├── runner.py
│   │   ├── metadata.py
│   │   └── hitl.py
│   ├── orchestrator/         # LangGraph Workflow·Editor
│   │   ├── workflow.py
│   │   ├── state.py
│   │   ├── editor.py
│   │   ├── articles.py
│   │   ├── hitl_apply.py
│   │   ├── logging.py
│   │   ├── research_agent.py
│   │   └── legacy_state.py
│   ├── standards/            # IETF Radar
│   │   └── radar.py
│   ├── ui/                   # Streamlit 공통
│   │   └── streamlit_utils.py
│   └── legacy/               # deprecated Chat UI subgraph
│       └── skeleton.py
│
├── fetch_script.py           # CLI wrapper → ipn_agent.collect.fetch
├── review_script.py          # CLI wrapper → ipn_agent.review.runner
├── standards_radar_script.py
├── newsletter_orchestrator.py
├── research_review_agent.py
├── reset_vault.py
├── newsletter_agent_skeleton.py
├── pipeline_graph.py         # deprecated wrapper
│
├── vault/                    # Obsidian Vault (데이터)
├── logs/                     # tool_runs.jsonl
├── output/pipeline_runs/     # Orchestrator run 스냅샷
└── docs/                     # 문서
```

## 모듈 ↔ 역할

| 패키지 | 역할 |
|--------|------|
| `ipn_agent.core` | Tool 로그, MVP 상한, 텍스트 정규화 |
| `ipn_agent.registry` | URL 중복·기발행 hash registry |
| `ipn_agent.vault` | Vault read/write, HITL approve/reject, 발행 |
| `ipn_agent.collect` | RSS/Tavily fetch, 본문 추출, Discovery pipeline |
| `ipn_agent.review` | LLM Review, review frontmatter, threshold routing |
| `ipn_agent.orchestrator` | Newsletter Orchestrator (LangGraph), Editor |
| `ipn_agent.standards` | IETF Radar |
| `ipn_agent.ui` | Streamlit 헬퍼 (Orchestrator 실행, Tool 로그) |
| `ipn_agent.legacy` | Chat UI용 skeleton (deprecated) |

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
