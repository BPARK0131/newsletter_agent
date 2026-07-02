"""
Streamlit 앱 공통 유틸
"""

from __future__ import annotations

from ipn_agent.paths import PROJECT_DIR

import html
import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import streamlit as st

from ipn_agent.core.tool_logger import LOG_FILE
from ipn_agent.vault.utils import get_vault_path


STATUS_ICONS = {
    "running": "🔄",
    "success": "✅",
    "error": "❌",
    "skip": "⏭️",
}

STATUS_VERBS: dict[str, str] = {
    "running": "중",
    "success": "완료",
    "error": "실패",
    "skip": "건너뜀",
}

# technical label → 사용자 친화 설명
TOOL_FRIENDLY_NAMES: dict[str, str] = {
    "RSS Collector Tool": "RSS 피드 수집",
    "Tavily Search Tool": "Tavily 검색",
    "Tavily Expansion Search": "웹 확장 검색 (Discovery)",
    "Tavily Extract Tool": "기사 본문 추출",
    "Raw Markdown Writer Tool": "Markdown 변환",
    "Content Recollect Tool": "본문 재수집",
    "IETF Datatracker Tool": "IETF Datatracker 조회",
    "Standards Radar Tool": "IETF 표준 Radar",
    "LLM Review Tool": "LLM 1차 리뷰",
    "HITL Queue": "Human in the Loop 검토",
}

# Tool 단위 Aggregate 표시 순서/라벨
AGGREGATE_TOOL_STEPS: list[tuple[str, str]] = [
    ("rss_collector", "RSS Collector Tool"),
    ("tavily_search", "Tavily Search Tool"),
    ("expansion_search", "Tavily Expansion Search"),
    ("tavily_extract", "Tavily Extract Tool"),
    ("markdown_writer", "Raw Markdown Writer Tool"),
    ("content_recollect", "Content Recollect Tool"),
    ("ietf_datatracker_api", "IETF Datatracker Tool"),
    ("standards_radar", "Standards Radar Tool"),
    ("standards_writer", "Standards Radar Tool"),
    ("standards_filter", "Standards Radar Tool"),
    ("llm_reviewer", "LLM Review Tool"),
    ("review_writer", "LLM Review Tool"),
    ("hitl_queue", "HITL Queue"),
]

THEME_CARD_CLASS = "ipn-theme-card"
THEME_CARD_META_CLASS = "ipn-theme-card-meta"
DISCOVERY_PREVIEW_CLASS = "ipn-discovery-preview"
DISCOVERY_PREVIEW_MAX_CHARS = 5000


def format_discovery_body_preview(
    body: str,
    url: str = "",
    title: str = "",
    max_chars: int = DISCOVERY_PREVIEW_MAX_CHARS,
) -> tuple[str, str, bool]:
    """Discovery 본문 미리보기용 정규화.

    Returns:
        (plain_text, hint_message, is_thin) — is_thin=True면 URL만/짧은 스니펫.
    """
    if not body or not body.strip():
        hint = "본문이 비어 있습니다. **원문 URL**에서 내용을 확인하세요."
        fallback = title.strip() if title else ""
        return fallback, hint, True

    url_key = url.rstrip("/").lower().split("?")[0]
    lines_out: list[str] = []
    url_only_lines = 0

    for line in body.splitlines():
        s = line.strip()
        if not s:
            if lines_out and lines_out[-1] != "":
                lines_out.append("")
            continue
        if re.match(r"^!\[.*\]\(.*\)$", s):
            continue
        if re.match(r"^https?://\S+$", s, re.I):
            line_url = s.rstrip("/").lower().split("?")[0]
            if url_key and (line_url == url_key or line_url.startswith(url_key)):
                url_only_lines += 1
                continue
            if len(s) < 120:
                url_only_lines += 1
                continue
        s = re.sub(r"^#+\s*", "", s)
        s = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1", s)
        lines_out.append(s)

    text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines_out)).strip()
    alpha_chars = len(re.sub(r"[\s\W\d]", "", text, flags=re.UNICODE))
    is_thin = len(text) < 120 or alpha_chars < 80 or (
        url_only_lines > 0 and alpha_chars < 200
    )

    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + "\n\n… (미리보기 생략)"

    if is_thin:
        hint = (
            "추출된 본문이 짧거나 URL·메타데이터 위주입니다. "
            "아래 스니펫과 **원문 링크**를 함께 확인하세요."
        )
    elif url_only_lines:
        hint = "URL-only 줄은 제외하고 본문만 표시합니다."
    else:
        hint = ""

    return text, hint, is_thin


def render_discovery_preview(body: str, url: str = "", title: str = "") -> None:
    """통일된 스타일의 Discovery 본문 미리보기."""
    text, hint, is_thin = format_discovery_body_preview(body, url=url, title=title)
    if hint:
        st.caption(hint)
    char_note = f"{len(text.replace('… (미리보기 생략)', '').strip())}자"
    if is_thin:
        char_note += " · ⚠️ 본문 부족"
    st.caption(char_note)
    safe = html.escape(text) if text else "(표시할 본문 없음)"
    st.markdown(
        f'<div class="{DISCOVERY_PREVIEW_CLASS}">{safe}</div>',
        unsafe_allow_html=True,
    )


def inject_theme_css() -> None:
    """다크/라이트 테마 모두에서 읽히도록 Streamlit CSS 변수 기반 스타일 주입."""
    st.markdown(
        """
<style>
.ipn-theme-card {
  border: 1px solid rgba(128, 128, 128, 0.22);
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 12px;
  background: var(--secondary-background-color);
  color: var(--text-color);
}
.ipn-source-card {
  border: 1px solid rgba(128, 128, 128, 0.2);
  border-radius: 8px;
  padding: 10px 14px;
  margin-bottom: 10px;
  background: var(--secondary-background-color);
}
.ipn-progress-line {
  font-size: 0.92rem;
  line-height: 1.75;
  margin-bottom: 0.15rem;
}
.ipn-sidebar-metric [data-testid="stMetric"] {
  margin-bottom: 0.25rem;
}
.ipn-theme-card b,
.ipn-theme-card strong,
.ipn-theme-card code {
  color: var(--text-color);
}
.ipn-theme-card-meta {
  font-size: 0.85em;
  opacity: 0.88;
}
.ipn-discovery-preview {
  font-size: 0.875rem;
  line-height: 1.55;
  font-family: var(--font);
  color: var(--text-color);
  background: var(--background-color);
  border: 1px solid rgba(128, 128, 128, 0.3);
  border-radius: 6px;
  padding: 12px 14px;
  margin: 6px 0 10px 0;
  max-height: 480px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
}
.ipn-discovery-preview,
.ipn-discovery-preview * {
  font-size: 0.875rem !important;
  line-height: 1.55 !important;
}

/* ── 메인 네비게이션 탭 고정 (스크롤 시 상단 유지) ── */
section.main [data-testid="stTabs"] > div:first-child {
  position: sticky;
  top: 0;
  z-index: 999;
  background-color: var(--background-color);
  padding-top: 0.35rem;
  padding-bottom: 0.35rem;
  margin-bottom: 0.25rem;
  border-bottom: 1px solid rgba(128, 128, 128, 0.28);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

section.main [data-testid="stTabs"] [data-baseweb="tab-list"] {
  background-color: var(--background-color);
  gap: 0.25rem;
}

section.main [data-testid="stTabs"] [data-baseweb="tab"] {
  background-color: var(--background-color);
}

section.main [data-testid="stTabs"] [data-baseweb="tab-highlight"] {
  background-color: var(--primary-color);
}

/* ── Orchestrator 실행 상태(st.status) — 전체 폭 + 가독성 ── */
[data-testid="stStatusWidget"] {
  width: 100% !important;
  max-width: none !important;
}

[data-testid="stStatusWidget"] > div {
  width: 100% !important;
  max-width: none !important;
}

[data-testid="stStatusWidget"] [data-testid="stMarkdownContainer"],
[data-testid="stStatusWidget"] [data-testid="stMarkdownContainer"] p,
[data-testid="stStatusWidget"] [data-testid="stMarkdownContainer"] li {
  width: 100% !important;
  max-width: 100% !important;
  font-size: 0.95rem !important;
  line-height: 1.65 !important;
  word-break: break-word;
}

.ipn-tool-status-panel {
  width: 100%;
  border: 1px solid rgba(128, 128, 128, 0.25);
  border-radius: 8px;
  padding: 14px 18px;
  background: var(--secondary-background-color);
}

.ipn-tool-status-panel p {
  margin-bottom: 0.65rem !important;
}

.ipn-tool-status-panel p:last-child {
  margin-bottom: 0 !important;
}
</style>
""",
        unsafe_allow_html=True,
    )


_COUNT_KEYS = (
    "collected_count",
    "reviewed_count",
    "approval_pending_count",
    "needs_human_review_count",
    "rejected_count",
    "approved_count",
    "published_filtered_count",
)


def _vault_has_pipeline_data(vault: Path) -> bool:
    from ipn_agent.vault.utils import vault_stats
    stats = vault_stats(vault)
    return sum(
        stats.get(k, 0)
        for k in ("01_raw", "02_review", "03_approved", "99_rejected")
    ) > 0


def _cached_state_still_valid(cached: dict, vault: Path) -> bool:
    for article in cached.get("articles") or []:
        for key in ("raw_path", "review_path", "approved_path"):
            rel = article.get(key)
            if rel and (vault / rel).is_file():
                return True
    return False


def build_live_workflow_state(vault: Path) -> dict | None:
    """Vault 실시간 스캔 기반 Workflow 카운트 (원문 본문 미포함)."""
    from ipn_agent.orchestrator.articles import (
        merge_article_lists,
        scan_approved_articles,
        scan_raw_articles,
        scan_review_articles,
    )
    from ipn_agent.orchestrator.state import merge_counts_into_state
    from ipn_agent.vault.utils import vault_stats

    articles = merge_article_lists(
        scan_raw_articles(vault),
        scan_review_articles(vault),
        scan_approved_articles(vault),
    )
    if not _vault_has_pipeline_data(vault):
        return None

    stats = vault_stats(vault)
    state = merge_counts_into_state({
        "articles": articles,
        "vault_path": str(vault),
        "step_status": {},
        "run_id": "",
        "draft_path": None,
        "editor_quality_ok": None,
    })
    state["rejected_count"] = max(
        int(state.get("rejected_count") or 0),
        stats.get("99_rejected", 0),
    )
    return state


def resolve_workflow_display_state(vault: Path) -> dict | None:
    """UI 표시용 Workflow 상태 — vault 기준으로 stale run 스냅샷 무효화."""
    live = build_live_workflow_state(vault)
    if live is None:
        st.session_state.pop("workflow_state", None)
        st.session_state.pop("pipeline_state", None)
        return None

    cached = st.session_state.get("workflow_state") or st.session_state.get("pipeline_state")
    if cached is None:
        try:
            from ipn_agent.orchestrator.logging import load_latest_state
            cached = load_latest_state()
        except Exception:
            cached = None

    if cached and not _cached_state_still_valid(cached, vault):
        cached = None
        st.session_state.pop("workflow_state", None)
        st.session_state.pop("pipeline_state", None)

    if not cached:
        return live

    merged = {**cached, "articles": live.get("articles") or []}
    for key in _COUNT_KEYS:
        merged[key] = live.get(key, 0)
    return merged


__all__ = [
    "load_tool_logs",
    "load_tool_logs_since",
    "get_tool_friendly_name",
    "run_agent",
    "run_agent_script",
    "run_orchestrator_workflow",
    "render_recent_tools_brief",
    "render_tool_log_card",
    "render_aggregate_tool_status",
    "inject_theme_css",
    "resolve_workflow_display_state",
    "render_discovery_preview",
    "format_discovery_body_preview",
    "DISCOVERY_PREVIEW_CLASS",
    "THEME_CARD_CLASS",
    "THEME_CARD_META_CLASS",
    "STATUS_ICONS",
    "TOOL_FRIENDLY_NAMES",
    "PROJECT_DIR",
]


def load_tool_logs(limit: int = 100) -> list[dict]:
    if not LOG_FILE.is_file():
        return []
    lines = LOG_FILE.read_text(encoding="utf-8").strip().splitlines()
    entries: list[dict] = []
    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    entries.reverse()
    return entries


def _log_line_count() -> int:
    if not LOG_FILE.is_file():
        return 0
    return len(LOG_FILE.read_text(encoding="utf-8").strip().splitlines())


def _read_logs_since(line_offset: int) -> list[dict]:
    if not LOG_FILE.is_file():
        return []
    lines = LOG_FILE.read_text(encoding="utf-8").strip().splitlines()
    entries: list[dict] = []
    for line in lines[line_offset:]:
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def load_tool_logs_since(line_offset: int) -> list[dict]:
    """JSONL 특정 줄 이후 로그 (현재 세션 Collect 실행분만 조회용)."""
    return _read_logs_since(line_offset)


def get_tool_friendly_name(tool_id: str) -> str:
    """tool id → 사용자 친화 설명 (예: rss_collector → RSS 피드 수집)."""
    tool_to_label = {t: label for t, label in AGGREGATE_TOOL_STEPS}
    label = tool_to_label.get(tool_id, tool_id)
    return TOOL_FRIENDLY_NAMES.get(label, label)


def aggregate_tool_states(logs: list[dict]) -> dict[str, dict]:
    """Tool별 최신 상태 집계."""
    # label → latest entry
    label_latest: dict[str, dict] = {}
    tool_to_label = {t: label for t, label in AGGREGATE_TOOL_STEPS}

    for entry in logs:
        tool = entry.get("tool", "")
        label = tool_to_label.get(tool, tool)
        label_latest[label] = entry
    return label_latest


def format_tool_status_line(entry: dict, technical_label: str) -> str:
    """예: RSS 피드 수집 완료 (RSS Collector Tool) — 4건 수집 완료"""
    friendly = TOOL_FRIENDLY_NAMES.get(technical_label, technical_label)
    status = entry.get("status", "")
    verb = STATUS_VERBS.get(status, "")
    icon = STATUS_ICONS.get(status, "•")
    msg = entry.get("message", "")
    if len(msg) > 120:
        msg = msg[:117] + "…"
    count = entry.get("count")
    if count is not None and "개" not in msg:
        msg = f"{msg} ({count}개)"
    headline = f"{friendly} {verb}".strip() if verb else friendly
    return f"{icon} **{headline}** · `{technical_label}` — {msg}"


# 진행률 줄 → 강조할 Tool 라벨
_PROGRESS_TOOL_LABEL: dict[str, str] = {
    "FETCH": "RSS Collector Tool",
    "DISCOVERY": "Tavily Expansion Search",
}


def render_aggregate_tool_status(
    logs: list[dict],
    placeholder,
    progress: dict[str, Any] | None = None,
) -> None:
    """Tool 단위 Aggregate 상태 + Fetch/Discovery 진행률(활성 Tool 옆)."""
    states = aggregate_tool_states(logs)
    seen_labels: set[str] = set()
    lines: list[str] = []

    for _tool, label in AGGREGATE_TOOL_STEPS:
        if label in seen_labels:
            continue
        if label not in states:
            continue
        seen_labels.add(label)
        lines.append(format_tool_status_line(states[label], label))

    prog = progress or {}
    prog_text = (prog.get("text") or "").strip()
    prog_kind = (prog.get("kind") or "").upper()
    if prog_text:
        target = _PROGRESS_TOOL_LABEL.get(prog_kind)
        attached = False
        if target:
            for i, line in enumerate(lines):
                if f"({target})" in line:
                    badge = f" · **진행 {prog_text}**"
                    if badge not in lines[i]:
                        lines[i] = lines[i] + badge
                    attached = True
                    break
        if not attached:
            lines.insert(0, f"📊 **진행** — {prog_text}")

    if not lines:
        if prog_text:
            placeholder.markdown(f"📊 **진행** — {prog_text}\n\n_Tool 실행 로그 대기 중…_")
        else:
            placeholder.info("Tool 실행 로그 대기 중...")
    else:
        placeholder.markdown("\n\n".join(lines))


_PROGRESS_LINE_RE = re.compile(
    r"\[(FETCH|DISCOVERY) PROGRESS\]\s*(\d+)/(\d+)\s*\|\s*([^|]+?)\s*\|\s*(.+)",
    re.I,
)


def _apply_collect_progress(line: str, progress_state: dict[str, Any]) -> None:
    """stdout [FETCH/DISCOVERY PROGRESS] → progress_state 갱신 (status 위젯은 건드리지 않음)."""
    stripped = line.strip()
    if not stripped:
        return
    m = _PROGRESS_LINE_RE.search(stripped)
    if m:
        kind, cur, total, name, msg = m.groups()
        cur_i, total_i = int(cur), int(total)
        pct = cur_i / total_i if total_i > 0 else 0.0
        progress_state["kind"] = kind.upper()
        progress_state["text"] = f"{cur_i}/{total_i} · {name.strip()} · {msg.strip()}"
        progress_state["pct"] = min(max(pct, 0.0), 1.0)
        return
    if "[FETCH PROGRESS]" in stripped or "[DISCOVERY PROGRESS]" in stripped:
        progress_state["text"] = stripped.split("]", 1)[-1].strip().lstrip("|").strip()


def run_agent(command: list[str], label: str, timeout: int = 600) -> bool:
    env = os.environ.copy()
    env.setdefault("OBSIDIAN_VAULT_PATH", str(get_vault_path()))
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")

    with st.status(f"{label} 실행 중...", expanded=True) as status:
        st.caption(f"최대 {timeout // 60}분 대기 · 창을 닫지 마세요")
        try:
            result = subprocess.run(
                command,
                cwd=str(PROJECT_DIR),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                env=env,
            )
            output = (result.stdout or "") + (result.stderr or "")
            if output.strip():
                st.code(output.strip()[-5000:], language=None)
            if result.returncode == 0:
                status.update(label=f"{label} 완료", state="complete")
                st.success(f"{label} 실행 완료")
                return True
            status.update(label=f"{label} 실패 (exit {result.returncode})", state="error")
            st.error(f"{label} 실패 — exit code {result.returncode}")
            return False
        except subprocess.TimeoutExpired:
            status.update(label=f"{label} 타임아웃", state="error")
            st.error(f"실행 타임아웃 ({timeout}s).")
            return False
        except Exception as e:
            status.update(label=f"{label} 오류", state="error")
            st.error(str(e))
            return False


AGENT_TIMEOUTS: dict[str, int] = {
    "fetch_script.py": 1200,
    "review_script.py": 3600,
    "standards_radar_script.py": 300,
    "newsletter_orchestrator.py": 7200,
    "research_review_agent.py": 7200,
}


def run_agent_script(script_name: str, label: str) -> bool:
    script_path = PROJECT_DIR / script_name
    if not script_path.is_file():
        st.error(f"스크립트 없음: {script_name}")
        return False
    timeout = AGENT_TIMEOUTS.get(script_name, 600)
    return run_agent([sys.executable, str(script_path)], label, timeout=timeout)


def render_recent_tools_brief(logs: list[dict], limit: int = 5) -> None:
    """실행 탭용 Tool 요약 (경로·JSON 없음)."""
    if not logs:
        st.caption("아직 실행 기록이 없습니다.")
        return
    states = aggregate_tool_states(logs)
    seen: set[str] = set()
    shown = 0
    for _tool, label in AGGREGATE_TOOL_STEPS:
        if label in seen:
            continue
        seen.add(label)
        entry = states.get(label)
        if not entry or entry.get("status") not in ("success", "running", "error"):
            continue
        icon = STATUS_ICONS.get(entry.get("status", ""), "•")
        friendly = TOOL_FRIENDLY_NAMES.get(label, label)
        msg = entry.get("message", "")
        if len(msg) > 60:
            msg = msg[:57] + "…"
        count = entry.get("count")
        extra = f" · {count}건" if count is not None else ""
        st.markdown(f"{icon} **{friendly}**{extra} — {msg}")
        shown += 1
        if shown >= limit:
            break
    if shown == 0:
        st.caption("표시할 Tool 요약이 없습니다.")


# compact 실행 탭 — Tool 그룹 (진행 표시용)
_COMPACT_PIPELINE_GROUPS: list[tuple[list[str], str]] = [
    (["expansion_search"], "웹검색 확장"),
    (["ietf_datatracker_api"], "IETF Datatracker 조회"),
    (["standards_radar", "standards_writer", "standards_filter"], "IETF Radar"),
    (["tavily_extract", "markdown_writer"], "본문 추출 · Markdown 저장"),
    (["llm_reviewer", "review_writer"], "Review 생성"),
    (["hitl_queue"], "HITL 검토 큐"),
]


def _latest_entries_by_tool(logs: list[dict]) -> dict[str, dict]:
    latest: dict[str, dict] = {}
    for entry in logs:
        tool = entry.get("tool", "")
        if tool:
            latest[tool] = entry
    return latest


def _phase_status(tool_ids: list[str], latest: dict[str, dict]) -> str:
    seen: list[str] = []
    for tid in tool_ids:
        if tid in latest:
            seen.append(latest[tid].get("status", ""))
    if not seen:
        return "pending"
    if any(s == "error" for s in seen):
        return "error"
    if any(s == "running" for s in seen):
        return "running"
    if any(s in ("success", "skip") for s in seen):
        return "success"
    return "pending"


def _phase_summary_message(tool_ids: list[str], latest: dict[str, dict]) -> str:
    for tid in reversed(tool_ids):
        if tid in latest:
            msg = (latest[tid].get("message") or "").strip()
            count = latest[tid].get("count")
            if count is not None:
                return f"{count}건"
            if msg:
                return msg[:80]
    return ""


_DISCOVERY_CAT_LABELS: dict[str, str] = {
    "routing_ops": "Routing/Internet Operations",
    "backbone_backhaul": "Backbone/Backhaul",
    "datacenter_network": "DataCenter Network",
    "ip_security": "IP Security",
    "netdevops": "NetDevOps",
    "standards_architecture": "Standards/Architecture",
}


def _progress_states_by_target(logs: list[dict], tool: str) -> dict[str, dict]:
    states: dict[str, dict] = {}
    for entry in logs:
        if entry.get("tool") != tool:
            continue
        target = (entry.get("target") or "").strip()
        if target:
            states[target] = entry
    return states


def _discovery_display_name(cat_id: str) -> str:
    if cat_id == "—":
        return "Discovery"
    return _DISCOVERY_CAT_LABELS.get(cat_id, cat_id)


def _format_fetch_log_line(source_id: str, entry: dict, name_map: dict[str, str]) -> str:
    name = name_map.get(source_id, source_id)
    status = entry.get("status", "")
    if status == "error":
        msg = (entry.get("message") or "오류").strip()
        return f"❌ **{name}** · 수집 실패 · {msg[:60]}"
    count = entry.get("count")
    if count is not None:
        return f"✓ **{name}** · 수집 완료 · {count}건"
    msg = (entry.get("message") or "수집 완료").strip()
    return f"✓ **{name}** · {msg[:70]}"


def _format_discovery_log_line(cat_id: str, entry: dict) -> str:
    label = _discovery_display_name(cat_id)
    status = entry.get("status", "")
    count = entry.get("count")
    if status == "error":
        msg = (entry.get("message") or "오류").strip()
        return f"❌ **{label}** · {msg[:70]}"
    if count is not None:
        return f"✓ **{label}** · 완료 · {count}건 raw"
    msg = (entry.get("message") or "완료").strip()
    return f"✓ **{label}** · {msg[:70]}"


def render_compact_collect_progress(
    logs: list[dict],
    *,
    placeholder,
    progress_state: dict[str, Any] | None,
    source_name_map: dict[str, str] | None,
    source_ids: list[str] | None,
    expansion_category_ids: list[str] | None = None,
    expansion_only: bool = False,
) -> dict[str, Any]:
    """실행 탭 compact 진행 UI — FETCH/DISCOVERY PROGRESS 기반."""
    name_map = source_name_map or {}
    prog = progress_state or {}
    fetch_states = _progress_states_by_target(logs, "fetch_progress")
    discovery_states = _progress_states_by_target(logs, "discovery_progress")
    latest = _latest_entries_by_tool(logs)
    ordered = [] if expansion_only else list(source_ids or [])
    expansion_cats = list(expansion_category_ids or [])

    current_lines: list[str] = []
    log_lines: list[str] = []
    failed_sources: list[str] = []

    # ── 소스 수집 (FETCH PROGRESS) ──
    if not expansion_only and ordered:
        for sid in ordered:
            entry = fetch_states.get(sid)
            disp = name_map.get(sid, sid)
            if not entry:
                current_lines.append(f"· {disp} · 대기")
                continue
            st_val = entry.get("status", "")
            if st_val == "running":
                current_lines.append(f"→ **{disp}** · 수집 중...")
            elif st_val == "error":
                current_lines.append(f"❌ **{disp}** · 수집 오류")
                failed_sources.append(disp)
                log_lines.append(_format_fetch_log_line(sid, entry, name_map))
            elif st_val == "success":
                log_lines.append(_format_fetch_log_line(sid, entry, name_map))
            else:
                current_lines.append(f"· {disp} · 대기")

        fetch_summary = fetch_states.get("—")
        if fetch_summary and fetch_summary.get("status") == "success":
            msg = (fetch_summary.get("message") or "").strip()
            if msg:
                log_lines.append(f"✓ **전체 수집** · {msg.split('·', 1)[-1].strip()[:70]}")

    elif expansion_only and expansion_cats:
        labels = [_discovery_display_name(cid) for cid in expansion_cats[:3]]
        preview = ", ".join(labels)
        if len(expansion_cats) > 3:
            preview += f" … 외 {len(expansion_cats) - 3}개"
        current_lines.append(f"· **웹검색 Discovery** · {preview}")
    elif expansion_only:
        current_lines.append("· **Tavily Discovery** · 웹검색만 실행")

    # ── Discovery (DISCOVERY PROGRESS) ──
    discovery_cats = [
        cid for cid in _DISCOVERY_CAT_LABELS
        if cid in discovery_states
    ]
    discovery_running = [
        cid for cid in discovery_cats
        if discovery_states[cid].get("status") == "running"
    ]
    discovery_active = discovery_running[-1] if discovery_running else None

    if discovery_active:
        current_lines.append(
            f"→ **{_discovery_display_name(discovery_active)}** · Discovery 검색 중..."
        )
    elif discovery_states:
        latest_disc = None
        for entry in logs:
            if entry.get("tool") == "discovery_progress":
                latest_disc = entry
        if latest_disc and latest_disc.get("status") == "running":
            target = (latest_disc.get("target") or "—").strip()
            msg = (latest_disc.get("message") or "").strip()
            label = _discovery_display_name(target)
            current_lines.append(f"→ **{label}** · {msg.split('·', 1)[-1].strip()[:60]}")

    for cat_id in discovery_cats:
        entry = discovery_states[cat_id]
        if entry.get("status") == "success":
            log_lines.append(_format_discovery_log_line(cat_id, entry))

    disc_summary = discovery_states.get("—")
    if disc_summary and disc_summary.get("status") == "success":
        msg = (disc_summary.get("message") or "").strip()
        if msg:
            log_lines.append(f"✓ **Discovery** · {msg.split('·', 1)[-1].strip()[:70]}")

    # ── Review / Radar (후반 파이프라인) ──
    review_phase = _phase_status(["llm_reviewer", "review_writer"], latest)
    if review_phase == "running":
        current_lines.append("→ **Review 생성** · 실행 중...")
    elif review_phase == "success":
        log_lines.append("✓ **Review 생성** · 완료")
    elif review_phase == "error":
        log_lines.append("❌ **Review 생성** · 일부 저장 실패")

    prog_kind = (prog.get("kind") or "").upper()
    prog_text = (prog.get("text") or "").strip()
    if prog_text and prog_kind in ("FETCH", "DISCOVERY"):
        current_lines.append(f"· 진행 · {prog_text}")

    parts: list[str] = ["**현재 작업**"]
    if current_lines:
        parts.extend(current_lines)
    else:
        parts.append("· 파이프라인 준비 중...")

    parts.append("")
    parts.append("**진행 로그**")
    if log_lines:
        parts.extend(log_lines)
    else:
        parts.append("_아직 완료된 단계가 없습니다._")

    placeholder.markdown("\n\n".join(parts))

    fetch_done = (
        expansion_only
        or not ordered
        or all(fetch_states.get(s, {}).get("status") in ("success", "error") for s in ordered)
    )
    discovery_done = (
        not expansion_cats
        or _phase_status(["expansion_search"], latest) in ("success", "error", "skip")
    )

    return {
        "failed_sources": failed_sources,
        "fetch_done": fetch_done,
        "rss_done": fetch_done,  # 하위 호환
        "review_done": review_phase == "success",
        "expansion_done": discovery_done,
    }


def build_compact_run_completion_summary(
    logs: list[dict],
    *,
    source_ids: list[str] | None,
    expansion_category_ids: list[str] | None = None,
    source_name_map: dict[str, str] | None,
    result: dict | None,
    progress_info: dict[str, Any],
    expansion_only: bool,
    run_label: str,
) -> dict[str, Any]:
    """실행 완료 후 실행 탭 요약용."""
    name_map = source_name_map or {}
    selected_count = len(source_ids or []) + len(expansion_category_ids or [])
    failed = list(progress_info.get("failed_sources") or [])
    errors = list((result or {}).get("errors") or [])

    return {
        "run_label": run_label,
        "selected_count": selected_count,
        "expansion_only": expansion_only,
        "expansion_selected": bool(expansion_category_ids),
        "failed_sources": failed,
        "errors": errors,
        "raw_ok": progress_info.get("fetch_done", progress_info.get("rss_done", False))
            or expansion_only
            or selected_count == 0,
        "review_ok": progress_info.get("review_done", False),
        "expansion_ok": progress_info.get("expansion_done", False),
    }


def render_compact_completion_block(summary: dict[str, Any]) -> None:
    """st.status 내부 — 실행 완료 요약."""
    st.markdown("---")
    st.markdown(f"**{summary.get('run_label', '실행')} 완료**")
    if summary.get("expansion_only"):
        st.markdown("- 수집 모드: 웹검색 Discovery만")
    else:
        st.markdown(f"- 선택 항목: **{summary.get('selected_count', 0)}**개 (RSS/API + 웹검색)")
    st.markdown(f"- Raw 수집: {'완료' if summary.get('raw_ok') else '확인 필요'}")
    if summary.get("expansion_selected"):
        st.markdown(f"- 웹검색 Discovery: {'완료' if summary.get('expansion_ok') else '미실행/확인 필요'}")
    st.markdown(f"- Review 생성: {'완료' if summary.get('review_ok') else '확인 필요'}")
    st.markdown("- HITL 검토 큐: **기사 검토** 탭에서 확인")
    failed = summary.get("failed_sources") or []
    if failed:
        st.markdown(f"- 실패 소스: {', '.join(failed)}")
    else:
        st.markdown("- 실패 소스: 없음")
    if summary.get("errors"):
        st.warning(str(summary["errors"][-1])[:200])


def run_orchestrator_workflow(
    *,
    mode: Literal["collect", "draft", "full"],
    source_ids: list[str] | None = None,
    expansion_category_ids: list[str] | None = None,
    expansion_only: bool = False,
    label: str | None = None,
    compact_ui: bool = False,
    source_name_map: dict[str, str] | None = None,
) -> dict | None:
    """Newsletter Orchestrator 실행 + Tool 로그 (compact_ui=True면 실행 탭용 간단 표시)."""
    from ipn_agent.orchestrator.workflow import run_newsletter_workflow

    run_label = label or {
        "collect": "Orchestrator · 수집",
        "draft": "Orchestrator · Draft",
        "full": "Orchestrator · 전체",
    }[mode]

    log_start = _log_line_count()
    st.session_state.show_collect_tool_status = True
    st.session_state.collect_tool_log_offset = log_start
    progress_state: dict[str, Any] = {"text": "", "kind": "", "pct": 0.0}
    result_holder: dict[str, Any] = {"result": None, "error": None}
    progress_info: dict[str, Any] = {}

    def _worker() -> None:
        try:
            result_holder["result"] = run_newsletter_workflow(
                mode=mode,
                source_ids=source_ids,
                expansion_category_ids=expansion_category_ids,
                expansion_only=expansion_only,
            )
        except Exception as exc:
            result_holder["error"] = exc

    timeout_sec = AGENT_TIMEOUTS["research_review_agent.py"]
    mode_caption = {
        "collect": "수집 → Discovery → Radar → Review → HITL Queue",
        "draft": "approved → draft 생성",
        "full": "수집 ~ draft 전체 파이프라인",
    }[mode]

    with st.status(f"{run_label} 실행 중...", expanded=True) as status:
        compact_ph = None
        if compact_ui:
            if mode in ("collect", "full"):
                preview_parts: list[str] = []
                if source_ids:
                    names = [source_name_map.get(s, s) for s in source_ids]
                    preview_parts.append(", ".join(names[:4]))
                    if len(source_ids) > 4:
                        preview_parts[-1] += f" … 외 {len(source_ids) - 4}개"
                if expansion_category_ids:
                    cat_names = [
                        _discovery_display_name(cid) for cid in expansion_category_ids[:3]
                    ]
                    cat_preview = ", ".join(cat_names)
                    if len(expansion_category_ids) > 3:
                        cat_preview += f" … 외 {len(expansion_category_ids) - 3}개"
                    preview_parts.append(f"웹검색 {cat_preview}")
                if preview_parts:
                    total = len(source_ids or []) + len(expansion_category_ids or [])
                    st.caption(f"수집 대상 · {' · '.join(preview_parts)} ({total}개)")
                compact_ph = st.empty()
                render_compact_collect_progress(
                    [],
                    placeholder=compact_ph,
                    progress_state=progress_state,
                    source_name_map=source_name_map,
                    source_ids=source_ids,
                    expansion_category_ids=expansion_category_ids,
                    expansion_only=expansion_only,
                )
                with st.expander("파이프라인 단계 안내", expanded=False):
                    st.caption(
                        "소스 수집 → 웹검색 확장 → 품질 필터 → Review 생성 → 기사 검토 큐"
                    )
            elif mode == "draft":
                st.write("승인 기사를 확인하고 Draft를 생성합니다.")
            else:
                st.write("파이프라인을 실행합니다.")
        else:
            st.caption(f"{mode_caption} · 최대 {timeout_sec // 60}분")
            st.markdown("#### Tool 실행 상태")
            log_container = st.container(border=True)
            with log_container:
                log_placeholder = st.empty()
                progress_bar = st.progress(0.0)
            render_aggregate_tool_status([], log_placeholder, progress_state)

        worker = threading.Thread(target=_worker, daemon=True)
        worker.start()
        deadline = time.time() + timeout_sec

        while worker.is_alive():
            if time.time() > deadline:
                status.update(label=f"{run_label} 타임아웃", state="error")
                st.error(f"{run_label} 타임아웃 ({timeout_sec // 60}분)")
                return None

            if compact_ui and compact_ph is not None and mode in ("collect", "full"):
                new_logs = _read_logs_since(log_start)
                progress_info = render_compact_collect_progress(
                    new_logs,
                    placeholder=compact_ph,
                    progress_state=progress_state,
                    source_name_map=source_name_map,
                    source_ids=source_ids,
                    expansion_category_ids=expansion_category_ids,
                    expansion_only=expansion_only,
                )
            elif not compact_ui:
                new_logs = _read_logs_since(log_start)
                render_aggregate_tool_status(new_logs, log_placeholder, progress_state)
                if progress_state.get("pct"):
                    progress_bar.progress(progress_state["pct"])
            time.sleep(0.35)

        worker.join()
        new_logs = _read_logs_since(log_start)

        if compact_ui and compact_ph is not None and mode in ("collect", "full"):
            progress_info = render_compact_collect_progress(
                new_logs,
                placeholder=compact_ph,
                progress_state=progress_state,
                source_name_map=source_name_map,
                source_ids=source_ids,
                expansion_category_ids=expansion_category_ids,
                expansion_only=expansion_only,
            )
        elif not compact_ui:
            render_aggregate_tool_status(new_logs, log_placeholder, progress_state)

        if result_holder["error"]:
            status.update(label=f"{run_label} 오류", state="error")
            err_msg = str(result_holder["error"])
            if compact_ui and mode in ("collect", "full"):
                st.error(f"실행 중 오류 · {err_msg[:180]}")
            else:
                st.error(err_msg)
            return None

        result = result_holder["result"]
        if not compact_ui:
            progress_state["pct"] = 1.0
            progress_bar.progress(1.0)
            render_aggregate_tool_status(new_logs, log_placeholder, progress_state)

        st.session_state.last_run_label = run_label
        st.session_state.last_run_time = datetime.now().strftime("%H:%M:%S")

        if compact_ui and mode in ("collect", "full"):
            summary = build_compact_run_completion_summary(
                new_logs,
                source_ids=source_ids,
                expansion_category_ids=expansion_category_ids,
                source_name_map=source_name_map,
                result=result,
                progress_info=progress_info,
                expansion_only=expansion_only,
                run_label=run_label,
            )
            st.session_state.last_run_summary = summary
            render_compact_completion_block(summary)
            status.update(label=f"{run_label} 완료", state="complete")
        else:
            status.update(label=f"{run_label} 완료", state="complete")

        if mode == "collect":
            if compact_ui:
                pass  # completion block already shown
            else:
                st.success("✅ HITL Queue 준비 완료 — **기사 검토** 탭에서 검수하세요.")
        elif mode == "draft":
            if result.get("draft_path"):
                status.update(label=f"{run_label} 완료", state="complete")
                st.success(
                    f"Draft 생성 완료 · `{Path(result['draft_path']).name}` — "
                    "**Draft 검토**에서 확인하세요."
                )
            elif result.get("errors"):
                status.update(label=f"{run_label} 실패", state="error")
                err = result["errors"][-1]
                st.error(str(err.get("error", err)))
            else:
                status.update(label=f"{run_label} 실패", state="error")
                st.error(
                    "Draft가 생성되지 않았습니다. "
                    "승인 기사(03_approved)가 있는지, 기발행 registry에 막히지 않았는지 확인하세요."
                )

        return result


def render_tool_log_card(entry: dict) -> None:
    icon = STATUS_ICONS.get(entry.get("status", ""), "•")
    ts = entry.get("ts", "")
    agent = entry.get("agent", "")
    tool = entry.get("tool", "")
    target = entry.get("target", "")
    message = entry.get("message", "")
    count = entry.get("count")
    count_str = f" · count={count}" if count is not None else ""
    target_str = f" · `{target}`" if target else ""

    st.markdown(
        f"""<div class="{THEME_CARD_CLASS}">
  <div class="{THEME_CARD_META_CLASS}">{icon} <b>{ts}</b> · <b>{agent}</b> / <code>{tool}</code>{target_str}{count_str}</div>
  <div style="margin-top:4px;">{message}</div>
</div>""",
        unsafe_allow_html=True,
    )
