from __future__ import annotations

import argparse
import shutil

from common import ROOT

REQUIRED = [
    'source/index.html',
    'source/styles.css',
    'source/app.js',
    'scripts/collect_github.py',
    'scripts/build_profile.py',
    'scripts/render_assets.py',
    'data/profile.json',
    '.github/workflows/refresh-profile.yml',
]

LEGACY = [
    'scene-01-hero.gif',
    'scene-02-thoth-browser.gif',
    'scene-02-builds.gif',
    'scene-03-profile.gif',
    'hero.gif',
    'activity.gif',
    'project-thoth-browser.gif',
    'profile.json',
    '.avatar.sha256',
    'START-HERE-V10.txt',
    'MIGRATION.md',
    'cleanup-v7.yml',
    'CHECK-ONLY.bat',
    'START-CLEANUP-V7.bat',
    'CLEANUP-V7.ps1',
    'README-SOURCE.md',
    'INSTALL.md',
    'PATCH-MANIFEST.json',
    'docs/REFERENCE-MAP.md',
    'docs/previews',
    'scripts/generate_profile.py',
    'scripts/__pycache__',
    'data/sample-runtime.json',
]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()

    missing = [path for path in REQUIRED if not (ROOT / path).exists()]
    if missing:
        raise SystemExit('SAFETY_GATE=FAIL missing: ' + ', '.join(missing))

    print('SAFETY_GATE=PASS')

    victims = [ROOT / path for path in LEGACY if (ROOT / path).exists()]

    generated = ROOT / 'assets/generated'
    if args.apply and generated.exists():
        shutil.rmtree(generated)
        generated.mkdir(parents=True)

    for path in victims:
        print(('DELETE ' if args.apply else 'WOULD_DELETE ') + str(path.relative_to(ROOT)))
        if not args.apply:
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()

    print(f'CLEANUP_CANDIDATES={len(victims)}')

if __name__ == '__main__':
    main()
