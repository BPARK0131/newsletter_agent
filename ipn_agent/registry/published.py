"""기발행 기사 registry — hash 기반 중복 차단 (LLM 없음)."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse, urlunparse

from ipn_agent.vault.utils import get_vault_path, parse_frontmatter, parse_review_body, read_md

REGISTRY_REL = Path("registry") / "published_articles.json"
UTM_PARAMS = frozenset({
    "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
})


def registry_path(vault: Path | None = None) -> Path:
    p = (vault or get_vault_path()) / REGISTRY_REL
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_url_for_hash(url: str) -> str:
    if not url or not str(url).strip():
        return ""
    raw = str(url).strip()
    p = urlparse(raw)
    scheme = (p.scheme or "https").lower()
    host = p.netloc.lower().removeprefix("www.")
    path = p.path.rstrip("/") or "/"
    qs = parse_qs(p.query, keep_blank_values=False)
    filtered = {k: v for k, v in qs.items() if k.lower() not in UTM_PARAMS}
    query = "&".join(
        f"{k}={filtered[k][0]}" for k in sorted(filtered.keys()) if filtered[k]
    )
    return urlunparse((scheme, host, path, "", query, "")).lower()


def normalized_url_hash(url: str) -> str:
    n = normalize_url_for_hash(url)
    return _sha256(n) if n else ""


def title_hash(title: str) -> str:
    if not title:
        return ""
    t = str(title).lower().strip()
    t = re.sub(r"\s+", " ", t)
    return _sha256(t)


def content_hash_from_text(text: str) -> str:
    if not text:
        return ""
    t = re.sub(r"\s+", " ", str(text).strip().lower())
    return _sha256(t)


def content_hash_for_article(
    *,
    body: str = "",
    summary: str = "",
    meta: dict | None = None,
) -> str:
    if body and len(body.strip()) >= 80:
        return content_hash_from_text(body[:50000])
    if summary:
        return content_hash_from_text(summary)
    if meta:
        sections = parse_review_body(body) if body and "# 요약" in body else {}
        s = sections.get("요약", "") or meta.get("summary", "")
        if s:
            return content_hash_from_text(s)
    return ""


def load_registry(vault: Path | None = None) -> list[dict[str, Any]]:
    path = registry_path(vault)
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        backup = path.with_suffix(f".corrupt.{datetime.now():%Y%m%d%H%M%S}.json")
        shutil.copy2(path, backup)
    return []


def save_registry(entries: list[dict[str, Any]], vault: Path | None = None) -> None:
    path = registry_path(vault)
    path.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def build_registry_entry(
    *,
    article_id: str,
    title: str,
    url: str,
    source: str,
    published_newsletter: str,
    published_at: str,
    content_text: str = "",
    summary: str = "",
) -> dict[str, Any]:
    return {
        "article_id": article_id,
        "title": title,
        "url": url,
        "source": source,
        "published_newsletter": published_newsletter,
        "published_at": published_at,
        "normalized_url_hash": normalized_url_hash(url),
        "title_hash": title_hash(title),
        "content_hash": content_hash_from_text(content_text or summary),
    }


def is_published_match(
    entry: dict[str, Any],
    *,
    article_id: str = "",
    url: str = "",
    title: str = "",
    source: str = "",
    content_hash: str = "",
    title_hash_val: str = "",
    url_hash: str = "",
) -> bool:
    if article_id and entry.get("article_id") == article_id:
        return True
    nu = url_hash or normalized_url_hash(url)
    if nu and entry.get("normalized_url_hash") == nu:
        return True
    ch = content_hash or content_hash_from_text("")
    if ch and entry.get("content_hash") == ch:
        return True
    th = title_hash_val or title_hash(title)
    src = (source or "").strip().lower()
    if th and src and entry.get("title_hash") == th:
        if (entry.get("source") or "").strip().lower() == src:
            return True
    return False


def find_published_entry(
    registry: list[dict[str, Any]],
    **kwargs: Any,
) -> dict[str, Any] | None:
    for e in registry:
        if is_published_match(e, **kwargs):
            return e
    return None


def is_article_published(
    *,
    article_id: str = "",
    url: str = "",
    title: str = "",
    source: str = "",
    content_hash: str = "",
    vault: Path | None = None,
) -> bool:
    reg = load_registry(vault)
    return find_published_entry(
        reg,
        article_id=article_id,
        url=url,
        title=title,
        source=source,
        content_hash=content_hash,
    ) is not None


def register_published_article(entry: dict[str, Any], vault: Path | None = None) -> None:
    reg = load_registry(vault)
    if find_published_entry(
        reg,
        article_id=entry.get("article_id", ""),
        url=entry.get("url", ""),
        title=entry.get("title", ""),
        source=entry.get("source", ""),
        content_hash=entry.get("content_hash", ""),
    ):
        return
    reg.append(entry)
    save_registry(reg, vault)


def sync_registry_from_used_folder(vault: Path | None = None) -> int:
    """06_newsletter_used → registry 백필."""
    v = vault or get_vault_path()
    used_root = v / "06_newsletter_used"
    if not used_root.is_dir():
        return 0
    added = 0
    for md in used_root.rglob("*.md"):
        if md.name == ".gitkeep":
            continue
        meta, body = read_md(md)
        url = meta.get("source_url") or meta.get("url") or ""
        entry = build_registry_entry(
            article_id=md.stem,
            title=meta.get("title", md.stem),
            url=url,
            source=meta.get("source_name") or meta.get("source_id") or "",
            published_newsletter=meta.get("used_in_issue", "unknown"),
            published_at=meta.get("published_at") or datetime.now().isoformat(),
            content_text=body,
            summary=parse_review_body(body).get("요약", "") if body else "",
        )
        before = len(load_registry(v))
        register_published_article(entry, v)
        if len(load_registry(v)) > before:
            added += 1
    return added
