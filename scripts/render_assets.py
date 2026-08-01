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
    """Encode a deterministic animated GIF.

    Prefer ffmpeg for long/high-FPS scenes: it is substantially faster than
    per-frame Pillow quantization and produces smoother palette transitions.
    Pillow remains a portable fallback if ffmpeg is unavailable.
    """
    out.parent.mkdir(parents=True,exist_ok=True)
    ffmpeg=shutil.which('ffmpeg')
    if ffmpeg and frames:
        import os, tempfile
        fps=max(1.0,1000.0/float(duration))
        with tempfile.TemporaryDirectory(prefix='thoth-gif-') as td:
            td=Path(td)
            for i,src in enumerate(frames):
                dst=td/f'frame-{i:04d}.png'
                try: os.link(src,dst)
                except OSError: shutil.copy2(src,dst)
            dither='none' if out.name in {'hero.gif','activity.gif'} else 'sierra2_4a'
            filt=f'[0:v]split[s0][s1];[s0]palettegen=max_colors=192:stats_mode=full[p];[s1][p]paletteuse=dither={dither}'
            cmd=[ffmpeg,'-hide_banner','-loglevel','error','-y','-framerate',f'{fps:.6f}','-i',str(td/'frame-%04d.png'),'-filter_complex',filt,'-loop','0',str(out)]
            proc=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            if proc.returncode==0 and out.exists() and out.stat().st_size>0:
                return
    imgs=[Image.open(x).convert('P',palette=Image.Palette.ADAPTIVE,colors=160) for x in frames]
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
        # Scene-specific pacing. The Hero is captured at 30fps because the
        # Hero uses an exact GIF-friendly 25 fps cadence (40 ms/frame).
        # The console advances one visible character per frame at 25 chars/s.
        console_lines=cfg.get('identity',{}).get('console',[]) or []
        console_chars=sum(len(str(x)) for x in console_lines)
        apple_headline_seconds=max(.8*1.1,.7*1.1+2.8*1.1)  # 3.85s
        console_pause_seconds=.075*max(0,len(console_lines)-1)
        hero_seconds=max(float(rend['hero_seconds']),apple_headline_seconds+.03+.36+.10+(console_chars/25.0)+console_pause_seconds+.45+.32)
        scenes=[('hero',hero_seconds,25),('stats',float(rend['stats_seconds'])*3.0,min(fps,6))]
        for pr in runtime.get('projects',[])[:3]: scenes.append(('project-'+pr['slug'],float(rend['project_seconds']),fps))
        scenes.append(('activity',7.8,20))
        for scene,seconds,scene_fps in scenes:
            if (out/f'{scene}.gif').exists():
                continue
            el=page.locator(f'[data-capture="{scene}"]')
            if await el.count()==0: continue
            count=max(16,round(seconds*scene_fps)); frames=[]
            for i in range(count):
                t=i/(count-1) if scene=='hero' and count>1 else i/count
                await page.evaluate("([scene,t])=>window.__THOTH_RENDER_FRAME(scene,t)",[scene,t])
                f=tmp/f'{scene}-{i:03d}.png'; await el.screenshot(path=str(f),animations='disabled'); frames.append(f)
            gif_from(frames,out/f'{scene}.gif',round(1000/scene_fps))
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
