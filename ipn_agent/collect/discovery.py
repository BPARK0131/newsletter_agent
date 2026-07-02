"""Tavily Discovery → quality gate → 01_raw/expansion/ (Review는 review_script)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ipn_agent.registry.article import find_url_in_vault
from ipn_agent.collect.extract import is_thin_content, score_content
from ipn_agent.registry.published import content_hash_for_article, is_article_published
from ipn_agent.review.metadata import domain_from_url, enrich_raw_meta


def apply_tavily_quality_gate(
    meta: dict,
    content: str,
    *,
    discovery_score: int,
    min_score: int,
    bias_risk: str,
) -> dict[str, Any]:
    """웹검색 품질 게이트 — RSS보다 엄격."""
    reasons: list[str] = []
    passed = True
    gate_route: str | None = None
    recollect_hint = False

    if discovery_score < min_score:
        return {
            "passed": False,
            "reason": f"below_min_score:{discovery_score}<{min_score}",
            "gate_route": "rejected",
            "recollect_hint": False,
            "reasons": reasons,
        }

    body_score = score_content(content)
    if is_thin_content(content, min_score=35):
        recollect_hint = True
        gate_route = "needs_human_review"
        reasons.append("thin_body")

    if len((content or "").strip()) < 500:
        passed = False
        reasons.append("content_too_short")
        return {
            "passed": False,
            "reason": "content_too_short",
            "gate_route": "rejected",
            "recollect_hint": True,
            "reasons": reasons,
        }

    if meta.get("date_reason", "").startswith("too_old") or meta.get("date_reason") == "unknown_date":
        if discovery_score <= 2:
            passed = False
            reasons.append("stale_or_unknown_date")
            return {
                "passed": False,
                "reason": meta.get("date_reason", "unknown_date"),
                "gate_route": "rejected",
                "recollect_hint": False,
                "reasons": reasons,
            }
        gate_route = "needs_human_review"
        reasons.append("date_uncertain")

    if bias_risk == "high":
        gate_route = "needs_human_review"
        reasons.append("vendor_bias_high")
    elif bias_risk == "medium" and gate_route != "needs_human_review":
        reasons.append("vendor_bias_medium")

    if body_score < 40:
        gate_route = "needs_human_review"
        reasons.append(f"low_body_score:{body_score:.0f}")

    return {
        "passed": passed,
        "reason": "",
        "gate_route": gate_route,
        "recollect_hint": recollect_hint,
        "reasons": reasons,
    }


def promote_tavily_to_raw(
    vault_path: str,
    meta: dict,
    content: str,
    subdir: str,
    dry_run: bool,
) -> dict[str, Any]:
    """Tavily item → quality gate → 01_raw/expansion/{subdir}/."""
    v = Path(vault_path)
    url = meta.get("url", "")
    title = meta.get("title", "untitled")

    if url:
        existing = find_url_in_vault(v, url)
        if existing:
            return {"status": "discarded", "reason": f"duplicate_url:{existing}"}

        pub = is_article_published(
            article_id="",
            url=url,
            title=title,
            source=meta.get("source_name", "expansion"),
            content_hash=content_hash_for_article(body=content, meta=meta),
            vault=v,
        )
        if pub:
            return {"status": "discarded", "reason": "already_published"}

    gate = apply_tavily_quality_gate(
        meta,
        content,
        discovery_score=int(meta.get("discovery_score") or 0),
        min_score=int(meta.get("_min_discovery_score") or 3),
        bias_risk=str(meta.get("bias_risk") or "low"),
    )
    if not gate["passed"]:
        return {"status": "discarded", "reason": gate["reason"], "gate": gate}

    enriched = enrich_raw_meta({
        **meta,
        "source_type": "tavily",
        "origin": "open_web_search",
        "domain": domain_from_url(url),
        "collect_method": meta.get("collect_method") or "tavily_expansion_discovery",
    })
    if gate.get("gate_route"):
        enriched["tavily_gate_hitl_route"] = gate["gate_route"]

    if dry_run:
        return {
            "status": "dry_run",
            "reason": "quality_gate_passed",
            "gate": gate,
            "raw_path": f"01_raw/expansion/{subdir}/",
        }

    dst_dir = v / "01_raw" / "expansion" / subdir
    dst_dir.mkdir(parents=True, exist_ok=True)
    from ipn_agent.collect.fetch import safe_filename, normalize_date
    pub = normalize_date(enriched.get("published") or enriched.get("published_at", ""))
    filename = f"{pub}-{safe_filename(title)}.md"
    dst = dst_dir / filename

    if dst.exists():
        return {"status": "discarded", "reason": f"raw_exists:{dst.name}"}

    from ipn_agent.vault.utils import build_frontmatter
    dst.write_text(build_frontmatter(enriched, content), encoding="utf-8")

    return {
        "status": "raw_saved",
        "reason": "",
        "raw_path": dst.relative_to(v).as_posix(),
        "gate": gate,
    }


# 하위 호환 alias (외부 import 대비)
promote_tavily_to_review_pipeline = promote_tavily_to_raw
