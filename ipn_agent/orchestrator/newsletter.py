"""뉴스레터 Editor 파이프라인 — approved 로딩 · 분석 · 표준 연결 · draft 생성."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, get_args

import yaml
from pydantic import BaseModel, Field

from ipn_agent.core.tool_logger import log_tool_event

CategoryType = Literal[
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


class RawArticle(BaseModel):
    title: str
    url: str
    content: str
    source_name: str
    published: str = ""
    is_vendor: bool = False
    category: str = ""
    summary: str = ""
    headline: str = ""
    keywords: list[str] = Field(default_factory=list)
    bias_risk: str = "low"
    bias_note: str = ""
    origin: str = ""
    source_type: str = ""
    approved_filename: str = ""


class ArticleAnalysis(BaseModel):
    title: str
    url: str
    headline: str = Field(description="한국어 헤드라인 1줄")
    summary: str = Field(description="핵심 내용 3~5줄, 한국어")
    category: CategoryType
    keywords: list[str] = []
    is_vendor: bool = False
    bias_flag: bool = False
    bias_note: str = ""
    standards_context: list[str] = Field(default_factory=list)


class NewsletterOutput(BaseModel):
    date: str
    total_articles: int
    used_sources: list[str] = []
    fallback_used: bool = False
    sections: dict[str, list[dict]] = {}
    review_required: list[str] = []


LOW_QUALITY_PHRASES: tuple[str, ...] = (
    "제공된 본문에는",
    "홍보성 요소가 많이 섞여",
    "핵심 논지는",
    "해석됩니다",
    "내용으로 보입니다",
)

IDR_BGP_KEYWORDS: tuple[str, ...] = (
    "bgp", "route leak", "route-leak", "hijack", "rpki", "aspa",
    "as path", "prefix hijack", "routing policy",
)
IDR_BGP_EXCLUDE_MARKERS: tuple[str, ...] = (
    "ipv6-only", "ipv6 only", "nat64", "clat",
)
AI_NETWORK_CATEGORIES: frozenset[str] = frozenset({
    "AI Network/Autonomous Network",
})

MAX_EDITOR_ARTICLE_SUMMARY_CHARS = 1500

_WG_MEANINGS_CACHE: dict[str, str] | None = None


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


def _parse_review_sections(body: str) -> dict[str, str]:
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


def _normalize_category(category: str) -> CategoryType:
    valid = set(get_args(CategoryType))
    if category in valid:
        return category  # type: ignore[return-value]
    return "Other"


def clean_text(text: str) -> str:
    if not text:
        return ""
    t = str(text).replace("\\n", "\n").replace("\\t", " ")
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = re.sub(r"[ \t]+", " ", t)
    return t.strip()


def _is_low_quality_text(text: str) -> bool:
    return any(p in (text or "") for p in LOW_QUALITY_PHRASES)


def obsidian_loader_node(state: dict[str, Any]) -> dict[str, Any]:
    """vault/03_approved/ 승인 Markdown 로딩."""
    vault_path = state.get("vault_path", "")
    approved_dir = Path(vault_path) / "03_approved" if vault_path else None

    log_tool_event(
        "newsletter", "approved_reader", "running",
        "Approved Markdown 읽기 시작", target="03_approved",
    )

    if not approved_dir or not approved_dir.is_dir():
        print(f"[WARN] 03_approved/ 폴더 없음 ({approved_dir})")
        log_tool_event(
            "newsletter", "approved_reader", "error",
            "03_approved 폴더 없음", target="03_approved",
        )
        return {"raw_articles": [], "fallback_used": False}

    articles: list[dict] = []
    for md_file in sorted(approved_dir.glob("*.md")):
        try:
            text = md_file.read_text(encoding="utf-8")
            meta, body = _parse_frontmatter(text)
            if not body.strip():
                continue
            sections = _parse_review_sections(body)
            summary = sections.get("요약", "")
            if meta.get("recollect_required") or _is_low_quality_text(summary):
                print(f"[SKIP] recollect_required — approved 제외: {md_file.name}")
                continue
            headline = clean_text(
                sections.get("뉴스레터 헤드라인")
                or sections.get("뉴스레터 후보 문장")
                or meta.get("title", md_file.stem)
            )
            articles.append(RawArticle(
                title=meta.get("title", md_file.stem),
                url=meta.get("source_url", meta.get("url", "")),
                content=body,
                source_name=meta.get("source_name", meta.get("source_id", "obsidian")),
                published=str(meta.get("published_at", meta.get("published", ""))),
                is_vendor=bool(meta.get("is_vendor", False)),
                category=meta.get("category", ""),
                summary=clean_text(summary),
                headline=headline[:300],
                keywords=list(meta.get("topic_tags") or []),
                bias_risk=str(meta.get("bias_risk", "low")),
                bias_note=clean_text(str(meta.get("bias_note") or ""))[:400],
                origin=str(meta.get("origin") or ""),
                source_type=str(meta.get("source_type") or ""),
                approved_filename=md_file.name,
            ).model_dump())
            articles[-1]["recollect_required"] = False
        except Exception as e:
            print(f"[WARN] 파일 로딩 실패 {md_file.name}: {e}")

    print(f"[INFO] Obsidian approved/ → {len(articles)}건 로딩")
    log_tool_event(
        "newsletter", "approved_reader", "success",
        f"{len(articles)}건 로딩 완료", target="03_approved", count=len(articles),
    )
    return {"raw_articles": articles, "fallback_used": False}


def load_approved_from_rel_paths(
    vault_path: str,
    rel_paths: list[str],
    *,
    max_summary_chars: int = MAX_EDITOR_ARTICLE_SUMMARY_CHARS,
) -> list[dict]:
    """지정 approved 경로만 metadata·요약 중심 로드."""
    articles: list[dict] = []
    vault = Path(vault_path)
    for rel in rel_paths:
        md = vault / rel.replace("\\", "/")
        if not md.is_file():
            print(f"[WARN] approved 파일 없음: {rel}")
            continue
        try:
            text = md.read_text(encoding="utf-8")
            meta, body = _parse_frontmatter(text)
            if not body.strip():
                continue
            sections = _parse_review_sections(body)
            summary = clean_text(sections.get("요약", ""))[:max_summary_chars]
            key_pts = clean_text(sections.get("핵심 포인트", ""))[:600]
            if key_pts and key_pts not in summary:
                summary = f"{summary}\n\n{key_pts}".strip()[:max_summary_chars]
            if meta.get("recollect_required") or _is_low_quality_text(summary):
                print(f"[SKIP] recollect_required — pipeline 제외: {md.name}")
                continue
            headline = clean_text(
                sections.get("뉴스레터 헤드라인")
                or sections.get("뉴스레터 후보 문장")
                or meta.get("title", md.stem)
            )
            articles.append(RawArticle(
                title=meta.get("title", md.stem),
                url=meta.get("source_url", meta.get("url", "")),
                content=summary,
                source_name=meta.get("source_name", meta.get("source_id", "obsidian")),
                published=str(meta.get("published_at", meta.get("published", ""))),
                is_vendor=bool(meta.get("is_vendor", False)),
                category=meta.get("category", ""),
                summary=summary,
                headline=headline[:300],
                keywords=list(meta.get("topic_tags") or []),
                bias_risk=str(meta.get("bias_risk", "low")),
                bias_note=clean_text(str(meta.get("bias_note") or ""))[:400],
                origin=str(meta.get("origin") or ""),
                source_type=str(meta.get("source_type") or ""),
                approved_filename=md.name,
            ).model_dump())
        except Exception as e:
            print(f"[WARN] pipeline loader 실패 {rel}: {e}")
    return articles


def analysis_node(state: dict[str, Any]) -> dict[str, Any]:
    raw = state.get("raw_articles", [])
    analyzed: list[dict] = []
    bias_count = 0

    for item in raw:
        article = RawArticle(**item)
        cat = _normalize_category(item.get("category") or article.category or "Other")
        summary = clean_text(item.get("summary") or article.summary or "")
        if not summary and article.content:
            summary = clean_text(article.content[:800])
        headline = clean_text(item.get("headline") or article.headline or article.title)
        keywords = item.get("keywords") or article.keywords or []
        if item.get("recollect_required") or _is_low_quality_text(summary):
            print(f"[SKIP] 본문 품질 부족 — 뉴스레터 제외: {article.title[:50]}")
            continue
        bias_flag = article.bias_risk in ("medium", "high")
        bias_note = clean_text(item.get("bias_note") or article.bias_note or "")
        analysis_result = ArticleAnalysis(
            title=clean_text(article.title),
            url=article.url,
            headline=headline[:200],
            summary=summary[:1500],
            category=cat,
            keywords=keywords,
            is_vendor=article.is_vendor,
            bias_flag=bias_flag,
            bias_note=bias_note[:300],
        )
        if analysis_result.bias_flag:
            bias_count += 1
        entry = analysis_result.model_dump()
        entry["source_name"] = article.source_name
        entry["origin"] = item.get("origin") or article.origin or ""
        entry["source_type"] = item.get("source_type") or article.source_type or ""
        entry["approved_filename"] = item.get("approved_filename") or article.approved_filename or ""
        analyzed.append(entry)

    return {"analyzed_articles": analyzed, "bias_count": bias_count}


def _load_wg_meanings() -> dict[str, str]:
    global _WG_MEANINGS_CACHE
    if _WG_MEANINGS_CACHE is not None:
        return _WG_MEANINGS_CACHE
    defaults = {
        "idr": "BGP 정책·Route Leak·Routing Security 논의와 연결",
        "bess": "EVPN/VXLAN·VPN 서비스 구현 방향과 연결",
        "lsr": "Link State·IGP 확장 동향과 연결",
        "spring": "SR-MPLS/SRv6·백본/기간망 아키텍처 흐름과 연결",
    }
    try:
        from ipn_agent.standards.radar import load_ietf_source_config
        cfg = load_ietf_source_config()
        radar = cfg.get("wg_radar", {})
        out = {wg: radar.get(wg, {}).get("change_meaning") or defaults[wg] for wg in defaults}
        _WG_MEANINGS_CACHE = out
        return out
    except Exception:
        _WG_MEANINGS_CACHE = defaults
        return defaults


def _article_match_text(article: dict) -> str:
    parts = [
        article.get("title", ""),
        article.get("headline", ""),
        article.get("summary", ""),
        " ".join(str(k) for k in (article.get("keywords") or [])),
    ]
    return clean_text(" ".join(parts)).lower().replace("_", "-")


def _count_keyword_hits(text: str, keywords: tuple[str, ...]) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    for kw in keywords:
        kn = kw.lower()
        if kn in text:
            score += 1
            reasons.append(kw)
    return score, reasons


def _link_standards_context(article: dict) -> tuple[list[str], int, list[str]]:
    text = _article_match_text(article)
    title_text = clean_text(
        f"{article.get('title', '')} {article.get('headline', '')}"
    ).lower()
    category = article.get("category", "")
    meanings = _load_wg_meanings()
    linked: list[str] = []
    all_reasons: list[str] = []
    total_score = 0
    seen: set[str] = set()

    skip_idr = (
        category in AI_NETWORK_CATEGORIES
        or any(m in text for m in IDR_BGP_EXCLUDE_MARKERS)
    )
    if not skip_idr:
        idr_score = 0
        idr_reasons: list[str] = []
        for kw in IDR_BGP_KEYWORDS:
            kn = kw.lower()
            if kn in title_text:
                idr_score += 2
                idr_reasons.append(f"title:{kw}")
            elif kn in text:
                idr_score += 1
                idr_reasons.append(f"body:{kw}")
        if idr_score >= 2:
            linked.append(f"- IDR / BGP: {meanings.get('idr', '')}")
            all_reasons.extend(idr_reasons)
            total_score += idr_score
            seen.add("idr")

    other_rules: list[tuple[tuple[str, ...], str, str]] = [
        (("evpn", "vxlan", "vpn"), "bess", "BESS / EVPN"),
        (("is-is", "isis", "ospf", "igp", "link-state", "link_state"), "lsr", "LSR / IGP"),
        (("srv6", "sr-mpls", "sr_mpls", "segment routing", "segment-routing"), "spring", "SPRING / Segment Routing"),
    ]
    for keywords, wg_key, label in other_rules:
        if wg_key in seen:
            continue
        hits, reasons = _count_keyword_hits(text, keywords)
        title_hits = sum(1 for kw in keywords if kw.lower() in title_text)
        wg_score = hits + title_hits
        if wg_score >= 2:
            linked.append(f"- {label}: {meanings.get(wg_key, label)}")
            all_reasons.extend([f"{wg_key}:{r}" for r in reasons])
            total_score += wg_score
            seen.add(wg_key)

    return linked, total_score, all_reasons


def standards_linker_node(state: dict[str, Any]) -> dict[str, Any]:
    analyzed = state.get("analyzed_articles", [])
    linked_count = 0
    updated: list[dict] = []
    for item in analyzed:
        entry = dict(item)
        contexts, match_score, match_reasons = _link_standards_context(entry)
        if match_score >= 2:
            entry["standards_context"] = contexts
            entry["standards_match_score"] = match_score
            entry["standards_match_reasons"] = match_reasons
            linked_count += 1
        else:
            entry["standards_context"] = []
            entry["standards_match_score"] = match_score
            entry["standards_match_reasons"] = match_reasons
        updated.append(entry)
    print(f"[INFO] standards_linker → {linked_count}/{len(updated)}건 표준 맥락 연결")
    log_tool_event(
        "newsletter", "standards_linker", "success",
        f"표준 맥락 연결 {linked_count}건", count=linked_count,
    )
    return {"analyzed_articles": updated}


def hitl_node(state: dict[str, Any]) -> dict[str, Any]:
    flagged = [
        a["title"] for a in state.get("analyzed_articles", [])
        if a.get("bias_flag")
    ]
    print(f"[HITL] 편향 항목 {len(flagged)}건: {flagged}")
    return {}


def _shorten(text: str, max_len: int = 45) -> str:
    t = clean_text(text or "").replace("\n", " ")
    t = re.sub(r"[.。!?！？…]+$", "", t).strip()
    if len(t) <= max_len:
        return t
    return t[:max_len].rstrip() + "…"


def _one_line_summary(summary: str, max_len: int = 120) -> str:
    s = clean_text(summary or "").replace("\n", " ")
    for sep in (". ", "。", "! ", "? ", "!\n", "?\n"):
        if sep in s:
            first = s.split(sep)[0].strip()
            if first:
                return _shorten(first, max_len) if len(first) > max_len else first
    return _shorten(s, max_len)


def _display_source_label(
    source_name: str,
    *,
    origin: str = "",
    source_type: str = "",
) -> str:
    """뉴스레터 표시용 출처 라벨 (웹검색·등록소스 구분)."""
    if not source_name or not str(source_name).strip():
        return ""
    sn = str(source_name).strip()
    origin_l = str(origin or "").strip().lower()
    stype = str(source_type or "").strip().lower()
    sn_lower = sn.lower()

    if (
        origin_l == "open_web_search"
        or stype in ("tavily", "expansion_search", "open_web")
        or sn_lower.startswith("expansion/")
        or sn_lower.startswith("expansion__")
    ):
        return "웹검색"

    s = sn
    for suffix in ("_blog", "_newsroom", "_news"):
        if s.lower().endswith(suffix):
            s = s[: -len(suffix)]
            break
    parts = [p for p in s.split("_") if p]
    if len(parts) >= 2:
        return " ".join(p.capitalize() for p in parts)
    if parts:
        return parts[0].capitalize()
    return s


def _format_tags(keywords: list[str] | None, max_tags: int = 6) -> str:
    tags = [k.strip() for k in (keywords or []) if k and str(k).strip()][:max_tags]
    if not tags:
        return ""
    return f"**keyword:** {', '.join(tags)}"


def _format_article_card(index: int, article: dict) -> list[str]:
    headline_raw = clean_text(article.get("headline") or article.get("title") or "제목 없음")
    short_headline = _shorten(headline_raw, 45)
    summary = clean_text(article.get("summary") or "")
    one_line = _one_line_summary(summary)
    tags_line = _format_tags(article.get("keywords"))
    url = (article.get("url") or "").strip()
    source_label = _display_source_label(
        article.get("source_name") or "",
        origin=article.get("origin") or "",
        source_type=article.get("source_type") or "",
    )

    block = [
        "",
        "---",
        "",
        f"#### {index}. {short_headline}",
        "",
    ]
    if one_line:
        block.extend([f"**한줄 요약:** {one_line}", ""])
    if summary:
        block.extend(["**상세 요약**", "", summary, ""])
    if tags_line:
        block.extend([tags_line, ""])
    ctx = article.get("standards_context") or []
    if ctx:
        block.extend(["**관련 표준 맥락**", ""] + ctx + [""])
    if source_label or url:
        parts: list[str] = []
        if source_label:
            parts.append(f"**출처:** {source_label}")
        if url:
            parts.append(f"[원문 보기]({url})")
        block.append(" · ".join(parts))
    if article.get("bias_flag"):
        note = clean_text(article.get("bias_note") or "")
        if not note and article.get("is_vendor"):
            note = "Vendor 소스 — 편향(Bias) 검토 권장"
        elif not note:
            note = "편향(Bias) 검토 권장"
        block.extend(["", f"**편향 검토:** {_shorten(note, 140)}"])
    return block


def _save_newsletter_md(
    vault_path: str,
    output: NewsletterOutput,
    *,
    included_urls: list[str] | None = None,
    included_approved_files: list[str] | None = None,
) -> None:
    out_dir = Path(vault_path) / "04_newsletter" / "draft"
    out_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{output.date}-newsletter.md"
    log_tool_event(
        "newsletter", "newsletter_writer", "running",
        "뉴스레터 Markdown 저장 중", target=filename,
    )
    body_lines = [
        f"# IP Network 기술 동향 뉴스레터 — {output.date}",
        f"\n총 기사: {output.total_articles}건 | 출처: {', '.join(output.used_sources)}",
    ]
    if output.fallback_used:
        body_lines.append("\n> ⚠️ 샘플 데이터 사용 (실제 수집 실패)")

    for category, articles in output.sections.items():
        body_lines.append(f"\n## {category}")
        for idx, a in enumerate(articles, start=1):
            body_lines.extend(_format_article_card(idx, a))

    body = "\n".join(body_lines)
    fm = {
        "issue_date": output.date,
        "status": "draft",
        "total_articles": output.total_articles,
        "used_sources": output.used_sources,
        "fallback_used": output.fallback_used,
        "included_urls": included_urls or [],
        "included_approved_files": included_approved_files or [],
    }
    full_text = f"---\n{yaml.dump(fm, allow_unicode=True, default_flow_style=False, sort_keys=False)}---\n\n{body}"

    try:
        (out_dir / filename).write_text(full_text, encoding="utf-8")
        print(f"[INFO] 뉴스레터 저장: 04_newsletter/draft/{filename}")
        log_tool_event(
            "newsletter", "newsletter_writer", "success",
            f"저장 완료: {filename}", target=filename,
        )
    except Exception as e:
        log_tool_event(
            "newsletter", "newsletter_writer", "error",
            f"저장 실패: {e}", target=filename,
        )
        raise


def editor_node(state: dict[str, Any]) -> dict[str, Any]:
    log_tool_event(
        "newsletter", "newsletter_generator", "running",
        "뉴스레터 생성 중",
    )
    analyzed = state.get("analyzed_articles", [])
    sections: dict[str, list] = {}
    review_required: list[str] = []
    used_sources: set[str] = set()

    for item in analyzed:
        if item.get("recollect_required"):
            review_required.append(item.get("title", "unknown"))
            continue
        a = ArticleAnalysis(**{k: v for k, v in item.items() if k in ArticleAnalysis.model_fields})
        if a.category == "Other":
            continue
        payload = a.model_dump()
        payload["headline"] = clean_text(payload.get("headline", ""))
        payload["summary"] = clean_text(payload.get("summary", ""))
        ctx = item.get("standards_context") or []
        if item.get("standards_match_score", 0) >= 2:
            payload["standards_context"] = ctx
        else:
            payload["standards_context"] = []
        payload["standards_match_score"] = item.get("standards_match_score", 0)
        payload["standards_match_reasons"] = item.get("standards_match_reasons") or []
        payload["source_name"] = item.get("source_name", "")
        payload["origin"] = item.get("origin", "")
        payload["source_type"] = item.get("source_type", "")
        payload["is_vendor"] = item.get("is_vendor", False)
        sections.setdefault(a.category, []).append(payload)
        if a.bias_flag:
            review_required.append(a.title)
        used_sources.add(
            _display_source_label(
                item.get("source_name", ""),
                origin=item.get("origin", ""),
                source_type=item.get("source_type", ""),
            ) or item.get("source_name", "unknown")
        )

    output = NewsletterOutput(
        date=datetime.now().strftime("%Y-%m-%d"),
        total_articles=len(analyzed),
        used_sources=sorted(used_sources),
        fallback_used=state.get("fallback_used", False),
        sections=sections,
        review_required=review_required,
    )

    included_urls: list[str] = []
    included_files: list[str] = []
    for item in analyzed:
        if item.get("recollect_required"):
            continue
        u = (item.get("url") or "").strip()
        if u and u not in included_urls:
            included_urls.append(u)
        fn = (item.get("approved_filename") or "").strip()
        if fn and fn not in included_files:
            included_files.append(fn)

    vault_path = state.get("vault_path", "")
    if vault_path:
        _save_newsletter_md(
            vault_path,
            output,
            included_urls=included_urls,
            included_approved_files=included_files,
        )

    log_tool_event(
        "newsletter", "newsletter_generator", "success",
        f"뉴스레터 생성 완료 ({output.total_articles}건)",
        count=output.total_articles,
    )
    return {"newsletter": output.model_dump()}
