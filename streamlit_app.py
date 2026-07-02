"""
IP Network Newsletter Agent — Streamlit v0.5
========================================================
실행 → 기사 검토 (통합 HITL) → 뉴스레터 · 아카이브 · 운영콘솔

실행:
  cd "mini pjt"
  streamlit run streamlit_app.py
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from ipn_agent.core.mvp_limits import mvp_limits_summary
from ipn_agent.review.metadata import source_type_badge
from ipn_agent.standards.radar import WG_CONTEXT, load_ietf_source_config
from ipn_agent.ui.streamlit_utils import (
    PROJECT_DIR,
    STATUS_ICONS,
    THEME_CARD_CLASS,
    THEME_CARD_META_CLASS,
    get_tool_friendly_name,
    inject_theme_css,
    load_tool_logs_since,
    render_aggregate_tool_status,
    render_recent_tools_brief,
    resolve_workflow_display_state,
    run_agent_script,
    run_orchestrator_workflow,
)
from ipn_agent.vault.utils import (
    BIAS_RISKS,
    CATEGORIES,
    approve_review,
    discovery_staging_stats,
    get_ietf_radar_path,
    get_vault_path,
    list_approved_items,
    list_used_article_files,
    list_archived_newsletter_files,
    list_discovery_staging,
    list_newsletter_files,
    list_published_newsletter_files,
    list_review_items,
    load_discovery_logs,
    load_sources_from_yaml,
    load_expansion_search_config,
    parse_frontmatter,
    parse_review_body,
    publish_newsletter,
    read_markdown,
    reject_review,
    sync_published_to_archive,
    vault_stats,
)

load_dotenv()


def _bias_badge(bias: str) -> str:
    if bias == "low":
        return "🟢"
    if bias == "medium":
        return "🟡"
    return "🔴"


def _wg_summaries() -> list[dict]:
    """HITL/IETF Radar용 WG 요약 (sources.yaml + WG_CONTEXT 병합)."""
    cfg = load_ietf_source_config()
    wg_radar = cfg.get("wg_radar", {})
    summaries: list[dict] = []
    for wg_key, ctx in WG_CONTEXT.items():
        radar = wg_radar.get(wg_key, {})
        summaries.append({
            "label": ctx.get("label", wg_key.upper()),
            "categories": ctx.get("categories", []),
            "keywords": ctx.get("keywords", []),
            "meaning": radar.get("change_meaning", "표준화 흐름 추적"),
        })
    return summaries


def render_standards_context(compact: bool = False) -> None:
    """IETF Radar 요약 — HITL Review 참고용."""
    summaries = _wg_summaries()
    if compact:
        st.markdown("**📡 Standards Context**")
        for s in summaries[:3]:
            kw = ", ".join(s["keywords"][:3])
            st.caption(f"- **{s['label']}:** {kw} — {s['meaning'][:60]}")
    else:
        for s in summaries:
            st.markdown(
                f"""<div class="{THEME_CARD_CLASS}">
  <div><b>{s['label']}</b></div>
  <div class="{THEME_CARD_META_CLASS}" style="margin-top:6px;">
    <b>연결 카테고리:</b> {', '.join(s['categories'])}<br/>
    <b>주요 키워드:</b> {', '.join(s['keywords'])}<br/>
    <b>의미:</b> {s['meaning']}
  </div>
</div>""",
                unsafe_allow_html=True,
            )


def filter_article_reviews(
    items: list[dict],
    category: str,
    bias: str,
    min_score: int,
    source_query: str,
    text_query: str,
    source_type_filter: str = "전체",
) -> list[dict]:
    out = items
    if category != "전체":
        out = [i for i in out if i["category"] == category]
    if bias != "전체":
        out = [i for i in out if i["bias_risk"] == bias]
    if min_score > 0:
        out = [i for i in out if i["importance_score"] >= min_score]
    if source_type_filter != "전체":
        if source_type_filter == "등록소스":
            out = [
                i for i in out
                if i.get("origin") == "curated_source"
                or i.get("source_type") in ("rss", "manual")
            ]
        elif source_type_filter == "웹검색":
            out = [
                i for i in out
                if i.get("source_type") == "tavily"
                or i.get("origin") == "open_web_search"
            ]
        elif source_type_filter == "Vendor":
            out = [
                i for i in out
                if i.get("source_type") in ("vendor", "vendor_blog")
                or (i.get("meta") or {}).get("is_vendor")
            ]
        elif source_type_filter == "Standards":
            out = [
                i for i in out
                if i.get("source_type") == "ietf"
                or i.get("origin") == "standards_context"
            ]
    if source_query.strip():
        q = source_query.strip().lower()
        out = [
            i for i in out
            if q in (i.get("source_id") or "").lower()
            or q in (i.get("source_name") or "").lower()
        ]
    if text_query.strip():
        q = text_query.strip().lower()
        out = [
            i for i in out
            if q in i["title"].lower()
            or q in i["body"].lower()
            or q in (i.get("summary") or "").lower()
        ]
    return out


_ORIGIN_LABELS = {
    "curated_source": "등록소스",
    "open_web_search": "웹검색",
    "standards_context": "Standards",
}
_ROUTE_LABELS = {
    "approval_pending": "승인 대기",
    "needs_human_review": "추가 검토",
    "rejected": "자동 제외",
}
_TRUST_LABELS = {"high": "높음", "medium": "보통", "low": "낮음"}


def _label_origin(origin: str) -> str:
    return _ORIGIN_LABELS.get(origin or "", origin or "—")


def _label_route(route: str) -> str:
    return _ROUTE_LABELS.get(route or "", route or "—")


def _label_trust(trust: str) -> str:
    return _TRUST_LABELS.get(trust or "", trust or "—")


def _count_review_pending() -> int:
    return len([
        i for i in list_review_items()
        if not i.get("is_published") and i.get("hitl_route") == "approval_pending"
    ])


def _render_recent_tools_sidebar(limit: int = 3) -> None:
    if not st.session_state.get("show_collect_tool_status"):
        st.caption("실행 후 표시됩니다")
        return
    offset = st.session_state.get("collect_tool_log_offset", 0)
    logs = load_tool_logs_since(offset)
    if not logs:
        st.caption("로그 없음")
        return
    render_recent_tools_brief(logs, limit=limit)


def _source_checkbox_key(source_id: str) -> str:
    return f"source_select_{source_id}"


_TIER_UI_GROUPS: list[tuple[str, str, bool]] = [
    ("Tier 1", "Core Sources · Tier 1", False),
    ("Tier 2", "Vendor Sources · Tier 2", True),
    ("News", "News Sources · Tier 3", False),
    ("Reference", "Standards / Reference", False),
]


def _default_selected_source_ids(sources: list[dict]) -> list[str]:
    """기본값: enabled Tier 1~3 + IETF (Reference 중 TM Forum 등은 제외)."""
    selected: list[str] = []
    for source in sources:
        if not source.get("enabled"):
            continue
        if source.get("tier") == "Reference":
            if source.get("is_ietf"):
                selected.append(source["id"])
            continue
        selected.append(source["id"])
    return selected


def _apply_source_selection(sources: list[dict], selected_ids: list[str]) -> None:
    selected_set = set(selected_ids)
    for source in sources:
        st.session_state[_source_checkbox_key(source["id"])] = source["id"] in selected_set
    st.session_state.selected_sources = [
        source["id"] for source in sources if source["id"] in selected_set
    ]


def _render_source_picker(all_sources: list[dict]) -> list[str]:
    """Tier별 compact checkbox 소스 선택 (실행 탭)."""
    if "default_selected_sources" not in st.session_state:
        st.session_state.default_selected_sources = _default_selected_source_ids(all_sources)
    if "selected_sources" not in st.session_state:
        _apply_source_selection(all_sources, st.session_state.default_selected_sources)

    st.markdown(
        """
<style>
p.ipn-src-tier-title {
  font-size: 0.93rem;
  font-weight: 600;
  margin: 0.45rem 0 0.1rem 0;
  line-height: 1.25;
}
p.ipn-src-tier-title:first-of-type { margin-top: 0.25rem; }
.ipn-src-picker-wrap [data-testid="stHorizontalBlock"] { align-items: flex-start; gap: 0.35rem; }
.ipn-src-picker-wrap [data-testid="stHorizontalBlock"] [data-testid="stVerticalBlock"] {
  min-width: 0;
  flex: 0 1 auto !important;
  width: auto !important;
}
.ipn-src-picker-wrap .stCheckbox { margin-bottom: 0; padding-bottom: 0; }
.ipn-src-picker-wrap .stCheckbox label p { font-size: 0.9rem; white-space: nowrap; }
.ipn-src-selected-count { margin: 0.35rem 0 0.15rem 0; font-size: 0.92rem; }
</style>
""",
        unsafe_allow_html=True,
    )

    all_ids = [s["id"] for s in all_sources]
    tier1_ids = [s["id"] for s in all_sources if s.get("tier") == "Tier 1"]
    non_vendor_ids = [s["id"] for s in all_sources if s.get("tier") != "Tier 2"]

    qa1, qa2, qa3, qa4, qa5 = st.columns(5)
    with qa1:
        if st.button("전체 선택", key="src_sel_all", use_container_width=True):
            _apply_source_selection(all_sources, all_ids)
            st.rerun()
    with qa2:
        if st.button("전체 해제", key="src_sel_none", use_container_width=True):
            _apply_source_selection(all_sources, [])
            st.rerun()
    with qa3:
        if st.button("기본값 복원", key="src_sel_default", use_container_width=True):
            _apply_source_selection(all_sources, st.session_state.default_selected_sources)
            st.rerun()
    with qa4:
        if st.button("Tier 1만", key="src_sel_tier1", use_container_width=True):
            _apply_source_selection(all_sources, tier1_ids)
            st.rerun()
    with qa5:
        if st.button("Vendor 제외", key="src_sel_no_vendor", use_container_width=True):
            _apply_source_selection(all_sources, non_vendor_ids)
            st.rerun()

    row_max = 4
    selected: list[str] = []

    with st.container():
        st.markdown('<div class="ipn-src-picker-wrap">', unsafe_allow_html=True)
        for tier_key, title, show_bias in _TIER_UI_GROUPS:
            group = [s for s in all_sources if s.get("tier") == tier_key]
            if not group:
                continue

            st.markdown(f'<p class="ipn-src-tier-title">{title}</p>', unsafe_allow_html=True)
            for row_start in range(0, len(group), row_max):
                row = group[row_start : row_start + row_max]
                n = len(row)
                col_weights = [1] * n + [max(3, row_max)]
                cols = st.columns(col_weights)
                for col, source in zip(cols[:n], row):
                    with col:
                        key = _source_checkbox_key(source["id"])
                        if key not in st.session_state:
                            st.session_state[key] = source["id"] in st.session_state.selected_sources

                        help_parts: list[str] = []
                        if source.get("is_ietf"):
                            help_parts.append("Standards Radar — 뉴스레터 기사 HITL 대상 아님")
                        elif show_bias:
                            help_parts.append("Vendor 소스 — 편향(Bias) 검토 권장")
                        if not source.get("enabled"):
                            help_parts.append("sources.yaml에서 비활성")

                        checked = st.checkbox(
                            source["name"],
                            key=key,
                            help=" · ".join(help_parts) if help_parts else None,
                        )
                        if checked:
                            selected.append(source["id"])
        st.markdown("</div>", unsafe_allow_html=True)

    st.session_state.selected_sources = selected
    st.markdown(
        f'<p class="ipn-src-selected-count">선택된 소스: <strong>{len(selected)}</strong>개</p>',
        unsafe_allow_html=True,
    )
    return selected


def _render_run_progress_summary() -> None:
    vault = get_vault_path()
    ws = resolve_workflow_display_state(vault)
    dstats = discovery_staging_stats(vault)

    st.markdown("#### 진행 상황")

    if summary := st.session_state.get("last_run_summary"):
        st.markdown(
            f"**{summary.get('run_label', '최근 실행')} 완료** · "
            f"선택 {summary.get('selected_count', 0)}개 · "
            f"실패 소스: {', '.join(summary.get('failed_sources') or []) or '없음'}"
        )

    if not ws:
        st.caption("수집 실행 후 단계별 요약이 표시됩니다.")
        return

    collected = ws.get("collected_count", 0)
    reviewed = ws.get("reviewed_count", 0)
    pending = ws.get("approval_pending_count", 0)
    needs = ws.get("needs_human_review_count", 0)
    rejected = ws.get("rejected_count", 0)
    expansion_raw = dstats.get("expansion_raw", 0)

    lines = [
        f"✅ 소스 수집 · {collected}건",
        f"✅ 웹검색 확장 · raw {expansion_raw}건",
        f"✅ 품질 필터 · 자동 제외 {rejected}건",
        f"✅ 리뷰 생성 · {reviewed}건",
        f"✅ 기사 검토 큐 · 승인대기 {pending}건 / 추가검토 {needs}건",
    ]
    for line in lines:
        st.markdown(f'<p class="ipn-progress-line">{line}</p>', unsafe_allow_html=True)

    st.markdown("#### 최근 Tool")
    offset = st.session_state.get("collect_tool_log_offset", 0)
    render_recent_tools_brief(load_tool_logs_since(offset), limit=5)


def render_sidebar(stats: dict[str, int], vault: Path) -> None:
    st.markdown("## 🛰️ IP Network Agent")
    st.caption("기술 동향 뉴스레터 자동 큐레이션")

    st.markdown("**오늘 상태**")
    pending = _count_review_pending()
    c1, c2 = st.columns(2)
    c1.metric("검토 대기", pending)
    c2.metric("승인 완료", stats.get("03_approved", 0))
    c3, c4 = st.columns(2)
    c3.metric("Draft", stats.get("newsletter_draft", 0))
    c4.metric(
        "Expansion raw",
        stats.get("expansion_raw", 0),
        help="Tavily 웹검색 결과 (01_raw/expansion/). review_script 대상.",
    )

    st.divider()
    st.markdown("**최근 실행**")
    last_label = st.session_state.get("last_run_label", "—")
    last_time = st.session_state.get("last_run_time", "")
    if last_label != "—":
        st.success(f"{last_label}\n{last_time}")
    else:
        st.caption("아직 실행 기록 없음")

    st.markdown("**최근 Tool**")
    _render_recent_tools_sidebar(limit=3)

    with st.expander("고급 정보", expanded=False):
        st.markdown("**Vault**")
        st.code(str(vault), language=None)
        st.markdown("**Storage**")
        s1, s2 = st.columns(2)
        s1.metric("Raw", stats.get("01_raw", 0))
        s2.metric("Expansion", stats.get("expansion_raw", 0))
        s3, s4 = st.columns(2)
        s3.metric("Review", stats.get("02_review", 0))
        s4.metric("Approved", stats.get("03_approved", 0))
        st.metric("Newsletter", stats.get("04_newsletter", 0))
        st.caption(
            f"Draft {stats.get('newsletter_draft', 0)} · "
            f"Published {stats.get('newsletter_published', 0)} · "
            f"Used {stats.get('newsletter_used', 0)} · "
            f"Archive {stats.get('newsletter_archive', 0)}"
        )
        st.metric("IETF Radar", stats.get("ietf_radar", 0))
        if limits := mvp_limits_summary():
            st.caption(f"처리 상한: {limits}")


def render_run_tab() -> None:
    st.header("▶ 실행")

    sources = load_sources_from_yaml()
    expansion = load_expansion_search_config()
    tavily_ok = bool(os.environ.get("TAVILY_API_KEY", "").strip())
    exp_enabled = bool(expansion.get("enabled")) and tavily_ok

    st.markdown("#### 오늘 수집할 소스")
    selected = _render_source_picker(sources)
    source_name_map = {s["id"]: s["name"] for s in sources}
    ietf_src = next((s for s in sources if s.get("is_ietf")), None)
    article_sources = [s for s in sources if not s.get("is_ietf")]

    st.markdown("#### 실행 옵션")
    o1, o2, o3 = st.columns(3)
    with o1:
        st.checkbox(
            "웹검색 확장 포함",
            value=exp_enabled,
            disabled=True,
            help="수집 실행 시 Tavily expansion_search가 자동 실행됩니다.",
        )
    with o2:
        st.checkbox(
            "IETF Radar 포함",
            value=True,
            disabled=True,
            help="수집 실행 시 standards_radar가 함께 실행됩니다.",
        )
    with o3:
        st.checkbox(
            "기발행 기사 제외",
            value=True,
            disabled=True,
            help="published registry에 등록된 기사는 HITL·Draft에서 자동 제외됩니다.",
        )

    wc1, wc2, wc3 = st.columns(3)
    with wc1:
        if st.button("수집 실행", type="primary", key="wf_collect"):
            result = run_orchestrator_workflow(
                mode="collect",
                source_ids=selected if selected else None,
                expansion_only=not selected,
                compact_ui=True,
                label="수집 실행",
                source_name_map=source_name_map,
            )
            if result:
                st.session_state.workflow_state = result
            st.rerun()
    with wc2:
        if st.button("Draft 생성", key="wf_draft"):
            result = run_orchestrator_workflow(
                mode="draft",
                compact_ui=True,
                label="Draft 생성",
            )
            if result:
                st.session_state.workflow_state = result
            st.rerun()
    with wc3:
        if st.button("전체 실행", key="wf_full"):
            result = run_orchestrator_workflow(
                mode="full",
                source_ids=selected if selected else None,
                expansion_only=not selected,
                compact_ui=True,
                label="전체 실행",
                source_name_map=source_name_map,
            )
            if result:
                st.session_state.workflow_state = result
            st.rerun()

    st.divider()
    _render_run_progress_summary()

    with st.expander("소스/검색 상세 설정", expanded=False):
        st.markdown("**등록된 소스 (전체)**")
        df = pd.DataFrame([
            {
                "활성": "✅" if s["enabled"] else "⬜",
                "source_id": s["id"],
                "이름": s["name"],
                "수집 방식": s["collect_method"],
                "Tier": s["tier"],
            }
            for s in article_sources
        ])
        st.dataframe(
            df[["활성", "source_id", "이름", "수집 방식", "Tier"]],
            width="stretch",
            hide_index=True,
        )
        if ietf_src:
            st.caption(
                f"IETF: `{ietf_src['id']}` · {ietf_src['collect_method']} · "
                "Radar 전용 (기사 HITL 대상 아님)"
            )
        st.markdown("**Tavily Expansion Search**")
        if expansion.get("enabled"):
            st.caption(
                f"min_score {expansion.get('min_discovery_score', 3)}/5 · "
                f"API 키: {'설정됨' if tavily_ok else '미설정 (SKIP)'}"
            )
            excl = expansion.get("exclude_domains") or []
            if excl:
                st.caption(f"제외 도메인: {', '.join(excl)}")
            exp_df = pd.DataFrame([
                {
                    "카테고리": c["name"],
                    "query": c["query"],
                    "기간": c["time_range"],
                    "상한": c["max_results"],
                }
                for c in expansion.get("categories", [])
            ])
            st.dataframe(exp_df, width="stretch", hide_index=True)
        else:
            st.caption("expansion_search 비활성 (`sources.yaml`)")
        if limits := mvp_limits_summary():
            st.caption(f"처리 상한: {limits}")


def render_ietf_radar_tab() -> None:
    st.header("📡 IETF Standardization Radar")
    st.caption(
        "표준화 컨텍스트 — HITL Review **전**에 참고 · "
        "일반 기사 승인/반려 대상 아님"
    )

    radar_path = get_ietf_radar_path()

    if st.button("▶ IETF Radar 재실행", key="ietf_rerun"):
        run_agent_script("standards_radar_script.py", "IETF Radar")
        st.rerun()

    st.divider()
    st.markdown("#### WG별 표준화 컨텍스트")
    render_standards_context(compact=False)

    st.divider()
    st.markdown("#### Radar 파일 Preview")
    if radar_path.is_file():
        st.caption(f"`{radar_path.relative_to(get_vault_path())}`")
        _, body = parse_frontmatter(read_markdown(radar_path))
        st.markdown(body if body else read_markdown(radar_path))
    else:
        st.warning(
            "`04_newsletter/ietf_radar.md`가 없습니다. "
            "Sources & Analyze 또는 [IETF Radar 재실행]을 실행하세요."
        )


def render_ops_console_tab() -> None:
    st.header("⚙️ 운영콘솔")
    st.caption("Vault · expansion raw · quality gate · workflow · Tool 로그 · IETF Radar")

    vault = get_vault_path()
    stats = vault_stats(vault)
    dstats = discovery_staging_stats(vault)
    expansion = load_expansion_search_config()
    ws = resolve_workflow_display_state(vault)

    st.markdown("#### Vault")
    st.code(str(vault), language=None)

    st.markdown("#### Storage 상태")
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Raw", stats.get("01_raw", 0))
    s2.metric("Expansion", stats.get("expansion_raw", 0))
    s3.metric("Review", stats.get("02_review", 0))
    s4.metric("Approved", stats.get("03_approved", 0))
    s5, s6, s7, s8 = st.columns(4)
    s5.metric("Draft", stats.get("newsletter_draft", 0))
    s6.metric("Published", stats.get("newsletter_published", 0))
    s7.metric("Used", stats.get("newsletter_used", 0))
    s8.metric("Archive", stats.get("newsletter_archive", 0))
    st.caption(
        f"Rejected {stats.get('99_rejected', 0)} · "
        f"IETF Radar {stats.get('ietf_radar', 0)} · "
        f"Newsletter 합계 {stats.get('04_newsletter', 0)}"
    )

    st.markdown("#### Workflow 상세")
    if ws:
        ss = ws.get("step_status") or {}
        for step, st_val in ss.items():
            st.caption(f"· {step}: **{st_val}**")
        w1, w2, w3, w4, w5, w6, w7 = st.columns(7)
        w1.metric("수집", ws.get("collected_count", 0))
        w2.metric("리뷰", ws.get("reviewed_count", 0))
        w3.metric("승인대기", ws.get("approval_pending_count", 0))
        w4.metric("추가검토", ws.get("needs_human_review_count", 0))
        w5.metric("자동제외", ws.get("rejected_count", 0))
        w6.metric("승인", ws.get("approved_count", 0))
        w7.metric("발행필터", ws.get("published_filtered_count", 0))
        if ws.get("run_id"):
            st.caption(
                f"run_id: `{ws['run_id']}` · draft: `{ws.get('draft_path') or '—'}` · "
                f"quality: {ws.get('editor_quality_ok', '—')}"
            )
    else:
        st.caption("Orchestrator 실행 후 run_id·step_status가 표시됩니다.")

    st.divider()
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Expansion raw", dstats.get("expansion_raw", 0))
    m2.metric("게이트 제외", dstats.get("gate_discarded", 0))
    m3.metric("저점수", dstats.get("gate_low_score", 0))
    m4.metric(
        "min_score",
        f"{expansion.get('min_discovery_score', 3)}/5" if expansion.get("enabled") else "—",
    )
    m5.metric("Review", stats.get("02_review", 0))

    st.markdown("#### Expansion raw (`01_raw/expansion/`)")
    expansion_items = list_discovery_staging(vault)
    if not expansion_items:
        st.caption("expansion raw 없음 — Orchestrator 수집 후 Tavily 결과가 저장됩니다.")
    else:
        st.caption(
            f"{len(expansion_items)}건 · discovery_score는 운영 디버그용 "
            "(기사 검토는 02_review / review_score)"
        )
        for item in expansion_items[:20]:
            st.markdown(
                f"★{item['discovery_score']}/5 · "
                f"{item['category']} · {item['title'][:55]}"
            )
            st.caption(f"{item.get('url', '')[:120]}")
        if len(expansion_items) > 20:
            st.caption(f"… 외 {len(expansion_items) - 20}건")

    with st.expander("Quality gate 제외 사유 (최근)", expanded=False):
        st.caption("로그 경로: `logs/discovery/search_discarded.jsonl`")
        discarded = load_discovery_logs("search_discarded.jsonl", limit=30)
        if not discarded:
            st.caption("제외 로그 없음")
        else:
            for row in reversed(discarded[-15:]):
                reason = row.get("discard_reason") or row.get("date_reason") or "—"
                st.caption(
                    f"· [{reason}] score={row.get('discovery_score', '—')} · "
                    f"{row.get('title', '')[:50]}"
                )

    with st.expander("Discovery logs (저점수)", expanded=False):
        st.caption("로그 경로: `logs/discovery/search_low_score.jsonl`")
        low_score = load_discovery_logs("search_low_score.jsonl", limit=30)
        if not low_score:
            st.caption("저점수 로그 없음")
        else:
            for row in reversed(low_score[-15:]):
                st.caption(
                    f"· score={row.get('discovery_score', '—')} · "
                    f"{row.get('title', '')[:50]}"
                )

    st.divider()
    st.markdown("#### 📡 IETF Standardization Radar")
    st.caption("standards_context — 뉴스레터 기사 HITL 대상 아님")
    radar_path = get_ietf_radar_path()
    if st.button("▶ IETF Radar 재실행", key="ietf_rerun_ops"):
        run_agent_script("standards_radar_script.py", "IETF Radar")
        st.rerun()
    render_standards_context(compact=False)
    if radar_path.is_file():
        st.caption(f"`{radar_path.relative_to(vault)}`")
        _, body = parse_frontmatter(read_markdown(radar_path))
        with st.expander("Radar Preview", expanded=False):
            st.markdown(body if body else read_markdown(radar_path))
    else:
        st.warning("Radar 파일 없음 — 실행 탭에서 Orchestrator를 실행하세요.")

    st.divider()
    st.markdown("#### Tool 로그")
    offset = st.session_state.get("collect_tool_log_offset", 0)
    logs = load_tool_logs_since(offset)
    if not logs:
        st.caption("Orchestrator 실행 후 표시됩니다.")
    else:
        render_aggregate_tool_status(logs, st.empty())


def render_article_review_tab() -> None:
    st.header("📋 기사 검토")
    st.caption(
        "RSS · 등록소스 · Tavily 웹검색 — 모두 `02_review/` 통합 HITL · "
        "review_score 기준 (≥0.80 승인대기 · 0.55~0.80 추가검토 · <0.55 자동제외)"
    )

    with st.expander("📡 Standards Context — 검수 참고", expanded=False):
        render_standards_context(compact=True)
        radar_path = get_ietf_radar_path()
        if radar_path.is_file():
            st.caption(f"상세: `{radar_path.name}` · 운영콘솔에서 전체 확인")

    items = list_review_items()
    active = [i for i in items if not i.get("is_published")]
    published_blocked = [i for i in items if i.get("is_published")]
    approved_done = list_approved_items()

    pending = [i for i in active if i.get("hitl_route") == "approval_pending"]
    needs_review = [i for i in active if i.get("hitl_route") == "needs_human_review"]
    recollect = [i for i in active if i.get("recollect_required")]
    other = [
        i for i in active
        if i.get("hitl_route") not in ("approval_pending", "needs_human_review")
    ]

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("승인 대기", len(pending))
    c2.metric("추가 검토", len(needs_review))
    c3.metric("재수집 필요", len(recollect))
    c4.metric("기타/미분류", len(other))
    c5.metric("기발행 차단", len(published_blocked))
    c6.metric("승인 완료", len(approved_done))

    if published_blocked:
        with st.expander(f"🚫 기발행 registry 차단 ({len(published_blocked)}건)", expanded=False):
            for i in published_blocked:
                st.caption(f"· {i['title'][:60]}")

    queue_mode = st.radio(
        "검토 큐",
        ["승인 대기", "추가 검토", "재수집 필요", "전체 (미발행)"],
        horizontal=True,
        key="review_queue_mode",
    )
    if queue_mode == "승인 대기":
        items = pending
    elif queue_mode == "추가 검토":
        items = needs_review
    elif queue_mode == "재수집 필요":
        items = recollect
    else:
        items = active

    if "review_selected" not in st.session_state:
        st.session_state.review_selected = items[0]["filename"] if items else None

    left, right = st.columns([0.35, 0.65])

    with left:
        st.markdown("**기사 목록**")
        cat_filter = st.selectbox("카테고리", ["전체"] + CATEGORIES, key="review_cat")
        origin_filter = st.selectbox(
            "출처 유형",
            ["전체", "등록소스", "웹검색", "Vendor", "Standards"],
            key="review_origin",
        )
        min_imp = st.slider("최소 importance", 0, 5, 0, key="review_imp")
        text_q = st.text_input("제목/본문 검색", key="review_search")
        with st.expander("고급 필터", expanded=False):
            bias_filter = st.selectbox("bias_risk", ["전체"] + BIAS_RISKS, key="review_bias")
            source_q = st.text_input("source_id / source_name", key="review_src")

        filtered = filter_article_reviews(
            items, cat_filter, bias_filter, min_imp, source_q, text_q, origin_filter,
        )
        filtered.sort(
            key=lambda x: (x.get("review_score") or 0, x["importance_score"]),
            reverse=True,
        )
        st.caption(f"표시 {len(filtered)}건 / 전체 {len(items)}건")

        if st.button("새로고침", key="review_refresh"):
            st.rerun()

        if not filtered:
            st.info("검토 대기 기사가 없습니다. **실행** 탭에서 Orchestrator를 실행하세요.")
            return

        labels = []
        for i in filtered:
            badge = source_type_badge(i.get("source_type", "rss"))
            src = (i.get("source_name") or i.get("source_id") or "—")[:18]
            rs = i.get("review_score")
            score_txt = f" · {rs:.2f}" if rs is not None else ""
            prefix = "⚠️ " if i.get("recollect_required") else ""
            labels.append(
                f"{prefix}★{i['importance_score']}{score_txt} · {badge} · {src} — {i['title'][:38]}"
            )
        filenames = [i["filename"] for i in filtered]
        current = st.session_state.review_selected
        idx = filenames.index(current) if current in filenames else 0

        selected_label = st.radio(
            "기사 선택",
            options=labels,
            index=idx,
            key="review_radio",
            label_visibility="collapsed",
        )
        st.session_state.review_selected = filenames[labels.index(selected_label)]

    with right:
        selected_fn = st.session_state.review_selected
        item = next((i for i in filtered if i["filename"] == selected_fn), None)
        if not item:
            st.info("좌측에서 기사를 선택하세요.")
            return

        meta = item["meta"]
        badge = source_type_badge(item.get("source_type", "rss"))
        st.markdown(f"## {item['title']}")
        rs = item.get("review_score")
        st.markdown(
            f"""<div class="{THEME_CARD_CLASS}">
  <b>출처</b> {badge} · {item.get('source_name', '')} ({item.get('source_id', '')}) ·
  <b>출처 유형</b> {_label_origin(item.get('origin', ''))} ·
  <b>도메인</b> {item.get('domain') or '—'} ·
  <b>신뢰도</b> {_label_trust(item.get('trust_level', ''))}<br/>
  <b>카테고리</b> {item['category']} ·
  <b>편향</b> {_bias_badge(item['bias_risk'])} {item['bias_risk']} ·
  <b>★</b>{item['importance_score']}
  {f" · <b>리뷰 점수</b> {rs:.2f}" if rs is not None else ""}
  · <b>검토 상태</b> {_label_route(item.get('hitl_route', ''))}
</div>""",
            unsafe_allow_html=True,
        )

        if item.get("source_url"):
            st.markdown(f"[원문]({item['source_url']})")
        if meta.get("bias_note"):
            st.warning(f"편향: {meta['bias_note']}")
        if item.get("recollect_required"):
            st.error(
                "⚠️ **본문 재수집 필요** — 승인 시 뉴스레터 자동 제외될 수 있습니다."
            )
        if item.get("summary"):
            with st.expander("요약", expanded=True):
                st.markdown(item["summary"])
        if item.get("key_points"):
            with st.expander("핵심 포인트", expanded=True):
                st.markdown(item["key_points"])
        if item.get("newsletter_candidate"):
            with st.expander("뉴스레터 후보 문장"):
                st.markdown(item["newsletter_candidate"])

        bc1, bc2 = st.columns(2)
        with bc1:
            if st.button("승인", type="primary", width="stretch", key="review_approve"):
                ok, msg = approve_review(item["filename"])
                st.success(msg) if ok else st.warning(msg)
                st.rerun()
        with bc2:
            if st.button("반려", width="stretch", key="review_reject"):
                ok, msg = reject_review(item["filename"])
                st.success(msg) if ok else st.warning(msg)
                st.rerun()


def render_newsletter_tab() -> None:
    st.header("📰 뉴스레터")

    approved = list_approved_items()
    approved.sort(key=lambda x: x["importance_score"], reverse=True)
    radar_path = get_ietf_radar_path()
    draft_files = list_newsletter_files()
    published_files = list_published_newsletter_files()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Approved", len(approved))
    m2.metric("IETF Radar", "✅" if radar_path.is_file() else "—")
    m3.metric("Draft", len(draft_files))
    m4.metric("Published", len(published_files))

    mode = st.radio(
        "뉴스레터 작업",
        ["Draft 생성", "Draft 검토", "발행본"],
        horizontal=True,
        key="nl_work_mode",
    )

    if mode == "Draft 생성":
        if not approved and not radar_path.is_file():
            st.warning("승인 기사와 IETF Radar가 없습니다. **기사 검토** 후 다시 확인하세요.")
            return

        st.markdown("#### 승인 기사 요약")
        if approved:
            by_cat: dict[str, list] = {}
            for item in approved:
                by_cat.setdefault(item["category"], []).append(item)
            for cat in CATEGORIES:
                if cat not in by_cat:
                    continue
                st.markdown(f"**{cat}** · {len(by_cat[cat])}건")
                for item in sorted(by_cat[cat], key=lambda x: -x["importance_score"])[:3]:
                    st.caption(f"· {item['title'][:55]} ★{item['importance_score']}")
                if len(by_cat[cat]) > 3:
                    st.caption(f"… 외 {len(by_cat[cat]) - 3}건")
        else:
            st.caption("승인된 기사가 없습니다.")

        if radar_path.is_file():
            st.info("IETF Radar가 포함됩니다 (표준화 참고 섹션).")

        if st.button("Draft 생성", type="primary", key="nl_generate"):
            if not approved:
                st.warning("승인된 기사(03_approved)가 없습니다. **기사 검토** 탭에서 먼저 승인하세요.")
            else:
                result = run_orchestrator_workflow(
                    mode="draft",
                    compact_ui=True,
                    label="Draft 생성",
                )
                if result:
                    st.session_state.workflow_state = result
                st.rerun()

    elif mode == "Draft 검토":
        if not draft_files:
            st.info("Draft가 없습니다. **Draft 생성**에서 먼저 생성하세요.")
            return

        sel = st.selectbox(
            "Draft 파일",
            draft_files,
            format_func=lambda p: p.name,
            key="nl_draft_sel",
        )
        if sel:
            content = read_markdown(sel)
            meta, body = parse_frontmatter(content)
            display = body if body.strip() else content
            if len(display.strip()) < 200:
                st.warning(
                    "뉴스레터 파일은 생성됐지만 본문이 거의 없습니다. "
                    "03_approved 기사가 충분한지 확인 후 다시 생성하세요."
                )
            incl = meta.get("included_approved_files") or []
            if incl:
                st.caption(f"포함 승인 기사 {len(incl)}건 · 발행 시 used 폴더로 이동")
            st.markdown(display)
            st.checkbox(
                "발행 확정 — approved → used 이동 및 draft 삭제에 동의",
                key="nl_publish_confirm",
            )
            if st.button("발행 확정", type="primary", key="nl_publish"):
                if not st.session_state.get("nl_publish_confirm"):
                    st.warning("발행 전 확인 체크박스를 선택하세요.")
                else:
                    ok, msg = publish_newsletter(sel.name)
                    st.success(msg) if ok else st.warning(msg)
                    st.rerun()

    else:
        if not published_files:
            st.info("발행본이 없습니다. **Draft 검토**에서 발행 확정하세요.")
            return

        pub_sel = st.selectbox(
            "발행본",
            published_files,
            format_func=lambda p: p.name,
            key="nl_pub_sel",
        )
        if pub_sel:
            meta, body = parse_frontmatter(read_markdown(pub_sel))
            if meta.get("published_at"):
                st.caption(f"발행: {meta['published_at']} · issue: {meta.get('issue_date', '—')}")
            st.markdown(body if body else read_markdown(pub_sel))


def render_archive_tab() -> None:
    st.header("📦 발행 아카이브")
    st.caption(
        "`05_newsletter_archive/{issue_date}/` — 호별 영구 보관 · "
        "`06_newsletter_used/` — 발행에 사용된 승인 기사"
    )

    archive_files = list_archived_newsletter_files()
    used_files = list_used_article_files()

    synced, synced_paths = sync_published_to_archive()
    if synced:
        st.success(
            f"아카이브 **{synced}건** 자동 동기화됨: "
            + ", ".join(f"`{p}`" for p in synced_paths)
        )
        archive_files = list_archived_newsletter_files()

    c1, c2 = st.columns(2)
    c1.metric("Archive", len(archive_files))
    c2.metric("Used articles", len(used_files))

    if st.button("📦 Published → Archive 동기화", key="arch_sync"):
        n, paths = sync_published_to_archive()
        if n:
            st.success(f"{n}건 아카이브: " + ", ".join(f"`{p}`" for p in paths))
        else:
            st.info("동기화할 발행본이 없습니다 (이미 아카이브됨).")
        st.rerun()

    if archive_files:
        st.subheader("뉴스레터 아카이브")

        def _archive_label(p: Path) -> str:
            try:
                rel = p.relative_to(get_vault_path() / "05_newsletter_archive")
                return str(rel).replace("\\", "/")
            except ValueError:
                return p.name

        arch_sel = st.selectbox(
            "아카이브 호",
            archive_files,
            format_func=_archive_label,
            key="arch_sel",
        )
        if arch_sel:
            meta, body = parse_frontmatter(read_markdown(arch_sel))
            cols = st.columns(3)
            cols[0].caption(f"issue: {meta.get('issue_date', '—')}")
            cols[1].caption(f"발행: {meta.get('published_at', '—')}")
            cols[2].caption(f"아카이브: {meta.get('archived_at', '—')}")
            if meta.get("source_published"):
                st.caption(f"출처: `{meta['source_published']}`")
            st.markdown(body if body else read_markdown(arch_sel))
    else:
        st.info(
            "아카이브가 비어 있습니다. 뉴스레터 **발행 확정** 시 "
            "`05_newsletter_archive/`에 자동 저장됩니다."
        )

    if used_files:
        st.subheader("Used — 발행에 사용된 승인 기사")

        def _used_label(p: Path) -> str:
            try:
                rel = p.relative_to(get_vault_path() / "06_newsletter_used")
                return str(rel).replace("\\", "/")
            except ValueError:
                return p.name

        used_sel = st.selectbox(
            "Used 기사",
            used_files,
            format_func=_used_label,
            key="used_sel",
        )
        if used_sel:
            meta, body = parse_frontmatter(read_markdown(used_sel))
            st.caption(
                f"issue: {meta.get('used_in_issue', '—')} · "
                f"발행: {meta.get('published_at', '—')}"
            )
            sections = parse_review_body(body) if "# 요약" in body else {}
            if sections.get("요약"):
                st.markdown(sections["요약"])
            elif body:
                st.markdown(body[:1500])


def main() -> None:
    st.set_page_config(
        page_title="IP Network Newsletter Agent",
        page_icon="🛰️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    inject_theme_css()

    if "last_run_label" not in st.session_state:
        st.session_state.last_run_label = "—"
    if "show_collect_tool_status" not in st.session_state:
        st.session_state.show_collect_tool_status = False
    if "collect_tool_log_offset" not in st.session_state:
        st.session_state.collect_tool_log_offset = 0

    vault = get_vault_path()
    stats = vault_stats(vault)

    with st.sidebar:
        render_sidebar(stats, vault)
    tab_run, tab_review, tab_nl, tab_arch, tab_ops = st.tabs([
        "▶ 실행",
        "📋 기사 검토",
        "📰 뉴스레터",
        "📦 아카이브",
        "⚙️ 운영콘솔",
    ])

    with tab_run:
        render_run_tab()
    with tab_review:
        render_article_review_tab()
    with tab_nl:
        render_newsletter_tab()
    with tab_arch:
        render_archive_tab()
    with tab_ops:
        render_ops_console_tab()


if __name__ == "__main__":
    import sys
    from pathlib import Path

    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        _has_ctx = get_script_run_ctx() is not None
    except Exception:
        _has_ctx = False

    if not _has_ctx:
        app_path = Path(__file__).resolve()
        print(
            "[INFO] Streamlit 앱은 `python streamlit_app.py`가 아니라 "
            f"`streamlit run {app_path.name}` 으로 실행해야 합니다.\n"
            "[INFO] streamlit run 으로 자동 재실행합니다…"
        )
        raise SystemExit(
            __import__("subprocess").call(
                [sys.executable, "-m", "streamlit", "run", str(app_path), *sys.argv[1:]]
            )
        )

    main()
