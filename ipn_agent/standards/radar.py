"""
표준화 레이더 생성 (IETF Datatracker 전용)
========================================================
역할:
  vault/01_raw/ietf_datatracker/ 의 표준 신호 MD를 읽어
  뉴스레터 하단용 "표준화 레이더" 섹션을 vault/04_newsletter/ 에 생성한다.

  IETF는 일반 기사 리뷰(review_script) 파이프라인과 분리된 reference 소스입니다.

실행:
  python standards_radar_script.py              # 레이더 MD 생성
  python standards_radar_script.py --dry-run    # 출력만 미리보기

전체 흐름:
  python fetch_script.py --source ietf_datatracker
  python standards_radar_script.py
  # → 04_newsletter/ietf_radar.md
"""

import argparse
import os
import re
import sys
import yaml
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

from ipn_agent.core.tool_logger import log_tool_event
from ipn_agent.paths import PROJECT_DIR, ensure_vault_path_env
from ipn_agent.vault.utils import get_vault_path

load_dotenv()
ensure_vault_path_env()

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass


IETF_RADAR_FILENAME = "ietf_radar.md"

# WG별 HITL/Newsletter 참고용 컨텍스트 (sources.yaml wg_radar와 병합)
WG_CONTEXT: dict[str, dict] = {
    "idr": {
        "label": "IDR / BGP",
        "categories": ["Routing/Internet Operations", "IP Security"],
        "keywords": ["BGP", "Route Leak", "BGP Hijack", "Routing Policy"],
    },
    "bess": {
        "label": "BESS / EVPN",
        "categories": ["DataCenter Network", "Backbone/Backhaul"],
        "keywords": ["EVPN", "VXLAN", "VPN"],
    },
    "lsr": {
        "label": "LSR / IGP",
        "categories": ["Routing/Internet Operations", "Backbone/Backhaul"],
        "keywords": ["IS-IS", "OSPF", "IGP", "Link State"],
    },
    "spring": {
        "label": "SPRING / Segment Routing",
        "categories": ["Backbone/Backhaul", "Transport/DCI"],
        "keywords": ["SR-MPLS", "SRv6", "Segment Routing"],
    },
    "grow": {
        "label": "GROW / Routing Ops",
        "categories": ["Routing/Internet Operations"],
        "keywords": ["BGP Operations", "Routing Security", "MANRS"],
    },
}


def parse_frontmatter(text: str) -> tuple[dict, str]:
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


def load_ietf_source_config() -> dict:
    config_path = PROJECT_DIR / "sources.yaml"
    if not config_path.is_file():
        return {}
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    for src in config.get("reference_sources", []):
        if src.get("id") == "ietf_datatracker":
            return src
    return {}


def load_ietf_signals(vault_path: Path) -> list[dict]:
    """01_raw/ietf_datatracker/*.md frontmatter 수집."""
    ietf_dir = vault_path / "01_raw" / "ietf_datatracker"
    if not ietf_dir.is_dir():
        return []

    signals: list[dict] = []
    for md_file in sorted(ietf_dir.glob("*.md")):
        try:
            meta, _ = parse_frontmatter(md_file.read_text(encoding="utf-8"))
            if not meta:
                continue
            meta["_file"] = md_file.name
            signals.append(meta)
        except Exception as e:
            print(f"  [WARN] 읽기 실패 {md_file.name}: {e}")
    return signals


def _parse_published_date(value: str) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    m = re.match(r"(\d{4}-\d{2}-\d{2})", text)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y-%m-%d")
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def filter_by_age(signals: list[dict], max_age_days: int) -> list[dict]:
    if max_age_days <= 0:
        return signals
    cutoff = datetime.now() - timedelta(days=max_age_days)
    filtered = []
    for sig in signals:
        pub = _parse_published_date(sig.get("published", ""))
        if pub is None or pub >= cutoff:
            filtered.append(sig)
    return filtered


def pick_latest_per_wg(signals: list[dict], wg_order: list[str]) -> dict[str, dict]:
    """WG별 최신 문서 1건."""
    by_wg: dict[str, dict] = {}
    for sig in sorted(signals, key=lambda s: s.get("published", ""), reverse=True):
        wg = str(sig.get("wg", "")).upper()
        if wg and wg not in by_wg:
            by_wg[wg] = sig
    # wg_filter 순서 유지
    ordered: dict[str, dict] = {}
    for wg in wg_order:
        key = wg.upper()
        if key in by_wg:
            ordered[key] = by_wg[key]
    return ordered


def build_radar_markdown(
    wg_docs: dict[str, dict],
    wg_radar: dict,
    today: str,
) -> str:
    lines = [
        "---",
        'title: "IETF Standardization Radar"',
        f"date: {today}",
        "section: standardization_radar",
        "source: ietf_datatracker",
        "status: context",
        "role: standards_context",
        "---",
        "",
        "# 📡 IETF Standardization Radar",
        "",
        "IETF Datatracker 기반 **표준화 컨텍스트**입니다. "
        "HITL Review에서 기사 중요도를 판단할 때 참고하고, "
        "뉴스레터 하단 **표준화 레이더** 섹션으로 활용합니다.",
        "",
        "> ⚠️ 일반 뉴스 기사가 아닙니다. 승인/반려 대상이 아닙니다.",
        "",
    ]

    for wg, sig in wg_docs.items():
        wg_key = wg.lower()
        radar = wg_radar.get(wg_key, wg_radar.get(wg, {}))
        ctx = WG_CONTEXT.get(wg_key, {})
        label = ctx.get("label", wg)
        categories = ctx.get("categories", [])
        keywords = ctx.get("keywords", [])
        meaning = radar.get("change_meaning", "표준화 진행 신호 추적")
        tech = radar.get("tech_area", sig.get("document_type", "—"))

        lines.append(f"## {label}")
        lines.append("")
        if categories:
            lines.append(f"- **연결 카테고리:** {', '.join(categories)}")
        if keywords:
            lines.append(f"- **주요 키워드:** {', '.join(keywords)}")
        lines.append(f"- **기술 영역:** {tech}")
        lines.append(f"- **의미:** {meaning}")
        lines.append("")

        title = sig.get("title", "untitled")
        url = sig.get("url", "")
        doc_name = sig.get("doc_name", "")
        pub = str(sig.get("published", ""))[:10]
        maturity = sig.get("maturity", "")
        maturity_label = {
            "published-rfc": "RFC",
            "wg-draft": "WG draft",
            "individual-draft": "individual draft",
        }.get(maturity, maturity or "document")

        lines.append(f"**최신 참고 문서:** {title} ({maturity_label}, {pub})")
        if doc_name:
            lines.append(f"- `{doc_name}`")
        if url:
            lines.append(f"- {url}")
        lines.append("")

    if not wg_docs:
        for wg_key in WG_CONTEXT:
            ctx = WG_CONTEXT[wg_key]
            radar = wg_radar.get(wg_key, {})
            lines.append(f"## {ctx.get('label', wg_key.upper())}")
            lines.append("")
            lines.append(f"- **연결 카테고리:** {', '.join(ctx.get('categories', []))}")
            lines.append(f"- **주요 키워드:** {', '.join(ctx.get('keywords', []))}")
            meaning = radar.get("change_meaning", "표준화 흐름 추적")
            lines.append(f"- **의미:** {meaning}")
            lines.append("")
        lines.extend([
            "_현재 수집된 IETF 표준 신호 없음. "
            "`fetch_script.py --source ietf_datatracker` 실행 후 다시 생성하세요._",
            "",
        ])

    lines.extend([
        "---",
        "",
        "## 표준화 레이더 요약표",
        "",
        "| WG | 기술 영역 | 변화 의미 |",
        "|---|---|---|",
    ])
    for wg, sig in wg_docs.items():
        wg_key = wg.lower()
        radar = wg_radar.get(wg_key, wg_radar.get(wg, {}))
        tech = radar.get("tech_area", sig.get("document_type", "—"))
        meaning = radar.get("change_meaning", "표준화 진행 신호 추적")
        ctx = WG_CONTEXT.get(wg_key, {})
        label = ctx.get("label", wg)
        lines.append(f"| {label} | {tech} | {meaning} |")

    return "\n".join(lines) + "\n"


def run(dry_run: bool = False) -> None:
    vault_path = str(get_vault_path())

    vault = Path(vault_path)
    ietf_cfg = load_ietf_source_config()
    wg_filter = ietf_cfg.get("wg_filter", ["idr", "bess", "lsr", "spring", "grow"])
    wg_radar = ietf_cfg.get("wg_radar", {})

    log_tool_event(
        "standards_radar", "ietf_datatracker_api", "running",
        "IETF Datatracker 신호 로드 중", target="01_raw/ietf_datatracker",
    )
    signals = load_ietf_signals(vault)
    log_tool_event(
        "standards_radar", "ietf_datatracker_api", "success",
        f"{len(signals)}건 신호 로드", target="01_raw/ietf_datatracker", count=len(signals),
    )

    max_age = ietf_cfg.get("max_article_age_days", 730)
    signals = filter_by_age(signals, max_age)
    wg_docs = pick_latest_per_wg(signals, wg_filter)
    log_tool_event(
        "standards_radar", "standards_filter", "success",
        f"WG 필터링 완료 — {len(wg_docs)}개 WG",
        target=",".join(wg_docs.keys()) or "none", count=len(wg_docs),
    )

    today = datetime.now().strftime("%Y-%m-%d")
    content = build_radar_markdown(wg_docs, wg_radar, today)

    out_dir = vault / "04_newsletter"
    out_file = out_dir / IETF_RADAR_FILENAME

    print(f"[INFO] IETF 신호 {len(signals)}건 | WG 대표 {len(wg_docs)}건")
    for wg, sig in wg_docs.items():
        print(f"  → [{wg}] {sig.get('title', '')[:55]}")

    if dry_run:
        print(f"\n[DRY-RUN] 저장 예정: 04_newsletter/{out_file.name}")
        print("\n" + content[:1200] + ("..." if len(content) > 1200 else ""))
        return

    log_tool_event(
        "standards_radar", "standards_writer", "running",
        f"레이더 Markdown 저장 중", target=out_file.name,
    )
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file.write_text(content, encoding="utf-8")
        log_tool_event(
            "standards_radar", "standards_writer", "success",
            f"저장 완료: {out_file.name}", target=out_file.name,
        )
        log_tool_event(
            "standards_radar", "standards_radar", "success",
            "Standards Radar Tool 수행 완료", target=IETF_RADAR_FILENAME,
        )
    except Exception as e:
        log_tool_event(
            "standards_radar", "standards_writer", "error",
            f"저장 실패: {e}", target=out_file.name,
        )
        raise

    print(f"\n[SAVED] 04_newsletter/{out_file.name}")
    print("[NEXT] 뉴스레터 편집 시 하단 '표준화 레이더' 섹션으로 병합하세요.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IETF 표준화 레이더 섹션 생성")
    parser.add_argument("--dry-run", action="store_true", help="저장 없이 미리보기")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
