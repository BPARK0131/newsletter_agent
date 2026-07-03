"""
Obsidian Vault — Multi-Agent Artifact Store 공통 유틸
Streamlit HITL · Agent 스크립트에서 공유
"""

from __future__ import annotations

from ipn_agent.paths import PROJECT_DIR, resolve_vault_path

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


CATEGORIES = [
    "Routing/Internet Operations",
    "Backbone/Backhaul",
    "Transport/DCI",
    "DataCenter Network",
    "IP Security",
    "NetDevOps",
    "AI Network/Autonomous Network",
    "Standards/Architecture",
    "Other",
]

BIAS_RISKS = ["low", "medium", "high"]

EXPANSION_SOURCE_PREFIX = "expansion:"


def expansion_virtual_source_id(category_id: str) -> str:
    return f"{EXPANSION_SOURCE_PREFIX}{category_id}"


def parse_expansion_category_id(source_id: str) -> str | None:
    if source_id.startswith(EXPANSION_SOURCE_PREFIX):
        return source_id[len(EXPANSION_SOURCE_PREFIX):]
    return None


def split_picker_selection(selected_ids: list[str]) -> tuple[list[str], list[str]]:
    """소스 피커 선택 → (RSS/API source_id, expansion category_id)."""
    rss_ids: list[str] = []
    expansion_ids: list[str] = []
    for sid in selected_ids:
        cat_id = parse_expansion_category_id(sid)
        if cat_id:
            expansion_ids.append(cat_id)
        else:
            rss_ids.append(sid)
    return rss_ids, expansion_ids


def build_expansion_picker_sources(
    expansion: dict[str, Any],
    *,
    tavily_available: bool = True,
) -> list[dict[str, Any]]:
    """Tavily expansion_search 카테고리를 RSS와 동일한 소스 피커 항목으로 변환."""
    if not expansion.get("enabled"):
        return []
    items: list[dict[str, Any]] = []
    for cat in expansion.get("categories") or []:
        cat_id = cat.get("id", "")
        if not cat_id:
            continue
        items.append({
            "id": expansion_virtual_source_id(cat_id),
            "name": cat.get("name", cat_id),
            "enabled": tavily_available,
            "tier": "Discovery",
            "collect_method": "tavily_search",
            "is_expansion": True,
            "expansion_category_id": cat_id,
        })
    return items


def get_vault_path() -> Path:
    default = resolve_vault_path()
    default.mkdir(parents=True, exist_ok=True)
    for sub in ("01_raw", "02_review", "03_approved", "04_newsletter", "99_rejected", "registry"):
        (default / sub).mkdir(parents=True, exist_ok=True)
    (default / "01_raw" / "expansion").mkdir(parents=True, exist_ok=True)
    (default / "06_newsletter_used").mkdir(parents=True, exist_ok=True)
    for sub in ("draft", "published"):
        (default / "04_newsletter" / sub).mkdir(parents=True, exist_ok=True)
    (default / "05_newsletter_archive").mkdir(parents=True, exist_ok=True)
    return default


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
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


def build_frontmatter(meta: dict[str, Any], body: str) -> str:
    fm = yaml.dump(meta, allow_unicode=True, default_flow_style=False, sort_keys=False)
    return f"---\n{fm}---\n\n{body}"


def read_md(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    return parse_frontmatter(text)


def count_md_files(folder: Path) -> int:
    if not folder.is_dir():
        return 0
    return sum(1 for f in folder.rglob("*.md") if f.name != ".gitkeep")


def vault_stats(vault: Path | None = None) -> dict[str, int]:
    v = vault or get_vault_path()
    rejected_dir = v / "99_rejected"
    if not rejected_dir.is_dir():
        rejected_dir.mkdir(parents=True, exist_ok=True)
    nl_dir = v / "04_newsletter"
    radar_count = 0
    draft_count = 0
    published_count = 0
    if nl_dir.is_dir():
        for f in nl_dir.glob("*.md"):
            if f.name == ".gitkeep":
                continue
            if is_ietf_radar_file(f):
                radar_count += 1
            elif is_newsletter_output_file(f):
                draft_count += 1
        draft_dir = nl_dir / "draft"
        if draft_dir.is_dir():
            draft_count += sum(
                1 for f in draft_dir.glob("*.md")
                if f.name != ".gitkeep" and is_newsletter_output_file(f)
            )
        pub_dir = nl_dir / "published"
        if pub_dir.is_dir():
            published_count = sum(
                1 for f in pub_dir.glob("*.md") if f.name != ".gitkeep"
            )
    return {
        "01_raw": count_md_files(v / "01_raw"),
        "expansion_raw": count_md_files(v / "01_raw" / "expansion"),
        "02_review": count_md_files(v / "02_review"),
        "03_approved": count_md_files(v / "03_approved"),
        "04_newsletter": draft_count + published_count,
        "newsletter_draft": draft_count,
        "newsletter_published": published_count,
        "newsletter_archive": count_md_files(v / "05_newsletter_archive"),
        "newsletter_used": count_md_files(v / "06_newsletter_used"),
        "ietf_radar": radar_count,
        "99_rejected": count_md_files(rejected_dir),
    }


def list_markdown_files(folder: Path) -> list[Path]:
    """폴더 내 Markdown 파일 목록 (재귀, .gitkeep 제외)."""
    if not folder.is_dir():
        return []
    return sorted(
        (f for f in folder.rglob("*.md") if f.name != ".gitkeep"),
        key=lambda p: p.name,
    )


def count_markdown_files(folder: Path) -> int:
    return count_md_files(folder)


def read_markdown(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8")


def move_file_safe(src: Path, dst_dir: Path) -> bool:
    """대상 파일이 이미 있으면 덮어쓰지 않고 False 반환."""
    if not src.is_file():
        return False
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name
    if dst.exists():
        return False
    src.rename(dst)
    return True


def list_review_items(vault: Path | None = None) -> list[dict[str, Any]]:
    from ipn_agent.review.hitl import importance_to_score, route_hitl_status
    from ipn_agent.registry.published import content_hash_for_article, is_article_published
    from ipn_agent.review.metadata import (
        domain_from_url,
        infer_origin,
        infer_source_type,
        infer_trust_level,
    )

    v = vault or get_vault_path()
    review_dir = v / "02_review"
    if not review_dir.is_dir():
        return []

    items: list[dict[str, Any]] = []
    for md in sorted(review_dir.glob("*.md")):
        if md.name == ".gitkeep":
            continue
        # 03_approved / 99_rejected 에 이미 있으면 02_review 잔존 복본(ghost) — UI 제외
        if (v / "03_approved" / md.name).is_file() or (v / "99_rejected" / md.name).is_file():
            continue
        try:
            meta, body = read_md(md)
            sections = parse_review_body(body)
            url = meta.get("source_url", meta.get("url", ""))
            title = meta.get("title", md.stem)
            source = meta.get("source_name") or meta.get("source_id") or ""
            st = meta.get("source_type") or infer_source_type(meta, md)
            origin = meta.get("origin") or infer_origin(meta, st)
            ch = content_hash_for_article(
                body=body, summary=sections.get("요약", ""), meta=meta,
            )
            score_raw = meta.get("review_score")
            if score_raw is None:
                score_raw = importance_to_score(meta.get("importance_score"))
            review_score = float(score_raw) if score_raw is not None else None
            hitl_route = meta.get("hitl_route") or route_hitl_status(review_score)
            is_published = bool(meta.get("is_published")) or is_article_published(
                article_id=md.stem,
                url=url,
                title=title,
                source=source,
                content_hash=ch,
                vault=v,
            )
            items.append({
                "filename": md.name,
                "path": md,
                "meta": meta,
                "body": body,
                "sections": sections,
                "title": title,
                "category": meta.get("category", "Other"),
                "bias_risk": meta.get("bias_risk", "low"),
                "importance_score": int(meta.get("importance_score") or 0),
                "review_score": review_score,
                "discovery_score": meta.get("discovery_score"),
                "hitl_route": hitl_route,
                "is_published": is_published,
                "source_type": st,
                "origin": origin,
                "source_id": meta.get("source_id", ""),
                "source_name": source,
                "source_url": url,
                "domain": meta.get("domain") or domain_from_url(url),
                "trust_level": meta.get("trust_level") or infer_trust_level(meta, st),
                "topic_tags": meta.get("topic_tags") or [],
                "reviewed_at": meta.get("reviewed_at", ""),
                "summary": sections.get("요약", ""),
                "key_points": sections.get("핵심 포인트", ""),
                "newsletter_candidate": sections.get("뉴스레터 후보 문장", "") or sections.get("뉴스레터 헤드라인", ""),
                "recollect_required": bool(meta.get("recollect_required", False)),
                "review_required_flag": bool(meta.get("review_required", False)),
            })
        except Exception:
            continue
    return items


def list_approved_items(vault: Path | None = None) -> list[dict[str, Any]]:
    v = vault or get_vault_path()
    approved_dir = v / "03_approved"
    if not approved_dir.is_dir():
        return []

    items: list[dict[str, Any]] = []
    for md in sorted(approved_dir.glob("*.md")):
        try:
            meta, body = read_md(md)
            sections = parse_review_body(body)
            items.append({
                "filename": md.name,
                "path": md,
                "meta": meta,
                "body": body,
                "title": meta.get("title", md.stem),
                "category": meta.get("category", "Other"),
                "bias_risk": meta.get("bias_risk", "low"),
                "importance_score": int(meta.get("importance_score") or 0),
                "source_name": meta.get("source_name", ""),
                "source_url": meta.get("source_url", meta.get("url", "")),
                "topic_tags": meta.get("topic_tags") or [],
                "summary": sections.get("요약", ""),
                "key_points": sections.get("핵심 포인트", ""),
                "newsletter_candidate": sections.get("뉴스레터 후보 문장", "") or sections.get("뉴스레터 헤드라인", ""),
            })
        except Exception:
            continue
    return items


def get_newsletter_draft_dir(vault: Path | None = None) -> Path:
    d = (vault or get_vault_path()) / "04_newsletter" / "draft"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_newsletter_published_dir(vault: Path | None = None) -> Path:
    d = (vault or get_vault_path()) / "04_newsletter" / "published"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_newsletter_archive_dir(vault: Path | None = None) -> Path:
    """장기 보관용 발행 아카이브 (`05_newsletter_archive/{issue_date}/`)."""
    d = (vault or get_vault_path()) / "05_newsletter_archive"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_newsletter_used_dir(vault: Path | None = None) -> Path:
    """발행에 사용된 승인 기사 (`06_newsletter_used/{issue_date}/`)."""
    d = (vault or get_vault_path()) / "06_newsletter_used"
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_used_article_files(vault: Path | None = None) -> list[Path]:
    root = get_newsletter_used_dir(vault)
    return sorted(
        (f for f in root.rglob("*.md") if f.name != ".gitkeep"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def _resolve_newsletter_draft(vault: Path, filename: str) -> Path | None:
    """draft/ 우선, 없으면 04_newsletter/ 루트(레거시)에서 조회."""
    for candidate in (
        vault / "04_newsletter" / "draft" / filename,
        vault / "04_newsletter" / filename,
    ):
        if candidate.is_file():
            return candidate
    return None


def list_newsletter_files(vault: Path | None = None) -> list[Path]:
    """생성·편집 중인 draft 뉴스레터 목록 (레거시 루트 파일 포함)."""
    v = vault or get_vault_path()
    nl_dir = v / "04_newsletter"
    if not nl_dir.is_dir():
        return []
    seen: set[str] = set()
    files: list[Path] = []
    draft_dir = nl_dir / "draft"
    if draft_dir.is_dir():
        for f in draft_dir.glob("*.md"):
            if is_newsletter_output_file(f) and f.name not in seen:
                seen.add(f.name)
                files.append(f)
    for f in nl_dir.glob("*.md"):
        if is_newsletter_output_file(f) and f.name not in seen:
            seen.add(f.name)
            files.append(f)
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def list_published_newsletter_files(vault: Path | None = None) -> list[Path]:
    pub_dir = get_newsletter_published_dir(vault)
    return sorted(
        (f for f in pub_dir.glob("*.md") if f.name != ".gitkeep"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def _safe_issue_folder(issue_date: str) -> str:
    """Windows 경로에 안전한 issue_date 폴더명."""
    s = re.sub(r'[<>:"/\\|?*]', "-", str(issue_date).strip())
    return s[:64] or "unknown"


def _archive_newsletter_path(vault: Path, issue_date: str, filename: str) -> Path:
    return get_newsletter_archive_dir(vault) / _safe_issue_folder(issue_date) / filename


def _write_newsletter_archive(
    vault: Path,
    filename: str,
    meta: dict[str, Any],
    body: str,
    *,
    source: str,
) -> Path:
    """published/draft 본문을 05_newsletter_archive/{issue_date}/ 에 저장."""
    issue_date = _safe_issue_folder(
        str(meta.get("issue_date") or filename.replace("-newsletter.md", ""))
    )
    archive_dst = _archive_newsletter_path(vault, issue_date, filename)
    archive_dst.parent.mkdir(parents=True, exist_ok=True)

    archive_meta = dict(meta)
    archive_meta.update({
        "status": "archived",
        "archived_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source_published": source,
    })
    archive_dst.write_text(build_frontmatter(archive_meta, body), encoding="utf-8")
    return archive_dst


def sync_published_to_archive(vault: Path | None = None) -> tuple[int, list[str]]:
    """published/ 에 있으나 archive에 없는 발행본을 백필."""
    v = vault or get_vault_path()
    synced = 0
    messages: list[str] = []
    for pub in list_published_newsletter_files(v):
        meta, body = parse_frontmatter(pub.read_text(encoding="utf-8"))
        issue_key = _safe_issue_folder(
            str(meta.get("issue_date") or pub.name.replace("-newsletter.md", ""))
        )
        archive_dst = _archive_newsletter_path(v, issue_key, pub.name)
        if archive_dst.is_file():
            continue
        rel = f"05_newsletter_archive/{issue_key}/{pub.name}"
        _write_newsletter_archive(
            v, pub.name, meta, body,
            source=f"04_newsletter/published/{pub.name}",
        )
        synced += 1
        messages.append(rel)
    return synced, messages


def list_archived_newsletter_files(vault: Path | None = None) -> list[Path]:
    """05_newsletter_archive/**/*.md — 발행 호별 영구 보관본."""
    root = get_newsletter_archive_dir(vault)
    files = [
        f for f in root.rglob("*.md")
        if f.name != ".gitkeep" and is_newsletter_output_file(f)
    ]
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def move_approved_to_used(
    vault: Path,
    issue_date: str,
    published_at: str,
    *,
    included_files: list[str] | None = None,
) -> tuple[int, list[str]]:
    """03_approved → 06_newsletter_used/{issue_date}/ 이동 + 01_raw URL 마킹."""
    from ipn_agent.registry.article import mark_raw_newsletter_used

    approved_dir = vault / "03_approved"
    if not approved_dir.is_dir():
        return 0, []

    issue_key = _safe_issue_folder(issue_date)
    used_dir = get_newsletter_used_dir(vault) / issue_key
    used_dir.mkdir(parents=True, exist_ok=True)

    targets = sorted(approved_dir.glob("*.md"))
    if included_files is not None:
        want = set(included_files)
        targets = [p for p in targets if p.name in want]

    moved = 0
    names: list[str] = []
    for src in targets:
        if src.name == ".gitkeep":
            continue
        dst = used_dir / src.name
        if dst.exists():
            continue
        text = src.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)
        url = meta.get("source_url") or meta.get("url") or ""
        meta.update({
            "status": "used",
            "used_in_issue": issue_key,
            "published_at": published_at,
        })
        dst.write_text(build_frontmatter(meta, body), encoding="utf-8")
        src.unlink()
        if url:
            mark_raw_newsletter_used(vault, url, issue_key)
        moved += 1
        names.append(src.name)
    return moved, names


def publish_newsletter(filename: str, vault: Path | None = None) -> tuple[bool, str]:
    """draft → published/ + archive + approved used 이동 + draft 삭제."""
    v = vault or get_vault_path()
    src = _resolve_newsletter_draft(v, filename)
    if src is None:
        return False, f"draft 파일 없음: {filename}"

    text = src.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)
    issue_date = str(meta.get("issue_date") or filename.replace("-newsletter.md", ""))
    published_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    meta.update({
        "status": "published",
        "published_at": published_at,
        "issue_date": issue_date,
        "source_draft": src.name,
    })
    dst_dir = get_newsletter_published_dir(v)
    dst = dst_dir / filename
    issue_key = _safe_issue_folder(issue_date)
    archive_dst = _archive_newsletter_path(v, issue_key, filename)
    if dst.exists():
        if archive_dst.is_file():
            return False, f"이미 발행됨: published/{filename} (아카이브도 존재)"
        pub_meta, pub_body = parse_frontmatter(dst.read_text(encoding="utf-8"))
        _write_newsletter_archive(
            v, filename, pub_meta, pub_body,
            source=f"04_newsletter/published/{filename}",
        )
        return True, (
            f"아카이브 동기화 완료 → 05_newsletter_archive/{issue_key}/{filename} "
            f"(published는 기존 유지)"
        )

    content = build_frontmatter(meta, body if body else text)
    dst.write_text(content, encoding="utf-8")

    if archive_dst.is_file():
        archive_msg = f" · archive/{issue_key}/{filename} (기존)"
    else:
        _write_newsletter_archive(
            v, filename, meta, body if body else text,
            source=f"04_newsletter/published/{filename}",
        )
        archive_msg = f" · archive/{issue_key}/{filename}"

    raw_included = meta.get("included_approved_files")
    file_filter = (
        list(raw_included)
        if isinstance(raw_included, list) and len(raw_included) > 0
        else None
    )
    moved, moved_names = move_approved_to_used(
        v, issue_date, published_at, included_files=file_filter,
    )
    if moved_names:
        _register_used_articles_in_registry(
            v, issue_key, filename, published_at, moved_names,
        )
    used_msg = (
        f" · used {moved}건 → 06_newsletter_used/{issue_key}/"
        if moved else " · used 이동 대상 없음"
    )

    draft_removed = False
    if src.is_file():
        src.unlink()
        draft_removed = True
    legacy = v / "04_newsletter" / filename
    if legacy.is_file() and legacy != src:
        legacy.unlink()
        draft_removed = True

    draft_msg = " · draft 삭제됨" if draft_removed else ""
    return True, (
        f"발행 완료 → published/{filename}{archive_msg}{used_msg}{draft_msg}"
    )


def approve_review(filename: str, vault: Path | None = None) -> tuple[bool, str]:
    """02_review → 03_approved 이동 (Human Agent 승인)."""
    v = vault or get_vault_path()
    src = v / "02_review" / filename
    if not src.is_file():
        return False, f"파일 없음: {filename}"

    dst_dir = v / "03_approved"
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / filename

    if dst.exists():
        src.unlink()
        return True, f"검토 큐 정리 완료 (이미 03_approved/{filename})"

    text = src.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)
    meta["status"] = "approved"
    meta["pipeline_status"] = "approved"
    meta["approved_at"] = datetime.now().strftime("%Y-%m-%d")
    dst.write_text(build_frontmatter(meta, body), encoding="utf-8")
    src.unlink()
    return True, f"승인 완료 → 03_approved/{filename}"


def reject_review(filename: str, vault: Path | None = None) -> tuple[bool, str]:
    """02_review → 99_rejected 이동 (Human Agent 반려)."""
    v = vault or get_vault_path()
    src = v / "02_review" / filename
    if not src.is_file():
        return False, f"파일 없음: {filename}"

    dst_dir = v / "99_rejected"
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / filename

    if dst.exists():
        src.unlink()
        return True, f"반려 완료 → 99_rejected/{filename} (검토 큐 중복 제거)"

    text = src.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)
    meta["status"] = "rejected"
    meta["pipeline_status"] = "rejected"
    meta["rejected_at"] = datetime.now().strftime("%Y-%m-%d")
    dst.write_text(build_frontmatter(meta, body), encoding="utf-8")
    src.unlink()
    return True, f"반려 완료 → 99_rejected/{filename}"


def _register_used_articles_in_registry(
    vault: Path,
    issue_key: str,
    newsletter_filename: str,
    published_at: str,
    moved_names: list[str],
) -> None:
    """06_newsletter_used 이동된 기사를 published registry에 등록."""
    from ipn_agent.registry.published import build_registry_entry, register_published_article

    used_dir = get_newsletter_used_dir(vault) / issue_key
    for name in moved_names:
        md = used_dir / name
        if not md.is_file():
            continue
        meta, body = read_md(md)
        sections = parse_review_body(body)
        url = meta.get("source_url") or meta.get("url") or ""
        entry = build_registry_entry(
            article_id=md.stem,
            title=meta.get("title", md.stem),
            url=url,
            source=meta.get("source_name") or meta.get("source_id") or "",
            published_newsletter=newsletter_filename,
            published_at=published_at,
            content_text=body,
            summary=sections.get("요약", ""),
        )
        register_published_article(entry, vault)


def parse_review_body(body: str) -> dict[str, str]:
    """리뷰 Markdown 본문에서 섹션 추출."""
    sections: dict[str, str] = {}
    current = ""
    lines: list[str] = []
    for line in body.splitlines():
        if line.startswith("# "):
            if current:
                sections[current] = "\n".join(lines).strip()
            current = line[2:].strip()
            lines = []
        else:
            lines.append(line)
    if current:
        sections[current] = "\n".join(lines).strip()
    return sections


IETF_RADAR_FILENAME = "ietf_radar.md"

COLLECTION_MODE_LABELS: dict[str, str] = {
    "rss": "RSS",
    "rss_or_url": "RSS (+ URL fallback)",
    "url": "URL Fetch",
    "blog_index": "웹 크롤링",
    "tavily_search": "Tavily 검색",
    "api": "API",
}


def collection_mode_label(mode: str) -> str:
    return COLLECTION_MODE_LABELS.get(mode, mode or "—")


def is_ietf_radar_file(path: Path) -> bool:
    return path.name == IETF_RADAR_FILENAME or path.name.endswith("-standardization_radar.md")


def is_newsletter_output_file(path: Path) -> bool:
    """실제 뉴스레터 산출물 (*-newsletter.md). ietf_radar 제외."""
    if is_ietf_radar_file(path):
        return False
    return path.name.endswith("-newsletter.md")


def get_ietf_radar_path(vault: Path | None = None) -> Path:
    return (vault or get_vault_path()) / "04_newsletter" / IETF_RADAR_FILENAME


def load_sources_from_yaml() -> list[dict[str, Any]]:
    """sources.yaml의 수집 가능 소스 목록 (UI 표시용)."""
    config_path = PROJECT_DIR / "sources.yaml"
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    sections = [
        ("regular_sources", "Tier 1"),
        ("vendor_sources", "Tier 2"),
        ("news_sources", "News"),
        ("community_sources", "Community"),
        ("reference_sources", "Reference"),
    ]
    sources: list[dict[str, Any]] = []
    for section_key, tier in sections:
        for src in config.get(section_key, []):
            sources.append({
                "id": src.get("id", ""),
                "name": src.get("name", src.get("id", "")),
                "type": src.get("type", ""),
                "collection_mode": src.get("collection_mode", ""),
                "collect_method": collection_mode_label(src.get("collection_mode", "")),
                "enabled": bool(src.get("enabled", False)),
                "tier": tier,
                "is_ietf": src.get("id") == "ietf_datatracker",
            })
    return sources


def load_expansion_search_config() -> dict[str, Any]:
    """sources.yaml expansion_search 섹션 (UI·수집 상한 표시용)."""
    config_path = PROJECT_DIR / "sources.yaml"
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}
    es = config.get("expansion_search") or {}
    categories: list[dict[str, Any]] = []
    for cat in es.get("search_categories", []):
        categories.append({
            "id": cat.get("id", ""),
            "name": cat.get("name", cat.get("id", "")),
            "query": cat.get("query", ""),
            "time_range": cat.get("time_range", es.get("default_time_range", "month")),
            "topic": cat.get("topic", es.get("default_topic", "news")),
            "max_article_age_days": int(cat.get("max_article_age_days") or es.get("default_max_article_age_days", 45)),
            "max_results": int(cat.get("max_results", 2)),
        })
    return {
        "enabled": bool(es.get("enabled", False)),
        "mode": es.get("mode", "semi_open_discovery"),
        "min_discovery_score": int(es.get("min_discovery_score", 3)),
        "max_saved_per_category": int(es.get("max_saved_per_category", 3)),
        "max_total_results": int(es.get("max_total_results", 20)),
        "default_topic": es.get("default_topic", "news"),
        "default_time_range": es.get("default_time_range", "month"),
        "default_max_article_age_days": int(es.get("default_max_article_age_days", 45)),
        "exclude_domains": list(es.get("default_exclude_domains") or es.get("exclude_domains") or []),
        "categories": categories,
    }


def load_discovery_logs(
    log_name: str = "search_discarded.jsonl",
    limit: int = 100,
) -> list[dict[str, Any]]:
    """logs/discovery/*.jsonl 최근 항목 (quality gate 감사 로그)."""
    log_path = PROJECT_DIR / "logs" / "discovery" / log_name
    if not log_path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in log_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    except Exception:
        return []
    return rows[-limit:]


def list_expansion_raw(vault: Path | None = None) -> list[dict[str, Any]]:
    """01_raw/expansion/**/*.md — Tavily discovery 수집 결과."""
    v = vault or get_vault_path()
    base = v / "01_raw" / "expansion"
    items: list[dict[str, Any]] = []
    for md in list_markdown_files(base):
        try:
            meta, body = read_md(md)
            url = meta.get("url", "")
            domain = ""
            if url:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc
            items.append({
                "path": md,
                "filename": md.name,
                "category": meta.get("category") or md.parent.name,
                "title": meta.get("title", md.stem),
                "url": url,
                "domain": domain,
                "discovery_score": int(meta.get("discovery_score") or 0),
                "discovery_reasons": meta.get("discovery_reasons") or [],
                "search_query": meta.get("search_query", ""),
                "bias_risk": meta.get("bias_risk", "low"),
                "body": body,
                "meta": meta,
            })
        except Exception:
            continue
    items.sort(key=lambda x: (-x["discovery_score"], x["title"]))
    return items


def discovery_ops_stats(vault: Path | None = None) -> dict[str, int]:
    """Expansion raw·게이트 집계 (운영콘솔)."""
    v = vault or get_vault_path()
    expansion_raw = count_md_files(v / "01_raw" / "expansion")
    discarded = len(load_discovery_logs("search_discarded.jsonl", limit=10000))
    low = len(load_discovery_logs("search_low_score.jsonl", limit=10000))
    return {
        "expansion_raw": expansion_raw,
        "gate_discarded": discarded,
        "gate_low_score": low,
    }


# 하위 호환 alias
discovery_staging_stats = discovery_ops_stats
list_discovery_staging = list_expansion_raw
