"""
IP Network Technology Trend Newsletter Agent — StateGraph Skeleton
==================================================================
아키텍처 개요 (3-레이어):

  [Phase 1 — fetch_script.py]
    Sources (RSS/URL/PDF)
      └─ MarkItDown → YAML frontmatter + MD 본문
         └─ vault/01_raw/{source_type}/ 저장

  [Phase 2 — review_script.py]
    vault/01_raw/ 읽기
      └─ LLM: 요약 + 분류 + 편향 검토
         └─ vault/02_review/ 에 리뷰 Markdown 생성
            └─ 사람이 Obsidian에서 검토 → 03_approved/ 이동

  [Phase 3 — 이 파일 (newsletter_agent_skeleton.py)]
    obsidian_loader_node  ← vault/03_approved/ .md 파일 읽기
      └─ [load_sample_node]  fallback: 03_approved/ 비었을 때
      └─ [tavily_node]       카테고리 공백 보강
    analysis_node          최종 분류 + structured output
      └─ [hitl_node]         편향 항목 최종 확인
      └─ standards_linker_node  룰 기반 IETF 표준 맥락 연결
    editor_node            NewsletterOutput 생성 + vault/04_newsletter/ 저장

  [Phase 4 — 표시·축적]
    Streamlit UI / DB / RAG

실행 전 확인 필요:
  pip install langgraph langchain-openai langchain-community
              markitdown feedparser pyyaml tavily-python
  .env: OPENAI_API_KEY, OBSIDIAN_VAULT_PATH, TAVILY_API_KEY (선택)

진입점: app  (langgraph.json 등록)
"""

# ── 표준 라이브러리 ─────────────────────────────────────────────
import json
import operator
import os
import re
import yaml
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal, get_args

# ── 서드파티 ────────────────────────────────────────────────────
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

from ipn_agent.core.tool_logger import log_tool_event
from ipn_agent.core.text_normalize import normalize_network_terms

# ── 선택 의존성: MarkItDown (없으면 requests fallback) ──────────
try:
    from markitdown import MarkItDown
    _MD_CONVERTER = MarkItDown()
    _MARKITDOWN_AVAILABLE = True
except ImportError:
    _MD_CONVERTER = None
    _MARKITDOWN_AVAILABLE = False

# ── 선택 의존성: Tavily (없으면 tavily_node 비활성화) ───────────
try:
    from langchain_community.tools.tavily_search import TavilySearchResults
    _TAVILY_AVAILABLE = True
except ImportError:
    _TAVILY_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════
# 1. Pydantic 모델 — 노드 간 데이터 계약
# ═══════════════════════════════════════════════════════════════

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
    """Research 노드 출력 단위"""
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
    approved_filename: str = ""


class BiasJudge(BaseModel):
    """LLM-as-Judge 출력 스키마"""
    verdict: Literal["vendor_bias", "ok"]
    evidence: str = ""                      # 편향 근거 직접 인용
    confidence: float = 0.0                 # 0.0 ~ 1.0


class ArticleAnalysis(BaseModel):
    """Analysis 노드 출력 단위"""
    title: str
    url: str
    headline: str = Field(description="한국어 헤드라인 1줄")
    summary: str  = Field(description="핵심 내용 3~5줄, 한국어")
    category: CategoryType
    keywords: list[str] = []
    is_vendor: bool = False
    bias_flag: bool = False
    bias_note: str = ""
    standards_context: list[str] = Field(default_factory=list)


class NewsletterOutput(BaseModel):
    """Editor 노드 최종 출력"""
    date: str
    total_articles: int
    used_sources: list[str] = []            # 실제 사용된 소스명 → Streamlit 상단 표시
    fallback_used: bool = False             # 샘플 데이터 사용 여부 → Streamlit 상단 표시
    sections: dict[str, list[dict]] = {}    # {category: [ArticleAnalysis.model_dump(), ...]}
    review_required: list[str] = []         # 검토 필요 항목 제목 목록


# ═══════════════════════════════════════════════════════════════
# 2. StateGraph State
# ═══════════════════════════════════════════════════════════════

class NewsletterState(TypedDict):
    # 공통
    messages: Annotated[list, add_messages]         # Chat UI 대화 흐름

    # source_loader_node 출력
    sources: list                                    # sources.yaml 파싱 결과 (vault 설정 포함)
    vault_path: str                                  # OBSIDIAN_VAULT_PATH (env 또는 yaml)

    # obsidian_loader_node / load_sample_node / tavily_node 출력 (누적)
    raw_articles: Annotated[list, operator.add]
    fallback_used: bool

    # analysis_node 출력
    analyzed_articles: list                          # list[ArticleAnalysis.model_dump()]
    bias_count: int                                  # conditional_edge 조건

    # editor_node 출력
    newsletter: dict                                 # NewsletterOutput.model_dump()

    # 공통 안전 장치
    attempt: int


# ═══════════════════════════════════════════════════════════════
# 3. LLM 초기화
# ═══════════════════════════════════════════════════════════════

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
# TODO: 분석/요약 전용으로 더 강력한 모델을 쓰고 싶다면 별도 인스턴스 선언
# analysis_llm = ChatOpenAI(model="gpt-4o", temperature=0)


# ═══════════════════════════════════════════════════════════════
# 4. 노드 함수 구현
# ═══════════════════════════════════════════════════════════════

# ── 4-1. source_loader_node ────────────────────────────────────
def source_loader_node(state: NewsletterState) -> dict:
    """sources.yaml과 Obsidian vault 경로를 읽어 State에 저장한다."""
    yaml_path = os.path.join(os.path.dirname(__file__), "sources.yaml")
    try:
        with open(yaml_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)
        sources = (
            config.get("regular_sources", [])
            + config.get("vendor_sources", [])
        )
    except FileNotFoundError:
        sources = []
        config = {}
        print("[WARN] sources.yaml not found — using empty source list")

    # Obsidian vault 경로: 환경변수 우선, 없으면 sources.yaml의 obsidian.vault_path
    vault_path = (
        os.environ.get("OBSIDIAN_VAULT_PATH")
        or config.get("obsidian", {}).get("vault_path", "")
    )
    if not vault_path:
        print("[WARN] OBSIDIAN_VAULT_PATH 미설정 — load_sample fallback으로 동작")

    return {"sources": sources, "vault_path": vault_path, "attempt": 0}


# ── 4-2. obsidian_loader_node ─────────────────────────────────
# Phase 1(fetch_script.py)에서 MarkItDown으로 수집·저장한 뒤
# 사람이 vault/raw/ → vault/approved/ 로 이동한 파일만 읽는다.
# ──────────────────────────────────────────────────────────────
def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """YAML frontmatter 파싱. (metadata_dict, body_text) 반환."""
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


def obsidian_loader_node(state: NewsletterState) -> dict:
    """Obsidian vault/approved/ 폴더의 승인된 MD 파일을 로딩한다."""
    vault_path = state.get("vault_path", "")
    approved_dir = Path(vault_path) / "03_approved" if vault_path else None

    log_tool_event(
        "newsletter", "approved_reader", "running",
        "Approved Markdown 읽기 시작", target="03_approved",
    )

    if not approved_dir or not approved_dir.is_dir():
        print(f"[WARN] 03_approved/ 폴더 없음 ({approved_dir}) — fallback으로 분기")
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


# ── 4-3. load_sample_node ────────────────────────────────────
def load_sample_node(state: NewsletterState) -> dict:
    """로컬 sample_articles.json을 로딩한다 (fallback)."""
    sample_path = os.path.join(os.path.dirname(__file__), "data", "sample_articles.json")
    try:
        with open(sample_path, encoding="utf-8") as f:
            samples = json.load(f)
        print("[INFO] Fallback: sample_articles.json 로딩 완료")
    except FileNotFoundError:
        print("[ERROR] sample_articles.json 없음 — 빈 목록 반환")
        samples = []
    return {
        "raw_articles": samples,
        "fallback_used": True,
    }


# ── 4-4. tavily_node ────────────────────────────────────────
def tavily_node(state: NewsletterState) -> dict:
    """카테고리 공백을 Tavily 검색으로 보강한다 (최대 2 쿼리)."""
    if not _TAVILY_AVAILABLE:
        print("[WARN] tavily-python 미설치 — tavily_node 건너뜀")
        return {"raw_articles": []}

    # TODO: sources.yaml의 expansion_search.target_categories와 queries 참조
    TARGET_QUERIES = [
        "IP backbone network technology 2025",
        "datacenter networking BGP evpn 2025",
    ]
    search = TavilySearchResults(max_results=3)
    new_articles: list[dict] = []
    for q in TARGET_QUERIES[:2]:  # 최대 2 쿼리
        try:
            results = search.invoke(q)
            for r in results:
                new_articles.append(RawArticle(
                    title=r.get("title", ""),
                    url=r.get("url", ""),
                    content=r.get("content", ""),
                    source_name="tavily",
                ).model_dump())
        except Exception as e:
            print(f"[WARN] Tavily 검색 실패: {e}")
    return {"raw_articles": new_articles}


# ── 4-5. analysis_node ────────────────────────────────────────
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


def clean_text(text: str) -> str:
    """출력 전 텍스트 정리 — literal \\n, \\t, 중복 공백, 네트워크 용어."""
    if not text:
        return ""
    t = str(text).replace("\\n", "\n").replace("\\t", " ")
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = re.sub(r"[ \t]+", " ", t)
    t = normalize_network_terms(t)
    return t.strip()


def _is_low_quality_text(text: str) -> bool:
    return any(p in (text or "") for p in LOW_QUALITY_PHRASES)


def analysis_node(state: NewsletterState) -> dict:
    """
    수집된 기사를 분류·요약·편향 검토한다.
    - 분류: Literal[CategoryType] structured output
    - 요약: 한국어 3~5줄
    - 편향 검토: LLM-as-Judge (BiasJudge)
    """
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
        analysis_result = ArticleAnalysis(
            title=clean_text(article.title),
            url=article.url,
            headline=headline[:200],
            summary=summary[:1500],
            category=cat,
            keywords=keywords,
            is_vendor=article.is_vendor,
            bias_flag=bias_flag,
            bias_note="",
        )
        if analysis_result.bias_flag:
            bias_count += 1
        entry = analysis_result.model_dump()
        entry["source_name"] = article.source_name
        entry["approved_filename"] = item.get("approved_filename") or article.approved_filename or ""
        analyzed.append(entry)

    return {"analyzed_articles": analyzed, "bias_count": bias_count}


# ── 4-6. standards_linker_node ───────────────────────────────
STANDARDS_KEYWORD_RULES: list[tuple[list[str], str, str]] = [
    (["bgp", "route-leak", "route_leak", "hijack", "rpki", "aspa"], "idr", "IDR / BGP"),
    (["evpn", "vxlan", "vpn"], "bess", "BESS / EVPN"),
    (["is-is", "isis", "ospf", "igp", "link-state", "link_state"], "lsr", "LSR / IGP"),
    (["srv6", "sr-mpls", "sr_mpls", "segment routing", "segment-routing"], "spring", "SPRING / Segment Routing"),
]

_WG_MEANINGS_CACHE: dict[str, str] | None = None


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
    """표준 맥락 연결 — match_score >= 2 일 때만 반환."""
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

    # IDR/BGP — 엄격 매칭
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

    # 기타 WG — 키워드 2개 이상 또는 title 직접 등장
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


def standards_linker_node(state: NewsletterState) -> dict:
    """analysis 이후 — 기사별 IETF 표준 맥락을 룰 기반으로 연결 (LLM 없음)."""
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


# ── 4-7. hitl_node ────────────────────────────────────────────
def hitl_node(state: NewsletterState) -> dict:
    """
    편향 항목 처리.
    MVP: bias_flag 항목을 review_required에 표시만 한다.
    선택 구현: interrupt() + Command(resume=...) 승인 흐름 적용.
    """
    # from langgraph.types import interrupt
    # interrupt({"message": "편향 항목이 발견되었습니다. 승인하시겠습니까?", ...})
    flagged = [
        a["title"] for a in state.get("analyzed_articles", [])
        if a.get("bias_flag")
    ]
    print(f"[HITL] 편향 항목 {len(flagged)}건: {flagged}")
    # MVP에서는 State를 그대로 통과
    return {}


# ── 4-8. editor_node ────────────────────────────────────────
def editor_node(state: NewsletterState) -> dict:
    """분석 결과를 카테고리별로 편집해 NewsletterOutput을 생성한다."""
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
        sections.setdefault(a.category, []).append(payload)
        if a.bias_flag:
            review_required.append(a.title)
        # TODO: RawArticle.source_name도 used_sources에 추가
        used_sources.add(item.get("source_name", "unknown"))

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

    # 최종 뉴스레터를 vault/04_newsletter/ 에 Markdown으로 저장
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


def _shorten(text: str, max_len: int = 45) -> str:
    """카드용 짧은 헤드라인."""
    t = clean_text(text or "").replace("\n", " ")
    t = re.sub(r"[.。!?！？…]+$", "", t).strip()
    if len(t) <= max_len:
        return t
    return t[:max_len].rstrip() + "…"


def _one_line_summary(summary: str, max_len: int = 120) -> str:
    """상세 요약에서 한 줄 요약 추출."""
    s = clean_text(summary or "").replace("\n", " ")
    for sep in (". ", "。", "! ", "? ", "!\n", "?\n"):
        if sep in s:
            first = s.split(sep)[0].strip()
            if first:
                return _shorten(first, max_len) if len(first) > max_len else first
    return _shorten(s, max_len)


def _short_source_label(source_name: str) -> str:
    """apnic_blog → apnic, ripe_labs → ripe 등 짧은 출처 라벨."""
    if not source_name or not str(source_name).strip():
        return ""
    s = str(source_name).strip()
    for suffix in ("_blog", "_newsroom", "_labs", "_news"):
        if s.lower().endswith(suffix):
            s = s[: -len(suffix)]
            break
    if "_" in s:
        return s.split("_")[0]
    return s


def _format_tags(keywords: list[str] | None, max_tags: int = 6) -> str:
    tags = [k.strip() for k in (keywords or []) if k and str(k).strip()][:max_tags]
    if not tags:
        return ""
    return f"**keyword:** {', '.join(tags)}"


def _format_article_card(index: int, article: dict) -> list[str]:
    """기사 1건 카드형 Markdown 블록."""
    headline_raw = clean_text(article.get("headline") or article.get("title") or "제목 없음")
    short_headline = _shorten(headline_raw, 45)
    summary = clean_text(article.get("summary") or "")
    one_line = _one_line_summary(summary)
    tags_line = _format_tags(article.get("keywords"))
    url = (article.get("url") or "").strip()
    source_label = _short_source_label(article.get("source_name") or "")

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
    return block


def _save_newsletter_md(
    vault_path: str,
    output: "NewsletterOutput",
    *,
    included_urls: list[str] | None = None,
    included_approved_files: list[str] | None = None,
) -> None:
    """NewsletterOutput을 YAML frontmatter + Markdown으로 draft/ 에 저장."""
    out_dir = Path(vault_path) / "04_newsletter" / "draft"
    out_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{output.date}-newsletter.md"
    log_tool_event(
        "newsletter", "newsletter_writer", "running",
        f"뉴스레터 Markdown 저장 중", target=filename,
    )
    body_lines = [
        f"# IP Network 기술 동향 뉴스레터 — {output.date}",
        f"\n총 기사: {output.total_articles}건 | 출처: {', '.join(output.used_sources)}",
    ]
    if output.fallback_used:
        body_lines.append("\n> ⚠️ 샘플 데이터 사용 (실제 수집 실패)")
    if output.review_required:
        body_lines.append(f"\n> ⚠️ 편향 검토 필요 항목: {', '.join(output.review_required)}")

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


# ═══════════════════════════════════════════════════════════════
# 5. 라우팅 함수 (conditional_edge)
# ═══════════════════════════════════════════════════════════════

def route_after_loader(state: NewsletterState) -> str:
    """Obsidian 로딩 결과에 따라 다음 노드를 결정한다."""
    articles = state.get("raw_articles", [])
    if not articles:
        return "load_sample"
    if len(articles) < 5:       # 카테고리 공백 의심 → Tavily 보강
        return "tavily"
    return "analysis"


def route_after_analysis(state: NewsletterState) -> str:
    """편향 항목 존재 여부에 따라 HITL 여부를 결정한다."""
    if state.get("bias_count", 0) > 0:
        return "hitl"
    return "standards_linker"


# ═══════════════════════════════════════════════════════════════
# 6. StateGraph 조립
# ═══════════════════════════════════════════════════════════════

def build_graph() -> StateGraph:
    """
    Deprecated — Chat UI / langgraph.json 호환용 Editor subgraph.
    운영 draft 생성은 newsletter_orchestrator.py 단일 Graph 사용.
    """
    builder = StateGraph(NewsletterState)

    # 노드 등록
    builder.add_node("source_loader",    source_loader_node)
    builder.add_node("obsidian_loader",  obsidian_loader_node)   # Phase 1 결과 읽기
    builder.add_node("load_sample",      load_sample_node)
    builder.add_node("tavily",           tavily_node)
    builder.add_node("analysis",         analysis_node)
    builder.add_node("hitl",             hitl_node)
    builder.add_node("standards_linker", standards_linker_node)
    builder.add_node("editor",           editor_node)

    # 엣지 연결
    builder.add_edge(START, "source_loader")
    builder.add_edge("source_loader", "obsidian_loader")
    builder.add_conditional_edges(
        "obsidian_loader",
        route_after_loader,
        {"load_sample": "load_sample", "tavily": "tavily", "analysis": "analysis"},
    )
    builder.add_edge("load_sample", "analysis")
    builder.add_edge("tavily",      "analysis")
    builder.add_conditional_edges(
        "analysis",
        route_after_analysis,
        {"hitl": "hitl", "standards_linker": "standards_linker"},
    )
    builder.add_edge("hitl", "standards_linker")
    builder.add_edge("standards_linker", "editor")
    builder.add_edge("editor", END)

    return builder


# ── 컴파일 ─────────────────────────────────────────────────────
_graph = build_graph()
app = _graph.compile(checkpointer=MemorySaver())   # langgraph.json 등록 진입점


# ═══════════════════════════════════════════════════════════════
# 7. 로컬 실행 헬퍼
# ═══════════════════════════════════════════════════════════════

def run_newsletter(thread_id: str = "default") -> NewsletterOutput | None:
    """
    Deprecated wrapper — newsletter_editor.run_editor_for_paths(load_all_approved=True).
    Chat UI는 기존 `app` subgraph 유지.
    """
    from ipn_agent.orchestrator.editor import run_editor_for_paths

    result = run_editor_for_paths([], run_id=thread_id, force=True, load_all_approved=True)
    return result.output if result else None


def _run_newsletter_editor_graph(thread_id: str = "default") -> NewsletterOutput | None:
    """Legacy — Editor LangGraph subgraph 직접 invoke (Chat UI용)."""
    config = {"configurable": {"thread_id": thread_id}}
    initial_state: NewsletterState = {
        "messages": [HumanMessage(content="IP Network 뉴스레터를 생성해줘.")],
        "sources": [],
        "vault_path": os.environ.get("OBSIDIAN_VAULT_PATH", ""),
        "raw_articles": [],
        "fallback_used": False,
        "analyzed_articles": [],
        "bias_count": 0,
        "newsletter": {},
        "attempt": 0,
    }
    result = app.invoke(initial_state, config=config)
    if result.get("newsletter"):
        return NewsletterOutput(**result["newsletter"])
    return None


MAX_EDITOR_ARTICLE_SUMMARY_CHARS = 1500


def _load_approved_from_rel_paths(
    vault_path: str,
    rel_paths: list[str],
    *,
    max_summary_chars: int = MAX_EDITOR_ARTICLE_SUMMARY_CHARS,
) -> list[dict]:
    """Orchestrator editor — 지정 approved 경로만 metadata·요약 중심 로드."""
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
                approved_filename=md.name,
            ).model_dump())
        except Exception as e:
            print(f"[WARN] pipeline loader 실패 {rel}: {e}")
    return articles


class PipelineNewsletterResult:
    """Deprecated — use newsletter_editor.DraftResult."""

    def __init__(self, output: NewsletterOutput, draft_path: str):
        self.output = output
        self.draft_path = draft_path


def run_newsletter_from_pipeline(
    approved_rel_paths: list[str],
    *,
    run_id: str = "",
    force: bool = False,
) -> PipelineNewsletterResult | None:
    """Deprecated wrapper — newsletter_editor.run_editor_for_paths()."""
    from ipn_agent.orchestrator.editor import run_editor_for_paths

    result = run_editor_for_paths(
        approved_rel_paths,
        run_id=run_id,
        force=force,
    )
    if result is None:
        return None
    return PipelineNewsletterResult(output=result.output, draft_path=result.draft_path)


def run_newsletter_via_orchestrator(thread_id: str = "default") -> NewsletterOutput | None:
    """03_approved 전체 → draft (Newsletter Orchestrator draft 모드)."""
    from ipn_agent.orchestrator.workflow import run_newsletter_workflow

    wf = run_newsletter_workflow(mode="draft")
    nl = wf.get("newsletter")
    if nl:
        return NewsletterOutput(**nl)
    return None


if __name__ == "__main__":
    output = run_newsletter()
    if output:
        print(f"\n=== 뉴스레터 생성 완료 ({output.date}) ===")
        print(f"총 기사: {output.total_articles}건")
        print(f"사용 소스: {output.used_sources}")
        print(f"Fallback 사용: {output.fallback_used}")
        print(f"카테고리: {list(output.sections.keys())}")
        if output.review_required:
            print(f"검토 필요 항목: {output.review_required}")

        # 결과 저장
        out_dir = os.path.join(os.path.dirname(__file__), "output")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, "newsletter_result.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output.model_dump(), f, ensure_ascii=False, indent=2)
        print(f"\n결과 저장: {out_path}")
    else:
        print("[ERROR] 뉴스레터 생성 실패")
