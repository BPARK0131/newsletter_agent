"""뉴스레터 Editor 핵심 로직 — Orchestrator editor node 및 legacy CLI에서 공유."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ipn_agent.legacy.skeleton import NewsletterOutput


@dataclass
class EditorContext:
    vault_path: str
    raw_articles: list[dict]
    approved_paths: list[str]
    fallback_used: bool = False


@dataclass
class DraftResult:
    output: NewsletterOutput
    draft_path: str
    quality_ok: bool
    quality_notes: list[str] = field(default_factory=list)
    analyzed_count: int = 0


def prepare_newsletter_context(
    vault_path: str,
    approved_rel_paths: list[str] | None = None,
    *,
    load_all_approved: bool = False,
) -> EditorContext | None:
    from ipn_agent.legacy.skeleton import (
        _load_approved_from_rel_paths,
        obsidian_loader_node,
    )

    paths = list(approved_rel_paths or [])
    fallback_used = False

    if load_all_approved or not paths:
        loader_out = obsidian_loader_node({"vault_path": vault_path})
        raw = loader_out.get("raw_articles") or []
        fallback_used = bool(loader_out.get("fallback_used"))
    else:
        raw = _load_approved_from_rel_paths(vault_path, paths)

    if not raw:
        return None

    return EditorContext(
        vault_path=vault_path,
        raw_articles=raw,
        approved_paths=paths,
        fallback_used=fallback_used,
    )


def generate_newsletter_draft(ctx: EditorContext) -> dict[str, Any]:
    from ipn_agent.legacy.skeleton import (
        analysis_node,
        editor_node,
        hitl_node,
        standards_linker_node,
    )

    state: dict[str, Any] = {
        "messages": [],
        "sources": [],
        "vault_path": ctx.vault_path,
        "raw_articles": ctx.raw_articles,
        "fallback_used": ctx.fallback_used,
        "analyzed_articles": [],
        "bias_count": 0,
        "newsletter": {},
        "attempt": 0,
    }
    for fn in (analysis_node, standards_linker_node, hitl_node, editor_node):
        state.update(fn(state))
    return {
        "newsletter": state.get("newsletter") or {},
        "analyzed_count": len(state.get("analyzed_articles") or []),
        "fallback_used": ctx.fallback_used,
    }


def refine_newsletter_draft(
    newsletter: dict[str, Any],
    *,
    vault_path: str = "",
) -> DraftResult | None:
    from ipn_agent.legacy.skeleton import NewsletterOutput

    if not newsletter:
        return None

    output = NewsletterOutput(**newsletter)
    notes: list[str] = []
    quality_ok = True

    section_articles = sum(len(v) for v in (output.sections or {}).values())
    if section_articles == 0:
        quality_ok = False
        notes.append("뉴스레터 섹션에 포함된 기사 0건")
    if output.review_required:
        notes.append(f"편향/품질 검토 필요 {len(output.review_required)}건")
    if output.fallback_used:
        notes.append("fallback 샘플 데이터 사용")

    draft_path = f"04_newsletter/draft/{output.date}-newsletter.md"
    if vault_path:
        full = Path(vault_path) / draft_path
        if not full.is_file():
            quality_ok = False
            notes.append(f"draft 파일 미생성: {draft_path}")

    return DraftResult(
        output=output,
        draft_path=draft_path,
        quality_ok=quality_ok,
        quality_notes=notes,
        analyzed_count=output.total_articles,
    )


def run_editor_for_paths(
    approved_rel_paths: list[str],
    *,
    run_id: str = "",
    force: bool = False,
    load_all_approved: bool = False,
) -> DraftResult | None:
    vault_path = os.environ.get("OBSIDIAN_VAULT_PATH", "")
    if not vault_path:
        print("[ERROR] OBSIDIAN_VAULT_PATH 미설정")
        return None
    if not approved_rel_paths and not force and not load_all_approved:
        print("[WARN] draft 대상 approved 경로 없음")
        return None

    ctx = prepare_newsletter_context(
        vault_path,
        approved_rel_paths,
        load_all_approved=load_all_approved,
    )
    if ctx is None:
        print("[WARN] Editor 컨텍스트 준비 실패 (기사 0건)")
        return None

    gen = generate_newsletter_draft(ctx)
    result = refine_newsletter_draft(gen["newsletter"], vault_path=vault_path)
    if result and run_id:
        try:
            from ipn_agent.orchestrator.logging import log_event
            log_event(
                run_id, "editor_generate", "done",
                extra={"articles": len(ctx.raw_articles), "quality_ok": result.quality_ok},
            )
        except Exception:
            pass
    return result
