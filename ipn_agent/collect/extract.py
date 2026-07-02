"""
기사 본문 추출 — 다중 전략 + 품질 점수 + 재수집 fallback
"""

from __future__ import annotations

import os
import re
from functools import lru_cache
from typing import Callable

import requests

_NAV_JUNK_PHRASES: tuple[str, ...] = (
    "skip to content",
    "skip to main",
    "sign in",
    "log in",
    "subscribe",
    "cookie",
    "all rights reserved",
    "related articles",
    "related posts",
    "share this",
    "newsletter signup",
    "accept all cookies",
    "privacy policy",
)

_ARTICLE_SELECTORS: tuple[str, ...] = (
    "article",
    "main",
    '[role="main"]',
    ".post-content",
    ".article-content",
    ".article-body",
    ".entry-content",
    ".content-body",
    "#article-body",
    "#content",
    ".single-post-content",
    ".field--name-body",
)

_USER_AGENT = "Mozilla/5.0 (compatible; newsletter-agent/1.0)"


@lru_cache(maxsize=1)
def _markitdown_converter():
    try:
        from markitdown import MarkItDown
        return MarkItDown()
    except ImportError:
        return None


@lru_cache(maxsize=1)
def _tavily_client():
    key = os.environ.get("TAVILY_API_KEY", "").strip()
    if not key:
        return None
    try:
        from tavily import TavilyClient
        return TavilyClient(api_key=key)
    except ImportError:
        return None


def score_content(text: str) -> float:
    """추출 본문 품질 점수 (높을수록 기사 본문에 가깝다)."""
    if not text or text.startswith("FETCH_FAILED"):
        return 0.0

    t = text.strip()
    if len(t) < 120:
        return len(t) / 120 * 0.25

    alpha = len(re.sub(r"[\s\W\d]", "", t, flags=re.UNICODE))
    alpha_ratio = alpha / max(len(t), 1)

    score = min(len(t) / 2500, 1.0) * 35
    score += alpha_ratio * 30

    paragraphs = [p for p in re.split(r"\n\s*\n", t) if len(p.strip()) > 80]
    score += min(len(paragraphs) * 4, 20)

    lower = t.lower()
    nav_hits = sum(1 for phrase in _NAV_JUNK_PHRASES if phrase in lower)
    score -= nav_hits * 8
    if nav_hits >= 3:
        score *= 0.45

    # 짧은 줄 반복(메뉴·푸터 링크 나열) 감점
    short_lines = sum(1 for line in t.splitlines() if 0 < len(line.strip()) < 40)
    if short_lines > 25:
        score -= min((short_lines - 25) * 0.5, 15)

    url_lines = sum(
        1 for line in t.splitlines()
        if re.match(r"^https?://\S+$", line.strip(), re.I)
    )
    score -= min(url_lines * 2, 12)

    return max(score, 0.0)


def is_thin_content(text: str, min_score: float = 32.0) -> bool:
    return score_content(text) < min_score


def _fetch_html(url: str, timeout: int = 15) -> str:
    try:
        resp = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": _USER_AGENT},
        )
        resp.raise_for_status()
        return resp.text
    except Exception:
        return ""


def _node_to_text(node) -> str:
    for tag in node.find_all(["script", "style", "nav", "header", "footer", "aside", "form"]):
        tag.decompose()
    text = node.get_text("\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_markitdown(url: str) -> str:
    md = _markitdown_converter()
    if not md:
        return ""
    try:
        result = md.convert_url(url)
        text = (result.text_content or "").strip()
        return text if len(text) > 200 else ""
    except Exception:
        return ""


def _extract_tavily(url: str) -> str:
    client = _tavily_client()
    if not client:
        return ""
    try:
        resp = client.extract(urls=[url], extract_depth="advanced")
        for item in resp.get("results", []):
            raw = (item.get("raw_content") or item.get("text") or "").strip()
            if len(raw) >= 300:
                return raw
    except Exception:
        pass
    return ""


def _extract_bs4_article(url: str) -> str:
    html = _fetch_html(url)
    if not html:
        return ""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return ""

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["script", "style", "nav", "header", "footer", "aside", "noscript"]):
        tag.decompose()

    best_text = ""
    best_score = 0.0
    for sel in _ARTICLE_SELECTORS:
        node = soup.select_one(sel)
        if not node:
            continue
        text = _node_to_text(node)
        sc = score_content(text)
        if sc > best_score:
            best_score = sc
            best_text = text

    if best_score >= 20:
        return best_text

    # fallback: 가장 긴 div/p 블록
    for node in soup.find_all(["div", "section"]):
        text = _node_to_text(node)
        sc = score_content(text)
        if sc > best_score and len(text) > 400:
            best_score = sc
            best_text = text

    return best_text if best_score >= 15 else ""


def _extract_requests_strip(url: str) -> str:
    html = _fetch_html(url)
    if not html:
        return ""
    text = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.I)
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:8000] if len(text) > 200 else ""


_EXTRACTORS: dict[str, Callable[[str], str]] = {
    "tavily_extract": _extract_tavily,
    "markitdown": _extract_markitdown,
    "bs4_article": _extract_bs4_article,
    "requests_strip": _extract_requests_strip,
}

_DEFAULT_FETCH_ORDER: tuple[str, ...] = (
    "markitdown",
    "bs4_article",
    "requests_strip",
)

_RECOLLECT_ORDER: tuple[str, ...] = (
    "tavily_extract",
    "bs4_article",
    "markitdown",
    "requests_strip",
)


def fetch_article_content(url: str, *, use_tavily: bool = False) -> tuple[str, str]:
    """URL 본문 추출. (content, method) 반환."""
    order = ("tavily_extract",) + _DEFAULT_FETCH_ORDER if use_tavily else _DEFAULT_FETCH_ORDER
    return _extract_best(url, order)


def _normalize_method(name: str) -> str:
    """collect_method 등 복합 문자열에서 추출기 id만 추출."""
    if not name:
        return ""
    for token in _EXTRACTORS:
        if token in name:
            return token
    if "rss" in name and "selftext" in name:
        return "rss_selftext"
    if "tavily" in name and "snippet" in name:
        return "tavily_snippet"
    return name.strip()


def recollect_article_content(url: str, skip_method: str = "") -> tuple[str, str]:
    """재수집 — 이전 방식을 제외하고 대안 추출기를 시도."""
    skip = _normalize_method(skip_method)
    order = tuple(m for m in _RECOLLECT_ORDER if m != skip)
    content, method = _extract_best(url, order)
    if content:
        return content, method
    return "", skip_method


def _extract_best(url: str, order: tuple[str, ...]) -> tuple[str, str]:
    candidates: list[tuple[str, str]] = []
    for name in order:
        if name == "tavily_extract" and not _tavily_client():
            continue
        fn = _EXTRACTORS.get(name)
        if not fn:
            continue
        text = fn(url)
        if text and not text.startswith("FETCH_FAILED") and len(text.strip()) >= 200:
            candidates.append((text, name))

    if not candidates:
        return "FETCH_FAILED: no content", "none"

    content, method = max(candidates, key=lambda item: score_content(item[0]))
    return content, method
