"""CLI wrapper — implementation in `ipn_agent.review.runner`."""
import runpy

if __name__ == "__main__":
    runpy.run_module("ipn_agent.review.runner", run_name="__main__")
