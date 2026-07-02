"""프로젝트 루트 경로 (sources.yaml, vault/, logs/ 기준)."""

from pathlib import Path

# ipn_agent/paths.py → mini pjt/
PROJECT_DIR = Path(__file__).resolve().parent.parent
