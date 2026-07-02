"""CLI wrapper — implementation in `ipn_agent.orchestrator.research_agent`."""
import runpy

if __name__ == "__main__":
    runpy.run_module("ipn_agent.orchestrator.research_agent", run_name="__main__")
