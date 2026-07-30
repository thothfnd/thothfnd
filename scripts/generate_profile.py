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
SCENE1_H = 620
SCENE2_H = 460
SCENE3_H = 520
BTN_W = 260
BTN_H = 52
BG = (7, 8, 10)
PANEL = (13, 15, 19)
INK = (242, 244, 247)
SOFT = (182, 187, 196)
MUTED = (121, 127, 138)
LINE = (48, 52, 60)
ACCENT = (211, 216, 224)

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
    headers = {"User-Agent": "thothfnd-v11-editorial", "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def github_user(login: str, token: str) -> dict:
    return json.loads(req_bytes(f"https://api.github.com/users/{login}", token).decode("utf-8"))


def github_repos(login: str, token: str) -> list[dict]:
    payload = req_bytes(f"https://api.github.com/users/{login}/repos?per_page=100&type=owner&sort=updated", token)
    data = json.loads(payload.decode("utf-8"))
    return [repo for repo in data if not repo.get("fork")]


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
    repos = [
        {"name": "THOTH-Browser", "html_url": f"https://github.com/{login}/THOTH-Browser", "description": "Privacy browser project"},
        {"name": "RelayX", "html_url": f"https://github.com/{login}/RelayX", "description": "RelayX public repository"},
    ]
    return user, repos, None, b"demo-avatar-v11"


def find_repo(project: dict, repos: list[dict]) -> dict | None:
    direct = str(project.get("url") or "").strip()
    if direct:
        return {"name": project.get("name", "PROJECT"), "html_url": direct, "description": project.get("summary", "")}
    candidates = {str(name).lower() for name in project.get("repo_names", [])}
    for repo in repos:
        if str(repo.get("name", "")).lower() in candidates:
            return repo
    return None


def active_links(config: dict, login: str) -> list[dict]:
    result = []
    for item in config.get("links", []):
        url = str(item.get("url") or "").strip()
        if item.get("id") == "github" and url == "AUTO":
            url = f"https://github.com/{login}"
        if url:
            result.append({**item, "url": url})
    return result


def save_gif(frames: list[Image.Image], path: Path, duration: int, loop: int = 0):
    frames[0].save(path, save_all=True, append_images=frames[1:], optimize=False, duration=duration, loop=loop, disposal=2)


def clean_generated():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)


def rounded_panel(size, radius=28, fill=PANEL, outline=(55,60,70), width=1):
    img = Image.new("RGBA", size, (0,0,0,0))
    dr = ImageDraw.Draw(img)
    dr.rounded_rectangle((1,1,size[0]-2,size[1]-2), radius=radius, fill=fill+(255,), outline=outline+(180,), width=width)
    return img


def add_grain(img: Image.Image, seed: str, amount: int = 16):
    rng = random.Random(seed)
    noise = Image.new("L", img.size)
    px = noise.load()
    for y in range(img.size[1]):
        for x in range(img.size[0]):
            px[x,y] = 128 + rng.randint(-amount, amount)
    noise = noise.filter(ImageFilter.GaussianBlur(0.25))
    overlay = Image.new("RGBA", img.size, (0,0,0,0))
    overlay.putalpha(noise)
    tint = Image.new("RGBA", img.size, (255,255,255,22))
    overlay = ImageChops.multiply(tint, overlay)
    img.alpha_composite(overlay)


def vertical_gradient(size, top, bottom):
    w,h = size
    base = Image.new("RGBA", size)
    px = base.load()
    for y in range(h):
        t = y/max(1,h-1)
        c = tuple(int(top[i]*(1-t)+bottom[i]*t) for i in range(3))
        for x in range(w):
            px[x,y] = (*c,255)
    return base


def radial(size, center, radius, color, alpha):
    layer = Image.new("RGBA", size, (0,0,0,0))
    dr = ImageDraw.Draw(layer)
    steps = 18
    for i in range(steps,0,-1):
        r = radius * i/steps
        a = int(alpha * (1 - (i-1)/steps) ** 2)
        dr.ellipse((center[0]-r, center[1]-r, center[0]+r, center[1]+r), fill=(*color,a))
    return layer.filter(ImageFilter.GaussianBlur(radius//6))


def draw_multiline(img, pos, text, fnt, fill, spacing=6):
    dr = ImageDraw.Draw(img)
    dr.multiline_text(pos, text, font=fnt, fill=fill, spacing=spacing)


def fit_lines(text: str, fnt, width: int, max_lines: int) -> list[str]:
    words = text.split()
    draw = ImageDraw.Draw(Image.new("RGB", (1,1)))
    lines = []
    cur = ""
    for word in words:
        test = (cur + " " + word).strip()
        if draw.textbbox((0,0), test, font=fnt)[2] > width and cur:
            lines.append(cur)
            cur = word
            if len(lines) >= max_lines:
                break
        else:
            cur = test
    if cur and len(lines) < max_lines:
        lines.append(cur)
    if len(lines) == max_lines and len(" ".join(lines).split()) < len(words):
        lines[-1] = lines[-1].rstrip(" .") + "…"
    return lines


def draw_button_frame(draw, box, label_left, label_right, sheen_x=None):
    x0,y0,x1,y1 = box
    r = 13
    draw.rounded_rectangle(box, radius=r, fill=(17,20,24), outline=(80,86,96), width=1)
    draw.rounded_rectangle((x0+1,y0+1,x1-1,y0+18), radius=r, fill=(255,255,255,14))
    draw.text((x0+18, y0+15), label_left, font=font("display",18), fill=INK)
    draw.text((x1-18 - ImageDraw.Draw(Image.new("RGB", (1,1))).textbbox((0,0), label_right, font=font("sans",14))[2], y0+18), label_right, font=font("sans",14), fill=SOFT)
    # arrow icon
    ax = x1 - 28
    ay = y0 + 26
    draw.line((ax-8,ay,ax,ay), fill=SOFT, width=2)
    draw.line((ax-4,ay-4,ax,ay), fill=SOFT, width=2)
    draw.line((ax-4,ay+4,ax,ay), fill=SOFT, width=2)
    if sheen_x is not None:
        mask = Image.new("L", (x1-x0, y1-y0), 0)
        md = ImageDraw.Draw(mask)
        md.rounded_rectangle((0,0,x1-x0-1,y1-y0-1), radius=r, fill=255)
        glow = Image.new("RGBA", (x1-x0, y1-y0), (0,0,0,0))
        gd = ImageDraw.Draw(glow)
        gd.rectangle((sheen_x-40,0,sheen_x+40,y1-y0), fill=(255,255,255,28))
        glow.putalpha(ImageChops.multiply(glow.getchannel('A'), mask))
        return glow
    return None


def build_owl_icon(size=(260,220), blink=0.0, head_shift=0.0):
    w,h = size
    img = Image.new("RGBA", size, (0,0,0,0))
    dr = ImageDraw.Draw(img)
    cx, cy = w//2 + int(head_shift), h//2
    # body silhouette
    dr.polygon([(cx-105,cy+65),(cx-128,cy-5),(cx-88,cy-76),(cx-28,cy-108),(cx,cy-86),(cx+28,cy-108),(cx+88,cy-76),(cx+128,cy-5),(cx+105,cy+65),(cx+42,cy+96),(cx,cy+118),(cx-42,cy+96)], fill=(15,18,23,255))
    # feather planes
    dr.polygon([(cx-98,cy+55),(cx-98,cy-12),(cx-65,cy-70),(cx-15,cy-92),(cx-4,cy+95),(cx-54,cy+84)], fill=(28,31,37,255))
    dr.polygon([(cx+98,cy+55),(cx+98,cy-12),(cx+65,cy-70),(cx+15,cy-92),(cx+4,cy+95),(cx+54,cy+84)], fill=(24,27,32,255))
    dr.polygon([(cx-56,cy+88),(cx,cy-66),(cx+56,cy+88),(cx,cy+112)], fill=(11,13,17,255))
    # face mask
    dr.polygon([(cx-62,cy-20),(cx-24,cy-58),(cx,cy-40),(cx+24,cy-58),(cx+62,cy-20),(cx+45,cy+32),(cx,cy+48),(cx-45,cy+32)], fill=(42,47,56,255))
    # eyes
    eye_h = max(4, int(18 * (1-blink)))
    dr.ellipse((cx-42,cy-18,cx-4,cy-18+eye_h), fill=(235,239,244,255))
    dr.ellipse((cx+4,cy-18,cx+42,cy-18+eye_h), fill=(235,239,244,255))
    if blink < 0.85:
        dr.ellipse((cx-32,cy-11,cx-14,cy+7), fill=(10,12,15,255))
        dr.ellipse((cx+14,cy-11,cx+32,cy+7), fill=(10,12,15,255))
    # beak
    dr.polygon([(cx-8,cy+10),(cx+8,cy+10),(cx,cy+28)], fill=(200,205,214,255))
    # top chrome line
    dr.arc((cx-78,cy-88,cx+78,cy-8), start=198, end=342, fill=(190,198,208,110), width=2)
    return img


def draw_wordmark(img, reveal_t: float, chrome_t: float):
    dr = ImageDraw.Draw(img)
    disp = font("display", 74)
    small = font("display", 32)
    base_x = 300
    y = 208
    text = "THOTH"
    # reveal letters one by one
    for i,ch in enumerate(text):
        alpha = max(0.0, min(1.0, (reveal_t*len(text) - i)))
        if alpha <= 0:
            continue
        x = base_x + i*56
        layer = Image.new("RGBA", img.size, (0,0,0,0))
        ld = ImageDraw.Draw(layer)
        ld.text((x,y), ch, font=disp, fill=(205,210,218,int(255*alpha)))
        # chrome sheen mask
        if chrome_t > 0:
            bbox = ld.textbbox((x,y), ch, font=disp)
            sw = int((bbox[2]-bbox[0]) * 0.58)
            sheen_x = int(bbox[0] + (bbox[2]-bbox[0]+sw) * chrome_t - sw)
            ld.rectangle((sheen_x,bbox[1],sheen_x+sw,bbox[3]), fill=(255,255,255,60))
            mask = Image.new("L", img.size, 0)
            ImageDraw.Draw(mask).text((x,y), ch, font=disp, fill=255)
            layer.putalpha(ImageChops.multiply(layer.getchannel('A'), mask))
        img.alpha_composite(layer)
    # /FND
    if reveal_t > 0.65:
        alpha = min(1.0, (reveal_t-0.65)/0.35)
        dr.text((604, 232), "/FND", font=small, fill=(218,223,231,int(255*alpha)))


def hero_background_frame(t: float, seed: str) -> Image.Image:
    img = vertical_gradient((W, SCENE1_H), (8,9,11), (4,5,7))
    img.alpha_composite(radial(img.size, (620,150), 210, (210,214,220), int(46+12*math.sin(t*math.tau))))
    img.alpha_composite(radial(img.size, (120,520), 180, (88,92,100), 20))
    img.alpha_composite(radial(img.size, (780,470), 140, (88,92,100), 14))
    dr = ImageDraw.Draw(img)
    # monolith / arch shapes
    dr.polygon([(0,620),(0,360),(98,280),(160,620)], fill=(11,12,15,255))
    dr.polygon([(880,620),(880,310),(760,250),(676,620)], fill=(10,11,14,255))
    dr.rounded_rectangle((92,118,788,560), radius=36, outline=(48,52,59,90), width=1)
    # subtle top arc
    dr.arc((190,95,700,510), 205, 335, fill=(88,93,102,90), width=1)
    # dust / stars
    rng = random.Random(seed)
    for i in range(26):
        x = (rng.randint(0,W-1) + int(t*22*(1+i%3))) % W
        y = 48 + (i*37) % 300
        a = 55 + int(45*(0.5+0.5*math.sin(t*math.tau + i)))
        r = 1 if i%5 else 2
        dr.ellipse((x-r,y-r,x+r,y+r), fill=(230,233,240,a))
    # linework
    dr.line((64,68,816,68), fill=(56,60,68,120), width=1)
    dr.line((64,552,816,552), fill=(44,48,56,120), width=1)
    add_grain(img, f"hero-{seed}-{int(t*1000)}", amount=8)
    return img


def make_scene_hero(config, user, links):
    frames = []
    name = config.get("display_name", "THOTH /FND")
    title_line = config.get("title_line", "")
    about = config.get("about", [])[:3]
    total = 28
    for i in range(total):
        t = i/(total-1)
        img = hero_background_frame(t, user["login"])
        dr = ImageDraw.Draw(img)
        # panel frame
        dr.rounded_rectangle((24,24,W-24,SCENE1_H-24), radius=32, outline=(72,78,88,180), width=1)
        dr.line((48,92,832,92), fill=(56,60,70,120), width=1)
        # owl reveal
        owl_alpha = min(1.0, max(0.0, (t-0.05)/0.20))
        blink = 0.92 if i in (12,13) else 0.0
        owl = build_owl_icon(blink=blink, head_shift=math.sin(t*math.tau)*1.5)
        owl = owl.resize((220, 186), Image.LANCZOS)
        if owl_alpha < 1:
            a = owl.getchannel('A').point(lambda p: int(p*owl_alpha))
            owl.putalpha(a)
        img.alpha_composite(owl, (82,150))
        # wordmark
        word_t = min(1.0, max(0.0, (t-0.18)/0.36))
        chrome_t = min(1.0, max(0.0, (t-0.48)/0.18))
        draw_wordmark(img, word_t, chrome_t)
        # title line
        if t > 0.54:
            alpha = min(1.0, (t-0.54)/0.16)
            dr.text((302, 300), title_line, font=font("sans", 18), fill=(196,201,210,int(255*alpha)))
        # body text
        body_font = font("serif", 21)
        y = 352
        for idx, paragraph in enumerate(about):
            appear = max(0.0, min(1.0, (t-(0.61 + idx*0.09))/0.12))
            if appear <= 0:
                continue
            wrapped = "\n".join(textwrap.wrap(paragraph, width=62))
            layer = Image.new("RGBA", img.size, (0,0,0,0))
            draw_multiline(layer, (82,y), wrapped, body_font, (238,241,245,int(255*appear)), spacing=8)
            img.alpha_composite(layer)
            y += 64
        # top tiny labels
        dr.text((50, 48), user["login"].upper(), font=font("mono", 10), fill=SOFT)
        dr.text((W-210, 48), "EDITORIAL PROFILE / V11", font=font("mono", 10), fill=MUTED)
        frames.append(img.convert("P", palette=Image.ADAPTIVE, colors=256))
    save_gif(frames, OUT / "scene-01-hero.gif", duration=90)


def builds_background_frame(t: float) -> Image.Image:
    img = vertical_gradient((W, SCENE2_H), (9,10,12), (6,7,9))
    dr = ImageDraw.Draw(img)
    dr.rounded_rectangle((24,24,W-24,SCENE2_H-24), radius=32, outline=(70,76,84,180), width=1)
    dr.line((440,70,440,390), fill=(50,54,62,140), width=1)
    dr.line((48,70,832,70), fill=(50,54,62,120), width=1)
    # calm background bands
    dr.arc((90,100,390,360), 215, 15, fill=(72,78,88,100), width=1)
    dr.arc((510,110,800,350), 195, 350, fill=(72,78,88,100), width=1)
    add_grain(img, f"builds-{int(t*1000)}", amount=7)
    return img


def draw_orbit_block(img, box, t, title, status, summary, mode="orbit"):
    x0,y0,x1,y1 = box
    dr = ImageDraw.Draw(img)
    dr.text((x0, y0), title.upper(), font=font("display", 36), fill=INK)
    dr.text((x0, y0+38), status.upper(), font=font("mono", 10), fill=MUTED)
    summary_lines = fit_lines(summary, font("serif", 18), x1-x0-16, 3)
    tx = x0
    ty = y1 - 88
    for line in summary_lines:
        dr.text((tx, ty), line, font=font("serif", 18), fill=SOFT)
        ty += 24
    cx = x0 + 140
    cy = y0 + 140
    if mode == "orbit":
        for r in (52,78,104):
            dr.ellipse((cx-r,cy-r,cx+r,cy+r), outline=(84,90,100,110), width=1)
        for j,ang in enumerate((t*360, -t*260+75, t*180+140)):
            a = math.radians(ang)
            r = (52,78,104)[j]
            px = cx + math.cos(a)*r
            py = cy + math.sin(a)*r
            dr.ellipse((px-8,py-8,px+8,py+8), fill=(232,236,241,220))
        dr.rounded_rectangle((cx-24,cy-16,cx+24,cy+16), radius=8, outline=(190,196,206,150), fill=(18,21,25), width=1)
        dr.line((cx-12,cy,cx+12,cy), fill=(220,224,230), width=2)
        dr.line((cx,cy-9,cx,cy+9), fill=(220,224,230), width=2)
    else:
        pts = [(x0+78,y0+172),(x0+138,y0+118),(x0+228,y0+132),(x0+248,y0+205),(x0+174,y0+242),(x0+98,y0+226)]
        for a,b in ((0,1),(1,2),(2,3),(3,4),(4,5),(5,0),(1,4),(2,5)):
            dr.line((*pts[a],*pts[b]), fill=(86,92,102,130), width=1)
        pulse = int((t*5)%len(pts))
        for idx,p in enumerate(pts):
            r = 6 if idx==pulse else 4
            fill = (236,239,244,230) if idx==pulse else (178,184,194,210)
            dr.ellipse((p[0]-r,p[1]-r,p[0]+r,p[1]+r), fill=fill)
        # packet moving on one edge
        a = pts[0]; b = pts[1]
        q = (t*2)%1.0
        px = a[0]*(1-q)+b[0]*q
        py = a[1]*(1-q)+b[1]*q
        dr.ellipse((px-5,py-5,px+5,py+5), fill=(255,255,255,240))


def make_scene_builds(config, repos):
    projects = config.get("projects", [])[:2]
    frames = []
    total = 24
    for i in range(total):
        t = i/(total-1)
        img = builds_background_frame(t)
        dr = ImageDraw.Draw(img)
        dr.text((50, 42), "CURRENT BUILDS", font=font("display", 16), fill=SOFT)
        left, right = projects[0], projects[1]
        draw_orbit_block(img, (60,98,396,390), t, left["name"], left.get("status",""), left.get("summary",""), mode="orbit")
        draw_orbit_block(img, (484,98,820,390), t, right["name"], right.get("status",""), right.get("summary",""), mode="network")
        frames.append(img.convert("P", palette=Image.ADAPTIVE, colors=256))
    save_gif(frames, OUT / "scene-02-builds.gif", duration=100)


def style_portrait(avatar: Image.Image | None, login: str) -> Image.Image:
    if avatar is None:
        base = Image.new("RGB", (360,360), (28,30,34))
        dr = ImageDraw.Draw(base)
        dr.ellipse((70,38,290,258), fill=(215,220,226))
        dr.rectangle((112,232,248,340), fill=(215,220,226))
        dr.text((130,150), login[:1].upper(), font=font("display", 110), fill=(20,22,26))
        avatar = base
    img = ImageOps.fit(avatar, (360, 360), method=Image.LANCZOS, centering=(0.5,0.42))
    gray = ImageOps.grayscale(img)
    gray = ImageOps.autocontrast(gray, cutoff=1)
    gray = ImageEnhance.Contrast(gray).enhance(1.55)
    sharp = gray.filter(ImageFilter.DETAIL)
    edges = gray.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(0.6))
    inv = ImageOps.invert(edges)
    merged = Image.blend(sharp, inv, 0.18)
    quant = ImageOps.posterize(merged.convert("RGB"), 4).convert("L")
    out = Image.merge("RGBA", (quant, quant, quant, Image.new("L", quant.size, 255)))
    # vignette
    vig = Image.new("L", out.size, 255)
    vd = ImageDraw.Draw(vig)
    vd.ellipse((-30,-30,out.size[0]+30,out.size[1]+30), fill=220)
    vig = vig.filter(ImageFilter.GaussianBlur(50))
    out.putalpha(vig)
    return out


def make_scene_profile(config, user, avatar, avatar_bytes):
    about = config.get("about", [])
    interests = config.get("interests", [])
    portrait = style_portrait(avatar, user["login"])
    digest = hashlib.sha256(avatar_bytes or b"demo-avatar-v11").hexdigest().upper()[:12]
    frames = []
    total = 28
    for i in range(total):
        t = i/(total-1)
        img = vertical_gradient((W, SCENE3_H), (8,9,12), (6,7,9))
        dr = ImageDraw.Draw(img)
        dr.rounded_rectangle((24,24,W-24,SCENE3_H-24), radius=32, outline=(70,76,84,180), width=1)
        dr.line((48,72,832,72), fill=(52,56,64,120), width=1)
        dr.text((50, 40), "PROFILE", font=font("display", 16), fill=SOFT)
        # left portrait frame
        dr.rounded_rectangle((58,110,388,440), radius=22, fill=(12,14,17), outline=(72,78,88), width=1)
        base = Image.new("RGBA", img.size, (0,0,0,0))
        base.alpha_composite(portrait, (70,122))
        # moving scan band ping-pong
        u = (i % total)/(total-1)
        tri = 1 - abs(2*u - 1)  # 0->1->0
        xpos = int(50 + tri*300)
        band_mask = Image.new("L", portrait.size, 0)
        bd = ImageDraw.Draw(band_mask)
        bd.rectangle((xpos-38, 0, xpos+38, portrait.size[1]), fill=180)
        band_mask = band_mask.filter(ImageFilter.GaussianBlur(22))
        enhanced = ImageEnhance.Contrast(portrait.convert("RGB")).enhance(1.28)
        enhanced = ImageEnhance.Brightness(enhanced).enhance(1.08).convert("RGBA")
        layer = portrait.copy()
        banded = Image.new("RGBA", portrait.size, (0,0,0,0))
        banded.paste(enhanced, (0,0), band_mask)
        layer.alpha_composite(banded)
        # subtle scan line
        line = Image.new("RGBA", portrait.size, (0,0,0,0))
        ld = ImageDraw.Draw(line)
        ld.rectangle((xpos, 0, xpos+2, portrait.size[1]), fill=(255,255,255,70))
        line = line.filter(ImageFilter.GaussianBlur(1))
        layer.alpha_composite(line)
        base.alpha_composite(layer, (70,122))
        img.alpha_composite(base)
        # right text
        dr.text((446, 116), config.get("display_name", "THOTH /FND"), font=font("display", 30), fill=INK)
        dr.text((446, 154), user["login"], font=font("mono", 11), fill=MUTED)
        meta = [
            ("SOURCE", "github/avatar"),
            ("DIGEST", digest),
            ("STATE", "synchronized"),
            ("LOOP", "bidirectional scan"),
        ]
        y = 192
        for k,v in meta:
            dr.text((446, y), k, font=font("mono", 10), fill=MUTED)
            dr.text((548, y-3), v, font=font("sans", 15), fill=SOFT)
            y += 28
        dr.text((446, 314), "INTERESTS", font=font("mono", 10), fill=MUTED)
        y = 342
        for item in interests[:9]:
            dr.text((446, y), item.upper(), font=font("sans", 16), fill=INK if y < 402 else SOFT)
            y += 20
        add_grain(img, f"profile-{i}", amount=6)
        frames.append(img.convert("P", palette=Image.ADAPTIVE, colors=256))
    save_gif(frames, OUT / "scene-03-profile.gif", duration=100)


def make_button(label: str, action: str, path: Path):
    frames = []
    total = 18
    for i in range(total):
        img = Image.new("RGBA", (BTN_W, BTN_H), (0,0,0,0))
        sheen = int(-40 + (BTN_W+80)*(i/(total-1)))
        overlay = draw_button_frame(ImageDraw.Draw(img), (0,0,BTN_W-1,BTN_H-1), label, action, sheen_x=sheen)
        if overlay is not None:
            img.alpha_composite(overlay, (0,0))
        frames.append(img.convert("P", palette=Image.ADAPTIVE, colors=256))
    save_gif(frames, path, duration=90)


def update_readme(user, links, repo_ctas):
    parts = []
    parts.append(f'<p align="center"><img src="assets/generated/scene-01-hero.gif" width="100%" alt="V11 hero"></p>')
    if links:
        link_html = []
        for link in links:
            slug = link["id"].lower()
            img = f'assets/generated/link-{slug}.gif'
            link_html.append(f'<a href="{link["url"]}"><img src="{img}" height="52" alt="{link["label"]}"></a>')
        parts.append(f'<p align="center">{"&nbsp;".join(link_html)}</p>')
    parts.append(f'<p align="center"><img src="assets/generated/scene-02-builds.gif" width="100%" alt="V11 builds"></p>')
    if repo_ctas:
        rows = []
        for cta in repo_ctas:
            rows.append(f'<a href="{cta["url"]}"><img src="assets/generated/{cta["asset"]}" height="52" alt="{cta["label"]}"></a>')
        parts.append(f'<p align="center">{"&nbsp;".join(rows)}</p>')
    parts.append(f'<p align="center"><img src="assets/generated/scene-03-profile.gif" width="100%" alt="V11 profile"></p>')
    md = "\n\n".join(parts) + "\n"
    README.write_text(md, encoding="utf-8")


def static_preview(path: Path):
    hero = Image.open(OUT / "scene-01-hero.gif")
    hero.seek(hero.n_frames-1)
    hero_final = hero.convert("RGBA")
    builds = Image.open(OUT / "scene-02-builds.gif")
    builds.seek(builds.n_frames//2)
    builds_frame = builds.convert("RGBA")
    profile = Image.open(OUT / "scene-03-profile.gif")
    profile.seek(profile.n_frames//2)
    profile_frame = profile.convert("RGBA")
    H = hero_final.height + builds_frame.height + profile_frame.height + 40
    canvas = Image.new("RGBA", (W, H), BG+(255,))
    y = 0
    for im in (hero_final, builds_frame, profile_frame):
        canvas.alpha_composite(im, (0,y))
        y += im.height + 20
    canvas.save(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--login", default=os.environ.get("GH_LOGIN", "thothfnd"))
    parser.add_argument("--preview", default="")
    args = parser.parse_args()

    config = json.loads(DATA.read_text(encoding="utf-8"))
    if args.demo or not os.environ.get("GITHUB_TOKEN"):
        user, repos, avatar, avatar_bytes = demo_data(args.login)
    else:
        token = os.environ.get("GITHUB_TOKEN", "")
        user = github_user(args.login, token)
        repos = github_repos(args.login, token)
        avatar, avatar_bytes = download_avatar(user.get("avatar_url", ""), token)
    user.setdefault("login", args.login)
    links = active_links(config, user["login"])
    clean_generated()
    # render buttons first for active links
    for link in links:
        make_button(link["label"], "OPEN", OUT / f'link-{link["id"].lower()}.gif')
    repo_ctas = []
    for project in config.get("projects", [])[:2]:
        repo = find_repo(project, repos)
        if repo:
            slug = project["name"].lower().replace(" ", "-")
            asset = f'cta-{slug}.gif'
            make_button(project["name"].upper(), "OPEN REPOSITORY", OUT / asset)
            repo_ctas.append({"label": project["name"], "asset": asset, "url": repo["html_url"]})
    make_scene_hero(config, user, links)
    make_scene_builds(config, repos)
    make_scene_profile(config, user, avatar, avatar_bytes)
    update_readme(user, links, repo_ctas)
    if args.preview:
        static_preview(Path(args.preview))

if __name__ == "__main__":
    main()
