from __future__ import annotations
import argparse, shutil
from pathlib import Path
from common import ROOT

REQUIRED=['source/index.html','source/styles.css','source/app.js','scripts/collect_github.py','scripts/build_profile.py','scripts/render_assets.py','data/profile.json','.github/workflows/refresh-profile.yml']
LEGACY=[
 'scene-01-hero.gif','scene-02-thoth-browser.gif','scene-02-builds.gif','scene-03-profile.gif',
 'hero.gif','activity.gif','project-thoth-browser.gif','profile.json','.avatar.sha256',
 'START-HERE-V10.txt','MIGRATION.md','cleanup-v7.yml','CHECK-ONLY.bat','START-CLEANUP-V7.bat','CLEANUP-V7.ps1'
]
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--apply',action='store_true'); args=ap.parse_args()
    missing=[x for x in REQUIRED if not (ROOT/x).exists()]
    if missing: raise SystemExit('SAFETY_GATE=FAIL missing: '+', '.join(missing))
    print('SAFETY_GATE=PASS')
    victims=[ROOT/x for x in LEGACY if (ROOT/x).exists()]
    # generated assets are always rebuilt, but source assets and data are preserved.
    gen=ROOT/'assets/generated'
    if args.apply and gen.exists(): shutil.rmtree(gen); gen.mkdir(parents=True)
    for p in victims:
        print(('DELETE ' if args.apply else 'WOULD_DELETE ')+str(p.relative_to(ROOT)))
        if args.apply:
            if p.is_dir(): shutil.rmtree(p)
            else: p.unlink()
    print(f'CLEANUP_CANDIDATES={len(victims)}')
if __name__=='__main__': main()
