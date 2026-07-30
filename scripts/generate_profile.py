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
BG = (5, 6, 8)
INK = (241, 243, 246)
SOFT = (182, 188, 198)
MUTED = (112, 120, 133)
LINE = (38, 43, 52)
CHROME = (215, 220, 228)

ASCII_RAMP = " .,:;irsXA253hMHGS#9B&@"

FONT_CANDIDATES = {
    "display": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ],
    "sans": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ],
    "serif": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    ],
    "mono": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ],
}


def font(kind: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_CANDIDATES[kind]:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default(size=size)


def req_bytes(url: str, token: str = "") -> bytes:
    headers = {"User-Agent": "thothfnd-v10-nocturne", "Accept": "application/vnd.github+json"}
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


def demo_data(login: str) -> tuple[dict, list[dict], Image.Image | None, bytes]:
    user = {
        "login": login,
        "name": login,
        "html_url": f"https://github.com/{login}",
        "avatar_url": "",
    }
    repos = [
        {"name": "THOTH-Browser", "html_url": f"https://github.com/{login}/THOTH-Browser", "description": "Privacy browser project"},
        {"name": "RelayX", "html_url": f"https://github.com/{login}/RelayX", "description": "RelayX public repository"},
    ]
    return user, repos, None, b"demo-avatar-v10"


def find_repo(project: dict, repos: list[dict]) -> dict | None:
    direct = str(project.get("url") or "").strip()
    if direct:
        return {"name": project.get("name", "PROJECT"), "html_url": direct, "description": project.get("description", "")}
    candidates = {str(name).lower() for name in project.get("repo_names", [])}
    for repo in repos:
        if str(repo.get("name", "")).lower() in candidates:
            return repo
    return None


def active_links(config: dict, login: str) -> list[dict]:
    result: list[dict] = []
    for item in config.get("links", []):
        url = str(item.get("url") or "").strip()
        if url == "AUTO" and item.get("id") == "github":
            url = f"https://github.com/{login}"
        if url:
            result.append({**item, "url": url})
    return result


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def ease(t: float) -> float:
    t = clamp(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def rgba(hex_rgb: tuple[int, int, int], alpha: int = 255) -> tuple[int, int, int, int]:
    return (*hex_rgb, alpha)


def vertical_gradient(size: tuple[int, int], stops: list[tuple[float, tuple[int, int, int]]]) -> Image.Image:
    w, h = size
    strip = Image.new("RGB", (1, h))
    draw = ImageDraw.Draw(strip)
    stops = sorted(stops, key=lambda x: x[0])
    for y in range(h):
        t = y / max(1, h - 1)
        left, right = stops[0], stops[-1]
        for i in range(len(stops) - 1):
            if stops[i][0] <= t <= stops[i + 1][0]:
                left, right = stops[i], stops[i + 1]
                break
        span = max(1e-9, right[0] - left[0])
        u = (t - left[0]) / span
        color = tuple(int(left[1][k] * (1-u) + right[1][k] * u) for k in range(3))
        draw.point((0, y), fill=color)
    return strip.resize((w, h))

def radial_glow(size: tuple[int, int], center: tuple[int, int], radius: int, color: tuple[int, int, int], alpha: int) -> Image.Image:
    w, h = size
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    steps = 16
    cx, cy = center
    for i in range(steps, 0, -1):
        r = radius * i / steps
        a = int(alpha * ((steps - i + 1) / steps) ** 2)
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(*color, a))
    return layer.filter(ImageFilter.GaussianBlur(radius // 7))


def metallic_fill(mask: Image.Image, light: tuple[int, int, int] = (238, 240, 244), dark: tuple[int, int, int] = (33, 37, 44)) -> Image.Image:
    w, h = mask.size
    strip = Image.new("RGBA", (w, 1))
    draw = ImageDraw.Draw(strip)
    for x in range(w):
        t = x / max(1, w - 1)
        shine = 0.20 + 0.58 * math.exp(-((t - 0.34) / 0.10) ** 2) + 0.30 * math.exp(-((t - 0.74) / 0.07) ** 2)
        c = tuple(int(dark[k] + (light[k] - dark[k]) * clamp(shine, 0, 1)) for k in range(3))
        draw.point((x, 0), fill=(*c, 255))
    grad = strip.resize((w, h))
    grad.putalpha(mask)
    return grad

def composite_text(img: Image.Image, xy: tuple[int, int], text: str, fnt, fill, anchor=None, alpha: float = 1.0, spacing: int = 4) -> None:
    if alpha <= 0:
        return
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    color = (*fill[:3], int(255 * clamp(alpha, 0, 1))) if len(fill) == 3 else fill
    draw.multiline_text(xy, text, font=fnt, fill=color, anchor=anchor, spacing=spacing)
    img.alpha_composite(layer)


def fit_text_lines(text: str, fnt, max_width: int, max_lines: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    for word in words:
        test = (cur + " " + word).strip()
        bbox = dummy.textbbox((0, 0), test, font=fnt)
        if bbox[2] - bbox[0] > max_width and cur:
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


def draw_noise_stars(img: Image.Image, stars: list[tuple[float, float, int, float]], phase: float) -> None:
    draw = ImageDraw.Draw(img)
    for sx, sy, r, seed in stars:
        pulse = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(phase * 2 * math.pi + seed))
        a = int(155 * pulse)
        draw.ellipse((sx - r, sy - r, sx + r, sy + r), fill=(220, 224, 230, a))


def make_stars(seed: str, count: int, w: int, h: int, y0: int = 0, y1: int | None = None) -> list[tuple[float, float, int, float]]:
    rng = random.Random(seed)
    y1 = h if y1 is None else y1
    return [(rng.uniform(20, w - 20), rng.uniform(y0, y1), rng.choice([1, 1, 1, 2]), rng.random() * math.tau) for _ in range(count)]


def fog_texture(seed: str, w: int, h: int, density: int = 20) -> Image.Image:
    rng = random.Random(seed)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for _ in range(density):
        cx = rng.randint(-100, w + 100)
        cy = rng.randint(0, h)
        rx = rng.randint(80, 240)
        ry = rng.randint(25, 75)
        a = rng.randint(8, 28)
        shade = rng.randint(90, 170)
        draw.ellipse((cx-rx, cy-ry, cx+rx, cy+ry), fill=(shade, shade+3, shade+9, a))
    return layer.filter(ImageFilter.GaussianBlur(36))


def shift_layer(layer: Image.Image, dx: int, dy: int = 0) -> Image.Image:
    result = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    w, h = layer.size
    dx = dx % w
    result.alpha_composite(layer, (dx, dy))
    result.alpha_composite(layer, (dx - w, dy))
    return result


def draw_frame_border(img: Image.Image, radius: int = 24) -> None:
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((1, 1, img.width-2, img.height-2), radius=radius, outline=(95, 102, 113, 110), width=1)
    draw.line((34, 26, img.width-34, 26), fill=(38, 43, 51, 130), width=1)


def owl_layer(size: tuple[int, int], phase: float, reveal: float = 1.0, center: tuple[int, int] = (440, 245), scale: float = 1.0) -> Image.Image:
    """A dark sculptural owl built as layered feather planes rather than a cartoon body."""
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    cx, cy = center
    bob = math.sin(phase * math.tau) * 2.5

    # large shadow wings behind the head
    shadow = Image.new("RGBA", size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    wing_alpha = int(145 * reveal)
    sd.polygon([(cx-30*scale,cy+10*scale+bob),(cx-240*scale,cy+20*scale+bob),(cx-182*scale,cy+145*scale+bob),(cx-52*scale,cy+100*scale+bob)], fill=(9,10,13,wing_alpha))
    sd.polygon([(cx+30*scale,cy+10*scale+bob),(cx+240*scale,cy+20*scale+bob),(cx+182*scale,cy+145*scale+bob),(cx+52*scale,cy+100*scale+bob)], fill=(9,10,13,wing_alpha))
    shadow = shadow.filter(ImageFilter.GaussianBlur(6))
    layer.alpha_composite(shadow)

    # head / cheek silhouette
    mask = Image.new("L", size, 0)
    d = ImageDraw.Draw(mask)
    pts = [
        (cx-155*scale, cy-55*scale+bob),
        (cx-105*scale, cy-154*scale+bob),
        (cx-42*scale, cy-108*scale+bob),
        (cx, cy-135*scale+bob),
        (cx+42*scale, cy-108*scale+bob),
        (cx+105*scale, cy-154*scale+bob),
        (cx+155*scale, cy-55*scale+bob),
        (cx+140*scale, cy+62*scale+bob),
        (cx+78*scale, cy+130*scale+bob),
        (cx, cy+172*scale+bob),
        (cx-78*scale, cy+130*scale+bob),
        (cx-140*scale, cy+62*scale+bob),
    ]
    d.polygon(pts, fill=int(255*reveal))
    # carved center notch gives the head a less mascot-like silhouette
    d.polygon([(cx-24*scale,cy-126*scale+bob),(cx,cy-92*scale+bob),(cx+24*scale,cy-126*scale+bob)], fill=int(70*reveal))
    metal = metallic_fill(mask, light=(235,238,242), dark=(20,22,27))
    metal = ImageEnhance.Brightness(metal).enhance(0.66 + 0.34*reveal)
    layer.alpha_composite(metal)

    face = Image.new("RGBA", size, (0,0,0,0))
    fd = ImageDraw.Draw(face)
    a=int(245*reveal)
    # feather planes around eyes
    fd.polygon([(cx-138*scale,cy-48*scale+bob),(cx-27*scale,cy-84*scale+bob),(cx-48*scale,cy+20*scale+bob),(cx-128*scale,cy+48*scale+bob)], fill=(9,11,14,a))
    fd.polygon([(cx+138*scale,cy-48*scale+bob),(cx+27*scale,cy-84*scale+bob),(cx+48*scale,cy+20*scale+bob),(cx+128*scale,cy+48*scale+bob)], fill=(9,11,14,a))
    fd.polygon([(cx-35*scale,cy-84*scale+bob),(cx,cy-105*scale+bob),(cx+35*scale,cy-84*scale+bob),(cx,cy+10*scale+bob)], fill=(41,45,53,int(215*reveal)))

    # almond eyes; mostly dark, with a thin liquid-chrome iris
    blink = abs((phase % 1.0)-0.50) < 0.026
    for sign in (-1,1):
        ex=cx+sign*63*scale; ey=cy-37*scale+bob
        glow=radial_glow(size,(int(ex),int(ey)),40,(215,222,233),int(72*reveal))
        face.alpha_composite(glow)
        if blink:
            fd.line((ex-30*scale,ey,ex+30*scale,ey),fill=(211,216,224,a),width=max(1,int(2*scale)))
        else:
            eye=[(ex-34*scale,ey),(ex-18*scale,ey-14*scale),(ex+18*scale,ey-14*scale),(ex+34*scale,ey),(ex+18*scale,ey+14*scale),(ex-18*scale,ey+14*scale)]
            fd.polygon(eye,fill=(191,197,207,a),outline=(240,242,245,a))
            fd.ellipse((ex-10*scale,ey-10*scale,ex+10*scale,ey+10*scale),fill=(8,9,11,a))
            fd.ellipse((ex-2*scale,ey-6*scale,ex+2*scale,ey-2*scale),fill=(255,255,255,int(230*reveal)))
    # beak and feather spine
    fd.polygon([(cx,cy-10*scale+bob),(cx+18*scale,cy+20*scale+bob),(cx,cy+52*scale+bob),(cx-18*scale,cy+20*scale+bob)],fill=(118,124,135,int(235*reveal)))
    fd.line((cx,cy+52*scale+bob,cx,cy+145*scale+bob),fill=(103,109,119,int(100*reveal)),width=1)

    # thin feather cuts — asymmetric enough to feel designed rather than generated by a repeated pattern
    cuts=[(-118,-5,-68,38),(-105,40,-54,73),(-85,78,-37,106),(118,-5,68,38),(105,40,54,73),(85,78,37,106)]
    for x1,y1,x2,y2 in cuts:
        fd.line((cx+x1*scale,cy+y1*scale+bob,cx+x2*scale,cy+y2*scale+bob),fill=(151,157,168,int(90*reveal)),width=1)
    # brow edges
    fd.arc((cx-129*scale,cy-102*scale+bob,cx-12*scale,cy+10*scale+bob),205,335,fill=(222,225,230,int(180*reveal)),width=max(1,int(2*scale)))
    fd.arc((cx+12*scale,cy-102*scale+bob,cx+129*scale,cy+10*scale+bob),205,335,fill=(222,225,230,int(180*reveal)),width=max(1,int(2*scale)))

    # barely perceptible head movement
    face=face.rotate(math.sin(phase*math.tau*.55)*0.85,resample=Image.Resampling.BICUBIC,center=(cx,cy))
    layer.alpha_composite(face)
    return layer

def chrome_wordmark_layer(size: tuple[int,int], reveal: float, shimmer: float, xy=(70, 402)) -> Image.Image:
    layer = Image.new("RGBA", size, (0,0,0,0))
    x, y = xy
    f = font("display", 82)
    f2 = font("sans", 45)
    mask = Image.new("L", size, 0)
    md = ImageDraw.Draw(mask)
    md.text((x, y), "THOTH", font=f, fill=int(255*reveal), anchor="la")
    bbox = md.textbbox((x, y), "THOTH", font=f, anchor="la")
    slash_x = bbox[2] + 18
    md.text((slash_x, y+17), "/FND", font=f2, fill=int(245*reveal), anchor="la")
    metal = metallic_fill(mask, light=(250,250,252), dark=(67,72,81))
    layer.alpha_composite(metal)
    # traveling specular highlight across wordmark
    shine_x = int(-150 + shimmer * (size[0] + 300))
    shine = Image.new("RGBA", size, (0,0,0,0))
    sd = ImageDraw.Draw(shine)
    sd.polygon([(shine_x-20, y-20),(shine_x+40,y-20),(shine_x-55,y+115),(shine_x-115,y+115)], fill=(255,255,255,80))
    shine.putalpha(ImageChops.multiply(shine.getchannel("A"), mask))
    layer.alpha_composite(shine)
    return layer


def create_intro_frame(cfg: dict, idx: int, frames: int, stars_data, fog_a, fog_b) -> Image.Image:
    t = idx / max(1, frames-1)
    phase = t
    base = vertical_gradient((W, 650), [(0,(3,4,6)),(.45,(7,8,11)),(1,(2,3,4))]).convert("RGBA")
    # True scenic background: huge moon, distant architectural silhouettes, fog and dust.
    moon = radial_glow(base.size, (440, 210), 255, (195,201,211), 100)
    base.alpha_composite(moon)
    d = ImageDraw.Draw(base)
    # distant moon disc
    d.ellipse((290,60,590,360), fill=(24,27,33,210), outline=(88,94,105,90), width=1)
    d.ellipse((310,80,570,340), outline=(53,59,69,100), width=1)
    # monumental architecture, no perspective grid
    for x, wid, hh, op in [(20,74,360,120),(112,34,290,80),(760,50,320,95),(822,36,250,70)]:
        d.rounded_rectangle((x,650-hh,x+wid,650), radius=9, fill=(10,12,15,op), outline=(36,41,49,op), width=1)
        d.rectangle((x+8,650-hh+24,x+wid-8,650-hh+30), fill=(43,48,57,op//2))
    # broken arch behind owl
    d.arc((170,70,710,590), 197, 343, fill=(55,61,70,110), width=3)
    d.arc((205,105,675,555), 197, 343, fill=(23,27,32,160), width=2)
    # ground ridges
    d.polygon([(0,555),(90,520),(180,542),(275,504),(360,535),(470,500),(560,534),(660,500),(760,528),(880,490),(880,650),(0,650)], fill=(5,6,8,255))
    d.line([(0,559),(90,524),(180,546),(275,508),(360,539),(470,504),(560,538),(660,504),(760,532),(880,494)], fill=(38,43,52,140), width=2)
    draw_noise_stars(base, stars_data, phase)
    # drifting fog
    base.alpha_composite(shift_layer(fog_a, int(phase*140)-60, 70))
    base.alpha_composite(shift_layer(fog_b, int(-phase*95)+20, 370))

    # Sequence timing: eyes/shape first, then mark, then copy. Entire scene remains alive after reveal.
    owl_reveal = ease((t - 0.06) / 0.25)
    owl_y = int(205 + (1-owl_reveal)*22)
    base.alpha_composite(owl_layer(base.size, phase, owl_reveal, center=(440,owl_y), scale=0.83))

    mark_reveal = ease((t - 0.27) / 0.24)
    base.alpha_composite(chrome_wordmark_layer(base.size, mark_reveal, (t*1.55)%1.0, xy=(177,405)))

    copy_alpha = ease((t - 0.48)/0.18)
    identity = cfg.get("identity", {})
    main_line = str(identity.get("lead", ""))
    second_line = str(identity.get("sublead", ""))
    lead_f = font("serif", 18)
    sub_f = font("sans", 14)
    lead_lines = fit_text_lines(main_line, lead_f, 720, 2)
    y = 528
    for line in lead_lines:
        composite_text(base, (440,y), line, lead_f, SOFT, anchor="ma", alpha=copy_alpha)
        y += 27
    second_lines = fit_text_lines(second_line, sub_f, 720, 2)
    y += 5
    for line in second_lines:
        composite_text(base, (440,y), line, sub_f, MUTED, anchor="ma", alpha=ease((t-0.57)/0.18))
        y += 23

    draw_frame_border(base, 26)
    return base.convert("RGB")


def draw_project_portal(img: Image.Image, rect: tuple[int,int,int,int], kind: str, phase: float, title: str, subtitle: str, status: str) -> None:
    x0,y0,x1,y1 = rect
    d = ImageDraw.Draw(img)
    # atmospheric large plate integrated in scene, not a generic card
    d.rounded_rectangle(rect, radius=22, fill=(10,12,15,210), outline=(57,64,76,170), width=1)
    glow = radial_glow(img.size, ((x0+x1)//2,(y0+y1)//2-40), 180, (150,160,178), 35)
    img.alpha_composite(glow)
    d = ImageDraw.Draw(img)
    if kind == "thoth":
        cx, cy = (x0+x1)//2, y0+210
        for r, speed, op in [(110,1.0,95),(76,-1.5,125),(44,2.0,155)]:
            angle = phase*360*speed
            # draw segmented orbit
            for seg in range(8):
                a0 = math.radians(angle + seg*45)
                a1 = math.radians(angle + seg*45 + 23)
                pts = []
                for s in range(10):
                    a = a0 + (a1-a0)*s/9
                    pts.append((cx+math.cos(a)*r, cy+math.sin(a)*r*0.56))
                d.line(pts, fill=(145,153,166,op), width=2)
        d.rounded_rectangle((cx-72,cy-45,cx+72,cy+45), radius=14, outline=(198,203,211,170), width=2)
        d.line((cx-50,cy-15,cx+50,cy-15), fill=(70,77,89,170), width=2)
        # small owl crest
        mini = owl_layer(img.size, phase, 1.0, center=(cx,cy-2), scale=0.18)
        img.alpha_composite(mini)
    else:
        cx, cy = (x0+x1)//2, y0+212
        rng = random.Random("relayx-v10")
        nodes = [(cx+rng.randint(-122,122), cy+rng.randint(-90,90), rng.random()*math.tau) for _ in range(13)]
        dd = ImageDraw.Draw(img)
        for i,(x,y,s) in enumerate(nodes):
            for j in range(i+1,len(nodes)):
                x2,y2,s2=nodes[j]
                dist=math.hypot(x2-x,y2-y)
                if dist < 112:
                    pulse=0.24+0.22*(.5+.5*math.sin(phase*math.tau*2+s+s2))
                    dd.line((x,y,x2,y2), fill=(112,121,136,int(120*pulse)), width=1)
        for x,y,s in nodes:
            rr=3+2*(.5+.5*math.sin(phase*math.tau*1.4+s))
            dd.ellipse((x-rr,y-rr,x+rr,y+rr), fill=(215,219,226,180), outline=(91,99,112,200))
        # moving packet
        p=phase%1
        x=cx-118+236*p
        y=cy+math.sin(p*math.pi*2)*28
        packet=radial_glow(img.size,(int(x),int(y)),24,(235,238,243),110)
        img.alpha_composite(packet)
    d = ImageDraw.Draw(img)
    title_f = font("display", 31)
    sub_f = font("sans", 13)
    status_f = font("mono", 11)
    d.text((x0+28,y1-104), title, font=title_f, fill=INK)
    d.text((x0+30,y1-66), subtitle, font=sub_f, fill=SOFT)
    d.text((x1-28,y1-32), status, font=status_f, fill=MUTED, anchor="ra")


def create_builds_frame(cfg: dict, repos: list[dict], idx: int, frames: int, fog) -> Image.Image:
    t=idx/max(1,frames-1)
    img=vertical_gradient((W,620),[(0,(3,4,6)),(.46,(8,9,12)),(1,(3,4,6))]).convert("RGBA")
    # one shared landscape instead of two UI cards
    img.alpha_composite(radial_glow(img.size,(220,250),310,(126,136,153),42))
    img.alpha_composite(radial_glow(img.size,(660,250),310,(102,113,133),34))
    d=ImageDraw.Draw(img)
    # dark horizon and broken vertical monoliths
    d.polygon([(0,420),(95,382),(170,410),(255,372),(350,405),(440,360),(545,408),(640,376),(730,402),(880,352),(880,620),(0,620)],fill=(4,5,7,255))
    d.line([(0,421),(95,383),(170,411),(255,373),(350,406),(440,361),(545,409),(640,377),(730,403),(880,353)],fill=(38,43,52,130),width=1)
    d.rectangle((424,0,456,620),fill=(6,7,9,190))
    d.line((440,0,440,620),fill=(69,76,89,115),width=1)
    # circular traces become environmental structures, not components
    for r,op in [(260,80),(215,70),(170,55)]:
        d.arc((-85,20,-85+r*2,20+r*2),210,335,fill=(74,81,94,op),width=1)
        d.arc((525,10,525+r*2,10+r*2),205,330,fill=(69,77,91,op),width=1)
    img.alpha_composite(shift_layer(fog,int(t*110)-50,205))

    projects=cfg.get("projects",[])[:2]
    left=projects[0] if projects else {"name":"THOTH BROWSER","subtitle":"","status":"IN DEVELOPMENT"}
    right=projects[1] if len(projects)>1 else {"name":"RELAYX","subtitle":"","status":"IN DEVELOPMENT"}
    lr=find_repo(left,repos); rr=find_repo(right,repos)

    # THOTH browser world — browser boundary rings + owl crest
    cx,cy=220,238
    dd=ImageDraw.Draw(img)
    for r,speed,op in [(130,1.0,105),(96,-1.35,125),(62,1.8,150)]:
        ang=t*360*speed
        for seg in range(7):
            a0=math.radians(ang+seg*360/7); a1=a0+math.radians(22)
            pts=[(cx+math.cos(a0+(a1-a0)*q/8)*r,cy+math.sin(a0+(a1-a0)*q/8)*r*.58) for q in range(9)]
            dd.line(pts,fill=(155,163,176,op),width=2)
    dd.rounded_rectangle((cx-84,cy-50,cx+84,cy+50),radius=13,outline=(210,214,221,155),width=2)
    dd.line((cx-58,cy-22,cx+58,cy-22),fill=(68,75,87,160),width=2)
    img.alpha_composite(owl_layer(img.size,t,1.0,center=(cx,cy+5),scale=.23))

    # RelayX world — layered relay lattice and moving packet
    cx2,cy2=660,235
    rng=random.Random("relayx-v10-world")
    nodes=[(cx2+rng.randint(-145,145),cy2+rng.randint(-110,110),rng.random()*math.tau) for _ in range(16)]
    dd=ImageDraw.Draw(img)
    for i,(x,y,s0) in enumerate(nodes):
        for j in range(i+1,len(nodes)):
            x2,y2,s2=nodes[j]
            dist=math.hypot(x2-x,y2-y)
            if dist<126:
                pulse=.36+.24*(.5+.5*math.sin(t*math.tau*2+s0+s2))
                dd.line((x,y,x2,y2),fill=(112,122,139,int(110*pulse)),width=1)
    for x,y,s0 in nodes:
        rrn=2.5+2.2*(.5+.5*math.sin(t*math.tau*1.3+s0))
        dd.ellipse((x-rrn,y-rrn,x+rrn,y+rrn),fill=(218,222,229,180),outline=(89,97,111,200))
    p=t%1; px=cx2-140+280*p; py=cy2+math.sin(p*math.tau)*38
    img.alpha_composite(radial_glow(img.size,(int(px),int(py)),28,(240,242,245),120))

    # typography belongs to the landscape, with no sub-panels
    title=font("display",34); sub=font("sans",13); mono=font("mono",10)
    dd=ImageDraw.Draw(img)
    dd.text((42,484),str(left.get("name","THOTH BROWSER")),font=title,fill=INK)
    dd.text((44,529),str(left.get("subtitle","")),font=sub,fill=SOFT)
    dd.text((42,563),"PUBLIC REPOSITORY" if lr else str(left.get("status","IN DEVELOPMENT")),font=mono,fill=MUTED)
    # right text is right-aligned so the scene feels intentionally mirrored
    dd.text((838,484),str(right.get("name","RELAYX")),font=title,fill=INK,anchor="ra")
    dd.text((836,529),str(right.get("subtitle","")),font=sub,fill=SOFT,anchor="ra")
    dd.text((838,563),"PUBLIC REPOSITORY" if rr else str(right.get("status","IN DEVELOPMENT")),font=mono,fill=MUTED,anchor="ra")
    draw_frame_border(img,26)
    return img.convert("RGB")

def ascii_lines(image: Image.Image | None, cols: int=62) -> list[str]:
    if image is None:
        fallback=[
            "                .;xXNNXx;.",
            "             .xN@@@@@@@@@@Nx.",
            "           :N@@@Xx;..;xX@@@N:",
            "          x@@@x          x@@@x",
            "         X@@N              N@@X",
            "         @@N     .;;;;.     N@@",
            "         @@x    x@@@@@@x    x@@",
            "         N@N    X@x  x@X    N@N",
            "          x@X    .xXXx.    X@x",
            "           :XNx.        .xNX:",
            "              ;xXNNNNXx;",
        ]
        return fallback
    img=image.convert("L")
    # center-crop and improve local readability without heavyweight CV dependencies
    w,h=img.size
    side=min(w,h)
    left=(w-side)//2; top=(h-side)//2
    img=img.crop((left,top,left+side,top+side))
    img=ImageOps.autocontrast(img)
    img=ImageEnhance.Contrast(img).enhance(1.65)
    rows=max(22,int(cols*0.48))
    img=img.resize((cols,rows),Image.Resampling.LANCZOS)
    px=img.load(); out=[]
    for y in range(rows):
        s=""
        for x in range(cols):
            v=px[x,y]
            s+=ASCII_RAMP[int((255-v)/255*(len(ASCII_RAMP)-1))]
        out.append(s.rstrip())
    return out


def create_profile_frame(cfg: dict, avatar: Image.Image | None, digest: str, idx: int, frames: int, stars_data, fog) -> Image.Image:
    t=idx/max(1,frames-1)
    img=vertical_gradient((W,620),[(0,(3,4,6)),(.50,(7,8,11)),(1,(3,4,6))]).convert("RGBA")
    img.alpha_composite(radial_glow(img.size,(245,300),300,(116,126,143),36))
    img.alpha_composite(radial_glow(img.size,(695,300),250,(89,99,115),25))
    draw_noise_stars(img,stars_data,t)
    img.alpha_composite(shift_layer(fog,int(-t*85)+40,260))
    d=ImageDraw.Draw(img)
    # open composition: a single division and orbital contours, no internal cards
    d.line((438,44,438,574),fill=(48,54,64,125),width=1)
    for i in range(4):
        yy=100+i*126+math.sin(t*math.tau+i)*7
        d.arc((355,yy-80,980,yy+120),194,338,fill=(40+i*4,46+i*4,56+i*4,78),width=1)
    # left ASCII is a floating object in the environment
    lines=ascii_lines(avatar,62)
    mono=font("mono",8)
    line_h=8
    top=128
    cycle=(t*1.25)%1
    reveal_count=int(clamp((cycle-.04)/.70,0,1)*len(lines))
    glow=radial_glow(img.size,(222,300),195,(182,190,202),35)
    img.alpha_composite(glow)
    d=ImageDraw.Draw(img)
    for i,line in enumerate(lines):
        alpha=230 if i<reveal_count else 22
        d.text((222,top+i*line_h),line,font=mono,fill=(226,230,235,alpha),anchor="ma")
    scan_y=top+int(cycle*max(1,len(lines)*line_h))
    d.line((74,scan_y,372,scan_y),fill=(245,246,248,145),width=1)
    # oversized ghost mark behind ASCII
    ghost=font("display",58)
    d.text((222,500),"THOTH",font=ghost,fill=(52,57,66,75),anchor="ma")
    meta=font("mono",9)
    d.text((70,555),f"avatar {digest[:10].lower()} · github",font=meta,fill=MUTED)

    identity=cfg.get("identity",{})
    title_f=font("display",27)
    serif_f=font("serif",16)
    d.text((480,78),"WHAT KEEPS ME CURIOUS",font=title_f,fill=INK)
    lead=str(identity.get("profile_line",identity.get("lead","")))
    lead_lines=fit_text_lines(lead,serif_f,340,5)
    yy=130
    for line in lead_lines:
        d.text((480,yy),line,font=serif_f,fill=SOFT)
        yy+=25
    yy+=28
    interests=[str(x) for x in identity.get("interests",[])][:9]
    for i,item in enumerate(interests):
        drift=math.sin(t*math.tau+i*.71)*5
        if i<3:
            ff=font("display",21); fill=(225,229,234)
            step=31
        else:
            ff=font("sans",16); fill=(151,158,169)
            step=25
        d.text((480+int(drift),yy),item.upper(),font=ff,fill=fill)
        yy+=step
        if yy>555: break
    draw_frame_border(img,26)
    return img.convert("RGB")

def create_button_frame(label: str, subtitle: str, idx: int, frames: int, width: int=880) -> Image.Image:
    t=idx/max(1,frames-1)
    h=72
    img=Image.new("RGBA",(width,h),rgba(BG))
    d=ImageDraw.Draw(img)
    # Not a rounded button: cinematic rail with angled ends and moving specular slit.
    pts=[(14,10),(width-30,10),(width-12,36),(width-30,62),(14,62),(2,36)]
    d.polygon(pts,fill=(10,12,15,255),outline=(72,79,91,190))
    d.line((28,19,width-43,19),fill=(35,40,48,150),width=1)
    shine_x=int(-90+t*(width+180))
    d.polygon([(shine_x-25,10),(shine_x+8,10),(shine_x-30,62),(shine_x-63,62)],fill=(225,229,235,42))
    f=font("display",20); sf=font("sans",11)
    d.text((34,27),label,font=f,fill=INK)
    if subtitle:
        d.text((34,49),subtitle,font=sf,fill=MUTED)
    # custom arrow
    ax=width-55; ay=36
    d.line((ax-14,ay,ax+10,ay),fill=CHROME,width=2)
    d.line((ax+2,ay-8,ax+10,ay),fill=CHROME,width=2)
    d.line((ax+2,ay+8,ax+10,ay),fill=CHROME,width=2)
    return img.convert("RGB")


def save_gif(path: Path, frames: list[Image.Image], duration: int=110) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    # Global palette based on a contact sheet of representative frames for consistent chrome gradients.
    sample=Image.new("RGB",(frames[0].width,frames[0].height*min(4,len(frames))))
    idxs=[0,len(frames)//3,2*len(frames)//3,len(frames)-1][:min(4,len(frames))]
    for row,i in enumerate(idxs):
        sample.paste(frames[i],(0,row*frames[0].height))
    pal=sample.quantize(colors=128,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.FLOYDSTEINBERG)
    palette=pal.getpalette()
    out=[]
    for frame in frames:
        q=frame.quantize(colors=128,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.FLOYDSTEINBERG)
        if palette:
            q.putpalette(palette)
        out.append(q)
    out[0].save(path,save_all=True,append_images=out[1:],duration=duration,loop=0,optimize=True,disposal=2)


def project_ctas(cfg: dict,repos: list[dict]) -> list[dict]:
    out=[]
    for project in cfg.get("projects",[])[:2]:
        repo=find_repo(project,repos)
        if repo:
            out.append({"id":project.get("id"),"label":project.get("name","PROJECT"),"url":repo["html_url"],"subtitle":"OPEN REPOSITORY"})
    return out


def write_readme(project_buttons: list[dict], links: list[dict]) -> None:
    lines=[
        '<p align="center"><img src="assets/generated/scene-01-intro.gif" width="100%" alt="THOTH /FND cinematic identity"></p>',
        '<p align="center"><img src="assets/generated/scene-02-builds.gif" width="100%" alt="THOTH Browser and RelayX"></p>',
    ]
    for item in project_buttons:
        lines.append(f'<p align="center"><a href="{item["url"]}"><img src="assets/generated/cta-{item["id"]}.gif" width="100%" alt="Open {item["label"]} repository"></a></p>')
    lines.append('<p align="center"><img src="assets/generated/scene-03-profile.gif" width="100%" alt="Animated profile and interests"></p>')
    for item in links:
        lines.append(f'<p align="center"><a href="{item["url"]}"><img src="assets/generated/link-{item["id"]}.gif" width="100%" alt="{item["label"]}"></a></p>')
    README.write_text("\n".join(lines)+"\n",encoding="utf-8")


def render(cfg: dict, login: str, repos: list[dict], avatar: Image.Image | None, avatar_raw: bytes, preview_static: bool=False) -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True,exist_ok=True)
    digest=hashlib.sha256(avatar_raw or b"no-avatar").hexdigest()

    if preview_static:
        # use final-ish frames to create PNG previews quickly
        stars1=make_stars("scene1",55,W,650,20,430)
        fog1=fog_texture("fog-intro",W,220,18)
        fog2=fog_texture("fog-intro-2",W,220,16)
        create_intro_frame(cfg,34,40,stars1,fog1,fog2).save(OUT/"scene-01-intro.png")
        fogb=fog_texture("fog-builds",W,300,16)
        create_builds_frame(cfg,repos,18,36,fogb).save(OUT/"scene-02-builds.png")
        starsp=make_stars("scene3",38,W,620,0,580)
        fogp=fog_texture("fog-profile",W,300,15)
        create_profile_frame(cfg,avatar,digest,22,36,starsp,fogp).save(OUT/"scene-03-profile.png")
        return

    # Hero is intentionally slower and one-shot-like within a loop; lower scenes use continuous loops.
    intro_n=52
    stars1=make_stars("scene1",55,W,650,20,430)
    fog1=fog_texture("fog-intro",W,220,18)
    fog2=fog_texture("fog-intro-2",W,220,16)
    intro=[create_intro_frame(cfg,i,intro_n,stars1,fog1,fog2) for i in range(intro_n)]
    save_gif(OUT/"scene-01-intro.gif",intro,115)

    builds_n=36
    fogb=fog_texture("fog-builds",W,300,16)
    builds=[create_builds_frame(cfg,repos,i,builds_n,fogb) for i in range(builds_n)]
    save_gif(OUT/"scene-02-builds.gif",builds,120)

    profile_n=36
    starsp=make_stars("scene3",38,W,620,0,580)
    fogp=fog_texture("fog-profile",W,300,15)
    profile=[create_profile_frame(cfg,avatar,digest,i,profile_n,starsp,fogp) for i in range(profile_n)]
    save_gif(OUT/"scene-03-profile.gif",profile,120)

    pb=project_ctas(cfg,repos)
    links=active_links(cfg,login)
    button_n=24
    for item in pb:
        frames=[create_button_frame(item["label"],item["subtitle"],i,button_n) for i in range(button_n)]
        save_gif(OUT/f'cta-{item["id"]}.gif',frames,90)
    for item in links:
        frames=[create_button_frame(item.get("label","LINK"),"OPEN",i,button_n) for i in range(button_n)]
        save_gif(OUT/f'link-{item["id"]}.gif',frames,90)
    write_readme(pb,links)


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--login",default=os.environ.get("GH_LOGIN","thothfnd"))
    ap.add_argument("--token",default=os.environ.get("GITHUB_TOKEN",""))
    ap.add_argument("--demo",action="store_true")
    ap.add_argument("--preview-static",action="store_true")
    args=ap.parse_args()
    cfg=json.loads(DATA.read_text(encoding="utf-8"))
    if args.demo or not args.token:
        user,repos,avatar,raw=demo_data(args.login)
    else:
        try:
            user=github_user(args.login,args.token)
            repos=github_repos(args.login,args.token)
            avatar,raw=download_avatar(user.get("avatar_url", ""),args.token)
        except Exception as error:
            print(f"live data fallback: {error}")
            user,repos,avatar,raw=demo_data(args.login)
    render(cfg,args.login,repos,avatar,raw,preview_static=args.preview_static)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
