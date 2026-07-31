from __future__ import annotations
import argparse, asyncio, subprocess, sys, time, shutil
from pathlib import Path
from PIL import Image
from common import ROOT, load_json
from playwright.async_api import async_playwright

async def wait_server(port=4173):
    import urllib.request
    for _ in range(80):
        try:
            urllib.request.urlopen(f'http://127.0.0.1:{port}/',timeout=.25); return
        except Exception: await asyncio.sleep(.1)
    raise RuntimeError('preview server did not start')

def gif_from(frames,out,duration):
    imgs=[Image.open(x).convert('P',palette=Image.Palette.ADAPTIVE,colors=192) for x in frames]
    out.parent.mkdir(parents=True,exist_ok=True)
    imgs[0].save(out,save_all=True,append_images=imgs[1:],duration=duration,loop=0,optimize=True,disposal=2)

def png_from(frame,out): out.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(frame,out)

async def capture(runtime):
    cfg=load_json(ROOT/'data/profile.json'); rend=cfg['render']; fps=int(rend.get('fps',12)); out=ROOT/'assets/generated'; out.mkdir(parents=True,exist_ok=True)
    tmp=ROOT/'build/frames'; shutil.rmtree(tmp,ignore_errors=True); tmp.mkdir(parents=True)
    # Self-contained HTML avoids relying on localhost/file navigation in restricted runners.
    html=(ROOT/'build/index.html').read_text(encoding='utf-8')
    css=(ROOT/'build/styles.css').read_text(encoding='utf-8')
    js=(ROOT/'build/app.js').read_text(encoding='utf-8')
    import re
    html=re.sub(r'<link rel="stylesheet" href="\./styles\.css"\s*/?>', '<style>'+css+'</style>', html)
    html=html.replace('<script src="./app.js"></script>','<script>'+js+'</script>')
    # External font links are optional; remove them for deterministic/offline rasterization.
    html=re.sub(r'<link rel="preconnect"[^>]*>', '', html)
    html=re.sub(r'<link href="https://fonts\.googleapis\.com[^"]+" rel="stylesheet">', '', html)
    async with async_playwright() as p:
        import shutil as _shutil
        system_chromium=_shutil.which('chromium') or _shutil.which('chromium-browser') or _shutil.which('google-chrome')
        launch_kwargs={'headless':True,'args':['--disable-dev-shm-usage','--no-sandbox']}
        if system_chromium: launch_kwargs['executable_path']=system_chromium
        browser=await p.chromium.launch(**launch_kwargs)
        page=await browser.new_page(viewport={'width':int(rend['width']),'height':900},device_scale_factor=int(rend.get('scale',1)))
        await page.set_content(html,wait_until='load')
        scenes=[('hero',float(rend['hero_seconds'])),('stats',float(rend['stats_seconds']))]
        for pr in runtime.get('projects',[])[:3]: scenes.append(('project-'+pr['slug'],float(rend['project_seconds'])))
        scenes.append(('activity',float(rend['activity_seconds'])))
        for scene,seconds in scenes:
            if (out/f'{scene}.gif').exists():
                continue
            el=page.locator(f'[data-capture="{scene}"]')
            if await el.count()==0: continue
            count=max(16,round(seconds*fps)); frames=[]
            for i in range(count):
                t=i/count
                await page.evaluate("([scene,t])=>window.__THOTH_RENDER_FRAME(scene,t)",[scene,t])
                f=tmp/f'{scene}-{i:03d}.png'; await el.screenshot(path=str(f),animations='disabled'); frames.append(f)
            gif_from(frames,out/f'{scene}.gif',round(1000/fps))
            if scene=='hero': png_from(frames[round(count*.55)],out/'hero-preview.png')
        for pr in runtime.get('projects',[])[:3]:
            for j,_ in enumerate([x for x in pr.get('links',[]) if x.get('url')][:5]):
                sel=f'[data-cta="{pr["slug"]}-{j}"]'; el=page.locator(sel)
                if await el.count()==0: continue
                frames=[]
                for i in range(8):
                    t=i/8; await page.evaluate("t=>window.__THOTH_RENDER_CTA(t)",t)
                    f=tmp/f'cta-{pr["slug"]}-{j}-{i:02d}.png'; await el.screenshot(path=str(f),animations='disabled'); frames.append(f)
                gif_from(frames,out/f'cta-{pr["slug"]}-{j}.gif',125)
        await page.evaluate("()=>window.__THOTH_RENDER_FRAME('all',.58)")
        await page.screenshot(path=str(out/'global-preview.png'),full_page=True,animations='disabled')
        await browser.close()

async def amain(args):
    rt=load_json(Path(args.runtime)); await capture(rt)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--runtime',default=str(ROOT/'data/runtime.json')); args=ap.parse_args(); asyncio.run(amain(args))
if __name__=='__main__': main()
