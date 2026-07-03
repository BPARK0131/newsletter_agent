"""
Newsletter Orchestrator — 단일 LangGraph StateGraph (수집 ~ draft).

실행:
  python newsletter_orchestrator.py --mode collect
  python newsletter_orchestrator.py --mode draft
  python newsletter_orchestrator.py --mode full
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

from ipn_agent.paths import ensure_vault_path_env
from langgraph.graph import END, START, StateGraph

load_dotenv()
ensure_vault_path_env()

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from ipn_agent.orchestrator.articles import (
    merge_article_lists,
    scan_approved_articles,
    scan_raw_articles,
    scan_review_articles,
)
from ipn_agent.orchestrator.hitl_apply import apply_threshold_routing_to_vault
from ipn_agent.orchestrator.logging import log_event, save_state_snapshot
from ipn_agent.orchestrator.state import (
    NewsletterWorkflowState,
    merge_counts_into_state,
)
from ipn_agent.registry.published import is_article_published, sync_registry_from_used_folder
from ipn_agent.orchestrator.research_agent import _run_step, load_enabled_source_ids
from ipn_agent.vault.utils import get_vault_path

# Public aliases
NewsletterState = NewsletterWorkflowState
PipelineState = NewsletterWorkflowState


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _vault(state: NewsletterWorkflowState) -> Path:
    return Path(state.get("vault_path") or str(get_vault_path()))


def _append_error(state: NewsletterWorkflowState, step: str, error: str, **extra) -> list[dict]:
    errs = list(state.get("errors") or [])
    errs.append({"step": step, "error": error, **extra})
    return errs


def _merge_step(state: NewsletterWorkflowState, step: str, status: str) -> dict[str, str]:
    prev = dict(state.get("step_status") or {})
    prev[step] = status
    return prev


def _refresh_articles(state: NewsletterWorkflowState) -> list[dict]:
    v = _vault(state)
    return merge_article_lists(
        scan_raw_articles(v),
        scan_review_articles(v),
        scan_approved_articles(v),
    )


def load_sources_node(state: NewsletterWorkflowState) -> NewsletterWorkflowState:
    run_id = state.get("run_id") or (
        datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    )
    vault = get_vault_path()
    (vault / "registry").mkdir(parents=True, exist_ok=True)
    sync_registry_from_used_folder(vault)

    log_event(run_id, "load_sources", "started")
    source_ids = state.get("source_ids")
    if source_ids is None:
        source_ids = load_enabled_source_ids()

    out: NewsletterWorkflowState = {
        "run_id": run_id,
        "started_at": _now(),
        "vault_path": str(vault),
        "source_ids": source_ids,
        "expansion_category_ids": list(state.get("expansion_category_ids") or []),
        "step_status": _merge_step(state, "load_sources", "done"),
        "errors": list(state.get("errors") or []),
        "articles": state.get("articles") or [],
        "pipeline_mode": state.get("pipeline_mode") or "collect",
        "expansion_only": bool(state.get("expansion_only")),
        "run_editor": bool(state.get("run_editor")),
        "force_review": bool(state.get("force_review")),
        "force_editor": bool(state.get("force_editor")),
    }
    log_event(run_id, "load_sources", "done", count=len(source_ids))
    save_state_snapshot(run_id, merge_counts_into_state(out))
    return out


def collect_node(state: NewsletterWorkflowState) -> NewsletterWorkflowState:
    run_id = state["run_id"]
    log_event(run_id, "collect", "started")
    errors = list(state.get("errors") or [])

    if state.get("expansion_only"):
        fetch_ids = ["ietf_datatracker"]
    else:
        fetch_ids = [s for s in (state.get("source_ids") or []) if s != "ietf_datatracker"]
        if "ietf_datatracker" not in fetch_ids:
            fetch_ids.append("ietf_datatracker")

    for sid in fetch_ids:
        rc = _run_step("fetch_script.py", ["--source", sid])
        if rc != 0:
            errors = _append_error(state, "collect", f"fetch {sid} exit {rc}")
            log_event(run_id, "collect", "failed", error=f"{sid} exit {rc}")

    articles = _refresh_articles(state)
    step = "partial" if state.get("expansion_only") else "done"
    out = {**state, "articles": articles, "errors": errors, "step_status": _merge_step(state, "collect", step)}
    log_event(
        run_id,
        "collect",
        "done",
        count=len(articles),
        extra={"expansion_only": bool(state.get("expansion_only"))},
    )
    save_state_snapshot(run_id, merge_counts_into_state(out))
    return out


def expansion_search_node(state: NewsletterWorkflowState) -> NewsletterWorkflowState:
    run_id = state["run_id"]
    log_event(run_id, "expansion_search", "started")
    errors = list(state.get("errors") or [])
    category_ids = list(state.get("expansion_category_ids") or [])
    if not category_ids:
        articles = _refresh_articles(state)
        out = {
            **state,
            "articles": articles,
            "errors": errors,
            "step_status": _merge_step(state, "expansion_search", "skipped"),
        }
        log_event(run_id, "expansion_search", "done", count=len(articles), extra={"skipped": "no_categories"})
        save_state_snapshot(run_id, merge_counts_into_state(out))
        return out

    args = ["--expansion-search", "--categories", ",".join(category_ids)]
    rc = _run_step("fetch_script.py", args)
    if rc != 0:
        errors = _append_error(state, "expansion_search", f"exit {rc}")
        log_event(run_id, "expansion_search", "failed", error=f"exit {rc}")
    articles = _refresh_articles(state)
    out = {
        **state,
        "articles": articles,
        "errors": errors,
        "step_status": _merge_step(state, "expansion_search", "done" if rc == 0 else "partial"),
    }
    log_event(run_id, "expansion_search", "done", count=len(articles))
    save_state_snapshot(run_id, merge_counts_into_state(out))
    return out


def standards_radar_node(state: NewsletterWorkflowState) -> NewsletterWorkflowState:
    run_id = state["run_id"]
    log_event(run_id, "standards_radar", "started")
    errors = list(state.get("errors") or [])
    rc = _run_step("standards_radar_script.py")
    if rc != 0:
        errors = _append_error(state, "standards_radar", f"exit {rc}")
        log_event(run_id, "standards_radar", "failed", error=f"exit {rc}")
        out = {**state, "errors": errors, "step_status": _merge_step(state, "standards_radar", "failed")}
        save_state_snapshot(run_id, merge_counts_into_state(out))
        return out
    articles = _refresh_articles(state)
    out = {**state, "articles": articles, "errors": errors, "step_status": _merge_step(state, "standards_radar", "done")}
    log_event(run_id, "standards_radar", "done")
    save_state_snapshot(run_id, merge_counts_into_state(out))
    return out


def first_review_node(state: NewsletterWorkflowState) -> NewsletterWorkflowState:
    run_id = state["run_id"]
    log_event(run_id, "first_review", "started")
    errors = list(state.get("errors") or [])
    args: list[str] = []
    if state.get("force_review"):
        args.append("--force")
    rc = _run_step("review_script.py", args or None)
    if rc != 0:
        errors = _append_error(state, "first_review", f"exit {rc}")
        log_event(run_id, "first_review", "failed", error=f"exit {rc}")
        out = {**state, "errors": errors, "step_status": _merge_step(state, "first_review", "failed")}
        save_state_snapshot(run_id, merge_counts_into_state(out))
        return out
    articles = _refresh_articles(state)
    out = {**state, "articles": articles, "errors": errors, "step_status": _merge_step(state, "first_review", "done")}
    log_event(run_id, "first_review", "done", count=len(articles))
    save_state_snapshot(run_id, merge_counts_into_state(out))
    return out


def threshold_routing_node(state: NewsletterWorkflowState) -> NewsletterWorkflowState:
    run_id = state["run_id"]
    log_event(run_id, "threshold_routing", "started")
    v = _vault(state)
    ap, nh, rej = apply_threshold_routing_to_vault(v, force=bool(state.get("force_review")))
    articles = _refresh_articles(state)
    filtered_pub = 0
    for a in articles:
        if is_article_published(
            article_id=a.get("article_id", ""),
            url=a.get("url", ""),
            title=a.get("title", ""),
            source=a.get("source", ""),
            content_hash=a.get("content_hash", ""),
            vault=v,
        ):
            a["status"] = "published"
            filtered_pub += 1
    out = {
        **state,
        "articles": articles,
        "approval_pending_count": ap,
        "needs_human_review_count": nh,
        "rejected_count": rej,
        "published_filtered_count": filtered_pub,
        "step_status": _merge_step(state, "threshold_routing", "done"),
    }
    out = merge_counts_into_state(out)
    log_event(run_id, "threshold_routing", "done", count=ap + nh + rej)
    save_state_snapshot(run_id, out)
    return out


def human_review_wait_node(state: NewsletterWorkflowState) -> NewsletterWorkflowState:
    run_id = state["run_id"]
    log_event(run_id, "human_review_wait", "started")
    out = {**state, "step_status": _merge_step(state, "human_review_wait", "waiting")}
    log_event(run_id, "human_review_wait", "done")
    save_state_snapshot(run_id, merge_counts_into_state(out))
    return out


def load_approved_articles_node(state: NewsletterWorkflowState) -> NewsletterWorkflowState:
    run_id = state["run_id"]
    log_event(run_id, "load_approved_articles", "started")
    v = _vault(state)
    articles = merge_article_lists(state.get("articles") or [], scan_approved_articles(v))
    out = {**state, "articles": articles, "step_status": _merge_step(state, "load_approved_articles", "done")}
    out = merge_counts_into_state(out)
    log_event(run_id, "load_approved_articles", "done", count=out.get("approved_count", 0))
    save_state_snapshot(run_id, out)
    return out


def filter_published_articles_node(state: NewsletterWorkflowState) -> NewsletterWorkflowState:
    run_id = state["run_id"]
    log_event(run_id, "filter_published_articles", "started")
    v = _vault(state)
    filtered = 0
    draft_candidates: list[dict] = []
    for a in state.get("articles") or []:
        if a.get("status") != "approved":
            continue
        if a.get("used_in_newsletter"):
            filtered += 1
            continue
        if is_article_published(
            article_id=a.get("article_id", ""),
            url=a.get("url", ""),
            title=a.get("title", ""),
            source=a.get("source", ""),
            content_hash=a.get("content_hash", ""),
            vault=v,
        ):
            a["status"] = "published"
            filtered += 1
            continue
        if a.get("approved_path"):
            draft_candidates.append(a)

    out = {
        **state,
        "articles": state.get("articles") or [],
        "published_filtered_count": int(state.get("published_filtered_count") or 0) + filtered,
        "draft_candidate_paths": [a["approved_path"] for a in draft_candidates],
        "step_status": _merge_step(state, "filter_published_articles", "done"),
    }
    out = merge_counts_into_state(out)
    log_event(run_id, "filter_published_articles", "done", count=len(draft_candidates))
    save_state_snapshot(run_id, out)
    return out


def editor_prepare_node(state: NewsletterWorkflowState) -> NewsletterWorkflowState:
    from ipn_agent.orchestrator.editor import prepare_newsletter_context

    run_id = state["run_id"]
    log_event(run_id, "editor_prepare", "started")
    paths = state.get("draft_candidate_paths") or []
    errors = list(state.get("errors") or [])
    vault = str(_vault(state))

    if not paths and not state.get("force_editor"):
        msg = "draft 생성 대상 approved 기사 0건"
        errors = _append_error(state, "editor_prepare", msg)
        out = {
            **state,
            "errors": errors,
            "editor_article_count": 0,
            "step_status": _merge_step(state, "editor_prepare", "skipped"),
        }
        log_event(run_id, "editor_prepare", "failed", error=msg)
        save_state_snapshot(run_id, merge_counts_into_state(out))
        return out

    load_all = not paths and bool(state.get("force_editor"))
    ctx = prepare_newsletter_context(vault, paths, load_all_approved=load_all)
    if ctx is None:
        msg = "Editor 입력 기사 0건 (요약 품질 미달 또는 경로 없음)"
        errors = _append_error(state, "editor_prepare", msg)
        out = {
            **state,
            "errors": errors,
            "editor_article_count": 0,
            "step_status": _merge_step(state, "editor_prepare", "failed"),
        }
        log_event(run_id, "editor_prepare", "failed", error=msg)
        save_state_snapshot(run_id, merge_counts_into_state(out))
        return out

    out = {
        **state,
        "errors": errors,
        "editor_article_count": len(ctx.raw_articles),
        "step_status": _merge_step(state, "editor_prepare", "done"),
    }
    log_event(run_id, "editor_prepare", "done", count=len(ctx.raw_articles))
    save_state_snapshot(run_id, merge_counts_into_state(out))
    return out


def editor_generate_node(state: NewsletterWorkflowState) -> NewsletterWorkflowState:
    from ipn_agent.orchestrator.editor import generate_newsletter_draft, prepare_newsletter_context

    run_id = state["run_id"]
    log_event(run_id, "editor_generate", "started")
    errors = list(state.get("errors") or [])
    paths = state.get("draft_candidate_paths") or []
    vault = str(_vault(state))

    if (state.get("step_status") or {}).get("editor_prepare") in ("skipped", "failed"):
        out = {**state, "step_status": _merge_step(state, "editor_generate", "skipped")}
        log_event(run_id, "editor_generate", "failed", error="editor_prepare 실패")
        save_state_snapshot(run_id, merge_counts_into_state(out))
        return out

    load_all = not paths and bool(state.get("force_editor"))
    ctx = prepare_newsletter_context(vault, paths, load_all_approved=load_all)
    if ctx is None:
        errors = _append_error(state, "editor_generate", "컨텍스트 재로드 실패")
        out = {**state, "errors": errors, "step_status": _merge_step(state, "editor_generate", "failed")}
        log_event(run_id, "editor_generate", "failed", error="context reload failed")
        save_state_snapshot(run_id, merge_counts_into_state(out))
        return out

    try:
        gen = generate_newsletter_draft(ctx)
    except Exception as e:
        errors = _append_error(state, "editor_generate", str(e))
        out = {**state, "errors": errors, "step_status": _merge_step(state, "editor_generate", "failed")}
        log_event(run_id, "editor_generate", "failed", error=str(e))
        save_state_snapshot(run_id, merge_counts_into_state(out))
        return out

    nl = gen.get("newsletter") or {}
    out = {
        **state,
        "newsletter": nl,
        "errors": errors,
        "step_status": _merge_step(state, "editor_generate", "done" if nl else "failed"),
    }
    log_event(run_id, "editor_generate", "done" if nl else "failed", count=gen.get("analyzed_count"))
    save_state_snapshot(run_id, merge_counts_into_state(out))
    return out


def editor_quality_check_node(state: NewsletterWorkflowState) -> NewsletterWorkflowState:
    from ipn_agent.orchestrator.editor import refine_newsletter_draft

    run_id = state["run_id"]
    log_event(run_id, "editor_quality_check", "started")
    errors = list(state.get("errors") or [])
    nl = state.get("newsletter") or {}

    if not nl:
        errors = _append_error(state, "editor_quality_check", "newsletter 출력 없음")
        out = {
            **state,
            "errors": errors,
            "editor_quality_ok": False,
            "editor_quality_notes": ["newsletter 출력 없음"],
            "step_status": _merge_step(state, "editor_quality_check", "failed"),
        }
        log_event(run_id, "editor_quality_check", "failed")
        save_state_snapshot(run_id, merge_counts_into_state(out))
        return out

    result = refine_newsletter_draft(nl, vault_path=str(_vault(state)))
    if result is None:
        errors = _append_error(state, "editor_quality_check", "refine 실패")
        out = {
            **state,
            "errors": errors,
            "editor_quality_ok": False,
            "step_status": _merge_step(state, "editor_quality_check", "failed"),
        }
        log_event(run_id, "editor_quality_check", "failed")
        save_state_snapshot(run_id, merge_counts_into_state(out))
        return out

    status = "done" if result.quality_ok else "warning"
    out = {
        **state,
        "draft_path": result.draft_path,
        "editor_quality_ok": result.quality_ok,
        "editor_quality_notes": result.quality_notes,
        "errors": errors,
        "step_status": _merge_step(state, "editor_quality_check", status),
    }
    log_event(
        run_id, "editor_quality_check", status,
        extra={"draft_path": result.draft_path, "notes": result.quality_notes},
    )
    save_state_snapshot(run_id, merge_counts_into_state(out))
    return out


def draft_created_node(state: NewsletterWorkflowState) -> NewsletterWorkflowState:
    run_id = state["run_id"]
    out = {
        **state,
        "completed_at": _now(),
        "step_status": _merge_step(state, "draft_created", "done"),
    }
    log_event(run_id, "draft_created", "done", extra={"draft_path": state.get("draft_path")})
    save_state_snapshot(run_id, merge_counts_into_state(out))
    return out


def route_after_load_sources(state: NewsletterWorkflowState) -> Literal["collect", "load_approved_articles"]:
    if state.get("pipeline_mode") == "draft":
        return "load_approved_articles"
    return "collect"


def route_after_human_wait(state: NewsletterWorkflowState) -> Literal["load_approved_articles", "__end__"]:
    if state.get("pipeline_mode") == "full" or state.get("run_editor"):
        return "load_approved_articles"
    return "__end__"


def route_after_filter(state: NewsletterWorkflowState) -> Literal["editor_prepare", "__end__"]:
    paths = state.get("draft_candidate_paths") or []
    if paths or state.get("force_editor"):
        return "editor_prepare"
    return "__end__"


def route_after_editor_prepare(state: NewsletterWorkflowState) -> Literal["editor_generate", "__end__"]:
    if (state.get("step_status") or {}).get("editor_prepare") == "done":
        return "editor_generate"
    return "__end__"


def build_newsletter_workflow() -> StateGraph:
    builder = StateGraph(NewsletterWorkflowState)

    builder.add_node("load_sources", load_sources_node)
    builder.add_node("collect", collect_node)
    builder.add_node("expansion_search", expansion_search_node)
    builder.add_node("standards_radar", standards_radar_node)
    builder.add_node("first_review", first_review_node)
    builder.add_node("threshold_routing", threshold_routing_node)
    builder.add_node("human_review_wait", human_review_wait_node)
    builder.add_node("load_approved_articles", load_approved_articles_node)
    builder.add_node("filter_published_articles", filter_published_articles_node)
    builder.add_node("editor_prepare", editor_prepare_node)
    builder.add_node("editor_generate", editor_generate_node)
    builder.add_node("editor_quality_check", editor_quality_check_node)
    builder.add_node("draft_created", draft_created_node)

    builder.add_edge(START, "load_sources")
    builder.add_conditional_edges(
        "load_sources",
        route_after_load_sources,
        {"collect": "collect", "load_approved_articles": "load_approved_articles"},
    )
    builder.add_edge("collect", "expansion_search")
    builder.add_edge("expansion_search", "standards_radar")
    builder.add_edge("standards_radar", "first_review")
    builder.add_edge("first_review", "threshold_routing")
    builder.add_edge("threshold_routing", "human_review_wait")
    builder.add_conditional_edges(
        "human_review_wait",
        route_after_human_wait,
        {"load_approved_articles": "load_approved_articles", "__end__": END},
    )
    builder.add_edge("load_approved_articles", "filter_published_articles")
    builder.add_conditional_edges(
        "filter_published_articles",
        route_after_filter,
        {"editor_prepare": "editor_prepare", "__end__": END},
    )
    builder.add_conditional_edges(
        "editor_prepare",
        route_after_editor_prepare,
        {"editor_generate": "editor_generate", "__end__": END},
    )
    builder.add_edge("editor_generate", "editor_quality_check")
    builder.add_edge("editor_quality_check", "draft_created")
    builder.add_edge("draft_created", END)

    return builder



newsletter_app = build_newsletter_workflow().compile()
pipeline_app = newsletter_app


def run_newsletter_workflow(
    *,
    mode: Literal["collect", "draft", "full"] = "collect",
    source_ids: list[str] | None = None,
    expansion_category_ids: list[str] | None = None,
    expansion_only: bool = False,
    run_editor: bool = False,
    force_review: bool = False,
    force_editor: bool = False,
) -> NewsletterWorkflowState:
    initial: NewsletterWorkflowState = {
        "pipeline_mode": mode,
        "source_ids": source_ids,
        "expansion_category_ids": expansion_category_ids or [],
        "expansion_only": expansion_only,
        "run_editor": run_editor or mode == "full",
        "force_review": force_review,
        "force_editor": force_editor,
        "errors": [],
        "step_status": {},
        "articles": [],
    }
    if mode == "draft":
        initial["run_editor"] = True
    return newsletter_app.invoke(initial)


run_pipeline = run_newsletter_workflow


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Newsletter Orchestrator (LangGraph)")
    parser.add_argument("--mode", choices=("collect", "draft", "full"), default="collect")
    parser.add_argument("--sources", help="쉼표 구분 source_id")
    parser.add_argument("--expansion-only", action="store_true")
    parser.add_argument("--force-review", action="store_true")
    parser.add_argument("--force-editor", action="store_true")
    args = parser.parse_args()

    ensure_vault_path_env()

    src = (
        [s.strip() for s in args.sources.split(",") if s.strip()]
        if args.sources else None
    )
    result = run_newsletter_workflow(
        mode=args.mode,
        source_ids=src,
        expansion_only=args.expansion_only,
        force_review=args.force_review,
        force_editor=args.force_editor,
    )
    print(f"\n[DONE] run_id={result.get('run_id')}")
    print(f"step_status: {result.get('step_status')}")
    c = merge_counts_into_state(result)
    print(
        f"counts: collected={c.get('collected_count')} pending={c.get('approval_pending_count')} "
        f"approved={c.get('approved_count')}"
    )
    if result.get("draft_path"):
        print(f"draft: {result['draft_path']}")
    sys.exit(0)
