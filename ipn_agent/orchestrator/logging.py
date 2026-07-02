"""Pipeline run 로그 — state.json + events.jsonl + llm_usage.jsonl."""

from __future__ import annotations
from ipn_agent.paths import PROJECT_DIR

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def run_output_dir(run_id: str) -> Path:
    d = PROJECT_DIR / "output" / "pipeline_runs" / run_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def log_event(
    run_id: str,
    step: str,
    status: str,
    *,
    count: int | None = None,
    error: str | None = None,
    extra: dict | None = None,
) -> None:
    d = run_output_dir(run_id)
    entry: dict[str, Any] = {
        "run_id": run_id,
        "step": step,
        "status": status,
        "timestamp": _now_iso(),
    }
    if count is not None:
        entry["count"] = count
    if error:
        entry["error"] = error
    if extra:
        entry.update(extra)
    with (d / "events.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def log_llm_usage(
    run_id: str,
    step: str,
    article_id: str,
    *,
    model: str = "",
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    cached: bool = False,
) -> None:
    d = run_output_dir(run_id)
    total = None
    if input_tokens is not None and output_tokens is not None:
        total = input_tokens + output_tokens
    entry = {
        "run_id": run_id,
        "step": step,
        "article_id": article_id,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total,
        "cached": cached,
        "timestamp": _now_iso(),
    }
    with (d / "llm_usage.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def save_state_snapshot(run_id: str, state: dict) -> Path:
    d = run_output_dir(run_id)
    path = d / "state.json"
    # JSON-serializable only — articles list OK (no body text)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_latest_state() -> dict | None:
    root = PROJECT_DIR / "output" / "pipeline_runs"
    if not root.is_dir():
        return None
    runs = sorted(root.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    for run_dir in runs:
        sf = run_dir / "state.json"
        if sf.is_file():
            try:
                return json.loads(sf.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
    return None
