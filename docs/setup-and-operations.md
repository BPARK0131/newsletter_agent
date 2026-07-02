# 설정 및 운영

## 의존성

```bash
pip install -r requirements.txt
```

주요 패키지: `streamlit`, `langgraph`, `langchain-openai`, `markitdown`, `feedparser`, `pyyaml`, `python-dotenv`, `pandas`

## 환경 변수 (`.env`)

> `.env` / `.env.example`은 **Git에 올리지 않습니다** (`.gitignore`).  
> 클론 후 프로젝트 루트에 `.env` 파일을 직접 만들고 아래 값을 채우세요.

| 변수 | 필수 | 설명 |
|------|------|------|
| `OPENAI_API_KEY` | ✅ | LLM 리뷰·뉴스레터 |
| `OBSIDIAN_VAULT_PATH` | 권장 | Vault 절대 경로 |
| `TAVILY_API_KEY` | 선택 | Tavily Discovery |
| `MVP_MAX_*` | 선택 | MVP 상한 |
| `LANGSMITH_*` | 선택 | LangSmith 트레이싱 |

템플릿 (로컬 `.env`에 복사 후 수정):

```env
OPENAI_API_KEY=sk-...
OBSIDIAN_VAULT_PATH=C:/path/to/mini pjt/vault

# 선택
# TAVILY_API_KEY=tvly-...
# MVP_MAX_ARTICLES_PER_SOURCE=2
# MVP_MAX_REVIEW=5
# LANGSMITH_TRACING=true
# LANGSMITH_API_KEY=lsv2_...
# LANGSMITH_PROJECT=ip-newsletter-agent
```

## Newsletter Orchestrator (유일한 진입점)

```bash
# 수집 ~ threshold HITL 큐
python newsletter_orchestrator.py --mode collect

# approved → draft
python newsletter_orchestrator.py --mode draft

# 전체
python newsletter_orchestrator.py --mode full
python newsletter_orchestrator.py --sources apnic_blog --mode collect
```

> v0.8에서 deprecated wrapper `pipeline_graph.py`를 삭제했습니다. `newsletter_orchestrator.py`만 사용하세요.

## 개별 스크립트

```bash
python fetch_script.py --source apnic_blog
python review_script.py
python standards_radar_script.py
python research_review_agent.py --sources apnic_blog   # 레거시 subprocess
```

## Streamlit (v0.8)

```bash
streamlit run streamlit_app.py
```

권장 흐름:

1. **📥 데이터 수집** → Orchestrator **수집 + HITL 큐** (RSS + Tavily → `02_review/`)
2. **📋 기사 검토** → 출처·큐 필터 후 승인/반려 (단일 HITL)
3. **📰 뉴스레터** → **Draft 생성** 또는 Orchestrator draft mode → **발행 확정**
4. **📦 아카이브** — 발행 호별 보관 확인 (선택)
5. **⚙️ 운영콘솔** — staging · gate 제외 사유 · IETF Radar · Tool 로그 (선택)

## Workflow run 로그

```
output/pipeline_runs/{run_id}/
├── state.json      # NewsletterWorkflowState (원문 없음)
└── events.jsonl    # node started/done/failed
```

## Vault 초기화

```bash
python reset_vault.py   # 주의: 데이터 삭제
```
