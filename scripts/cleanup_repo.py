#!/usr/bin/env python3
from __future__ import annotations
import argparse, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "README.md", "requirements.txt", "LICENSE", "data/profile.json",
    "scripts/generate_profile.py", "scripts/cleanup_repo.py",
    ".github/workflows/refresh-profile.yml",
]
LEGACY_EXACT = [
    ".avatar.sha256", "profile.json", "INSTALL-SIMPLE.txt", "INSTALL.md", "SETUP.md",
    "WORKFLOW-PASTE.txt", "START-HERE-V8.txt", "START-HERE-V9.txt", "START-HERE-V10.txt",
    "START-HERE-V11.txt", "V8.0.1-HOTFIX.txt", "V8.0.2-HOTFIX.txt", "data/capabilities.json",
    "assets/projects", "scripts/render_ascii.py", "scripts/render_meta.py", "scripts/sync_avatar.py",
    ".github/workflows/cleanup-v7.yml", ".github/workflows/cleanup-v8.yml",
    ".github/workflows/cleanup-v9.yml", ".github/workflows/cleanup-v10.yml",
    ".github/workflows/cleanup-v11.yml",
]
LEGACY_ROOT_ASSETS = {
    "about.svg","activity.svg","avatar-ascii.svg","capabilities.svg","footer.svg","hero.svg",
    "identity.svg","portrait.svg","profile-meta.svg","signal.svg","stack.svg","stats.svg","works.svg",
    "year.svg","hd-about.svg","hd-stack.svg","hd-projects.svg","hd-stats.svg",
}

def verify() -> None:
    missing = [x for x in REQUIRED if not (ROOT/x).exists()]
    if missing:
        print("V12 CLEANUP ABORTED — required V12 files are missing:")
        for x in missing: print(f"  - {x}")
        print("Nothing was deleted.")
        raise SystemExit(2)

def candidates() -> list[Path]:
    found=[]
    for item in LEGACY_EXACT:
        p=ROOT/item
        if p.exists(): found.append(p)
    assets=ROOT/"assets"
    if assets.exists():
        for name in LEGACY_ROOT_ASSETS:
            p=assets/name
            if p.exists(): found.append(p)
    workflows=ROOT/".github"/"workflows"
    if workflows.exists():
        for p in workflows.iterdir():
            if p.name=="refresh-profile.yml": continue
            low=p.name.lower()
            if any(t in low for t in ("cleanup","legacy","migration")): found.append(p)
    return sorted({p.resolve():p for p in found}.values(), key=lambda p:str(p.relative_to(ROOT)).lower())

def remove(p:Path)->None:
    shutil.rmtree(p) if p.is_dir() else p.unlink()

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--apply",action="store_true"); ap.add_argument("--audit",action="store_true"); a=ap.parse_args()
    verify(); found=candidates()
    if not found:
        print("V12 CLEANUP: repository already clean."); return 0
    if a.audit or not a.apply:
        print("V12 CLEANUP candidates:")
        for p in found: print(f"  - {p.relative_to(ROOT)}")
    if not a.apply:
        print("DRY RUN: nothing deleted."); return 0
    for p in found: remove(p)
    print(f"V12 CLEANUP: removed {len(found)} legacy item(s).")
    return 0
if __name__=="__main__": raise SystemExit(main())
