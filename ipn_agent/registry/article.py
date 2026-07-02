"""
Vault 전역 기사 URL 레지스트리 — 수집·리뷰·뉴스레터 중복 방지
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse, urlunparse

import yaml

# URL 중복 검사 대상 Phase
URL_INDEX_PHASES: tuple[str, ...] = (
    "01_raw",
    "02_review",
    "03_approved",
    "06_newsletter_used",
    "99_rejected",
)


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    try:
        meta = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        meta = {}
    return meta, parts[2].strip()


def _build_frontmatter(meta: dict, body: str) -> str:
    fm = yaml.dump(meta, allow_unicode=True, default_flow_style=False, sort_keys=False)
    return f"---\n{fm}---\n\n{body}"


def canonical_url(url: str) -> str:
    """중복 비교용 URL 정규화 (scheme/host/path, query·fragment 제거)."""
    if not url or not str(url).strip():
        return ""
    raw = str(url).strip()
    p = urlparse(raw)
    scheme = (p.scheme or "https").lower()
    host = p.netloc.lower().removeprefix("www.")
    if not host:
        return raw.lower().split("?")[0].split("#")[0].rstrip("/")
    path = p.path.rstrip("/") or "/"
    return urlunparse((scheme, host, path, "", "", "")).lower()


def _url_from_meta(meta: dict) -> str:
    for key in ("source_url", "url", "link", "canonical_url"):
        val = meta.get(key)
        if val:
            return canonical_url(str(val))
    return ""


def _iter_phase_md_files(vault: Path, phase: str) -> list[Path]:
    root = vault / phase
    if not root.is_dir():
        return []
    return sorted(
        f for f in root.rglob("*.md")
        if f.name != ".gitkeep"
    )


def build_url_index(vault: Path) -> dict[str, list[str]]:
    """canonical_url → vault 상대 경로 목록."""
    index: dict[str, list[str]] = {}
    for phase in URL_INDEX_PHASES:
        for md in _iter_phase_md_files(vault, phase):
            try:
                text = md.read_text(encoding="utf-8")
                meta, _ = _parse_frontmatter(text)
            except OSError:
                continue
            url = _url_from_meta(meta)
            if not url:
                continue
            rel = md.relative_to(vault).as_posix()
            index.setdefault(url, []).append(rel)
    return index


def find_url_in_vault(
    vault: Path,
    url: str,
    *,
    exclude_rel_paths: set[str] | None = None,
    phases: tuple[str, ...] | None = None,
) -> str | None:
    """URL이 vault에 있으면 첫 번째 상대 경로 반환, 없으면 None."""
    key = canonical_url(url)
    if not key:
        return None
    exclude = exclude_rel_paths or set()
    scan_phases = phases or URL_INDEX_PHASES
    for phase in scan_phases:
        for md in _iter_phase_md_files(vault, phase):
            rel = md.relative_to(vault).as_posix()
            if rel in exclude:
                continue
            try:
                meta, _ = _parse_frontmatter(md.read_text(encoding="utf-8"))
            except OSError:
                continue
            if _url_from_meta(meta) == key:
                return rel
    return None


def url_blocks_review(vault: Path, url: str, raw_rel: str | None = None) -> str | None:
    """리뷰 생성 스킵 — 동일 URL이 review/approved/used 에 있으면."""
    exclude = {raw_rel} if raw_rel else set()
    loc = find_url_in_vault(
        vault, url,
        exclude_rel_paths=exclude,
        phases=("02_review", "03_approved", "06_newsletter_used"),
    )
    if loc:
        return loc
    return None


def mark_raw_newsletter_used(vault: Path, url: str, issue_date: str) -> int:
    """01_raw 내 동일 URL frontmatter에 newsletter_used_in 기록."""
    key = canonical_url(url)
    if not key:
        return 0
    updated = 0
    for md in _iter_phase_md_files(vault, "01_raw"):
        try:
            text = md.read_text(encoding="utf-8")
            meta, body = _parse_frontmatter(text)
        except OSError:
            continue
        if _url_from_meta(meta) != key:
            continue
        if meta.get("newsletter_used_in") == issue_date:
            continue
        meta["newsletter_used_in"] = issue_date
        meta["status"] = "newsletter_used"
        md.write_text(_build_frontmatter(meta, body), encoding="utf-8")
        updated += 1
    return updated
