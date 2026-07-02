"""Score threshold 기반 HITL 라우팅 (LLM 없음)."""

from __future__ import annotations

AUTO_PENDING_THRESHOLD = 0.80
REVIEW_REQUIRED_THRESHOLD = 0.55


def importance_to_score(importance: int | float | None) -> float | None:
    """review importance_score 1~5 → 0.0~1.0."""
    if importance is None:
        return None
    try:
        v = float(importance)
    except (TypeError, ValueError):
        return None
    if v <= 0:
        return None
    return min(max(v / 5.0, 0.0), 1.0)


def route_hitl_status(score: float | None) -> str:
    """approval_pending | needs_human_review | rejected (approved는 사람만)."""
    if score is None:
        return "needs_human_review"
    if score >= AUTO_PENDING_THRESHOLD:
        return "approval_pending"
    if score >= REVIEW_REQUIRED_THRESHOLD:
        return "needs_human_review"
    return "rejected"


def article_status_from_route(route: str) -> str:
    if route == "approval_pending":
        return "approval_pending"
    if route == "needs_human_review":
        return "needs_human_review"
    if route == "rejected":
        return "rejected"
    return "reviewed"
