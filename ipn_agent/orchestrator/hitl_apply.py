"""Threshold routing — 02_review frontmatter 갱신 및 auto-reject 이동."""

from __future__ import annotations

from pathlib import Path

from ipn_agent.review.hitl import importance_to_score, route_hitl_status
from ipn_agent.vault.utils import build_frontmatter, get_vault_path, parse_frontmatter, read_md


def apply_threshold_routing_to_vault(
    vault: Path | None = None,
    *,
    force: bool = False,
) -> tuple[int, int, int]:
    """
    02_review 기사에 hitl_route / review_score 기록.
    rejected(score < 0.55) → 99_rejected/ 이동.
    Returns: (approval_pending, needs_human_review, rejected)
    """
    v = vault or get_vault_path()
    review_dir = v / "02_review"
    rejected_dir = v / "99_rejected"
    rejected_dir.mkdir(parents=True, exist_ok=True)

    ap = nh = rej = 0
    if not review_dir.is_dir():
        return 0, 0, 0

    for md in sorted(review_dir.glob("*.md")):
        if md.name == ".gitkeep":
            continue
        meta, body = read_md(md)
        if meta.get("hitl_route") and not force:
            route = meta["hitl_route"]
        else:
            score = importance_to_score(meta.get("importance_score"))
            route = route_hitl_status(score)
            meta["review_score"] = round(score, 3) if score is not None else None
            meta["hitl_route"] = route
            meta["pipeline_status"] = route

        if route == "approval_pending":
            ap += 1
        elif route == "needs_human_review":
            nh += 1
        elif route == "rejected":
            rej += 1
            meta["status"] = "rejected"
            meta["pipeline_status"] = "rejected"
            dst = rejected_dir / md.name
            if not dst.exists():
                dst.write_text(build_frontmatter(meta, body), encoding="utf-8")
                md.unlink()
            continue

        meta.setdefault("status", "review")
        md.write_text(build_frontmatter(meta, body), encoding="utf-8")

    return ap, nh, rej
