"""Vault md → ArticleRef 스캔 (metadata·path만, 원문 state 미저장)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ipn_agent.review.hitl import importance_to_score, route_hitl_status
from ipn_agent.registry.published import (
    content_hash_for_article,
    is_article_published,
    normalized_url_hash,
    title_hash,
)
from ipn_agent.vault.utils import get_vault_path, parse_frontmatter, parse_review_body, read_md


def _rel(vault: Path, p: Path) -> str:
    try:
        return p.relative_to(vault).as_posix()
    except ValueError:
        return str(p)


def article_id_from_path(path: Path) -> str:
    return path.stem


def ref_from_raw(vault: Path, md: Path) -> dict[str, Any]:
    meta, body = read_md(md)
    url = meta.get("url") or meta.get("source_url") or ""
    title = meta.get("title") or md.stem
    source = meta.get("source_name") or meta.get("source_id") or md.parent.name
    ch = content_hash_for_article(body=body, meta=meta)
    return {
        "article_id": article_id_from_path(md),
        "title": title,
        "source": source,
        "url": url,
        "normalized_url_hash": normalized_url_hash(url),
        "title_hash": title_hash(title),
        "content_hash": ch,
        "category": meta.get("category", ""),
        "score": None,
        "status": "raw",
        "reason": "",
        "raw_path": _rel(vault, md),
        "review_path": "",
        "approved_path": "",
        "used_in_newsletter": bool(meta.get("newsletter_used_in")),
        "published_at": meta.get("published_at"),
        "hitl_route": "",
    }


def ref_from_review(vault: Path, md: Path) -> dict[str, Any]:
    meta, body = read_md(md)
    sections = parse_review_body(body)
    url = meta.get("source_url") or meta.get("url") or ""
    title = meta.get("title") or md.stem
    source = meta.get("source_name") or meta.get("source_id") or ""
    imp = meta.get("importance_score")
    score = meta.get("review_score")
    if score is None:
        score = importance_to_score(imp)
    route = meta.get("hitl_route") or ""
    if not route and score is not None:
        route = route_hitl_status(float(score))
    status = meta.get("pipeline_status") or (
        route if route else "reviewed"
    )
    ch = content_hash_for_article(body=body, summary=sections.get("요약", ""), meta=meta)
    pub = is_article_published(
        article_id=md.stem, url=url, title=title, source=source,
        content_hash=ch, vault=vault,
    )
    if pub:
        status = "published"
    return {
        "article_id": article_id_from_path(md),
        "title": title,
        "source": source,
        "url": url,
        "normalized_url_hash": normalized_url_hash(url),
        "title_hash": title_hash(title),
        "content_hash": ch,
        "category": meta.get("category", "Other"),
        "score": float(score) if score is not None else None,
        "status": status,
        "reason": meta.get("hitl_reason") or meta.get("bias_note") or "",
        "raw_path": "",
        "review_path": _rel(vault, md),
        "approved_path": "",
        "used_in_newsletter": False,
        "published_at": meta.get("published_at"),
        "hitl_route": route,
    }


def ref_from_approved(vault: Path, md: Path) -> dict[str, Any]:
    meta, body = read_md(md)
    sections = parse_review_body(body)
    url = meta.get("source_url") or meta.get("url") or ""
    title = meta.get("title") or md.stem
    source = meta.get("source_name") or meta.get("source_id") or ""
    imp = meta.get("importance_score")
    score = meta.get("review_score") or importance_to_score(imp)
    ch = content_hash_for_article(body=body, summary=sections.get("요약", ""), meta=meta)
    pub = is_article_published(
        article_id=md.stem, url=url, title=title, source=source,
        content_hash=ch, vault=vault,
    )
    st: str = "published" if pub else "approved"
    return {
        "article_id": article_id_from_path(md),
        "title": title,
        "source": source,
        "url": url,
        "normalized_url_hash": normalized_url_hash(url),
        "title_hash": title_hash(title),
        "content_hash": ch,
        "category": meta.get("category", "Other"),
        "score": float(score) if score is not None else None,
        "status": st,
        "reason": "",
        "raw_path": "",
        "review_path": "",
        "approved_path": _rel(vault, md),
        "used_in_newsletter": bool(meta.get("used_in_issue")),
        "published_at": meta.get("published_at"),
        "hitl_route": meta.get("hitl_route") or "",
    }


def scan_raw_articles(vault: Path) -> list[dict[str, Any]]:
    root = vault / "01_raw"
    if not root.is_dir():
        return []
    return [ref_from_raw(vault, md) for md in sorted(root.rglob("*.md")) if md.name != ".gitkeep"]


def scan_review_articles(vault: Path) -> list[dict[str, Any]]:
    root = vault / "02_review"
    if not root.is_dir():
        return []
    return [ref_from_review(vault, md) for md in sorted(root.glob("*.md")) if md.name != ".gitkeep"]


def scan_approved_articles(vault: Path) -> list[dict[str, Any]]:
    root = vault / "03_approved"
    if not root.is_dir():
        return []
    return [ref_from_approved(vault, md) for md in sorted(root.glob("*.md")) if md.name != ".gitkeep"]


def merge_article_lists(*lists: list[dict]) -> list[dict]:
    """article_id / url_hash 기준 병합 — 후순위가 덮어씀."""
    by_key: dict[str, dict] = {}
    for items in lists:
        for a in items:
            key = a.get("article_id") or a.get("normalized_url_hash") or a.get("title", "")
            if not key:
                continue
            if key in by_key:
                by_key[key] = {**by_key[key], **{k: v for k, v in a.items() if v not in (None, "", [])}}
            else:
                by_key[key] = dict(a)
    return list(by_key.values())
