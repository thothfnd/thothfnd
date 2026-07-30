#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "README.md",
    "requirements.txt",
    "LICENSE",
    "data/profile.json",
    "scripts/generate_profile.py",
    "scripts/cleanup_repo.py",
    ".github/workflows/refresh-profile.yml",
]

LEGACY_EXACT = [
    ".avatar.sha256",
    "profile.json",
    "INSTALL-SIMPLE.txt",
    "INSTALL.md",
    "SETUP.md",
    "WORKFLOW-PASTE.txt",
    "START-HERE-V8.txt",
    "START-HERE-V9.txt",
    "START-HERE-V10.txt",
    "V8.0.1-HOTFIX.txt",
    "V8.0.2-HOTFIX.txt",
    "data/capabilities.json",
    "assets/projects",
    "scripts/render_ascii.py",
    "scripts/render_meta.py",
    "scripts/sync_avatar.py",
    ".github/workflows/cleanup-v7.yml",
    ".github/workflows/cleanup-v8.yml",
    ".github/workflows/cleanup-v9.yml",
]

LEGACY_ROOT_ASSETS = {
    "about.svg", "activity.svg", "avatar-ascii.svg", "capabilities.svg", "footer.svg",
    "hero.svg", "identity.svg", "portrait.svg", "profile-meta.svg", "signal.svg",
    "stack.svg", "stats.svg", "works.svg", "year.svg", "hd-about.svg", "hd-stack.svg",
    "hd-projects.svg", "hd-stats.svg",
}


def verify() -> None:
    missing = [item for item in REQUIRED if not (ROOT / item).exists()]
    if missing:
        print("V11 CLEANUP ABORTED — required V11 files are missing:")
        for item in missing:
            print(f"  - {item}")
        print("Nothing was deleted.")
        raise SystemExit(2)


def candidates() -> list[Path]:
    result: list[Path] = []
    for item in LEGACY_EXACT:
        path = ROOT / item
        if path.exists():
            result.append(path)

    assets = ROOT / "assets"
    if assets.exists():
        for name in LEGACY_ROOT_ASSETS:
            path = assets / name
            if path.exists():
                result.append(path)

    workflows = ROOT / ".github" / "workflows"
    if workflows.exists():
        for path in workflows.iterdir():
            if path.name == "refresh-profile.yml":
                continue
            low = path.name.lower()
            if any(token in low for token in ("cleanup", "legacy", "migration")):
                result.append(path)

    unique = {path.resolve(): path for path in result}
    return sorted(unique.values(), key=lambda p: str(p.relative_to(ROOT)).lower())


def remove(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--audit", action="store_true")
    args = parser.parse_args()

    verify()
    found = candidates()
    if not found:
        print("V11 CLEANUP: repository already clean.")
        return 0

    if args.audit or not args.apply:
        print("V11 CLEANUP candidates:")
        for path in found:
            print(f"  - {path.relative_to(ROOT)}")

    if not args.apply:
        print("DRY RUN: nothing deleted.")
        return 0

    for path in found:
        remove(path)
    print(f"V11 CLEANUP: removed {len(found)} legacy item(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
