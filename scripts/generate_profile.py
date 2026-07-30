#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import random
import shutil
import textwrap
import urllib.request
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "profile.json"
OUT = ROOT / "assets" / "generated"
README = ROOT / "README.md"

W = 880
HERO_H = 560
BUILDS_H = 420
PROFILE_H = 520
BG = (13, 17, 23)          # GitHub-dark family
BG2 = (9, 12, 17)
INK = (240, 246, 252)
SOFT = (177, 186, 196)
MUTED = (125, 133, 144)
LINE = (48, 54, 61)
BUTTON = (33, 38, 45)
BUTTON_BORDER = (48, 54, 61)
BUTTON_HOVER = (43, 49, 57)
ACCENT = (210, 216, 224)

FONT_CANDIDATES = {
    "display": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ],
    "sans": ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
    "serif": ["/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"],
    "mono": ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"],
}


def font(kind: str, size: int):
    for p in FONT_CANDIDATES[kind]:
        if Path(p).exists():
            return ImageFont.truetype(p, size=size)
    return ImageFont.load_default()


def req_bytes(url: str, token: str = "") -> bytes:
    headers = {"User-Agent": "thothfnd-v12-continuum", "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def github_user(login: str, token: str) -> dict:
    return json.loads(req_bytes(f"https://api.github.com/users/{login}", token).decode())


def github_repos(login: str, token: str) -> list[dict]:
    data = json.loads(req_bytes(f"https://api.github.com/users/{login}/repos?per_page=100&type=owner&sort=updated", token).decode())
    return [r for r in data if not r.get("fork")]


def download_avatar(url: str, token: str) -> tuple[Image.Image | None, bytes]:
    if not url:
        return None, b""
    try:
        raw = req_bytes(url + ("&" if "?" in url else "?") + "s=900", token)
        return Image.open(io.BytesIO(raw)).convert("RGB"), raw
    except Exception:
        return None, b""


def demo_data(login: str):
    user = {"login": login, "name": login, "html_url": f"https://github.com/{login}", "avatar_url": ""}
    # Preview/demo never invents repository links. Live runs detect real public repos.
    repos = []
    return user, repos, None, b"v12-demo-avatar"


def find_repo(project: dict, repos: list[dict]) -> dict | None:
    direct = str(project.get("url") or "").strip()
    if direct:
        return {"html_url": direct, "name": project.get("name", "PROJECT")}
    candidates = {str(x).lower() for x in project.get("repo_names", [])}
    for repo in repos:
        if str(repo.get("name", "")).lower() in candidates:
            return repo
    return None


def active_links(config: dict, login: str) -> list[dict]:
    out = []
    for item in config.get("links", []):
        url = str(item.get("url") or "").strip()
        if item.get("id") == "github" and url == "AUTO":
            url = f"https://github.com/{login}"
        if url:
            out.append({**item, "url": url})
    return out


def clean_generated() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)


def save_gif(frames: list[Image.Image], path: Path, duration: int = 100) -> None:
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=duration, loop=0, disposal=2, optimize=False)


def gradient(size: tuple[int, int], top=BG, bottom=BG2) -> Image.Image:
    w, h = size
    strip = Image.new("RGB", (1, h))
    d = ImageDraw.Draw(strip)
    for y in range(h):
        t = y / max(1, h - 1)
        c = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
        d.point((0, y), fill=c)
    return strip.resize((w, h)).convert("RGBA")


def glow(size: tuple[int, int], center: tuple[int, int], radius: int, color=(255, 255, 255), alpha=32) -> Image.Image:
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy = center
    for i in range(16, 0, -1):
        r = radius * i / 16
        a = int(alpha * ((17 - i) / 16) ** 2)
        d.ellipse((cx-r, cy-r, cx+r, cy+r), fill=(*color, a))
    return layer.filter(ImageFilter.GaussianBlur(max(10, radius // 7)))


def background(size: tuple[int, int], phase: float, seed: str, section: int) -> Image.Image:
    img = gradient(size)
    w, h = size
    # One coherent studio light source, not a noisy "cinematic" wallpaper.
    light_x = int(w * (0.70 + 0.04 * math.sin(phase * math.tau)))
    img.alpha_composite(glow(size, (light_x, int(h * 0.22)), int(min(w, h) * 0.44), (221, 225, 231), 35))
    img.alpha_composite(glow(size, (int(w * 0.12), int(h * 0.82)), int(min(w, h) * 0.28), (112, 118, 128), 12))
    d = ImageDraw.Draw(img)
    # editorial chrome rails / very large geometry
    if section == 1:
        d.arc((390, -170, 930, 370), 120, 260, fill=(83, 89, 98, 90), width=1)
        d.line((52, 74, 828, 74), fill=(48, 54, 61, 130), width=1)
        d.line((52, h-36, 828, h-36), fill=(48, 54, 61, 110), width=1)
    elif section == 2:
        d.line((52, 36, 828, 36), fill=(48, 54, 61, 110), width=1)
        d.line((440, 84, 440, h-50), fill=(48, 54, 61, 115), width=1)
    else:
        d.line((52, 36, 828, 36), fill=(48, 54, 61, 110), width=1)
        d.arc((-140, 150, 420, 710), 285, 72, fill=(83, 89, 98, 70), width=1)
    # sparse dust: subtle, deterministic and subordinate
    rng = random.Random(f"{seed}-{section}")
    for i in range(15):
        x = (rng.randrange(w) + int(phase * (8 + i % 4))) % w
        y = rng.randrange(20, h - 20)
        a = 34 + int(20 * (0.5 + 0.5 * math.sin(phase * math.tau + i)))
        d.point((x, y), fill=(235, 238, 244, a))
    return img


def text_width(text: str, fnt) -> int:
    d = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    b = d.textbbox((0, 0), text, font=fnt)
    return b[2] - b[0]


def fit_lines(text: str, fnt, max_width: int, max_lines: int) -> list[str]:
    words = text.split()
    d = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    lines, cur = [], ""
    for word in words:
        trial = (cur + " " + word).strip()
        if cur and d.textbbox((0, 0), trial, font=fnt)[2] > max_width:
            lines.append(cur)
            cur = word
            if len(lines) >= max_lines:
                break
        else:
            cur = trial
    if cur and len(lines) < max_lines:
        lines.append(cur)
    if len(lines) == max_lines and len(" ".join(lines).split()) < len(words):
        lines[-1] = lines[-1].rstrip(" .") + "…"
    return lines


def owl_emblem(size=(260, 280), phase=0.0, reveal=1.0) -> Image.Image:
    """Custom dark owl emblem: recognizable silhouette, restrained chrome, no cartoon geometry."""
    w, h = size
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = w // 2 + int(math.sin(phase * math.tau) * 1.5)
    cy = h // 2 + int(math.sin(phase * math.tau * 0.7) * 2)
    # broad wing silhouette
    d.polygon([(cx-116,cy+72),(cx-126,cy-12),(cx-90,cy-92),(cx-42,cy-122),(cx-10,cy-94),
               (cx,cy-70),(cx+10,cy-94),(cx+42,cy-122),(cx+90,cy-92),(cx+126,cy-12),(cx+116,cy+72),
               (cx+62,cy+112),(cx+18,cy+126),(cx,cy+138),(cx-18,cy+126),(cx-62,cy+112)], fill=(11,14,18,255))
    # feather planes
    d.polygon([(cx-100,cy+68),(cx-98,cy-24),(cx-62,cy-91),(cx-18,cy-106),(cx-4,cy+117),(cx-50,cy+104)], fill=(26,30,36,255))
    d.polygon([(cx+100,cy+68),(cx+98,cy-24),(cx+62,cy-91),(cx+18,cy-106),(cx+4,cy+117),(cx+50,cy+104)], fill=(22,26,32,255))
    # face shield
    d.polygon([(cx-70,cy-26),(cx-32,cy-72),(cx,cy-54),(cx+32,cy-72),(cx+70,cy-26),
               (cx+48,cy+36),(cx,cy+58),(cx-48,cy+36)], fill=(40,45,54,255))
    d.polygon([(cx-62,cy-18),(cx-24,cy-52),(cx-8,cy-34),(cx-20,cy+20),(cx-48,cy+24)], fill=(54,60,70,255))
    d.polygon([(cx+62,cy-18),(cx+24,cy-52),(cx+8,cy-34),(cx+20,cy+20),(cx+48,cy+24)], fill=(45,51,61,255))
    # eyes, narrow and emblematic
    blink = 0.93 if 0.47 < (phase % 1.0) < 0.50 else 0.0
    eye_h = max(3, int(13 * (1 - blink)))
    d.polygon([(cx-48,cy-14),(cx-16,cy-20),(cx-23,cy-20+eye_h),(cx-48,cy-14+eye_h)], fill=(236,240,245,255))
    d.polygon([(cx+48,cy-14),(cx+16,cy-20),(cx+23,cy-20+eye_h),(cx+48,cy-14+eye_h)], fill=(236,240,245,255))
    if blink < .8:
        d.ellipse((cx-34,cy-12,cx-24,cy-2), fill=(5,7,10,255))
        d.ellipse((cx+24,cy-12,cx+34,cy-2), fill=(5,7,10,255))
    d.polygon([(cx-8,cy+10),(cx+8,cy+10),(cx,cy+34)], fill=(195,201,210,255))
    # a few controlled chrome cuts
    d.line((cx-78,cy-80,cx-28,cy-106), fill=(175,183,194,90), width=2)
    d.line((cx+78,cy-80,cx+28,cy-106), fill=(175,183,194,80), width=2)
    d.line((cx-54,cy+82,cx-12,cy+120), fill=(175,183,194,45), width=1)
    d.line((cx+54,cy+82,cx+12,cy+120), fill=(175,183,194,45), width=1)
    if reveal < 1.0:
        alpha = img.getchannel("A").point(lambda p: int(p * max(0, min(1, reveal))))
        img.putalpha(alpha)
    return img


def draw_wordmark(img: Image.Image, progress: float, sheen: float) -> None:
    d = ImageDraw.Draw(img)
    big = font("display", 78)
    small = font("display", 30)
    x0, y0 = 354, 146
    for idx, ch in enumerate("THOTH"):
        a = max(0.0, min(1.0, progress * 6 - idx))
        if a <= 0:
            continue
        x = x0 + idx * 62
        d.text((x, y0), ch, font=big, fill=(235, 239, 244, int(255*a)))
    if progress > .62:
        a = min(1.0, (progress - .62) / .25)
        d.text((670, 191), "/FND", font=small, fill=(219, 224, 231, int(255*a)))
    if sheen > 0:
        # soft chrome reflection across wordmark region
        overlay = Image.new("RGBA", img.size, (0,0,0,0))
        od = ImageDraw.Draw(overlay)
        sx = int(330 + sheen * 500)
        od.polygon([(sx-38,125),(sx+5,125),(sx+90,245),(sx+47,245)], fill=(255,255,255,20))
        overlay = overlay.filter(ImageFilter.GaussianBlur(8))
        img.alpha_composite(overlay)


def render_hero(config: dict, user: dict) -> None:
    frames=[]
    about=config.get("about", [])[:3]
    total=36
    for i in range(total):
        t=i/(total-1)
        img=background((W,HERO_H), t, user["login"], 1)
        d=ImageDraw.Draw(img)
        d.text((52,42), config.get("eyebrow","THOTHFND").upper(), font=font("mono",10), fill=MUTED)
        # reveal owl + wordmark, then hold while background remains alive
        reveal=min(1.0,max(0.0,(t-.03)/.20))
        owl=owl_emblem(phase=t, reveal=reveal)
        img.alpha_composite(owl,(52,118))
        word=min(1.0,max(0.0,(t-.13)/.28))
        sheen=max(0.0,min(1.0,(t-.38)/.18))
        draw_wordmark(img,word,sheen)
        if t>.45:
            a=min(1.0,(t-.45)/.12)
            title="privacy · security · anonymity · systems · automation"
            layer=Image.new("RGBA",img.size,(0,0,0,0)); ld=ImageDraw.Draw(layer)
            ld.text((356,246),title,font=font("sans",16),fill=(*SOFT,int(255*a)))
            img.alpha_composite(layer)
        # personal copy: controlled line count, no overlap
        body_font=font("serif",19)
        y=318
        for idx,p in enumerate(about):
            appear=max(0.0,min(1.0,(t-(.53+idx*.08))/.12))
            if appear<=0: continue
            lines=fit_lines(p,body_font,700,2)
            layer=Image.new("RGBA",img.size,(0,0,0,0)); ld=ImageDraw.Draw(layer)
            yy=y
            for line in lines:
                ld.text((84,yy),line,font=body_font,fill=(232,235,240,int(255*appear)))
                yy+=27
            img.alpha_composite(layer)
            y+=67
        frames.append(img.convert("P",palette=Image.ADAPTIVE,colors=192))
    save_gif(frames,OUT/"scene-01-hero.gif",95)


def render_builds(config: dict) -> None:
    projects=config.get("projects",[])[:2]
    total=28; frames=[]
    for i in range(total):
        t=i/(total-1)
        img=background((W,BUILDS_H),t,"builds",2)
        d=ImageDraw.Draw(img)
        d.text((52,50),"CURRENT BUILDS",font=font("display",16),fill=SOFT)
        for idx,p in enumerate(projects):
            x0=60 if idx==0 else 482
            d.text((x0,95),p["name"].upper(),font=font("display",34),fill=INK)
            d.text((x0,135),p.get("status","").upper(),font=font("mono",10),fill=MUTED)
            cx=x0+125; cy=232
            if idx==0:
                # browser/isolation graphic
                d.rounded_rectangle((cx-70,cy-52,cx+70,cy+52),radius=14,outline=(113,121,132,160),width=1)
                d.rounded_rectangle((cx-48,cy-34,cx+48,cy+34),radius=10,outline=(80,88,98,150),width=1)
                for j,r in enumerate((80,103)):
                    a=math.radians((t*360*(1 if j==0 else -0.7))+j*100)
                    px=cx+math.cos(a)*r; py=cy+math.sin(a)*r*.62
                    d.ellipse((px-5,py-5,px+5,py+5),fill=(230,234,240,220))
                d.line((cx-22,cy,cx+22,cy),fill=(212,217,224),width=2)
                d.line((cx,cy-14,cx,cy+14),fill=(212,217,224),width=2)
            else:
                pts=[(cx-70,cy+20),(cx-20,cy-48),(cx+66,cy-30),(cx+88,cy+40),(cx+10,cy+70)]
                edges=((0,1),(1,2),(2,3),(3,4),(4,0),(1,4))
                for a,b in edges: d.line((*pts[a],*pts[b]),fill=(93,101,112,150),width=1)
                pulse=int((t*6)%len(pts))
                for j,pnt in enumerate(pts):
                    r=6 if j==pulse else 4
                    d.ellipse((pnt[0]-r,pnt[1]-r,pnt[0]+r,pnt[1]+r),fill=(236,239,244,230) if j==pulse else (160,168,179,200))
            summary=fit_lines(p.get("summary",""),font("serif",16),320,3)
            yy=325
            for line in summary:
                d.text((x0,yy),line,font=font("serif",16),fill=SOFT); yy+=23
        frames.append(img.convert("P",palette=Image.ADAPTIVE,colors=160))
    save_gif(frames,OUT/"scene-02-builds.gif",100)


def portrait_image(avatar: Image.Image | None, login: str) -> Image.Image:
    if avatar is None:
        # neutral preview placeholder that makes the layout visible without pretending to be the real avatar
        img=Image.new("RGB",(320,320),(20,24,30)); d=ImageDraw.Draw(img)
        d.ellipse((58,36,262,240),fill=(202,208,216)); d.rectangle((108,220,212,315),fill=(202,208,216))
        d.text((90,130),"LIVE",font=font("display",48),fill=(20,24,30)); d.text((72,182),"AVATAR",font=font("display",34),fill=(20,24,30))
        avatar=img
    img=ImageOps.fit(avatar,(320,320),method=Image.LANCZOS,centering=(0.5,0.45))
    g=ImageOps.grayscale(img); g=ImageOps.autocontrast(g,cutoff=1)
    g=ImageEnhance.Contrast(g).enhance(1.38)
    # editorial posterization with a small amount of detail retained
    q=ImageOps.posterize(g.convert("RGB"),5).convert("L")
    detail=g.filter(ImageFilter.DETAIL)
    mix=Image.blend(q,detail,0.28)
    return Image.merge("RGBA",(mix,mix,mix,Image.new("L",mix.size,255)))


def render_profile(config: dict, user: dict, avatar: Image.Image | None, avatar_bytes: bytes) -> None:
    portrait=portrait_image(avatar,user["login"])
    digest=hashlib.sha256(avatar_bytes or b"v12-demo-avatar").hexdigest().upper()[:12]
    interests=config.get("interests",[])[:9]
    total=32; frames=[]
    for i in range(total):
        t=i/(total-1)
        img=background((W,PROFILE_H),t,"profile",3)
        d=ImageDraw.Draw(img)
        d.text((52,48),"PROFILE",font=font("display",16),fill=SOFT)
        # portrait — no card; only the image itself with a controlled matte edge
        matte=Image.new("RGBA",portrait.size,(0,0,0,0))
        matte.alpha_composite(portrait)
        # smooth ping-pong scan from left to right and back
        tri=1-abs(2*t-1)
        xpos=int(18+tri*(portrait.width-36))
        mask=Image.new("L",portrait.size,0); md=ImageDraw.Draw(mask)
        md.rectangle((xpos-40,0,xpos+40,portrait.height),fill=150)
        mask=mask.filter(ImageFilter.GaussianBlur(24))
        enhanced=ImageEnhance.Contrast(portrait.convert("RGB")).enhance(1.24)
        enhanced=ImageEnhance.Brightness(enhanced).enhance(1.08).convert("RGBA")
        band=Image.new("RGBA",portrait.size,(0,0,0,0)); band.paste(enhanced,(0,0),mask)
        matte.alpha_composite(band)
        scan=Image.new("RGBA",portrait.size,(0,0,0,0)); sd=ImageDraw.Draw(scan)
        sd.rectangle((xpos,0,xpos+1,portrait.height),fill=(255,255,255,80))
        scan=scan.filter(ImageFilter.GaussianBlur(1)); matte.alpha_composite(scan)
        img.alpha_composite(matte,(60,108))
        # metadata below image
        d.text((60,442),"@"+user["login"],font=font("mono",11),fill=SOFT)
        d.text((60,466),f"AVATAR SHA256  {digest}",font=font("mono",9),fill=MUTED)
        # right side
        d.text((430,110),config.get("display_name","THOTH /FND"),font=font("display",30),fill=INK)
        d.text((430,150),"INTERESTS",font=font("mono",10),fill=MUTED)
        # 2-column interest composition, larger and cleaner
        left=interests[:5]; right=interests[5:]
        yy=186
        for j,item in enumerate(left):
            f=font("sans",20 if j<3 else 17)
            d.text((430,yy),item,font=f,fill=INK if j<3 else SOFT); yy+=38
        yy=186
        for item in right:
            d.text((655,yy),item,font=font("sans",16),fill=SOFT); yy+=36
        frames.append(img.convert("P",palette=Image.ADAPTIVE,colors=192))
    save_gif(frames,OUT/"scene-03-profile.gif",105)


def render_button(label: str, action: str, path: Path) -> None:
    w,h=250,40; frames=[]; total=18
    for i in range(total):
        img=Image.new("RGBA",(w,h),(0,0,0,0)); d=ImageDraw.Draw(img)
        # GitHub-like base: 6px radius, subtle border, no sci-fi bevels.
        d.rounded_rectangle((0,0,w-1,h-1),radius=6,fill=BUTTON,outline=BUTTON_BORDER,width=1)
        d.line((7,1,w-8,1),fill=(71,78,87,90),width=1)
        d.text((14,10),label,font=font("sans",14),fill=INK)
        aw=text_width(action,font("sans",12))
        d.text((w-34-aw,11),action,font=font("sans",12),fill=SOFT)
        # small drawn arrow
        ax=w-18; ay=20
        d.line((ax-6,ay,ax,ay),fill=SOFT,width=2); d.line((ax-3,ay-3,ax,ay),fill=SOFT,width=2); d.line((ax-3,ay+3,ax,ay),fill=SOFT,width=2)
        # restrained moving highlight
        x=int(-24+(w+48)*(i/(total-1)))
        sheen=Image.new("RGBA",(w,h),(0,0,0,0)); sd=ImageDraw.Draw(sheen)
        sd.polygon([(x-15,0),(x+4,0),(x+25,h),(x+6,h)],fill=(255,255,255,16))
        img.alpha_composite(sheen)
        frames.append(img.convert("P",palette=Image.ADAPTIVE,colors=96))
    save_gif(frames,path,90)


def write_readme(links: list[dict], repo_ctas: list[dict]) -> None:
    out=[]
    out.append('<p align="center"><img src="assets/generated/scene-01-hero.gif" width="100%" alt="THOTH /FND"></p>')
    if links:
        buttons=[]
        for link in links:
            buttons.append(f'<a href="{link["url"]}"><img src="assets/generated/link-{link["id"].lower()}.gif" height="40" alt="{link["label"]}"></a>')
        out.append('<p align="center">'+'&nbsp;'.join(buttons)+'</p>')
    out.append('<p align="center"><img src="assets/generated/scene-02-builds.gif" width="100%" alt="Current builds"></p>')
    if repo_ctas:
        buttons=[]
        for c in repo_ctas:
            buttons.append(f'<a href="{c["url"]}"><img src="assets/generated/{c["asset"]}" height="40" alt="{c["label"]}"></a>')
        out.append('<p align="center">'+'&nbsp;'.join(buttons)+'</p>')
    out.append('<p align="center"><img src="assets/generated/scene-03-profile.gif" width="100%" alt="Profile"></p>')
    README.write_text('\n\n'.join(out)+'\n',encoding='utf-8')


def preview(path: Path) -> None:
    items=[]
    for name,which in (("scene-01-hero.gif","last"),("scene-02-builds.gif","mid"),("scene-03-profile.gif","mid")):
        im=Image.open(OUT/name)
        im.seek(im.n_frames-1 if which=="last" else im.n_frames//2)
        items.append(im.convert("RGBA"))
    canvas=Image.new("RGBA",(W,sum(x.height for x in items)+40),(13,17,23,255))
    y=0
    for im in items:
        canvas.alpha_composite(im,(0,y)); y+=im.height+20
    canvas.save(path)


def export_frames(prefix: str) -> None:
    # frame audit helpers for package validation
    for gif in ("scene-01-hero.gif","scene-02-builds.gif","scene-03-profile.gif"):
        im=Image.open(OUT/gif)
        for label,idx in (("start",0),("mid",im.n_frames//2),("end",im.n_frames-1)):
            im.seek(idx)
            im.convert("RGBA").save(ROOT/f"{prefix}-{gif[:-4]}-{label}.png")


def main() -> None:
    ap=argparse.ArgumentParser(); ap.add_argument("--demo",action="store_true"); ap.add_argument("--login",default=os.environ.get("GH_LOGIN","thothfnd")); ap.add_argument("--preview",default=""); ap.add_argument("--audit-frames",action="store_true"); args=ap.parse_args()
    config=json.loads(DATA.read_text(encoding="utf-8"))
    if args.demo or not os.environ.get("GITHUB_TOKEN"):
        user,repos,avatar,avatar_bytes=demo_data(args.login)
    else:
        token=os.environ.get("GITHUB_TOKEN","")
        user=github_user(args.login,token); repos=github_repos(args.login,token); avatar,avatar_bytes=download_avatar(user.get("avatar_url",""),token)
    user.setdefault("login",args.login)
    links=active_links(config,user["login"])
    clean_generated()
    for link in links:
        render_button(link["label"],"Open",OUT/f'link-{link["id"].lower()}.gif')
    repo_ctas=[]
    for p in config.get("projects",[])[:2]:
        repo=find_repo(p,repos)
        if repo:
            slug=p["name"].lower().replace(" ","-")
            asset=f"cta-{slug}.gif"
            render_button(p["name"],"Repository",OUT/asset)
            repo_ctas.append({"label":p["name"],"url":repo["html_url"],"asset":asset})
    render_hero(config,user)
    render_builds(config)
    render_profile(config,user,avatar,avatar_bytes)
    write_readme(links,repo_ctas)
    if args.preview: preview(Path(args.preview))
    if args.audit_frames: export_frames("V12-AUDIT")

if __name__=="__main__": main()
