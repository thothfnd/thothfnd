#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_V9 = [
    "README.md",
    "requirements.txt",
    "LICENSE",
    "data/profile.json",
    "scripts/generate_profile.py",
    "scripts/cleanup_repo.py",
    ".github/workflows/refresh-profile.yml",
]

# Files/folders known to belong to pre-V9 iterations or one-shot migrations.
LEGACY_EXACT = [
    ".avatar.sha256",
    "profile.json",
    "INSTALL-SIMPLE.txt",
    "INSTALL.md",
    "SETUP.md",
    "WORKFLOW-PASTE.txt",
    "START-HERE-V8.txt",
    "V8.0.1-HOTFIX.txt",
    "V8.0.2-HOTFIX.txt",
    "data/capabilities.json",
    "assets/projects",
    "scripts/render_ascii.py",
    "scripts/render_meta.py",
    "scripts/sync_avatar.py",
    ".github/workflows/cleanup-v7.yml",
    ".github/workflows/cleanup-v8.yml",
]

LEGACY_ASSET_ROOT_NAMES = {
    "about.svg", "activity.svg", "avatar-ascii.svg", "capabilities.svg", "footer.svg",
    "hero.svg", "identity.svg", "portrait.svg", "profile-meta.svg", "signal.svg",
    "stack.svg", "stats.svg", "works.svg", "year.svg",
    "hd-about.svg", "hd-stack.svg", "hd-projects.svg", "hd-stats.svg",
}

EXPECTED_GENERATED = {
    "scene-01-intro.svg",
    "scene-02-builds.svg",
    "scene-03-profile.svg",
    "footer.svg",
    "cta-thoth-browser.svg",
    "cta-relayx.svg",
    "link-github.svg",
    "link-telegram.svg",
    "link-channel.svg",
    "link-website.svg",
}


def verify_v9() -> None:
    missing = [p for p in REQUIRED_V9 if not (ROOT / p).exists()]
    if missing:
        print("V9 CLEANUP ABORTED: required V9 files are missing:")
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
        for name in LEGACY_ASSET_ROOT_NAMES:
            p = assets / name
            if p.exists():
                result.append(p)

    generated = assets / "generated"
    if generated.exists():
        for path in generated.iterdir():
            if path.is_file() and path.name not in EXPECTED_GENERATED:
                result.append(path)

    workflows = ROOT / ".github" / "workflows"
    if workflows.exists():
        for p in workflows.iterdir():
            if p.name == "refresh-profile.yml":
                continue
            low = p.name.lower()
            if "cleanup" in low or "legacy" in low or "migration" in low:
                result.append(p)

    # Deduplicate while preserving deterministic order.
    unique = {p.resolve(): p for p in result}
    return sorted(unique.values(), key=lambda p: str(p.relative_to(ROOT)).lower())


def remove(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Actually remove legacy artifacts")
    ap.add_argument("--audit", action="store_true", help="Print cleanup details")
    args = ap.parse_args()

    verify_v9()
    found = candidates()
    if not found:
        print("V9 CLEANUP: repository already clean.")
        return 0

    if args.audit or not args.apply:
        print("V9 CLEANUP candidates:")
        for p in found:
            print(f"  - {p.relative_to(ROOT)}")

    if not args.apply:
        print("DRY RUN: nothing deleted.")
        return 0

    for p in found:
        remove(p)
    print(f"V9 CLEANUP: removed {len(found)} legacy item(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
