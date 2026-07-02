"""Newsletter Orchestrator — Workflow State (원문 본문 저장 금지)."""

from __future__ import annotations

from typing import Literal, TypedDict

ArticleStatus = Literal[
    "raw",
    "reviewed",
    "approval_pending",
    "needs_human_review",
    "approved",
    "rejected",
    "drafted",
    "published",
]

WorkflowMode = Literal["collect", "draft", "full"]

# deprecated alias
PipelineMode = WorkflowMode


class ArticleRef(TypedDict, total=False):
    article_id: str
    title: str
    source: str
    url: str
    normalized_url_hash: str
    title_hash: str
    content_hash: str
    category: str
    score: float
    status: ArticleStatus
    reason: str
    raw_path: str
    review_path: str
    approved_path: str
    used_in_newsletter: bool
    published_at: str | None
    hitl_route: str


class NewsletterWorkflowState(TypedDict, total=False):
    """단일 LangGraph Orchestrator state — 수집~draft."""

    run_id: str
    started_at: str
    completed_at: str | None
    vault_path: str
    pipeline_mode: WorkflowMode
    source_ids: list[str]
    expansion_category_ids: list[str]
    expansion_only: bool
    run_editor: bool
    force_review: bool
    force_editor: bool

    step_status: dict[str, str]
    articles: list[ArticleRef]

    collected_count: int
    reviewed_count: int
    approval_pending_count: int
    needs_human_review_count: int
    rejected_count: int
    approved_count: int
    published_filtered_count: int

    draft_candidate_paths: list[str]
    editor_article_count: int
    newsletter: dict
    editor_quality_ok: bool
    editor_quality_notes: list[str]

    draft_path: str | None
    errors: list[dict]
    output_paths: dict[str, str]


# Orchestrator 진입점용 alias (Editor Graph `NewsletterState`와 별개)
NewsletterState = NewsletterWorkflowState
PipelineState = NewsletterWorkflowState


def recompute_counts(state: NewsletterWorkflowState) -> dict[str, int]:
    articles = state.get("articles") or []
    counts = {
        "collected_count": 0,
        "reviewed_count": 0,
        "approval_pending_count": 0,
        "needs_human_review_count": 0,
        "rejected_count": 0,
        "approved_count": 0,
        "published_filtered_count": int(state.get("published_filtered_count") or 0),
    }
    for a in articles:
        st = a.get("status") or ""
        hr = a.get("hitl_route") or ""
        if st == "raw":
            counts["collected_count"] += 1
        if st in ("reviewed", "approval_pending", "needs_human_review") or hr:
            counts["reviewed_count"] += 1
        if st == "approval_pending" or hr == "approval_pending":
            counts["approval_pending_count"] += 1
        if st == "needs_human_review" or hr == "needs_human_review":
            counts["needs_human_review_count"] += 1
        if st == "rejected" or hr == "rejected":
            counts["rejected_count"] += 1
        if st == "approved":
            counts["approved_count"] += 1
    return counts


def merge_counts_into_state(state: NewsletterWorkflowState) -> NewsletterWorkflowState:
    return {**state, **recompute_counts(state)}
