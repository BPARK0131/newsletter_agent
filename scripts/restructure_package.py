"""One-shot: flat root .py → ipn_agent/ package. Run from project root."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MOVES: dict[str, str] = {
    "tool_logger.py": "ipn_agent/core/tool_logger.py",
    "mvp_limits.py": "ipn_agent/core/mvp_limits.py",
    "text_normalize.py": "ipn_agent/core/text_normalize.py",
    "article_registry.py": "ipn_agent/registry/article.py",
    "published_registry.py": "ipn_agent/registry/published.py",
    "vault_utils.py": "ipn_agent/vault/utils.py",
    "reset_vault.py": "ipn_agent/vault/reset.py",
    "content_extract.py": "ipn_agent/collect/extract.py",
    "fetch_script.py": "ipn_agent/collect/fetch.py",
    "discovery_pipeline.py": "ipn_agent/collect/discovery.py",
    "review_script.py": "ipn_agent/review/runner.py",
    "review_metadata.py": "ipn_agent/review/metadata.py",
    "hitl_routing.py": "ipn_agent/review/hitl.py",
    "pipeline_articles.py": "ipn_agent/orchestrator/articles.py",
    "pipeline_hitl_apply.py": "ipn_agent/orchestrator/hitl_apply.py",
    "pipeline_logging.py": "ipn_agent/orchestrator/logging.py",
    "pipeline_state.py": "ipn_agent/orchestrator/legacy_state.py",
    "newsletter_workflow_state.py": "ipn_agent/orchestrator/state.py",
    "newsletter_orchestrator.py": "ipn_agent/orchestrator/workflow.py",
    "newsletter_editor.py": "ipn_agent/orchestrator/editor.py",
    "research_review_agent.py": "ipn_agent/orchestrator/research_agent.py",
    "newsletter_agent_skeleton.py": "ipn_agent/legacy/skeleton.py",
    "standards_radar_script.py": "ipn_agent/standards/radar.py",
    "streamlit_utils.py": "ipn_agent/ui/streamlit_utils.py",
}

IMPORT_REPLACEMENTS: list[tuple[str, str]] = [
    ("from newsletter_workflow_state import", "from ipn_agent.orchestrator.state import"),
    ("from newsletter_orchestrator import", "from ipn_agent.orchestrator.workflow import"),
    ("from newsletter_editor import", "from ipn_agent.orchestrator.editor import"),
    ("from research_review_agent import", "from ipn_agent.orchestrator.research_agent import"),
    ("from pipeline_hitl_apply import", "from ipn_agent.orchestrator.hitl_apply import"),
    ("from pipeline_articles import", "from ipn_agent.orchestrator.articles import"),
    ("from pipeline_logging import", "from ipn_agent.orchestrator.logging import"),
    ("from pipeline_state import", "from ipn_agent.orchestrator.legacy_state import"),
    ("from standards_radar_script import", "from ipn_agent.standards.radar import"),
    ("from discovery_pipeline import", "from ipn_agent.collect.discovery import"),
    ("from content_extract import", "from ipn_agent.collect.extract import"),
    ("from fetch_script import", "from ipn_agent.collect.fetch import"),
    ("from review_metadata import", "from ipn_agent.review.metadata import"),
    ("from review_script import", "from ipn_agent.review.runner import"),
    ("from hitl_routing import", "from ipn_agent.review.hitl import"),
    ("from published_registry import", "from ipn_agent.registry.published import"),
    ("from article_registry import", "from ipn_agent.registry.article import"),
    ("from streamlit_utils import", "from ipn_agent.ui.streamlit_utils import"),
    ("from vault_utils import", "from ipn_agent.vault.utils import"),
    ("from text_normalize import", "from ipn_agent.core.text_normalize import"),
    ("from mvp_limits import", "from ipn_agent.core.mvp_limits import"),
    ("from tool_logger import", "from ipn_agent.core.tool_logger import"),
]

PROJECT_DIR_PATTERNS = [
    re.compile(r"^PROJECT_DIR\s*=\s*Path\(__file__\)\.resolve\(\)\.parent\s*$", re.M),
    re.compile(r"^PROJECT_DIR\s*=\s*Path\(__file__\)\.resolve\(\)\.parent\s*#.*$", re.M),
]

WRAPPER_TEMPLATE = '''\
"""CLI wrapper — implementation in `{module}`."""
import runpy

if __name__ == "__main__":
    runpy.run_module("{module}", run_name="__main__")
'''

CLI_WRAPPERS: dict[str, str] = {
    "fetch_script.py": "ipn_agent.collect.fetch",
    "review_script.py": "ipn_agent.review.runner",
    "standards_radar_script.py": "ipn_agent.standards.radar",
    "newsletter_orchestrator.py": "ipn_agent.orchestrator.workflow",
    "research_review_agent.py": "ipn_agent.orchestrator.research_agent",
    "reset_vault.py": "ipn_agent.vault.reset",
    "newsletter_agent_skeleton.py": "ipn_agent.legacy.skeleton",
}

PIPELINE_GRAPH_WRAPPER = '''\
"""Deprecated wrapper — use newsletter_orchestrator.py instead."""
from ipn_agent.orchestrator.workflow import (  # noqa: F401
    NewsletterState,
    PipelineState,
    build_newsletter_workflow,
    build_pipeline_graph,
    newsletter_app,
    pipeline_app,
    run_newsletter_workflow,
    run_pipeline,
)

if __name__ == "__main__":
    import runpy
    runpy.run_module("ipn_agent.orchestrator.workflow", run_name="__main__")
'''

INIT_FILES = [
    "ipn_agent/core/__init__.py",
    "ipn_agent/registry/__init__.py",
    "ipn_agent/vault/__init__.py",
    "ipn_agent/collect/__init__.py",
    "ipn_agent/review/__init__.py",
    "ipn_agent/orchestrator/__init__.py",
    "ipn_agent/standards/__init__.py",
    "ipn_agent/ui/__init__.py",
    "ipn_agent/legacy/__init__.py",
]


def transform_content(text: str, *, inject_paths: bool) -> str:
    for old, new in IMPORT_REPLACEMENTS:
        text = text.replace(old, new)
    if inject_paths:
        for pat in PROJECT_DIR_PATTERNS:
            text = pat.sub("", text)
        if "from ipn_agent.paths import PROJECT_DIR" not in text:
            # insert after future imports / first block
            lines = text.splitlines(keepends=True)
            insert_at = 0
            for i, line in enumerate(lines):
                if line.startswith("from __future__"):
                    insert_at = i + 1
                elif insert_at and line.strip() and not line.startswith("#"):
                    break
                elif not line.startswith("from __future__") and line.strip() and not line.startswith('"""'):
                    insert_at = i
                    break
            lines.insert(insert_at, "from ipn_agent.paths import PROJECT_DIR\n")
            if insert_at > 0 and lines[insert_at - 1].strip():
                pass
            text = "".join(lines)
    return text


def main() -> None:
    for init_path in INIT_FILES:
        p = ROOT / init_path
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            p.write_text('"""Package."""\n', encoding="utf-8")

    for src_name, dest_rel in MOVES.items():
        src = ROOT / src_name
        if not src.is_file():
            print(f"SKIP missing {src_name}")
            continue
        dest = ROOT / dest_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        content = src.read_text(encoding="utf-8")
        needs_paths = src_name in {
            "tool_logger.py", "vault_utils.py", "streamlit_utils.py",
            "pipeline_logging.py", "research_review_agent.py",
        }
        content = transform_content(content, inject_paths=needs_paths)
        dest.write_text(content, encoding="utf-8")
        src.unlink()
        print(f"MOVED {src_name} -> {dest_rel}")

    for wrapper_name, module in CLI_WRAPPERS.items():
        (ROOT / wrapper_name).write_text(
            WRAPPER_TEMPLATE.format(module=module),
            encoding="utf-8",
        )
        print(f"WRAPPER {wrapper_name}")

    (ROOT / "pipeline_graph.py").write_text(PIPELINE_GRAPH_WRAPPER, encoding="utf-8")
    print("WRAPPER pipeline_graph.py")

    print("DONE")


if __name__ == "__main__":
    main()
