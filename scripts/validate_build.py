from __future__ import annotations
from pathlib import Path
from PIL import Image, ImageChops, ImageStat
from common import ROOT, load_json
import sys

def motion_metrics(a,b):
    d=ImageChops.difference(a.convert('RGB'),b.convert('RGB'))
    st=ImageStat.Stat(d)
    mean=sum(st.mean)/3
    # Ratio of pixels with a clearly visible RGB delta. This prevents a large
    # canvas from making localized but intentional motion look numerically zero.
    px=d.load(); w,h=d.size; changed=0
    for y in range(h):
        for x in range(w):
            if max(px[x,y]) >= 10: changed += 1
    return mean, changed/(w*h)

def main():
    rt=load_json(ROOT/'data/runtime.json'); gen=ROOT/'assets/generated'; required=['hero.gif','stats.gif','activity.gif','global-preview.png']+[f'project-{p["slug"]}.gif' for p in rt.get('projects',[])[:3]]
    missing=[x for x in required if not (gen/x).exists()]
    if missing: raise SystemExit('MISSING: '+', '.join(missing))
    for name in required:
        if not name.endswith('.gif'): continue
        im=Image.open(gen/name); n=getattr(im,'n_frames',1)
        if n<8: raise SystemExit(f'{name}: animation has only {n} frames')
        idx=[0,n//4,n//2,(3*n)//4,n-1]; frames=[]
        for i in idx: im.seek(i); frames.append(im.copy())
        metrics=[motion_metrics(frames[i],frames[i+1]) for i in range(len(frames)-1)]
        max_mean=max(x[0] for x in metrics); max_ratio=max(x[1] for x in metrics)
        # Dual gate: reject truly static/nearly-static assets, but do not fail a
        # localized timeline animation solely because the section canvas is large.
        if max_mean < 0.30 and max_ratio < 0.0025:
            raise SystemExit(f'{name}: motion imperceptible, max frame-diff={max_mean:.3f}, changed-pixels={max_ratio:.4%}')
        print(f'PASS {name}: frames={n}, max-diff={max_mean:.3f}, changed-pixels={max_ratio:.4%}')
    # README must reference only existing CTA images
    text=(ROOT/'README.md').read_text(encoding='utf-8')
    import re
    for rel in re.findall(r'src="(\./assets/generated/[^"]+)"',text):
        if not (ROOT/rel[2:]).exists(): raise SystemExit('README missing asset: '+rel)
    print('BUILD_VALIDATION=PASS')
if __name__=='__main__': main()
