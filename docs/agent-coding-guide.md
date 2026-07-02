# LangGraph 에이전트 코딩 가이드

> LangGraph 학습 과정에서 도출한 **설계 인사이트 + 코드 작성 팁**.  
> Cursor 채팅: `@docs/agent-coding-guide.md`

---

## 핵심 한 줄

**LLM에게 흐름·기억·안전을 맡기지 말고, 그래프·State·도구·프롬프트·미들웨어로 명시한다.**

---

## 1. StateGraph — 얼마나 복잡하게?

| 복잡도 | 패턴 | State | 노드 |
|--------|------|-------|------|
| 단순 | ReAct | `messages` 1개 | `agent` + `tools` |
| 중간 | Agentic RAG | `messages` + `query` + `documents` + `attempt` | 5노드 + 분기 |
| 복잡 | Plan-Execute / ReWOO | `plan`, `past_steps`, `results` … | 4노드+ |
| 조합 | Supervisor / Hierarchical | 공유 State + sub-graph | 팀·worker 트리 |

**인사이트:** 5노드 Agentic RAG의 분기를 코드로 다 짜다가 ReAct로 줄이면 State 5→1, 노드 5→2.  
→ **LLM 판단에 맡겨도 되면 ReAct**, **코드로 반드시 통제해야 하면 명시적 노드**.

### ReAct 골격 (가장 자주 쓰는 패턴)

```python
class State(TypedDict):
    messages: Annotated[list, add_messages]

builder = StateGraph(State)
builder.add_node("agent", agent)
builder.add_node("tools", ToolNode(tools))
builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
builder.add_edge("tools", "agent")
graph = builder.compile()
```

`ToolNode`는 prebuilt — tool 실행·ToolMessage 추가를 자동 처리. 직접 루프 짜지 않기.

---

## 2. State 설계

1. **노드끼리 주고받을 데이터는 전부 State** — 노드 간 직접 인자 전달 X
2. **각 필드의 “누가·언제·바꾸는지”** 한 줄로 적고 시작
3. **reducer로 누적 vs 덮어쓰기 명시**
   - 대화: `Annotated[list, add_messages]`
   - 로그·완료 목록: `Annotated[list, operator.add]`
   - 단일 값(query, attempt): reducer 없음 → 덮어쓰기
4. **무한 루프 방지 필드** — `attempt`, `replan_count`, `iteration_count`
5. **필드는 적게** — supervisor/다음 노드가 **실제로 쓰는 것만**

| 필드 | 용도 |
|------|------|
| `messages` | 대화 + tool_call/result |
| `query` | 검색용 — rewrite 시 query만 갱신 |
| `search_result` / `db_result` | worker 결과를 구조화해 다음 노드가 읽기 쉽게 |

→ messages만 파싱해서 라우팅하게 두지 말고, **중요 중간 결과는 명시 필드**.

---

## 3. StateGraph vs create_agent

| 상황 | 추천 |
|------|------|
| 커스텀 분기·학습·노드가 보여야 할 때 | `StateGraph` 수동 조립 |
| 미들웨어·HITL·체크포인터·빠른 완성 | `create_agent` + middleware |
| 역할 2~3개 분리 | Agents-as-Tools (`@tool` wrap) |
| 부서별 worker 트리 | `create_supervisor` / hierarchical |
| replan·DAG·병렬 | Plan-Execute / ReWOO + `Send` |

**팁:** `create_agent`로 동작 확인 → 부족한 분기만 `StateGraph`로 빼기.

---

## 4. 분기 — 코드 vs 프롬프트 vs structured output

| 방식 | 쓸 때 |
|------|-------|
| `conditional_edges` + 조건 함수 | attempt 한도, grade yes/no, HITL resume |
| system prompt | ReAct 도구 호출 **순서·전략** |
| `with_structured_output` | supervisor 라우팅, grade, judge |

**원칙:** 돈·안전·무한루프 → **코드/structured**. 도구 선택 순서 → **prompt**.  
supervisor 라우팅은 자유 텍스트 금지 → `Literal["search","db","FINISH"]` 등.

---

## 5. 도구(@tool)

- **docstring = API 스펙** — 모델이 호출 여부·인자를 여기서 결정
- **한 도구 = 한 책임**
- **반환은 문자열** — `"검색 결과 없음"`, `"직원 정보 없음"`처럼 다음 행동 가능하게
- **read-only 우선** — write/send는 HITL
- **`RunnableConfig`** — `user_id`, `role`, `thread_id`는 `config["configurable"]`

---

## 6. context / State / Store

| | 역할 |
|--|------|
| **State** | 턴마다 바꾸는 작업 메모 (plan, documents …) |
| **configurable** | 외부가 고정으로 주는 메타 (thread_id, user_id) |
| **Store** | 세션을 넘는 기억 (위키, 프로필) |

“내 id는 3” → LLM 기억 X → **Store + remember_fact** 또는 State 필드.

---

## 7. RAG defaults (코스 검증값)

- chunk **700 / overlap 150**
- MMR: `k=8`, `fetch_k=16`, `lambda_mult=0.5`
- Chroma + `persist_directory`, `collection_name="techcorp"`
- **No-answer policy** 필수: `"문서에 없으면 '문서 밖'. 추측 금지."`
- 검색 결과: `"[{source}]\n{content}"`, 답변 끝 **출처**

Faithfulness↓ → prompt 먼저. Recall↓ → top-K / reranker.

---

## 8. 멀티 에이전트 선택

```
ReAct + tools  →  Agents-as-Tools  →  Supervisor  →  Hierarchical  →  ReWOO / Plan-Execute
```

- sub-agent **`name=` 필수**
- supervisor: **같은 worker 재호출 금지** + **`recursion_limit` 20~50**
- cheap model → worker·도구·구조화 / expensive → 종합·보고서·supervisor

---

## 9. 안전 습관 (Day 4)

1. PII → **before_model** middleware
2. RAG/DB → **No-answer / 추측 금지**
3. write/update/send → **HITL**
4. 모든 루프 → **`recursion_limit`**
5. 멀티턴 → **thread_id** + checkpointer
6. 디버깅 → **LangSmith** (`LANGSMITH_TRACING=true`)

미들웨어 순서 예: `PIIGuard → WikiInject → HumanInTheLoop`

---

## 10. 새 기능 추가 시 빠른 결정

```
1. LLM 판단으로 충분?  YES → ReAct + prompt   NO → conditional / structured
2. 다음 노드가 결과 읽음?  YES → State 필드     NO → messages만
3. 세션 넘어 기억?       YES → Store           NO → State / configurable
4. 외부에 영향?          YES → HITL            NO → read-only tool
5. 품질 확인?            YES → EVAL_CASE 1개   NO → LangSmith trace
```

---

## 11. 자주 하는 실수

| 실수 | 대신 |
|------|------|
| `from click import Command` | `from langgraph.types import Command` |
| State 필드 남발 | 판단에 쓰는 것만 |
| messages만으로 라우팅 | `db_result`, `report` 등 명시 필드 |
| LLM이 도구 대신 “실행한 척” | `create_agent` + real tools |
| `Field(default=[])` | `Field(default_factory=list)` |
| RAG 추측 | No-answer policy |
| supervisor 무한 호출 | prompt + recursion_limit |

---

## 12. 레퍼런스 (원본 코드)

| 주제 | 파일 |
|------|------|
| State·reducer | `day2/lecture/code/day02_02_state_reducer.py` |
| Agentic RAG State | `day2/lecture/Day2_Part4_Agentic_RAG.md` |
| ReAct 단순화 | `day2/lecture/Day2_Part5_ReAct_Pattern.md` |
| Runtime context | `day3/lecture/code/day03_03_runtime_context.py` |
| 가드레일 | `day4/lecture/code/day04_04_guardrail_input.py` |
| Supervisor | `day5/lecture/code/day05_02_supervisor_prebuilt.py` |
| 종합 예시 | `day8/practice/solutions/example_hr_assistant.py` |
| **본 프로젝트 Orchestrator** | `newsletter_orchestrator.py` → `ipn_agent.orchestrator.workflow` / `.state` |
| **Editor 함수** | `ipn_agent.orchestrator.editor` |

---

## 13. 본 프로젝트 (mini pjt) Newsletter Orchestrator 팁

- **단일 Graph** — `newsletter_orchestrator.py`(`ipn_agent.orchestrator.workflow`) = 수집~draft 전체, **유일한 진입점**
- **State에는 metadata·path만** — `NewsletterWorkflowState.articles[]`에 원문 금지
- **Editor는 함수 + node** — `ipn_agent.orchestrator.editor.prepare_newsletter_context` → `generate_newsletter_draft` → `refine_newsletter_draft`
- **rule 노드는 LLM 없이** — threshold(`ipn_agent.review.hitl`), registry(`ipn_agent.registry.published`), dedupe
- **subprocess wrapper 유지** — fetch/review 내부 로직 변경 최소화
- v0.8에서 `pipeline_graph.py`·Chat UI Editor subgraph를 삭제했다 — 새 기능은 Orchestrator node로만 추가
