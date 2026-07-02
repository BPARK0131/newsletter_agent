"""
Agent Tool 실행 로그 — JSONL 저장
Streamlit Agent Console / Sidebar에서 조회
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ipn_agent.paths import PROJECT_DIR

LOG_DIR = PROJECT_DIR / "logs"
LOG_FILE = LOG_DIR / "tool_runs.jsonl"


def log_tool_event(
    agent: str,
    tool: str,
    status: str,
    message: str,
    target: str = "",
    count: int | None = None,
) -> None:
    """logs/tool_runs.jsonl에 Tool 실행 이벤트를 append한다."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    entry: dict = {
        "ts": datetime.now().strftime("%H:%M:%S"),
        "agent": agent,
        "tool": tool,
        "status": status,
        "message": message,
        "target": target,
    }
    if count is not None:
        entry["count"] = count
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
