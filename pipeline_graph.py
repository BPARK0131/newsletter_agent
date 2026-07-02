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
