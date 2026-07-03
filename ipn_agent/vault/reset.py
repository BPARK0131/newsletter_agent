"""
Vault 초기화 스크립트
========================================================
역할:
  Obsidian vault의 Phase별 폴더 내 Markdown을 삭제한다.
  .gitkeep 은 유지하여 폴더 구조와 Git 추적을 보존한다.

실행:
  python reset_vault.py --phase 01              # 01_raw/ 만 초기화
  python reset_vault.py --phase 02              # 02_review/ 만 초기화
  python reset_vault.py --phase 03              # 03_approved/ 만 초기화
  python reset_vault.py --phase 04              # 04_newsletter/ 만 초기화
  python reset_vault.py --phase 01 02           # 여러 Phase 동시 초기화
  python reset_vault.py --all                   # 01~04 전체 초기화
  python reset_vault.py --dry-run --all         # 삭제 대상만 출력 (실제 삭제 X)
  python reset_vault.py --yes --phase 02        # 확인 없이 즉시 삭제

주의:
  - 삭제된 .md 파일은 복구되지 않습니다. 필요하면 Git commit/backup 후 실행하세요.
  - 01_raw 초기화 후에는 fetch_script.py 로 다시 수집해야 합니다.
  - 02_review 초기화 후에는 review_script.py 로 다시 리뷰를 생성하세요.
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from ipn_agent.paths import ensure_vault_path_env
from ipn_agent.vault.utils import get_vault_path

load_dotenv()
ensure_vault_path_env()

# Windows 터미널 인코딩
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════════
# Phase 정의
# ═══════════════════════════════════════════════════════════════

PHASE_DIRS: dict[str, str] = {
    "01": "01_raw",
    "02": "02_review",
    "03": "03_approved",
    "04": "04_newsletter",
    "05": "05_newsletter_archive",
    "06": "06_newsletter_used",
    "99": "99_rejected",
}

PHASE_LABELS: dict[str, str] = {
    "01": "Phase 1 — 수집 (fetch_script.py)",
    "02": "Phase 2 — 리뷰 (review_script.py)",
    "03": "Phase 3 — 승인 (수동 이동)",
    "04": "Phase 4 — 뉴스레터 (newsletter_orchestrator.py)",
    "05": "Phase 5 — 발행 아카이브 (05_newsletter_archive/)",
    "06": "Phase 6 — 발행 used 기사 (06_newsletter_used/)",
    "99": "반려 — HITL rejected (99_rejected/)",
}

# --all 시 초기화 순서
ALL_PHASES: list[str] = ["01", "02", "03", "04", "05", "06", "99"]

KEEP_FILENAMES = {".gitkeep"}


# ═══════════════════════════════════════════════════════════════
# 유틸
# ═══════════════════════════════════════════════════════════════

def collect_md_files(phase_dir: Path) -> list[Path]:
    """Phase 폴더 아래 삭제 대상 .md 파일 목록 (KEEP 제외)."""
    if not phase_dir.exists():
        return []
    files = []
    for path in phase_dir.rglob("*.md"):
        if path.name in KEEP_FILENAMES:
            continue
        files.append(path)
    return sorted(files)


def collect_phase_targets(vault_path: Path, phase: str) -> list[Path]:
    """Phase별 삭제 대상."""
    phase_dir = vault_path / PHASE_DIRS[phase]
    return sorted(set(collect_md_files(phase_dir)))


def remove_empty_dirs(root: Path) -> int:
    """빈 하위 디렉터리를 bottom-up 으로 제거. 제거한 개수 반환."""
    removed = 0
    if not root.exists():
        return removed
    for dirpath in sorted(root.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if not dirpath.is_dir():
            continue
        if dirpath == root:
            continue
        try:
            if not any(dirpath.iterdir()):
                dirpath.rmdir()
                removed += 1
        except OSError:
            pass
    return removed


def reset_phase(
    vault_path: Path,
    phase: str,
    dry_run: bool,
    clean_empty_dirs: bool,
) -> tuple[int, int]:
    """
    단일 Phase 초기화.
    반환: (삭제된 md 파일 수, 제거된 빈 디렉터리 수)
    """
    dir_name = PHASE_DIRS[phase]
    phase_dir = vault_path / dir_name
    label = PHASE_LABELS[phase]

    print(f"\n[{phase}] {label}")
    print(f"  경로: {phase_dir}")

    if not phase_dir.exists():
        print(f"  [WARN] 폴더 없음 — 건너뜀")
        return 0, 0

    targets = collect_phase_targets(vault_path, phase)
    if not targets:
        print(f"  [INFO] 삭제할 파일 없음")
        return 0, 0

    print(f"  [INFO] 삭제 대상: {len(targets)}개")
    for path in targets:
        rel = path.relative_to(vault_path)
        if dry_run:
            print(f"    [DRY-RUN] {rel}")
        else:
            path.unlink()
            print(f"    [DELETED] {rel}")

    empty_removed = 0
    if clean_empty_dirs and phase == "01" and not dry_run:
        empty_removed = remove_empty_dirs(phase_dir)
        if empty_removed:
            print(f"  [INFO] 빈 하위 폴더 {empty_removed}개 제거")

    return len(targets), empty_removed


def confirm(phases: list[str], vault_path: Path) -> bool:
    """사용자 확인 프롬프트."""
    print("\n" + "=" * 60)
    print("[WARN] 아래 Phase의 Markdown 파일이 영구 삭제됩니다.")
    print(f"  vault: {vault_path}")
    for phase in phases:
        print(f"  - [{phase}] {PHASE_DIRS[phase]}  ({PHASE_LABELS[phase]})")
    print("=" * 60)
    answer = input("계속하려면 yes 입력: ").strip().lower()
    return answer in ("yes", "y")


def run(
    phases: list[str],
    dry_run: bool = False,
    yes: bool = False,
    clean_empty_dirs: bool = True,
) -> None:
    vault_path = get_vault_path()

    if not vault_path.exists():
        print(f"[ERROR] vault 폴더 없음: {vault_path}")
        sys.exit(1)

    # 미리 삭제 대상 집계
    total_targets = 0
    for phase in phases:
        total_targets += len(collect_phase_targets(vault_path, phase))

    if total_targets == 0:
        print(f"[INFO] 삭제할 .md 파일 없음 | vault: {vault_path}")
        return

    if not dry_run and not yes:
        if not confirm(phases, vault_path):
            print("[CANCEL] 초기화 취소")
            return

    mode = "DRY-RUN" if dry_run else "RESET"
    print(f"\n[{mode}] vault: {vault_path}")

    deleted_files = 0
    deleted_dirs = 0
    for phase in phases:
        n_files, n_dirs = reset_phase(vault_path, phase, dry_run, clean_empty_dirs)
        deleted_files += n_files
        deleted_dirs += n_dirs

    # .gitkeep 및 필수 하위 폴더 보장
    if not dry_run:
        for phase in phases:
            phase_dir = vault_path / PHASE_DIRS[phase]
            phase_dir.mkdir(parents=True, exist_ok=True)
            if phase == "01":
                (phase_dir / "expansion").mkdir(parents=True, exist_ok=True)
            if phase == "04":
                for sub in ("draft", "published"):
                    (phase_dir / sub).mkdir(parents=True, exist_ok=True)
            gitkeep = phase_dir / ".gitkeep"
            if not gitkeep.exists():
                gitkeep.touch()

    suffix = " (dry-run)" if dry_run else ""
    print(f"\n[DONE]{suffix} Markdown {deleted_files}개 삭제", end="")
    if deleted_dirs:
        print(f", 빈 폴더 {deleted_dirs}개 제거", end="")
    print()

    if not dry_run and deleted_files > 0:
        hints = []
        if "01" in phases:
            hints.append("python fetch_script.py")
        if "02" in phases:
            hints.append("python review_script.py")
        if "03" in phases and "02" not in phases:
            hints.append("02_review/ 에서 승인 후 03_approved/ 로 이동")
        if "04" in phases:
            hints.append("python newsletter_orchestrator.py --mode draft")
        if "05" in phases:
            hints.append("발행 아카이브(05) 초기화 — published는 04/reset 별도")
        if "06" in phases:
            hints.append("used 기사(06) 초기화 — 발행 이력 소실 주의")
        if hints:
            print("[NEXT] " + " → ".join(hints))


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

def parse_phases(args: argparse.Namespace) -> list[str]:
    if args.all:
        return ALL_PHASES
    if args.phase:
        return args.phase
    print("[ERROR] --phase 또는 --all 중 하나를 지정하세요.")
    print("  예: python reset_vault.py --phase 02")
    print("  예: python reset_vault.py --all")
    sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Obsidian vault Phase별 초기화 (01_raw ~ 04_newsletter, registry, 99_rejected)",
    )
    parser.add_argument(
        "--phase",
        nargs="+",
        choices=sorted(PHASE_DIRS.keys()),
        metavar="NN",
        help="초기화할 Phase (01=raw, 02=review, 03=approved, 04=newsletter, 05=archive, 06=used, 99=rejected)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="01~06, 99(rejected) 전체 초기화",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="삭제 대상만 출력 (실제 삭제 X)",
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="확인 프롬프트 없이 즉시 삭제",
    )
    parser.add_argument(
        "--keep-dirs",
        action="store_true",
        help="01_raw 하위 빈 폴더는 유지 (기본: 빈 폴더 제거)",
    )
    args = parser.parse_args()

    phases = parse_phases(args)
    # 중복 제거, 순서 유지
    seen: set[str] = set()
    ordered: list[str] = []
    for p in phases:
        if p not in seen:
            seen.add(p)
            ordered.append(p)

    run(
        phases=ordered,
        dry_run=args.dry_run,
        yes=args.yes,
        clean_empty_dirs=not args.keep_dirs,
    )
