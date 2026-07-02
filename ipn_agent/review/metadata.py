"""02_review item 메타데이터 정규화 — RSS / Tavily / Vendor 공통."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from ipn_agent.review.hitl import importance_to_score, route_hitl_status

SOURCE_TYPE_LABELS: dict[str, str] = {
    "rss": "RSS",
    "tavily": "Web",
    "manual": "Manual",
    "ietf": "Standards",
    "vendor": "Vendor",
}

ORIGIN_LABELS: dict[str, str] = {
    "curated_source": "등록소스",
    "open_web_search": "웹검색",
    "standards_context": "Standards",
}


def domain_from_url(url: str) -> str:
    if not url:
        return ""
    try:
        return urlparse(str(url)).netloc.lower().removeprefix("www.")
    except Exception:
        return ""


def infer_source_type(meta: dict, md_file: Path | None = None) -> str:
    explicit = str(meta.get("source_type") or "").lower()
    if explicit in ("tavily", "expansion_search", "open_web"):
        return "tavily"
    if explicit in ("vendor_blog", "vendor"):
        return "vendor"
    if explicit in ("standard_reference", "ietf"):
        return "ietf"
    if explicit == "rss":
        return "rss"

    origin = str(meta.get("origin") or "")
    if origin == "open_web_search":
        return "tavily"
    if origin == "standards_context":
        return "ietf"

    collect = str(meta.get("collect_method") or "")
    if "tavily" in collect or "expansion" in collect:
        return "tavily"
    if meta.get("is_vendor") or meta.get("source_type") == "vendor_blog":
        return "vendor"
    if "rss" in collect or meta.get("collection_mode") in ("rss", "rss_or_url"):
        return "rss"

    if md_file and md_file.parts:
        parts = md_file.as_posix().split("/")
        if "expansion" in parts:
            return "tavily"
    return "rss"


def infer_origin(meta: dict, source_type: str | None = None) -> str:
    explicit = meta.get("origin")
    if explicit in ("curated_source", "open_web_search", "standards_context"):
        return str(explicit)

    st = source_type or infer_source_type(meta)
    if st == "tavily":
        return "open_web_search"
    if st == "ietf":
        return "standards_context"
    return "curated_source"


def infer_trust_level(meta: dict, source_type: str | None = None) -> str:
    explicit = meta.get("trust_level")
    if explicit in ("high", "medium", "low"):
        return str(explicit)

    st = source_type or infer_source_type(meta)
    bias = str(meta.get("bias_risk") or "low")
    if st == "tavily":
        return "medium" if bias == "low" else "low"
    if st == "vendor" or bias == "high":
        return "low"
    if st == "rss" and bias == "low":
        return "high"
    if bias == "medium":
        return "medium"
    return "high"


def source_type_badge(source_type: str) -> str:
    return SOURCE_TYPE_LABELS.get(source_type, source_type or "—")


def merge_hitl_route(
    review_score: float | None,
    *,
    recollect_required: bool = False,
    gate_route: str | None = None,
    bias_risk: str = "low",
) -> str:
    route = route_hitl_status(review_score)
    if gate_route == "needs_human_review" and route == "approval_pending":
        route = "needs_human_review"
    if gate_route == "rejected":
        route = "rejected"
    if recollect_required:
        route = "needs_human_review"
    if bias_risk == "high" and route == "approval_pending":
        route = "needs_human_review"
    return route


def enrich_raw_meta(meta: dict, md_file: Path | None = None) -> dict:
    """01_raw frontmatter 보강 (수집 시)."""
    out = dict(meta)
    st = infer_source_type(out, md_file)
    out["source_type"] = st
    out["origin"] = infer_origin(out, st)
    out["domain"] = out.get("domain") or domain_from_url(
        out.get("source_url") or out.get("url") or ""
    )
    out["trust_level"] = infer_trust_level(out, st)
    return out


def build_review_meta(
    meta: dict,
    result,
    md_file: Path,
    *,
    recollect_required: bool = False,
    is_published: bool = False,
) -> dict:
    """02_review frontmatter 통합 필드."""
    from datetime import datetime

    def _source_url(m: dict) -> str:
        for key in ("source_url", "url", "link", "canonical_url"):
            val = m.get(key)
            if val:
                return str(val).strip()
        return ""

    def _source_id(m: dict, f: Path) -> str:
        for key in ("source_id", "source", "source_name"):
            val = m.get(key)
            if val:
                return str(val).strip()
        return f.parent.name if f.parent.name else "unknown_source"

    def _published(m: dict) -> str:
        for key in ("published_at", "published", "updated_at", "updated"):
            val = m.get(key)
            if val:
                return str(val).strip()[:10]
        return datetime.now().strftime("%Y-%m-%d")

    source_url = _source_url(meta)
    today = datetime.now().strftime("%Y-%m-%d")
    st = infer_source_type(meta, md_file)
    origin = infer_origin(meta, st)
    review_score = importance_to_score(result.importance_score)
    gate_route = meta.get("tavily_gate_hitl_route")
    hitl_route = merge_hitl_route(
        review_score,
        recollect_required=recollect_required,
        gate_route=str(gate_route) if gate_route else None,
        bias_risk=str(result.bias_risk or meta.get("bias_risk") or "low"),
    )

    review_meta = {
        "title": meta.get("title", "untitled"),
        "source_id": _source_id(meta, md_file),
        "source_name": meta.get("source_name", ""),
        "source_url": source_url,
        "source_type": st,
        "origin": origin,
        "domain": meta.get("domain") or domain_from_url(source_url),
        "trust_level": infer_trust_level(meta, st),
        "category": result.category,
        "status": "review",
        "bias_risk": result.bias_risk,
        "bias_note": result.bias_note,
        "published_at": _published(meta),
        "collected_at": meta.get("collected_at") or today,
        "reviewed_at": today,
        "importance_score": result.importance_score,
        "review_score": review_score,
        "hitl_route": hitl_route,
        "topic_tags": result.topic_tags,
        "recollect_required": recollect_required,
        "review_required": recollect_required or result.bias_risk in ("medium", "high"),
        "is_published": is_published,
    }
    if meta.get("discovery_score") is not None:
        review_meta["discovery_score"] = int(meta.get("discovery_score") or 0)
    if meta.get("discovery_reasons"):
        review_meta["discovery_reasons"] = meta.get("discovery_reasons")
    return review_meta
