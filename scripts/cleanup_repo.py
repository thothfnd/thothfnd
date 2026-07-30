#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_V8 = [
    "README.md",
    "LICENSE",
    "requirements.txt",
    "data/profile.json",
    "scripts/generate_profile.py",
    "scripts/cleanup_repo.py",
    ".github/workflows/refresh-profile.yml",
]

# Explicit legacy paths known from previous profile generations.
LEGACY_PATHS = [
    ".avatar.sha256",
    "profile.json",
    "INSTALL-SIMPLE.txt",
    "SETUP.md",
    "WORKFLOW-PASTE.txt",
    "START-HERE-V8.txt",
    "INSTALL.md",
    "data/capabilities.json",
    "assets/about.svg",
    "assets/activity.svg",
    "assets/avatar-ascii.svg",
    "assets/footer.svg",
    "assets/hero.svg",
    "assets/identity.svg",
    "assets/portrait.svg",
    "assets/profile-meta.svg",
    "assets/signal.svg",
    "assets/stack.svg",
    "assets/stats.svg",
    "assets/works.svg",
    "assets/year.svg",
    "assets/hd-about.svg",
    "assets/hd-stack.svg",
    "assets/hd-projects.svg",
    "assets/hd-stats.svg",
    "assets/projects",
    "scripts/render_ascii.py",
    "scripts/render_meta.py",
    "scripts/sync_avatar.py",
    ".github/workflows/cleanup-v7.yml",
    ".github/workflows/v7-legacy-cleanup.yml",
]

# Old generated names that must never coexist with V8. The V8 renderer also clears
# assets/generated/*.svg before every generation, but migration removes them early.
V7_GENERATED = [
    "assets/generated/hero.svg",
    "assets/generated/capabilities.svg",
    "assets/generated/works.svg",
]


def remove(path: Path, dry_run: bool) -> bool:
    if not path.exists() and not path.is_symlink():
        return False
    print(f"REMOVE {path.relative_to(ROOT)}")
    if dry_run:
        return True
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()
    return True


def verify_v8() -> None:
    missing = [p for p in REQUIRED_V8 if not (ROOT / p).exists()]
    if missing:
        raise SystemExit("V8 safety gate failed. Missing: " + ", ".join(missing))


def audit_unknown() -> None:
    allowed_root = {".git", ".github", "assets", "data", "scripts", "README.md", "LICENSE", "requirements.txt", "INSTALL-V8.md"}
    unknown = sorted(p.name for p in ROOT.iterdir() if p.name not in allowed_root)
    if unknown:
        print("UNKNOWN ROOT ITEMS (not deleted automatically):")
        for name in unknown:
            print(f"  - {name}")
    else:
        print("UNKNOWN ROOT ITEMS: none")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Actually delete known legacy files")
    ap.add_argument("--migration", action="store_true", help="Also remove V7 generated files and V8 migration helpers")
    ap.add_argument("--audit", action="store_true", help="Report unknown root items without deleting them")
    args = ap.parse_args()

    verify_v8()
    dry_run = not args.apply
    targets = list(LEGACY_PATHS)
    if args.migration:
        targets += V7_GENERATED

    removed = 0
    for rel in targets:
        removed += int(remove(ROOT / rel, dry_run))

    # Old non-generated assets are obsolete in V8. Remove any remaining SVG at
    # assets/ root, but never touch assets/generated here.
    assets = ROOT / "assets"
    if assets.exists():
        for p in assets.glob("*.svg"):
            removed += int(remove(p, dry_run))

    # Old scripts are obsolete. Preserve only the two V8 scripts.
    scripts = ROOT / "scripts"
    if scripts.exists():
        for p in scripts.glob("*.py"):
            if p.name not in {"generate_profile.py", "cleanup_repo.py"}:
                removed += int(remove(p, dry_run))

    if args.audit:
        audit_unknown()

    action = "would remove" if dry_run else "removed"
    print(f"V8 CLEANUP: {action} {removed} legacy item(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
