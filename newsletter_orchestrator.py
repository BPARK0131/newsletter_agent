"""CLI wrapper — implementation in `ipn_agent.orchestrator.workflow`."""
import runpy

if __name__ == "__main__":
    runpy.run_module("ipn_agent.orchestrator.workflow", run_name="__main__")
