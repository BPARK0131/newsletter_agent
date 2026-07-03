"""프로젝트 루트 경로 (sources.yaml, vault/, logs/ 기준)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# ipn_agent/paths.py → 프로젝트 루트
PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_VAULT_DIR = PROJECT_DIR / "vault"


def _path_is_writable_dir(path: Path) -> bool:
    """존재하는 디렉터리에 쓰기 가능한지 확인."""
    try:
        if not path.is_dir():
            return False
        probe = path / ".ipn_vault_write_probe"
        probe.touch()
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def _can_use_vault_path(path: Path) -> bool:
    """Vault 경로가 이미 있거나, 바로 아래 한 단계에서 안전하게 생성 가능한지."""
    try:
        candidate = path.expanduser()
    except (OSError, ValueError):
        return False
    if candidate.exists():
        return candidate.is_dir() and _path_is_writable_dir(candidate)
    parent = candidate.parent
    return parent.exists() and _path_is_writable_dir(parent)


def resolve_vault_path(*, configured: str | None = None) -> Path:
    """
    Vault 절대 경로를 결정한다.

    우선순위:
      1. 접근 가능한 OBSIDIAN_VAULT_PATH (또는 configured 인자)
      2. 프로젝트 루트의 vault/ (git clone 위치 기준)
    """
    raw = (
        configured
        if configured is not None
        else os.environ.get("OBSIDIAN_VAULT_PATH", "")
    ).strip()
    if raw:
        candidate = Path(raw)
        if _can_use_vault_path(candidate):
            try:
                return candidate.expanduser().resolve()
            except OSError:
                pass
    return DEFAULT_VAULT_DIR.resolve()


def ensure_vault_path_env(*, quiet: bool = False) -> Path:
    """OBSIDIAN_VAULT_PATH를 검증·보정하고 환경변수에 반영한다."""
    configured = os.environ.get("OBSIDIAN_VAULT_PATH", "").strip()
    resolved = resolve_vault_path(configured=configured)
    if configured and not quiet:
        try:
            configured_resolved = Path(configured).expanduser().resolve()
        except OSError:
            configured_resolved = None
        if configured_resolved != resolved:
            print(
                f"[INFO] OBSIDIAN_VAULT_PATH 접근 불가 — "
                f"프로젝트 vault 사용: {resolved}",
                file=sys.stderr,
            )
    os.environ["OBSIDIAN_VAULT_PATH"] = str(resolved)
    return resolved
