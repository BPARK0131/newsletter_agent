"""
Phase 1 - MarkItDown 수집 스크립트
========================================================
역할:
  sources.yaml의 enabled 소스를 순회하며 MarkItDown으로 각 기사를
  Markdown으로 변환하고 YAML frontmatter와 함께 Obsidian vault/raw/ 에 저장.

실행:
  python fetch_script.py              # 전체 소스 수집 (enabled: true만)
  python fetch_script.py --dry-run    # URL 목록만 출력 (실제 저장 X)
  python fetch_script.py --source apnic_blog        # 특정 소스만
  python fetch_script.py --source apnic_blog --dry-run

지원 수집 섹션 (sources.yaml):
  - regular_sources   : Tier 1 기술 기준 소스 (operator_blog, open_infra)
  - vendor_sources    : Tier 2 벤더 소스
  - news_sources      : Tier 3 뉴스 소스

collection_mode 처리:
  rss           → RSS 피드 파싱 후 개별 기사 fetch
  rss_or_url    → RSS 우선 시도, 실패 시 URL 직접 fetch
  url           → URL 직접 fetch (블로그 목록 페이지)
  tavily_search → Tavily API 검색 (TAVILY_API_KEY 필요, 없으면 SKIP)
  api           → reference_sources API (IETF Datatracker 등, --source 로 개별 실행)

사전 조건:
  pip install markitdown feedparser pyyaml requests python-dotenv
  .env: OBSIDIAN_VAULT_PATH=/path/to/vault
  .env: TAVILY_API_KEY=tvly-...   (선택 - Kentik, TM Forum 수집 시 필요)

Obsidian 검수 흐름:
  1. 이 스크립트 실행 → vault/01_raw/{type}/*.md 생성
  2. Obsidian에서 01_raw/ 폴더 열기 → 기사 검토
  3. 뉴스레터에 포함할 파일 → 03_approved/ 폴더로 이동
  4. 제외할 파일 → 02_review/ 에서 삭제 또는 방치
  5. newsletter_agent_skeleton.py 실행 → 03_approved/ 읽어서 분석·편집
"""

from urllib.parse import urlparse

import argparse
import json
import os
import re
import sys
import yaml
import feedparser
import requests
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from ipn_agent.core.tool_logger import log_tool_event
from ipn_agent.core.mvp_limits import apply_mvp_source_caps, mvp_limits_summary


def _emit_collect_progress(
    kind: str,
    cur: int,
    total: int,
    name: str,
    msg: str,
    *,
    count: int | None = None,
) -> None:
    """터미널 [FETCH|DISCOVERY PROGRESS] + Streamlit UI용 tool_runs.jsonl 기록."""
    print(f"[{kind} PROGRESS] {cur}/{total} | {name} | {msg}", flush=True)
    tool = "fetch_progress" if kind == "FETCH" else "discovery_progress"
    if "실패" in msg:
        status = "error"
    elif "완료" in msg:
        status = "success"
    elif "시작" in msg:
        status = "running"
    else:
        status = "running"
    log_tool_event(
        "research",
        tool,
        status,
        f"{cur}/{total} · {msg}",
        target=name,
        count=count,
    )
from ipn_agent.paths import PROJECT_DIR
from ipn_agent.registry.article import find_url_in_vault
from ipn_agent.collect.extract import fetch_article_content, recollect_article_content, score_content

# Windows 터미널 인코딩 - 특수 유니코드 문자(non-breaking hyphen 등)를 ? 로 대체
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(errors='replace')
    except Exception:
        pass

# ── MarkItDown (없으면 requests fallback) ──────────────────────
try:
    from markitdown import MarkItDown
    _MD = MarkItDown()
    _MARKITDOWN_AVAILABLE = True
    print("[INFO] MarkItDown 사용 가능")
except ImportError:
    _MD = None
    _MARKITDOWN_AVAILABLE = False
    print("[WARN] markitdown 미설치 → requests fallback 사용 (pip install markitdown 권장)")

# ── Tavily (없으면 tavily_search 소스 SKIP) ───────────────────
try:
    from tavily import TavilyClient
    _TAVILY_KEY = os.environ.get("TAVILY_API_KEY", "")
    _TAVILY_CLIENT = TavilyClient(api_key=_TAVILY_KEY) if _TAVILY_KEY else None
    if _TAVILY_CLIENT:
        print("[INFO] Tavily 사용 가능")
    else:
        print("[WARN] TAVILY_API_KEY 미설정 → tavily_search 소스는 SKIP됩니다")
except ImportError:
    _TAVILY_CLIENT = None
    print("[WARN] tavily-python 미설치 → tavily_search 소스는 SKIP됩니다 (pip install tavily-python)")


# ═══════════════════════════════════════════════════════════════
# 유틸 함수
# ═══════════════════════════════════════════════════════════════

def safe_filename(title: str, max_len: int = 60) -> str:
    """파일명에 사용할 수 없는 문자를 제거한다."""
    name = re.sub(r"[\n\r\t]+", " ", title or "")
    name = re.sub(r'[\\/:*?"<>|]', "", name)
    name = name.strip().replace(" ", "-")
    name = re.sub(r"-{2,}", "-", name)
    return name[:max_len] if name else "untitled"


def normalize_date(date_str: str) -> str:
    """다양한 날짜 포맷을 YYYY-MM-DD로 정규화한다.

    지원 포맷:
      YYYY-MM-DD              (이미 정규화된 경우)
      Mon, 29 Jun 2026 ...    (RSS 표준)
      2026-06-29T10:00:00Z    (ISO 8601)
      June 17, 2026           (블로그 영문)
      26 Jun 2026             (TM Forum 등)
      20 August 2026          (day Month year)
    """
    if not date_str:
        return datetime.now().strftime("%Y-%m-%d")

    # 이미 YYYY-MM-DD 형식
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str.strip()):
        return date_str.strip()

    _DATE_FORMATS = [
        "%a, %d %b %Y %H:%M:%S %z",   # RSS: Mon, 29 Jun 2026 10:00:00 +0000
        "%a, %d %b %Y %H:%M:%S %Z",   # RSS: Mon, 29 Jun 2026 10:00:00 GMT
        "%Y-%m-%dT%H:%M:%S%z",        # ISO: 2026-06-29T10:00:00+00:00
        "%Y-%m-%dT%H:%M:%SZ",         # ISO: 2026-06-29T10:00:00Z
        "%Y-%m-%dT%H:%M:%S",          # ISO (no tz)
        "%B %d, %Y",                   # June 17, 2026
        "%B %d %Y",                    # June 17 2026
        "%b %d, %Y",                   # Jun 17, 2026
        "%b %d %Y",                    # Jun 17 2026
        "%d %B %Y",                    # 17 June 2026
        "%d %b %Y",                    # 17 Jun 2026
        "%Y-%m-%d %H:%M:%S",          # 2026-06-29 10:00:00
    ]
    cleaned = date_str.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    # 파싱 실패
    return datetime.now().strftime("%Y-%m-%d")


def parse_date_or_none(date_str: str) -> str | None:
    """날짜 문자열을 YYYY-MM-DD로 변환. 실패 시 None (오늘 날짜 fallback 없음)."""
    if not date_str or not str(date_str).strip():
        return None
    s = str(date_str).strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return s
    m = re.match(r"^(\d{4}-\d{2}-\d{2})", s)
    if m:
        return m.group(1)
    _DATE_FORMATS = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%B %d, %Y",
        "%B %d %Y",
        "%b %d, %Y",
        "%b %d %Y",
        "%d %B %Y",
        "%d %b %Y",
        "%Y-%m-%d %H:%M:%S",
    ]
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s[:80].strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _published_from_title(title: str) -> str | None:
    """제목에 포함된 게시일 추출 (예: Route leak ... January 22, 2026)."""
    if not title:
        return None
    iso = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", title)
    if iso:
        return iso.group(1)
    month_pat = (
        r"(January|February|March|April|May|June|July|August|September|October|November|December|"
        r"Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)"
        r"\s+(\d{1,2}),?\s+(20\d{2})"
    )
    m = re.search(month_pat, title, re.I)
    if m:
        raw = f"{m.group(1)} {m.group(2)}, {m.group(3)}"
        return parse_date_or_none(raw)
    return None


def _published_from_html(html: str) -> str | None:
    """HTML meta / JSON-LD / time 태그에서 게시일 추출."""
    if not html:
        return None
    patterns = [
        r'property=["\']article:published_time["\'][^>]+content=["\']([^"\']+)',
        r'content=["\']([^"\']+)["\'][^>]+property=["\']article:published_time["\']',
        r'property=["\']og:published_time["\'][^>]+content=["\']([^"\']+)',
        r'content=["\']([^"\']+)["\'][^>]+property=["\']og:published_time["\']',
        r'name=["\']date["\'][^>]+content=["\']([^"\']+)',
        r'"datePublished"\s*:\s*"([^"]+)"',
        r'"dateModified"\s*:\s*"([^"]+)"',
        r'<time[^>]+datetime=["\']([^"\']+)["\']',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.I)
        if m:
            parsed = parse_date_or_none(m.group(1))
            if parsed:
                return parsed
    return None


def _published_from_tavily_item(item: dict) -> str | None:
    for key in ("published_date", "publishedDate", "date", "pub_date"):
        if val := item.get(key):
            if parsed := parse_date_or_none(str(val)):
                return parsed
    return None


def guess_expansion_published(
    url: str,
    title: str,
    content: str,
    tavily_item: dict,
    html: str = "",
) -> str:
    """웹 검색 결과의 게시일 추정 — Tavily → 제목 → HTML meta → 수집일."""
    for candidate in (
        _published_from_tavily_item(tavily_item),
        _published_from_title(title),
        _published_from_html(html),
        _published_from_html(content),
    ):
        if candidate:
            return candidate
    return datetime.now().strftime("%Y-%m-%d")


_ARTICLE_URL_PATTERNS = ("/blog/", "/news/", "/article/", "/research/", "/posts/")
_DISCOVERY_STOP_WORDS = frozenset({
    "the", "and", "for", "with", "from", "network", "networks", "2026", "2025",
})


def _host_matches_domain(host: str, domain: str) -> bool:
    d = domain.lower().lstrip(".")
    h = host.lower().removeprefix("www.")
    return h == d or h.endswith("." + d)


def _domain_in_trusted_list(host: str, domains: list[str]) -> bool:
    return any(_host_matches_domain(host, d) for d in domains)


def _discovery_exclude_domains(es_cfg: dict) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for key in ("default_exclude_domains", "exclude_domains"):
        for dom in es_cfg.get(key, []) or []:
            d = dom.lower().lstrip(".")
            if d and d not in seen:
                seen.add(d)
                out.append(d)
    return out


def _expansion_url_blocked(url: str, title: str, es_cfg: dict) -> tuple[bool, str]:
    """제외 도메인·URL 패턴·PDF·Wikipedia 등 — (blocked, reason)."""
    if not url:
        return True, "empty_url"
    host = urlparse(url).netloc.lower().removeprefix("www.")
    path = (urlparse(url).path or "").lower()
    url_l = url.lower().split("?")[0].split("#")[0]

    if path.rstrip("/").endswith(".pdf") or url_l.rstrip("/").endswith(".pdf"):
        return True, "pdf_url"

    for dom in _discovery_exclude_domains(es_cfg):
        if _host_matches_domain(host, dom):
            return True, f"blocked_domain:{dom}"

    for pat in es_cfg.get("blocked_url_patterns", []) or []:
        p = pat.lower()
        if p in path or path.startswith(p.rstrip("/")):
            return True, f"blocked_url_pattern:{pat}"

    if re.search(r"\bwikipedia\b", title or "", re.I):
        return True, "wikipedia_title"
    if re.search(r"\bwikipedia\b", url or "", re.I):
        return True, "wikipedia_url"
    return False, ""


def _keywords_from_query(query: str) -> list[str]:
    words = re.findall(r"[a-zA-Z0-9][a-zA-Z0-9+./-]{1,}", query.lower())
    return [w for w in words if len(w) > 2 and w not in _DISCOVERY_STOP_WORDS]


def _is_article_url(url: str) -> bool:
    path = (urlparse(url).path or "").lower()
    return any(p in path for p in _ARTICLE_URL_PATTERNS)


def _days_since_published(published: str) -> int | None:
    """발행일로부터 경과 일수. 파싱 실패 시 None."""
    if not published:
        return None
    try:
        pub = datetime.strptime(normalize_date(published), "%Y-%m-%d")
        return (datetime.now() - pub).days
    except (ValueError, TypeError):
        return None


def _validate_article_age(
    published: str, max_age_days: int,
) -> tuple[bool, str]:
    """max_article_age_days 초과 시 reject. 반환: (ok, date_reason)."""
    days = _days_since_published(published)
    if days is None:
        return True, "unknown_date"
    if days > max_age_days:
        return False, f"too_old:{days}d>{max_age_days}d"
    if days <= 7:
        return True, f"recent_7d:{days}d"
    if days <= 30:
        return True, f"recent_30d:{days}d"
    return True, f"age_ok:{days}d"


def _build_tavily_search_kwargs(
    query: str,
    max_results: int,
    topic: str = "news",
    time_range: str = "month",
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
) -> dict:
    """Tavily search kwargs — None 값은 포함하지 않음."""
    kwargs: dict = {
        "query": query,
        "max_results": max_results,
        "search_depth": "advanced",
        "topic": topic,
        "time_range": time_range,
    }
    if include_domains:
        kwargs["include_domains"] = include_domains
    if exclude_domains:
        kwargs["exclude_domains"] = exclude_domains
    return kwargs


def compute_discovery_score(
    url: str,
    title: str,
    content: str,
    published: str,
    query: str,
    es_cfg: dict,
    max_age_days: int = 45,
) -> tuple[int, list[str], str, bool, str]:
    """discovery_score (1~5), reasons, bias_risk, is_vendor, date_reason."""
    reasons: list[str] = []
    raw = 0
    keywords = _keywords_from_query(query)
    title_l = (title or "").lower()
    content_l = (content or "").lower()

    days = _days_since_published(published)
    if days is None:
        raw -= 1
        reasons.append("unknown_date(-1)")
        date_reason = "unknown_date"
    elif days > max_age_days:
        date_reason = f"too_old:{days}d"
        return 1, reasons, "low", False, date_reason
    elif days <= 7:
        raw += 2
        reasons.append("recent_7d(+2)")
        date_reason = f"published_{days}d_ago"
    elif days <= 30:
        raw += 1
        reasons.append("recent_30d(+1)")
        date_reason = f"published_{days}d_ago"
    else:
        date_reason = f"published_{days}d_ago"

    title_hits = [k for k in keywords if k in title_l]
    if title_hits:
        raw += 2
        reasons.append(f"title_keywords(+2):{','.join(title_hits[:4])}")

    body_hits = [k for k in keywords if k in content_l]
    if len(body_hits) >= 2:
        raw += 2
        reasons.append(f"body_keywords(+2):{len(body_hits)}")

    if _is_article_url(url):
        raw += 1
        reasons.append("article_url(+1)")

    if len(content or "") >= 800:
        raw += 1
        reasons.append("long_body(+1)")

    host = urlparse(url).netloc.lower()
    trusted = es_cfg.get("trusted_domains", {}) or {}
    tech = trusted.get("technical", []) or []
    news = trusted.get("news", []) or []
    vendor = trusted.get("vendor", []) or []

    bias_risk = "low"
    is_vendor = False
    if _domain_in_trusted_list(host, tech):
        raw += 2
        reasons.append("technical_domain(+2)")
    elif _domain_in_trusted_list(host, news):
        raw += 1
        reasons.append("news_domain(+1)")
    elif _domain_in_trusted_list(host, vendor):
        raw += 1
        reasons.append("vendor_domain(+1)")
        bias_risk = "medium"
        is_vendor = True

    score = _normalize_discovery_score(raw)
    reasons.append(f"normalized({raw}→{score}/5)")
    return score, reasons, bias_risk, is_vendor, date_reason


def _normalize_discovery_score(raw: int) -> int:
    """내부 heuristic raw 점수 → 1~5 (RSS importance_score와 동일 척도)."""
    r = max(raw, 0)
    if r >= 9:
        return 5
    if r >= 7:
        return 4
    if r >= 5:
        return 3
    if r >= 3:
        return 2
    return 1


def _discovery_log_dir() -> Path:
    """Quality gate 감사 로그 — vault 밖 프로젝트 logs/discovery/."""
    d = PROJECT_DIR / "logs" / "discovery"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _append_discovery_log(_vault_path: str, log_name: str, entry: dict) -> None:
    log_path = _discovery_log_dir() / log_name
    entry.setdefault("logged_at", datetime.now().isoformat(timespec="seconds"))
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _fetch_url_html(url: str) -> str:
    """본문 fetch 시 HTML 원문도 함께 확보 (meta 날짜 추출용)."""
    try:
        resp = requests.get(
            url, timeout=15,
            headers={"User-Agent": "Mozilla/5.0 (compatible; newsletter-agent/1.0)"},
        )
        resp.raise_for_status()
        return resp.text
    except Exception:
        return ""


def fetch_to_markdown(url: str, use_tavily: bool = False) -> str:
    """URL → Markdown 변환 (다중 추출기 중 최고 품질 선택)."""
    content, _ = fetch_article_content(url, use_tavily=use_tavily)
    return content


def _raw_subdir(src: dict) -> str:
    """소스 ID를 폴더명으로 사용한다. 소스 추가 시 코드 수정 불필요."""
    return src.get("id", "etc")


def save_to_vault(vault_path: str, meta: dict, content: str, dry_run: bool = False, src: dict | None = None) -> bool:
    """YAML frontmatter + 본문을 vault/01_raw/{source_id}/ 에 저장한다."""
    subdir = _raw_subdir(src) if src else meta.get("source_name", "etc")
    raw_dir = Path(vault_path) / "01_raw" / subdir

    # 파일명 앞에 publish 날짜 사용 (fetch 날짜 아님)
    pub_date = normalize_date(meta.get("published", ""))
    filename = f"{pub_date}-{safe_filename(meta['title'])}.md"

    if dry_run:
        print(f"  [DRY-RUN] 저장 예정: 01_raw/{subdir}/{filename}")
        return True

    log_tool_event(
        "research", "markdown_writer", "running",
        f"Markdown 저장 중: {filename}", target=f"01_raw/{subdir}/{filename}",
    )

    raw_dir.mkdir(parents=True, exist_ok=True)
    filepath = raw_dir / filename

    url = meta.get("url", "")
    if url:
        existing_loc = find_url_in_vault(Path(vault_path), url)
        if existing_loc:
            print(f"  [SKIP] URL 중복 (vault): {existing_loc}")
            log_tool_event(
                "research", "markdown_writer", "skip",
                f"중복 URL — 저장 생략: {existing_loc}",
                target=existing_loc,
            )
            return False

    # 레거시: 같은 source 폴더 내 제목 prefix + URL (vault 스캔 보조)
    for existing in raw_dir.glob(f"*{safe_filename(meta['title'])[:30]}*.md"):
        existing_text = existing.read_text(encoding="utf-8", errors="ignore")
        if url and url in existing_text:
            print(f"  [SKIP] 이미 존재: {existing.name}")
            log_tool_event(
                "research", "markdown_writer", "skip",
                f"중복 URL — 저장 생략: {existing.name}",
                target=f"01_raw/{subdir}/{existing.name}",
            )
            return False

    try:
        frontmatter = yaml.dump(meta, allow_unicode=True, default_flow_style=False, sort_keys=False)
        full_text = f"---\n{frontmatter}---\n\n{content}"
        filepath.write_text(full_text, encoding="utf-8")
        print(f"  [SAVED] {filepath.name}")
        log_tool_event(
            "research", "markdown_writer", "success",
            f"저장 완료: {filepath.name}", target=f"01_raw/{subdir}/{filename}",
        )
        return True
    except Exception as e:
        log_tool_event(
            "research", "markdown_writer", "error",
            f"저장 실패: {e}", target=f"01_raw/{subdir}/{filename}",
        )
        return False


def _rss_request_headers(src: dict) -> dict:
    """RSS fetch 헤더. sources.yaml fetch_headers 우선."""
    default = {"User-Agent": "Mozilla/5.0 (compatible; newsletter-agent/1.0)"}
    custom = src.get("fetch_headers") or {}
    return {**default, **custom}


def _html_to_plaintext(html: str) -> str:
    """RSS HTML selftext → plain text."""
    html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        md_div = soup.find("div", class_="md")
        target = md_div if md_div else soup
        return target.get_text("\n", strip=True)
    except ImportError:
        text = re.sub(r"<[^>]+>", " ", html)
        return re.sub(r"\s+", " ", text).strip()


def _extract_rss_entry_body(entry) -> str:
    """feedparser entry 의 content/summary HTML에서 본문 텍스트 추출."""
    html = ""
    content_list = entry.get("content") if hasattr(entry, "get") else None
    if content_list:
        html = content_list[0].get("value", "")
    if not html:
        html = entry.get("summary", "") or entry.get("description", "")
    if not html or "<" not in html:
        # HTML 태그 없으면 그대로 반환 (plain summary)
        return (html or "").strip()
    return _html_to_plaintext(html)


def _uses_rss_html_body(src: dict) -> bool:
    """Reddit 등 community_signal: RSS selftext HTML을 본문으로 사용."""
    return (
        src.get("body_extract") == "rss_html"
        or src.get("type") == "community_signal"
    )


# ═══════════════════════════════════════════════════════════════
# 수집 로직
# ═══════════════════════════════════════════════════════════════

def collect_rss(src: dict, vault_path: str, max_articles: int, dry_run: bool) -> int:
    """RSS 피드에서 기사를 수집한다. 저장 성공 건수 반환."""
    rss_url = src.get("rss") or src.get("url")
    body_extract = src.get("body_extract", "")
    source_id = src.get("id", src.get("name", "unknown"))
    log_tool_event(
        "research", "rss_collector", "running",
        f"{src['name']} RSS 수집 중", target=source_id,
    )
    print(f"\n[RSS] {src['name']} -> {rss_url}")
    headers = _rss_request_headers(src)
    use_rss_body = _uses_rss_html_body(src)
    if use_rss_body:
        print("  [CONFIG] RSS selftext HTML → 본문 (community_signal / rss_html)")

    # User-Agent 없이 접근 시 일부 피드가 빈 결과를 반환하므로 requests로 먼저 수신
    try:
        resp = requests.get(rss_url, timeout=15, headers=headers)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
    except Exception:
        # fallback: feedparser 직접 파싱
        try:
            feed = feedparser.parse(rss_url, request_headers=headers)
        except Exception as e:
            print(f"  [ERROR] RSS 파싱 실패: {e}")
            log_tool_event(
                "research", "rss_collector", "error",
                f"RSS 파싱 실패: {e}", target=source_id,
            )
            return 0

    if not feed.entries:
        print("  [WARN] 피드 항목 없음")
        log_tool_event(
            "research", "rss_collector", "success",
            "피드 항목 없음", target=source_id, count=0,
        )
        return 0

    entries = feed.entries[:max_articles]

    # Tavily Extract 일괄 요청 (body_extract: tavily_extract 설정 시)
    body_map: dict[str, str] = {}
    if body_extract == "tavily_extract" and _TAVILY_CLIENT and not dry_run:
        urls_to_extract = [e.get("link", "") for e in entries if e.get("link")]
        print(f"  [TAVILY_EXTRACT] {len(urls_to_extract)}개 URL 본문 추출 중...")
        log_tool_event(
            "research", "tavily_extract", "running",
            f"{len(urls_to_extract)}개 URL 본문 추출 중", target=source_id,
        )
        try:
            extract_resp = _TAVILY_CLIENT.extract(
                urls=urls_to_extract,
                extract_depth="advanced",
            )
            extracted = 0
            for item in extract_resp.get("results", []):
                raw = item.get("raw_content", "") or item.get("text", "")
                if len(raw.strip()) >= 500:
                    body_map[item["url"]] = raw
                    extracted += 1
                else:
                    print(f"    [WARN] Tavily Extract 본문 부족 ({item['url'][:60]})")
            log_tool_event(
                "research", "tavily_extract", "success",
                f"본문 추출 완료", target=source_id, count=extracted,
            )
        except Exception as e:
            print(f"  [WARN] Tavily Extract 실패: {e} -> MarkItDown fallback")
            log_tool_event(
                "research", "tavily_extract", "error",
                f"Extract 실패: {e}", target=source_id,
            )
    elif body_extract == "tavily_extract" and not _TAVILY_CLIENT:
        print("  [WARN] TAVILY_API_KEY 미설정 -> MarkItDown fallback")

    saved = 0
    for entry in entries:
        url   = entry.get("link", "")
        title = entry.get("title", "untitled")
        if not url:
            continue

        print(f"  -> {title[:60]}")

        from_rss_html = False
        extract_method = "tavily_extract" if url in body_map else ""
        # 본문: Tavily Extract → RSS HTML selftext → 다중 추출 fallback
        content = body_map.get(url, "")
        if not content and use_rss_body:
            content = _extract_rss_entry_body(entry)
            if content:
                from_rss_html = True
                extract_method = "rss_selftext"
        if not content:
            content, extract_method = fetch_article_content(
                url, use_tavily=(body_extract == "tavily_extract"),
            )

        if content.startswith("FETCH_FAILED"):
            print(f"    [SKIP] {content}")
            continue
        if len(content) < 300:
            print(f"    [SKIP] 본문 너무 짧음 ({len(content)}자)")
            continue

        if from_rss_html:
            collect_method = "rss+reddit_selftext"
        else:
            collect_method = f"rss+{body_extract or extract_method or 'markitdown'}"

        meta = {
            "title":           title,
            "url":             url,
            "source_name":     src["id"],
            "source_type":     src.get("type", ""),
            "published":       entry.get("published", datetime.now().strftime("%Y-%m-%d")),
            "is_vendor":       src.get("type") == "vendor_blog",
            "bias_risk":       src.get("bias_risk", "low"),
            "direct_citation": src.get("direct_citation", True),
            "collect_method":  collect_method,
            "body_extract_method": extract_method or body_extract or "markitdown",
        }
        if save_to_vault(vault_path, meta, content, dry_run, src=src):
            saved += 1

    log_tool_event(
        "research", "rss_collector", "success",
        f"{saved}건 수집 완료", target=source_id, count=saved,
    )
    return saved


def collect_url(src: dict, vault_path: str, dry_run: bool) -> int:
    """URL 직접 fetch (RSS 없는 소스용)."""
    url = src.get("url", "")
    print(f"\n[URL] {src['name']} → {url}")

    content, extract_method = fetch_article_content(url)
    if content.startswith("FETCH_FAILED"):
        print(f"  [SKIP] {content}")
        return 0

    meta = {
        "title":       src.get("name", src["id"]),
        "url":         url,
        "source_name": src["id"],
        "source_type": src.get("type", ""),
        "published":   datetime.now().strftime("%Y-%m-%d"),
        "is_vendor":   src.get("type") == "vendor_blog",
        "bias_risk":   src.get("bias_risk", "low"),
        "direct_citation": src.get("direct_citation", True),
        "body_extract_method": extract_method,
    }
    return 1 if save_to_vault(vault_path, meta, content, dry_run, src=src) else 0


def _matches_include_keywords(doc: dict, keywords: list[str]) -> bool:
    """title/name/abstract 에 include_keywords 중 하나라도 포함되면 True."""
    if not keywords:
        return True
    haystack = " ".join([
        doc.get("name", ""),
        doc.get("title", ""),
        doc.get("abstract", "") or "",
    ]).lower()
    return any(kw.lower() in haystack for kw in keywords)


def _ietf_doc_excluded(name: str, prefixes: list[str]) -> bool:
    """agenda/minutes 등 비기술 문서 제외."""
    n = name.lower()
    return any(n.startswith(p.lower()) for p in prefixes)


def _ietf_document_type(name: str) -> str:
    if name.lower().startswith("rfc"):
        return "rfc"
    if name.lower().startswith("draft-"):
        return "internet-draft"
    return "other"


def _ietf_maturity(name: str) -> str:
    n = name.lower()
    if n.startswith("rfc"):
        return "published-rfc"
    if n.startswith("draft-ietf-"):
        return "wg-draft"
    if n.startswith("draft-"):
        return "individual-draft"
    return "other"


def _doc_within_age(doc: dict, max_age_days: int) -> bool:
    """max_age_days 이내 갱신 문서만 통과."""
    if max_age_days <= 0:
        return True
    time_str = doc.get("time", "")
    if not time_str:
        return True
    try:
        # ISO 8601
        ts = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        if ts.tzinfo:
            ts = ts.replace(tzinfo=None)
        cutoff = datetime.now() - timedelta(days=max_age_days)
        return ts >= cutoff
    except ValueError:
        return True


def _ietf_doc_url(name: str) -> str:
    return f"https://datatracker.ietf.org/doc/{name}/"


def _build_ietf_content(doc: dict, wg_acronym: str) -> str:
    """IETF API 응답을 review_script가 읽을 수 있는 Markdown 본문으로 변환."""
    title = doc.get("title") or doc.get("name", "untitled")
    lines = [
        f"# {title}",
        "",
        f"- Document: `{doc.get('name', '')}`",
    ]
    if wg_acronym:
        lines.append(f"- Working Group: {wg_acronym.upper()}")
    if doc.get("time"):
        lines.append(f"- Updated: {doc.get('time')}")
    if doc.get("pages"):
        lines.append(f"- Pages: {doc['pages']}")

    abstract = (doc.get("abstract") or "").strip()
    if abstract:
        lines.extend(["", "## Abstract", "", abstract])

    lines.extend(["", f"Full document: {_ietf_doc_url(doc.get('name', ''))}"])
    return "\n".join(lines)


def collect_api(src: dict, vault_path: str, dry_run: bool) -> int:
    """IETF Datatracker API — 표준 변화 감지용 (WG당 최신 1건)."""
    api_url = src.get("url", "").rstrip("/")
    if not api_url:
        print(f"\n[SKIP] {src['name']} - API URL 없음")
        return 0

    api_params = dict(src.get("api_params") or {})
    max_results = src.get("max_lookup_results", 5)
    max_per_wg = src.get("max_per_wg", 1)
    max_age_days = src.get("max_article_age_days", 730)
    include_keywords = src.get("include_keywords") or []
    wg_filter = src.get("wg_filter") or []
    exclude_prefixes = src.get("exclude_doc_prefixes") or ["agenda-", "minutes-"]

    print(f"\n[API] {src['name']} -> {api_url}")
    print(f"  [CONFIG] WG {len(wg_filter)}개 | max {max_results}건 | age<={max_age_days}일 | WG당 {max_per_wg}건")

    if not wg_filter:
        print("  [WARN] wg_filter 없음 — api_params만으로 단일 요청")
        wg_filter = [""]

    fetch_limit = api_params.get("limit", 15)
    headers = {"User-Agent": "Mozilla/5.0 (compatible; newsletter-agent/1.0)"}
    selected: list[tuple[dict, str]] = []

    for wg in wg_filter:
        params = {k: v for k, v in api_params.items() if k != "limit"}
        params["limit"] = fetch_limit
        if wg:
            params["group__acronym"] = wg

        try:
            resp = requests.get(f"{api_url}/", params=params, timeout=20, headers=headers)
            resp.raise_for_status()
            objects = resp.json().get("objects", [])
        except Exception as e:
            print(f"  [ERROR] API 요청 실패 (wg={wg or 'all'}): {e}")
            continue

        wg_candidates: list[dict] = []
        for doc in objects:
            name = doc.get("name", "")
            if not name or _ietf_doc_excluded(name, exclude_prefixes):
                continue
            if not _matches_include_keywords(doc, include_keywords):
                continue
            if not _doc_within_age(doc, max_age_days):
                continue
            title = (doc.get("title") or "").strip()
            if not title or title == name:
                if not name.startswith(("draft-", "rfc")):
                    continue
            wg_candidates.append(doc)

        wg_candidates.sort(key=lambda d: d.get("time", ""), reverse=True)
        for doc in wg_candidates[:max_per_wg]:
            selected.append((doc, wg))

    # 전체 상한
    selected.sort(key=lambda x: x[0].get("time", ""), reverse=True)
    selected = selected[:max_results]

    if not selected:
        print("  [WARN] 필터 통과 문서 없음 (WG/키워드/기간 확인)")
        return 0

    print(f"  [INFO] 저장 대상: {len(selected)}건")
    saved = 0
    for doc, wg in selected:
        name = doc.get("name", "")
        title = doc.get("title") or name
        url = _ietf_doc_url(name)
        wg_label = wg.upper() if wg else "IETF"
        print(f"  -> [{wg_label}] {doc.get('time', '')[:10]} {title[:55]}")

        content = _build_ietf_content(doc, wg)
        meta = {
            "title":           title,
            "url":             url,
            "source_id":       src["id"],
            "source_name":     src["id"],
            "source_type":     src.get("type", ""),
            "published":       doc.get("time", datetime.now().strftime("%Y-%m-%d")),
            "is_vendor":       False,
            "bias_risk":       src.get("bias_risk", "low"),
            "direct_citation": src.get("direct_citation", True),
            "collect_method":  "ietf_datatracker_api",
            "review_mode":     src.get("review_mode", "standards_signal"),
            "output_section":  src.get("output_section", "standardization_radar"),
            "doc_name":        name,
            "wg":              wg_label,
            "document_type":   _ietf_document_type(name),
            "maturity":        _ietf_maturity(name),
        }
        if save_to_vault(vault_path, meta, content, dry_run, src=src):
            saved += 1

    return saved


def _tavily_url_ok(url: str, src: dict) -> tuple[bool, str]:
    """sources.yaml의 URL 필터 규칙으로 URL을 검증한다.

    규칙 (sources.yaml):
      url_must_contain         : 이 문자열이 URL에 없으면 제외
      url_must_not_end         : URL 경로가 이 값으로 끝나면 제외 (인덱스 페이지)
      url_must_not_contain_any : 이 목록 중 하나라도 URL에 포함되면 제외 (author/category 등)
    """
    path = url.split("?")[0].rstrip("/")

    must_contain = src.get("url_must_contain", "")
    if must_contain and must_contain not in url:
        return False, f"url_must_contain({must_contain}) 불일치"

    must_not_end = src.get("url_must_not_end", "")
    if must_not_end and path.endswith(must_not_end.rstrip("/")):
        return False, f"url_must_not_end({must_not_end}) - 인덱스 페이지 제외"

    for pattern in src.get("url_must_not_contain_any", []):
        if pattern in url:
            return False, f"url_must_not_contain_any({pattern}) - 목록/메타 페이지 제외"

    return True, ""


def collect_blog_index(src: dict, vault_path: str, dry_run: bool) -> int:
    """블로그 인덱스 페이지를 파싱해 최신 기사만 추출 후 본문을 수집한다.

    RSS 피드가 없는 블로그 전용 수집 모드.
    수집 순서:
      1. 인덱스 HTML 파싱 (BeautifulSoup) → 기사 카드 단위로 URL/제목/날짜/카테고리 추출
      2. 날짜 필터 (max_article_age_days) - 오래된 "Highlights" 고정글 제외
      3. 카테고리 필터 (include_categories / exclude_categories)
      4. 본문 추출: body_extract=tavily_extract 이면 Tavily Extract, 없으면 MarkItDown fallback

    사전 조건:
      pip install beautifulsoup4
    """
    import requests
    from datetime import timedelta
    try:
        from bs4 import BeautifulSoup
        _BS4 = True
    except ImportError:
        _BS4 = False
        print("  [WARN] beautifulsoup4 미설치 → 간이 regex 파싱 사용 (pip install beautifulsoup4 권장)")

    # 설정값 로드
    index_url       = src.get("url", "")
    base_url        = src.get("article_base_url", "").rstrip("/")
    url_pattern     = src.get("article_url_pattern", "/blog/")
    exclude_url     = src.get("url_must_not_contain_any", [])
    max_articles    = src.get("max_articles_per_run", 5)
    max_age_days    = src.get("max_article_age_days", 30)
    include_cats    = set(src.get("include_categories", []))
    exclude_cats    = set(src.get("exclude_categories", []))
    body_extract    = src.get("body_extract", "")      # "tavily_extract" or ""
    cutoff_date     = datetime.now() - timedelta(days=max_age_days)

    # 날짜 파싱 — 여러 영어 날짜 포맷 지원
    # 처리 가능 포맷:
    #   "June 17, 2026"   → %B %d, %Y   (Kentik)
    #   "June 17 2026"    → %B %d %Y
    #   "26 Jun 2026"     → %d %b %Y    (TM Forum)
    #   "20 August 2026"  → %d %B %Y    (TM Forum)
    #   "2026-06-26"      → %Y-%m-%d    (ISO, TM Forum)
    _DATE_PATTERNS = [
        (re.compile(r"[A-Z][a-z]+ \d{1,2},? \d{4}"), ["%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y"]),
        (re.compile(r"\d{1,2} [A-Z][a-z]+ \d{4}"),   ["%d %B %Y", "%d %b %Y"]),
        (re.compile(r"\d{4}-\d{2}-\d{2}"),            ["%Y-%m-%d"]),
    ]

    def _parse_date(text: str):
        for pat, fmts in _DATE_PATTERNS:
            m = pat.search(text)
            if not m:
                continue
            date_str = m.group()
            for fmt in fmts:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
        return None

    print(f"\n[BLOG_INDEX] {src['name']} -> {index_url}")
    print(f"  [CONFIG] 날짜 기준: {max_age_days}일 이내 | 카테고리 필터: include={len(include_cats)} exclude={len(exclude_cats)}")

    # ── 1. 인덱스 페이지 fetch ───────────────────────────────────────
    try:
        resp = requests.get(
            index_url, timeout=15,
            headers={"User-Agent": "Mozilla/5.0 (compatible; newsletter-agent/1.0)"},
        )
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        print(f"  [ERROR] 인덱스 페이지 fetch 실패: {e}")
        return 0

    # ── 2. 기사 카드 파싱 ─────────────────────────────────────────────
    articles: list[dict] = []
    seen_urls: set[str]  = set()

    if _BS4:
        soup = BeautifulSoup(html, "html.parser")
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]

            # 절대 경로 변환
            if href.startswith("/"):
                href = base_url + href
            elif not href.startswith("http"):
                continue

            if url_pattern not in href:
                continue
            if href.rstrip("/") == index_url.rstrip("/"):
                continue
            if any(excl in href for excl in exclude_url):
                continue
            if href in seen_urls:
                continue
            seen_urls.add(href)

            # 날짜 / 카테고리 추출 — 최대 5단계 조상까지 올라가며 날짜를 탐색
            pub_date = None
            block    = ""
            node     = a_tag
            for _ in range(5):
                node = node.find_parent()
                if node is None:
                    break
                block = node.get_text(" ", strip=True)
                pub_date = _parse_date(block)
                if pub_date:
                    break

            # 날짜 없는 링크 = Highlights 고정 영역이나 네비 링크 → 제외
            if pub_date is None:
                continue

            # 날짜 필터: cutoff_date 이전 글 제외
            if pub_date < cutoff_date:
                continue

            # 카테고리 필터
            if exclude_cats and any(cat in block for cat in exclude_cats):
                continue
            if include_cats and not any(cat in block for cat in include_cats):
                continue

            # 제목: 링크 자체 텍스트 사용
            title = a_tag.get_text(" ", strip=True)
            if not title or title.lower() in {"read more", "blog", "most recent"}:
                slug  = href.rstrip("/").split("/")[-1]
                title = slug.replace("-", " ").title()

            articles.append({
                "url":      href,
                "title":    title,
                "pub_date": pub_date,
                "block":    block[:300],
            })
    else:
        # BeautifulSoup 없을 때 regex fallback (날짜 필터만 적용)
        for href in re.findall(r'href=["\']([^"\']+)["\']', html):
            if href.startswith("/"):
                href = base_url + href
            elif not href.startswith("http"):
                continue
            if url_pattern not in href or href.rstrip("/") == index_url.rstrip("/"):
                continue
            if any(excl in href for excl in exclude_url):
                continue
            if href in seen_urls:
                continue
            seen_urls.add(href)
            slug  = href.rstrip("/").split("/")[-1]
            articles.append({"url": href, "title": slug.replace("-", " ").title(),
                             "pub_date": datetime.now(), "block": ""})

    # 최신순 정렬 후 상위 N개
    articles.sort(key=lambda x: x["pub_date"], reverse=True)
    selected = articles[:max_articles]

    if not selected:
        print(f"  [WARN] 필터 조건 통과 기사 없음 (날짜 기준 {max_age_days}일, 카테고리 필터 적용)")
        return 0

    print(f"  [INFO] 필터 통과: {len(selected)}건 / 후보: {len(articles)}건")
    for a in selected:
        print(f"    [{a['pub_date'].strftime('%Y-%m-%d')}] {a['title'][:60]} -> {a['url']}")

    if dry_run:
        return 0

    # ── 3. 본문 추출 ─────────────────────────────────────────────────
    # Tavily Extract 우선, 없으면 MarkItDown fallback
    body_map: dict[str, str] = {}

    if body_extract == "tavily_extract" and _TAVILY_CLIENT:
        urls_to_extract = [a["url"] for a in selected]
        print(f"  [TAVILY_EXTRACT] {len(urls_to_extract)}개 URL 본문 추출 중...")
        log_tool_event(
            "research", "tavily_extract", "running",
            f"{len(urls_to_extract)}개 URL 본문 추출 중",
            target=src.get("id", "blog_index"),
        )
        try:
            extract_resp = _TAVILY_CLIENT.extract(
                urls=urls_to_extract,
                extract_depth="advanced",
            )
            extracted = 0
            for item in extract_resp.get("results", []):
                raw = item.get("raw_content", "") or item.get("text", "")
                if len(raw.strip()) >= 500:
                    body_map[item["url"]] = raw
                    extracted += 1
                else:
                    print(f"    [WARN] Tavily Extract 본문 부족 ({item['url'][:60]})")
            log_tool_event(
                "research", "tavily_extract", "success",
                "본문 추출 완료", target=src.get("id", "blog_index"), count=extracted,
            )
        except Exception as e:
            print(f"  [WARN] Tavily Extract 실패: {e} -> MarkItDown fallback")
            log_tool_event(
                "research", "tavily_extract", "error",
                f"Extract 실패: {e}", target=src.get("id", "blog_index"),
            )
    elif body_extract == "tavily_extract" and not _TAVILY_CLIENT:
        print("  [WARN] TAVILY_API_KEY 미설정 -> MarkItDown fallback")

    # ── 4. 저장 ──────────────────────────────────────────────────────
    saved = 0
    for art in selected:
        url   = art["url"]
        title = art["title"]

        # 본문: Tavily Extract 결과 우선 → 다중 추출 fallback
        content = body_map.get(url, "")
        extract_method = "tavily_extract" if content else ""
        if not content:
            print(f"  [FETCH] {url[:70]}")
            content, extract_method = fetch_article_content(
                url, use_tavily=(body_extract == "tavily_extract"),
            )

        if content.startswith("FETCH_FAILED"):
            print(f"    [SKIP] {content}")
            continue
        if len(content) < 500:
            print(f"    [SKIP] 본문 너무 짧음 ({len(content)}자)")
            continue

        # Markdown 첫 H1 헤딩으로 제목 보정
        h1 = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if h1:
            title = h1.group(1).strip()

        meta = {
            "title":          title,
            "url":            url,
            "source_name":    src["id"],
            "source_type":    src.get("type", ""),
            "published":      art["pub_date"].strftime("%Y-%m-%d"),
            "is_vendor":      src.get("type") == "vendor_blog",
            "bias_risk":      src.get("bias_risk", "medium"),
            "direct_citation": src.get("direct_citation", True),
            "collect_method": f"blog_index+{body_extract or extract_method or 'markitdown'}",
            "body_extract_method": extract_method or body_extract or "markitdown",
        }
        if save_to_vault(vault_path, meta, content, dry_run, src=src):
            saved += 1

    return saved


def collect_tavily(src: dict, vault_path: str, dry_run: bool) -> int:
    """Tavily 검색으로 기사를 수집한다 (RSS/URL 없는 소스용)."""
    source_id = src.get("id", src.get("name", "unknown"))
    if not _TAVILY_CLIENT:
        print(f"\n[SKIP] {src['name']} - TAVILY_API_KEY 미설정 (tavily_search 소스)")
        log_tool_event(
            "research", "tavily_search", "skip",
            "TAVILY_API_KEY 미설정", target=source_id,
        )
        return 0

    query = src.get("tavily_query") or f"{src['name']} 2026"
    max_results = src.get("max_articles_per_run", 5)
    topic = src.get("tavily_topic") or src.get("topic") or "news"
    time_range = src.get("tavily_time_range") or src.get("time_range") or "month"
    max_age_days = int(src.get("max_article_age_days") or 45)
    excl = _discovery_exclude_domains({})  # source-level: no es_cfg; skip exclude unless in src
    if src.get("exclude_domains"):
        excl = list(src.get("exclude_domains") or [])
    log_tool_event(
        "research", "tavily_search", "running",
        f"Tavily 검색: {query} (topic={topic}, range={time_range})", target=source_id,
    )
    print(f"\n[TAVILY] {src['name']} → 쿼리: {query} · topic={topic} · range={time_range}")

    if dry_run:
        print(f"  [DRY-RUN] Tavily 검색 예정: '{query}' (max {max_results}건)")
        return 0

    try:
        inc = src.get("include_domains") or None
        result = _TAVILY_CLIENT.search(**_build_tavily_search_kwargs(
            query, max_results * 2, topic, time_range, inc, excl or None,
        ))
    except Exception as e:
        print(f"  [ERROR] Tavily 검색 실패: {e}")
        log_tool_event(
            "research", "tavily_search", "error",
            f"검색 실패: {e}", target=source_id,
        )
        return 0

    saved = 0
    for item in result.get("results", []):
        if saved >= max_results:
            break

        url   = item.get("url", "")
        title = item.get("title", "untitled")
        if not url:
            continue

        # URL 필터 검사
        ok, reason = _tavily_url_ok(url, src)
        if not ok:
            print(f"  [FILTER] {url[:70]} → {reason}")
            continue

        print(f"  → {title[:60]}")

        # Tavily snippet 우선 사용, 너무 짧으면 다중 추출 fallback
        content = item.get("content", "")
        extract_method = "tavily_snippet" if content and len(content) >= 300 else ""
        if not content or len(content) < 300:
            print(f"    [FETCH] snippet 부족({len(content)}자) → 원문 직접 fetch")
            content, extract_method = fetch_article_content(url, use_tavily=True)

        if content.startswith("FETCH_FAILED"):
            print(f"    [SKIP] {content}")
            continue

        # 최소 길이 미달 시 스킵 (마케팅 페이지·네비 텍스트 필터)
        if len(content) < 500:
            print(f"    [SKIP] 본문 너무 짧음({len(content)}자) - 마케팅/네비 페이지 가능성")
            continue

        html = _fetch_url_html(url) if len(content) < 800 else ""
        published = guess_expansion_published(url, title, content, item, html)
        age_ok, date_reason = _validate_article_age(published, max_age_days)
        if not age_ok:
            print(f"    [SKIP] 기간 초과: {date_reason} | {title[:50]}")
            continue

        meta = {
            "title":       title,
            "url":         url,
            "source_name": src["id"],
            "source_type": src.get("type", ""),
            "published":   published,
            "date_reason": date_reason,
            "topic":       topic,
            "time_range":  time_range,
            "is_vendor":   src.get("type") == "vendor_blog",
            "bias_risk":   src.get("bias_risk", "medium"),
            "direct_citation": src.get("direct_citation", True),
            "collect_method": "tavily_search",
            "body_extract_method": extract_method,
        }
        if save_to_vault(vault_path, meta, content, dry_run, src=src):
            saved += 1

    log_tool_event(
        "research", "tavily_search", "success",
        f"{saved}건 수집 완료", target=source_id, count=saved,
    )
    return saved


# ═══════════════════════════════════════════════════════════════
# 카테고리별 Tavily 확장 검색
# ═══════════════════════════════════════════════════════════════

def run_expansion_search(
    config: dict,
    vault_path: str,
    dry_run: bool = False,
    target_category: str | None = None,
) -> int:
    """sources.yaml expansion_search — semi-open discovery.

    Tavily 검색 → discovery_score → quality gate → 01_raw/expansion/
    Review는 review_script가 01_raw 전체를 처리.
    Gate 제외 로그: logs/discovery/*.jsonl
    """
    if not _TAVILY_CLIENT:
        print("\n[SKIP] expansion_search - TAVILY_API_KEY 미설정")
        return 0

    es_cfg = config.get("expansion_search", {})
    if not es_cfg.get("enabled", False):
        print("\n[SKIP] expansion_search - enabled: false")
        return 0

    min_score = int(es_cfg.get("min_discovery_score", 3))
    max_per_cat = int(es_cfg.get("max_saved_per_category", 3))
    max_total = int(es_cfg.get("max_total_results", max_per_cat * 5))
    default_topic = es_cfg.get("default_topic", "news")
    default_time_range = es_cfg.get("default_time_range", "month")
    default_max_age = int(es_cfg.get("default_max_article_age_days", 45))
    mode = es_cfg.get("mode", "semi_open_discovery")
    global_exclude = _discovery_exclude_domains(es_cfg)
    categories = es_cfg.get("search_categories", [])
    if target_category:
        categories = [c for c in categories if c["id"] == target_category]
        if not categories:
            print(f"[ERROR] expansion_search 카테고리 '{target_category}'를 찾을 수 없습니다.")
            return 0

    print(
        f"\n[EXPANSION_SEARCH] mode={mode} · {len(categories)}개 카테고리 · "
        f"min_score={min_score} · 카테고리당 최대 {max_per_cat}건 · 전역 상한 {max_total}건"
    )
    log_tool_event(
        "research", "expansion_search", "running",
        f"Tavily discovery 시작 (min_score={min_score})",
    )

    global_seen: set[str] = set()
    total_saved = 0
    collected_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    cat_total = len(categories)
    _emit_collect_progress("DISCOVERY", 0, cat_total, "—", "카테고리 검색 시작")

    for cat_idx, cat in enumerate(categories, start=1):
        if total_saved >= max_total:
            print(f"  [CAP] 전역 상한 {max_total}건 도달 — 검색 중단")
            break

        cat_id = cat.get("id", "unknown")
        cat_name = cat.get("name", cat_id)
        _emit_collect_progress("DISCOVERY", cat_idx, cat_total, cat_id, "검색 중")
        query = (cat.get("query") or "").strip()
        time_range = cat.get("time_range") or default_time_range
        topic = cat.get("topic") or default_topic
        max_age_days = int(cat.get("max_article_age_days") or default_max_age)
        subdir = cat.get("vault_subdir", cat_id)
        domains = cat.get("include_domains") or []
        remaining_global = max_total - total_saved
        max_save = min(int(cat.get("max_saved_per_category", max_per_cat)), remaining_global)
        fetch_n = min(int(cat.get("max_results", max_per_cat)) * 2, 20)

        print(f"\n  [{cat_name}]")
        print(
            f"  쿼리: {query[:80]}…" if len(query) > 80 else f"  쿼리: {query}"
        )
        print(
            f"  topic={topic} | time_range={time_range} | max_age={max_age_days}d | "
            f"include_domains: {domains or '(open)'} | 저장 상한: {max_save}"
        )

        if dry_run:
            print(f"  [DRY-RUN] Tavily Search 예정 (fetch~{fetch_n}, save≤{max_save})")
            continue

        try:
            result = _TAVILY_CLIENT.search(**_build_tavily_search_kwargs(
                query, max(fetch_n, 8), topic, time_range,
                domains if domains else None,
                global_exclude or None,
            ))
        except Exception as e:
            print(f"  [ERROR] Tavily 검색 실패: {e}")
            continue

        scored_items: list[tuple[int, dict, str, str, str, list[str], str, bool]] = []
        for item in result.get("results", []):
            url = item.get("url", "")
            title = item.get("title", "untitled")
            if not url or url in global_seen:
                continue

            blocked, block_reason = _expansion_url_blocked(url, title, es_cfg)
            if blocked:
                print(f"    [DISCARD] {block_reason}: {title[:45]}")
                _append_discovery_log(vault_path, "search_discarded.jsonl", {
                    "url": url, "title": title, "category": cat_id,
                    "search_query": query, "discard_reason": block_reason,
                    "discovery_score": 0,
                })
                continue

            global_seen.add(url)
            html = ""
            content = item.get("content", "") or item.get("raw_content", "") or ""
            need_html = (
                len(content) < 300
                or not (_published_from_tavily_item(item) or _published_from_title(title))
            )
            if need_html:
                html = _fetch_url_html(url)
            if len(content) < 300:
                content, extract_method = fetch_article_content(url, use_tavily=True)
            else:
                extract_method = "tavily_snippet"
            if content.startswith("FETCH_FAILED") or len(content) < 500:
                _append_discovery_log(vault_path, "search_discarded.jsonl", {
                    "url": url, "title": title, "category": cat_id,
                    "search_query": query, "discard_reason": "fetch_failed_or_short",
                    "discovery_score": 0,
                })
                continue

            published = guess_expansion_published(url, title, content, item, html)
            age_ok, date_reason = _validate_article_age(published, max_age_days)
            if not age_ok:
                print(f"    [DISCARD] {date_reason}: {title[:45]}")
                _append_discovery_log(vault_path, "search_discarded.jsonl", {
                    "url": url, "title": title, "category": cat_id,
                    "search_query": query, "discard_reason": "too_old",
                    "date_reason": date_reason, "published": published,
                    "discovery_score": 0,
                })
                continue

            score, reasons, bias_risk, is_vendor, date_reason = compute_discovery_score(
                url, title, content, published, query, es_cfg, max_age_days,
            )
            scored_items.append((
                score, item, title, url, content, reasons, published,
                bias_risk, is_vendor, date_reason, topic, time_range,
            ))

        scored_items.sort(key=lambda x: x[0], reverse=True)
        saved_cat = 0
        for row in scored_items:
            (
                score, item, title, url, content, reasons, published,
                bias_risk, is_vendor, date_reason, topic, time_range,
            ) = row
            if saved_cat >= max_save or total_saved >= max_total:
                break

            if score >= min_score:
                print(f"    [CANDIDATE] score={score} | {title[:55]}")
                meta = {
                    "title": title,
                    "url": url,
                    "source_name": f"expansion/{cat_id}",
                    "source_type": "tavily",
                    "origin": "open_web_search",
                    "discovery_score": score,
                    "discovery_reasons": reasons,
                    "search_query": query,
                    "category": cat_id,
                    "topic": topic,
                    "time_range": time_range,
                    "published": published,
                    "published_at": published,
                    "discovered_date": collected_at.split()[0],
                    "date_reason": date_reason,
                    "max_article_age_days": max_age_days,
                    "collected_at": collected_at,
                    "is_vendor": is_vendor,
                    "bias_risk": bias_risk,
                    "collect_method": "tavily_expansion_discovery",
                    "_min_discovery_score": min_score,
                }
                from ipn_agent.collect.discovery import promote_tavily_to_raw

                pipe = promote_tavily_to_raw(
                    vault_path,
                    meta,
                    content,
                    subdir,
                    dry_run,
                )
                status = pipe.get("status", "")
                if status in ("raw_saved", "dry_run"):
                    saved_cat += 1
                    total_saved += 1
                    raw_rel = pipe.get("raw_path", "")
                    print(f"    [RAW] score={score} → {raw_rel or '01_raw/expansion/'}")
                    log_tool_event(
                        "research", "markdown_writer", "success",
                        f"저장 완료: {Path(raw_rel).name}" if raw_rel else "raw 저장",
                        target=raw_rel or f"01_raw/expansion/{subdir}/",
                    )
                elif status == "discarded":
                    reason = pipe.get("reason", "discarded")
                    print(f"    [GATE] {reason}: {title[:50]}")
                    _append_discovery_log(vault_path, "search_discarded.jsonl", {
                        "url": url, "title": title, "category": cat_id,
                        "search_query": query, "discovery_score": score,
                        "discovery_reasons": reasons, "date_reason": date_reason,
                        "discard_reason": reason, "gate": pipe.get("gate"),
                    })
            elif score >= 3:
                print(f"    [LOW] score={score}: {title[:50]}")
                _append_discovery_log(vault_path, "search_low_score.jsonl", {
                    "url": url, "title": title, "category": cat_id,
                    "search_query": query, "discovery_score": score,
                    "discovery_reasons": reasons, "date_reason": date_reason,
                })
            else:
                print(f"    [DISCARD] score={score}: {title[:50]}")
                _append_discovery_log(vault_path, "search_discarded.jsonl", {
                    "url": url, "title": title, "category": cat_id,
                    "search_query": query, "discovery_score": score,
                    "discovery_reasons": reasons,
                    "date_reason": date_reason,
                    "discard_reason": "below_min_score",
                })

        print(f"  -> {saved_cat}건 01_raw/expansion 저장 (quality gate 통과)")
        _emit_collect_progress(
            "DISCOVERY", cat_idx, cat_total, cat_id,
            f"완료 ({saved_cat}건 raw)", count=saved_cat,
        )

    _emit_collect_progress(
        "DISCOVERY", cat_total, cat_total, "—",
        f"전체 Discovery 완료 (raw {total_saved}건)", count=total_saved,
    )
    log_tool_event(
        "research", "expansion_search", "success",
        "Tavily discovery 완료", count=total_saved,
    )
    return total_saved


# ═══════════════════════════════════════════════════════════════
# 메인
# ═══════════════════════════════════════════════════════════════

def load_all_sources(config: dict) -> list[dict]:
    """sources.yaml에서 모든 수집 대상 섹션을 통합해 반환한다."""
    sections = [
        "regular_sources",
        "vendor_sources",
        "news_sources",        # v0.6 추가
        "community_sources",   # v0.6 추가 (기본 enabled: false)
        "reference_sources",   # collect_by_default: false — --source 플래그로만 수집
    ]
    all_sources = []
    for section in sections:
        all_sources.extend(config.get(section, []))
    return all_sources


def run(target_source: str | None = None, dry_run: bool = False) -> None:
    vault_path = os.environ.get("OBSIDIAN_VAULT_PATH", "")
    if not vault_path and not dry_run:
        print("[ERROR] OBSIDIAN_VAULT_PATH 환경변수 미설정. .env 파일을 확인하세요.")
        sys.exit(1)

    config_path = PROJECT_DIR / "sources.yaml"
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    all_sources = [s for s in load_all_sources(config) if s.get("enabled", False)]
    # collect_by_default: false 소스(IETF, TM Forum 등)는 --source 지정 시에만 수집
    if not target_source:
        all_sources = [s for s in all_sources if s.get("collect_by_default", True)]

    if target_source:
        # enabled 여부와 관계없이 지정 소스 단건 실행
        all_by_id = load_all_sources(config)
        matched = [s for s in all_by_id if s["id"] == target_source]
        if not matched:
            print(f"[ERROR] 소스 '{target_source}'를 찾을 수 없습니다.")
            print(f"  등록된 소스 ID 목록:")
            for s in all_by_id:
                status = "✅" if s.get("enabled") else "⬜ disabled"
                print(f"    {status} {s['id']}")
            sys.exit(1)
        all_sources = matched
        if not all_sources[0].get("enabled", False):
            print(f"[WARN] '{target_source}'는 enabled: false 상태입니다. --source 지정으로 강제 실행합니다.")

    print(f"[INFO] 수집 대상: {len(all_sources)}개 소스 | vault: {vault_path or '(dry-run)'}")
    if mvp := mvp_limits_summary():
        print(f"[MVP] {mvp}")

    total_saved = 0
    source_total = len(all_sources)
    for idx, src in enumerate(all_sources, start=1):
        sid = src.get("id", "unknown")
        _emit_collect_progress("FETCH", idx, source_total, sid, "시작")
        src = apply_mvp_source_caps(src)
        mode  = src.get("collection_mode", "rss_or_url")
        max_a = src.get("max_articles_per_run", 5)
        saved = 0

        if mode in ("rss", "rss_or_url"):
            saved = collect_rss(src, vault_path, max_a, dry_run)
        elif mode == "blog_index":
            saved = collect_blog_index(src, vault_path, dry_run)
        elif mode == "tavily_search":
            saved = collect_tavily(src, vault_path, dry_run)
        elif mode == "api":
            saved = collect_api(src, vault_path, dry_run)
        else:
            saved = collect_url(src, vault_path, dry_run)

        total_saved += saved
        _emit_collect_progress(
            "FETCH", idx, source_total, sid, f"완료 ({saved}건 저장)", count=saved,
        )

    if source_total:
        _emit_collect_progress(
            "FETCH", source_total, source_total, "—",
            f"전체 fetch 완료 (총 {total_saved}건)", count=total_saved,
        )

    print(f"\n[DONE] 총 {total_saved}건 저장 완료")
    if not dry_run and total_saved > 0:
        print(f"[NEXT] Obsidian에서 {vault_path}/01_raw/ 폴더를 열어 기사를 확인하세요.")
        print(f"       다음 단계: python review_script.py - Agent가 요약/분류 후 02_review/ 에 저장합니다.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IP Network 뉴스레터 소스 수집기")
    parser.add_argument("--source",           help="특정 소스 ID만 수집 (enabled 여부 무관하게 강제 실행)")
    parser.add_argument("--dry-run",          action="store_true", help="저장 없이 URL 목록만 출력")
    parser.add_argument("--expansion-search", action="store_true",
                        help="카테고리별 Tavily 확장 검색만 실행 (RSS 수집 생략)")
    parser.add_argument("--category",         help="--expansion-search 시 특정 카테고리만 실행")
    args = parser.parse_args()

    if args.expansion_search:
        # 확장 검색 단독 실행
        vault_path = os.environ.get("OBSIDIAN_VAULT_PATH", "")
        if not vault_path and not args.dry_run:
            print("[ERROR] OBSIDIAN_VAULT_PATH 환경변수 미설정.")
            sys.exit(1)
        config_path = PROJECT_DIR / "sources.yaml"
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)
        run_expansion_search(config, vault_path, dry_run=args.dry_run,
                             target_category=args.category)
    else:
        run(target_source=args.source, dry_run=args.dry_run)
