# 뉴스레터 파이프라인

## 단일 진입점 (v0.8)

**`newsletter_orchestrator.py`** — 수집부터 draft까지 하나의 LangGraph Workflow.  
HITL은 Streamlit **기사 검토** 탭에서 단일 단계로 처리합니다.

```bash
python newsletter_orchestrator.py --mode collect   # 수집 ~ HITL 큐
python newsletter_orchestrator.py --mode draft     # approved → draft
python newsletter_orchestrator.py --mode full
```

## 입력

- `vault/03_approved/*.md` — HITL 승인 기사
- frontmatter category, summary, headline, keywords, bias 재사용
- **기발행 registry에 없는 기사만** draft 대상

## Editor 단계 (`ipn_agent.orchestrator.editor`)

Orchestrator의 editor node 3개가 아래 함수를 호출한다.

| 함수 | 역할 |
|------|------|
| `prepare_newsletter_context()` | approved 경로 → 요약 중심 `RawArticle` 목록 |
| `generate_newsletter_draft()` | analysis → standards_linker → hitl → editor → vault 저장 |
| `refine_newsletter_draft()` | 섹션·파일 존재·review_required 품질 검사 |

### 내부 처리 (generate)

1. **analysis_node** — `ArticleAnalysis` structured output
2. **standards_linker_node** — 룰 기반 `standards_context` (LLM 없음)
3. **hitl_node** — 편향 항목 `review_required` 표시
4. **editor_node** — `NewsletterOutput` + `04_newsletter/draft/{date}-newsletter.md`

기사당 요약 최대 ~1500자 — 원문 전체 미사용.

## Workflow editor node 흐름

```
filter_published_articles
  → editor_prepare      (경로·count)
  → editor_generate     (draft md 저장)
  → editor_quality_check (품질·draft_path)
  → draft_created
```

결과: `NewsletterWorkflowState.draft_path` + `output/pipeline_runs/{run_id}/state.json`

## Legacy / deprecated

| 경로 | 상태 |
|------|------|
| `ipn_agent.orchestrator.editor.run_editor_for_paths()` | CLI/스크립트에서 approved 경로 지정 실행용 헬퍼 (Orchestrator 우회 경로) |

> v0.8에서 `pipeline_graph.py`, `newsletter_agent_skeleton.py`(Chat UI Editor subgraph)를 삭제했습니다. `newsletter_orchestrator.py`가 유일한 draft 생성 경로입니다.

## 발행 워크플로 (Graph 밖)

```
[draft 생성] → 04_newsletter/draft/
       ↓ Streamlit Preview + 발행 확인
[발행 확정] publish_newsletter()
       ├─ published/
       ├─ 05_newsletter_archive/
       ├─ 06_newsletter_used/
       ├─ registry/published_articles.json
       └─ draft 삭제
```

## 중복·기발행 차단

| 레이어 | 모듈 | 시점 |
|--------|------|------|
| URL | `ipn_agent.registry.article` | fetch / review |
| Hash | `ipn_agent.registry.published` | HITL · draft 직전 |

## Streamlit (v0.8)

- **📥 데이터 수집**: Newsletter Orchestrator · Workflow 상태 · Tool 로그
- **📋 기사 검토**: RSS · Tavily **통합** threshold HITL · 출처 필터 · review_score 중심
- **⚙️ 운영콘솔**: Discovery staging · quality gate 로그 · IETF Radar
- **📰 뉴스레터**: Orchestrator `mode=draft` 또는 Draft 생성 버튼
