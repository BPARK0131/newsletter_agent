"""
Collect & Analyze Orchestrator
========================================================
순차 실행: fetch → expansion search → IETF Radar → review → HITL Queue Ready

  python research_review_agent.py --sources apnic_blog,ripe_labs
  python research_review_agent.py   # sources.yaml enabled 전체
"""

from __future__ import annotations

from ipn_agent.paths import PROJECT_DIR, ensure_vault_path_env
from ipn_agent.vault.utils import get_vault_path

import argparse
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
ensure_vault_path_env()

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


from ipn_agent.core.tool_logger import log_tool_event  # noqa: E402


def _run_step(script: str, extra_args: list[str] | None = None) -> int:
    cmd = [sys.executable, "-u", str(PROJECT_DIR / script)] + (extra_args or [])
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    print(f"\n{'=' * 60}\n[STEP] {' '.join(cmd)}\n{'=' * 60}")
    result = subprocess.run(cmd, cwd=str(PROJECT_DIR), env=env)
    return result.returncode


def load_enabled_source_ids() -> list[str]:
    import yaml

    config_path = PROJECT_DIR / "sources.yaml"
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    sections = [
        "regular_sources", "vendor_sources", "news_sources",
        "community_sources", "reference_sources",
    ]
    ids: list[str] = []
    for section in sections:
        for src in config.get(section, []):
            if src.get("enabled", False) and src.get("collect_by_default", True):
                ids.append(src["id"])
    return ids


def run(
    sources: list[str] | None = None,
    expansion_only: bool = False,
    expansion_categories: list[str] | None = None,
) -> int:
    vault = str(get_vault_path())

    if expansion_only:
        print("[INFO] Collect & Analyze — Expansion-only (Tavily 웹 검색)")
        rc = _run_step("fetch_script.py", ["--source", "ietf_datatracker"])
        if rc != 0:
            print(f"[WARN] fetch ietf_datatracker 실패 (exit {rc}) — 계속 진행")
    else:
        selected = sources if sources is not None else load_enabled_source_ids()
        if not selected:
            print("[ERROR] 실행할 소스가 없습니다. (--expansion-only 또는 --sources 지정)")
            return 1
        print(f"[INFO] Collect & Analyze 시작 | 소스: {', '.join(selected)}")

        fetch_ids = [s for s in selected if s != "ietf_datatracker"]
        if "ietf_datatracker" not in fetch_ids:
            fetch_ids.append("ietf_datatracker")

        fetch_total = len(fetch_ids)
        print(f"[FETCH PROGRESS] 0/{fetch_total} | — | RSS/API 수집 시작", flush=True)
        for idx, sid in enumerate(fetch_ids, start=1):
            print(f"[FETCH PROGRESS] {idx}/{fetch_total} | {sid} | 시작", flush=True)
            rc = _run_step("fetch_script.py", ["--source", sid])
            if rc != 0:
                print(
                    f"[FETCH PROGRESS] {idx}/{fetch_total} | {sid} | 실패 (exit {rc})",
                    flush=True,
                )
                print(f"[WARN] fetch --source {sid} 실패 (exit {rc}) — 계속 진행")
            else:
                print(
                    f"[FETCH PROGRESS] {idx}/{fetch_total} | {sid} | 완료",
                    flush=True,
                )
        print(f"[FETCH PROGRESS] {fetch_total}/{fetch_total} | — | 전체 소스 fetch 완료", flush=True)

    # Tavily expansion search (선택 카테고리만; None이면 전체 카테고리)
    if expansion_categories is not None and not expansion_categories:
        print("\n[SKIP] expansion_search - 선택된 웹검색 카테고리 없음")
    else:
        print("[DISCOVERY PROGRESS] — | Tavily Discovery Search 시작", flush=True)
        args = ["--expansion-search"]
        if expansion_categories:
            args.extend(["--categories", ",".join(expansion_categories)])
        rc = _run_step("fetch_script.py", args)
        if rc != 0:
            print(f"[WARN] expansion-search 실패 (exit {rc}) — 계속 진행")

    # 2. IETF Radar (표준화 컨텍스트)
    rc = _run_step("standards_radar_script.py")
    if rc != 0:
        print(f"[ERROR] standards_radar_script 실패 (exit {rc})")
        return rc

    # 3. LLM Review → 02_review
    rc = _run_step("review_script.py")
    if rc != 0:
        print(f"[ERROR] review_script 실패 (exit {rc})")
        return rc

    log_tool_event(
        "orchestrator", "hitl_queue", "success",
        "HITL Queue 준비 완료",
    )
    print("\n[DONE] Collect → Expansion Search → IETF Radar → Review → HITL Queue Ready")
    print(f"[NEXT] Streamlit HITL Review 탭에서 {vault}/02_review/ 검수")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Collect & Analyze Orchestrator")
    parser.add_argument(
        "--sources",
        help="쉼표 구분 source_id (예: apnic_blog,ripe_labs). 미지정 시 enabled 전체",
    )
    parser.add_argument(
        "--expansion-only",
        action="store_true",
        help="RSS 소스 수집 생략, Tavily expansion search부터 실행",
    )
    args = parser.parse_args()
    src_list = (
        [s.strip() for s in args.sources.split(",") if s.strip()]
        if args.sources is not None
        else None
    )
    sys.exit(run(sources=src_list, expansion_only=args.expansion_only))
