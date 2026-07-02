"""
MVP 시연용 수집 상한 — 환경변수
미설정 시 제한 없음 (sources.yaml / 전체 처리 유지)
"""

from __future__ import annotations

import os


def _parse_positive_int(env_name: str) -> int | None:
    raw = os.environ.get(env_name, "").strip()
    if not raw:
        return None
    try:
        val = int(raw)
        return val if val > 0 else None
    except ValueError:
        return None


def mvp_max_articles_per_source() -> int | None:
    """소스당 fetch 상한 (sources.yaml max_articles_per_run 과 min 적용)."""
    return _parse_positive_int("MVP_MAX_ARTICLES_PER_SOURCE")


def effective_max_articles_per_source(src: dict) -> int:
    base = int(src.get("max_articles_per_run", 5))
    cap = mvp_max_articles_per_source()
    if cap is not None:
        return min(base, cap)
    return base


def apply_mvp_source_caps(src: dict) -> dict:
    """fetch용 소스 dict에 MVP 상한 적용."""
    cap = mvp_max_articles_per_source()
    if cap is None:
        return src
    out = {**src, "max_articles_per_run": effective_max_articles_per_source(src)}
    if "max_lookup_results" in out:
        out["max_lookup_results"] = min(int(out["max_lookup_results"]), cap)
    return out


def mvp_limits_summary() -> str:
    parts: list[str] = []
    if (n := mvp_max_articles_per_source()):
        parts.append(f"소스당 수집 ≤{n}")
    return " · ".join(parts)
