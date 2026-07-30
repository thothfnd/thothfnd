#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import html
import io
import json
import math
import os
import random
import textwrap
import urllib.request
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "profile.json"
OUT = ROOT / "assets" / "generated"
README = ROOT / "README.md"

W = 1200
BG = "#050506"
BLACK = "#08090a"
GRAPHITE = "#111318"
GRAPHITE_2 = "#171a20"
LINE = "#2b2f37"
MUTED = "#8f96a3"
SOFT = "#c1c6cf"
WHITE = "#f4f5f7"
CHROME = "#d9dde4"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8")


def svg(height: int, body: str, extra_style: str = "") -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{height}" viewBox="0 0 {W} {height}">
<style>
.display{{font-family:ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;fill:{WHITE}}}
.text{{font-family:ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;fill:{SOFT}}}
.mono{{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,"Liberation Mono",monospace;fill:{MUTED}}}
{extra_style}
</style>
{body}
</svg>'''


def req_bytes(url: str, token: str = "") -> bytes:
    headers = {"User-Agent": "thothfnd-v9-cinematic", "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def github_user(login: str, token: str) -> dict:
    return json.loads(req_bytes(f"https://api.github.com/users/{login}", token).decode("utf-8"))


def github_repos(login: str, token: str) -> list[dict]:
    data = json.loads(req_bytes(f"https://api.github.com/users/{login}/repos?per_page=100&type=owner&sort=updated", token).decode("utf-8"))
    return [r for r in data if not r.get("fork")]


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
        {"name": "THOTH-Browser", "html_url": f"https://github.com/{login}/THOTH-Browser", "description": "Privacy-first browser project"},
        {"name": "RelayX", "html_url": f"https://github.com/{login}/RelayX", "description": "Second public project"},
    ]
    return user, repos, None, b"demo-avatar"


def find_repo(project: dict, repos: list[dict]) -> dict | None:
    direct = str(project.get("url") or "").strip()
    if direct:
        return {"name": project.get("name", "PROJECT"), "html_url": direct, "description": project.get("description", "")}
    candidates = {str(x).lower() for x in project.get("repo_names", [])}
    for repo in repos:
        if str(repo.get("name", "")).lower() in candidates:
            return repo
    return None


def active_links(config: dict, login: str) -> list[dict]:
    result = []
    for item in config.get("links", []):
        url = str(item.get("url") or "").strip()
        if url == "AUTO" and item.get("id") == "github":
            url = f"https://github.com/{login}"
        if url:
            result.append({**item, "url": url})
    return result


def stars(seed: str, count: int, width: int, height: int, y_min: int = 0) -> str:
    rng = random.Random(seed)
    out = []
    for i in range(count):
        x = rng.randint(30, width - 30)
        y = rng.randint(y_min + 20, height - 20)
        r = rng.choice([0.7, 0.8, 1.0, 1.2, 1.5])
        op = rng.uniform(0.12, 0.55)
        dur = rng.uniform(4.0, 10.0)
        delay = rng.uniform(0.0, 6.0)
        out.append(
            f'<circle cx="{x}" cy="{y}" r="{r}" fill="{WHITE}" opacity="{op:.2f}">'
            f'<animate attributeName="opacity" values="{op:.2f};{min(.75, op+.25):.2f};{op:.2f}" dur="{dur:.1f}s" begin="{delay:.1f}s" repeatCount="indefinite"/>'
            '</circle>'
        )
    return "".join(out)


def static_or_animated(static: bool, final: str, animated: str) -> str:
    return final if static else animated


def owl_art(static: bool, x: int, y: int, scale: float = 1.0) -> str:
    # Original geometric owl: faceted chrome, no pixel-art.
    reveal = static_or_animated(
        static,
        'opacity="1" transform="translate(0 0)"',
        'opacity="0" transform="translate(0 18)"><animate attributeName="opacity" from="0" to="1" dur="1.4s" begin="1.0s" fill="freeze"/><animateTransform attributeName="transform" type="translate" from="0 18" to="0 0" dur="1.4s" begin="1.0s" fill="freeze"',
    )
    # close-tag handling differs because animated string intentionally leaves transform animate open? avoid cleverness
    if static:
        open_group = f'<g transform="translate({x} {y}) scale({scale})" opacity="1">'
    else:
        open_group = f'<g transform="translate({x} {y}) scale({scale})" opacity="0"><animate attributeName="opacity" from="0" to="1" dur="1.4s" begin="1.0s" fill="freeze"/>'
    return open_group + f'''
<g>
  <animateTransform attributeName="transform" type="translate" values="0 0;0 -5;0 0" dur="5.8s" begin="3s" repeatCount="indefinite"/>
  <path d="M-146,-98 L-74,-160 L-34,-126 L0,-150 L34,-126 L74,-160 L146,-98 L123,52 L72,128 L0,162 L-72,128 L-123,52 Z" fill="url(#owlBody)" stroke="url(#chromeEdge)" stroke-width="2.2"/>
  <path d="M-146,-98 L-50,-70 L-94,20 L-123,52 Z" fill="#17191f" opacity=".92"/>
  <path d="M146,-98 L50,-70 L94,20 L123,52 Z" fill="#17191f" opacity=".92"/>
  <path d="M-74,-160 L-42,-86 L0,-150 L42,-86 L74,-160 L34,-126 L0,-104 L-34,-126 Z" fill="#20232a" stroke="#454b56" stroke-width="1"/>
  <path d="M-102,-38 Q-65,-88 -18,-48 Q-52,28 -105,18 Z" fill="#0a0b0d" stroke="#59606b" stroke-width="1.4"/>
  <path d="M102,-38 Q65,-88 18,-48 Q52,28 105,18 Z" fill="#0a0b0d" stroke="#59606b" stroke-width="1.4"/>
  <circle cx="-59" cy="-25" r="21" fill="url(#eyeLens)"/>
  <circle cx="59" cy="-25" r="21" fill="url(#eyeLens)"/>
  <circle cx="-59" cy="-25" r="6" fill="{WHITE}"><animate attributeName="opacity" values=".95;.55;.95" dur="3.4s" repeatCount="indefinite"/></circle>
  <circle cx="59" cy="-25" r="6" fill="{WHITE}"><animate attributeName="opacity" values=".95;.55;.95" dur="3.4s" begin=".2s" repeatCount="indefinite"/></circle>
  <path d="M0,-28 L24,12 L0,38 L-24,12 Z" fill="url(#beak)" stroke="#6b717b" stroke-width="1"/>
  <path d="M-93,32 L-38,58 L0,142 L-72,110 Z" fill="#1d2026" opacity=".95"/>
  <path d="M93,32 L38,58 L0,142 L72,110 Z" fill="#1d2026" opacity=".95"/>
  <path d="M-38,58 L0,82 L38,58 L0,142 Z" fill="#2a2e36" opacity=".95"/>
  <path d="M-122,2 Q-162,52 -184,118" fill="none" stroke="#424750" stroke-width="1.4" opacity=".55"/>
  <path d="M122,2 Q162,52 184,118" fill="none" stroke="#424750" stroke-width="1.4" opacity=".55"/>
  <ellipse cx="0" cy="4" rx="178" ry="190" fill="none" stroke="url(#orbital)" stroke-width="1" opacity=".35"><animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="28s" repeatCount="indefinite"/></ellipse>
</g>
</g>'''


def wordmark(static: bool) -> str:
    # THOTH is custom vector line geometry; /FND stays secondary.
    strokes = [
        "M0,0 H94 M47,0 V126",  # T
        "M124,0 V126 M214,0 V126 M124,62 H214",  # H
        "M256,16 Q256,0 274,0 H338 Q356,0 356,18 V108 Q356,126 338,126 H274 Q256,126 256,108 Z",  # O
        "M394,0 H488 M441,0 V126",  # T
        "M520,0 V126 M610,0 V126 M520,62 H610",  # H
    ]
    out = ['<g transform="translate(118 0)" fill="none" stroke="url(#wordmarkChrome)" stroke-width="12" stroke-linecap="square" stroke-linejoin="round">']
    for i, d in enumerate(strokes):
        if static:
            out.append(f'<path d="{d}"/>')
        else:
            out.append(f'<path d="{d}" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1"><animate attributeName="stroke-dashoffset" from="1" to="0" dur="1.15s" begin="{2.2+i*.17:.2f}s" fill="freeze"/></path>')
    out.append('</g>')
    fnd_op = '1' if static else '0'
    out.append(f'<text x="800" y="106" class="display" font-size="66" font-weight="300" letter-spacing="9" opacity="{fnd_op}">/FND' + ('' if static else '<animate attributeName="opacity" from="0" to="1" dur=".8s" begin="3.55s" fill="freeze"/>') + '</text>')
    if not static:
        out.append('<rect x="82" y="-20" width="150" height="170" fill="url(#wordSweep)" opacity="0"><animate attributeName="x" values="82;940" dur="1.6s" begin="4.1s" fill="freeze"/><animate attributeName="opacity" values="0;.55;0" dur="1.6s" begin="4.1s" fill="freeze"/></rect>')
    return ''.join(out)


def scene_intro(cfg: dict, static: bool) -> str:
    identity = cfg["identity"]
    lines = identity.get("lines", [])
    body = f'''
<defs>
  <radialGradient id="bgHalo"><stop offset="0" stop-color="#323640" stop-opacity=".32"/><stop offset=".52" stop-color="#15171d" stop-opacity=".18"/><stop offset="1" stop-color="#050506" stop-opacity="0"/></radialGradient>
  <linearGradient id="frame" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#cdd1d8" stop-opacity=".34"/><stop offset=".24" stop-color="#454a54" stop-opacity=".24"/><stop offset="1" stop-color="#15171c" stop-opacity=".8"/></linearGradient>
  <linearGradient id="owlBody" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#414650"/><stop offset=".42" stop-color="#14161b"/><stop offset=".7" stop-color="#2c3038"/><stop offset="1" stop-color="#0a0b0d"/></linearGradient>
  <linearGradient id="chromeEdge"><stop stop-color="#f3f4f6"/><stop offset=".42" stop-color="#777e89"/><stop offset="1" stop-color="#292d34"/></linearGradient>
  <radialGradient id="eyeLens"><stop stop-color="#fafafa"/><stop offset=".16" stop-color="#8b929d"/><stop offset=".4" stop-color="#1a1c20"/><stop offset="1" stop-color="#050506"/></radialGradient>
  <linearGradient id="beak"><stop stop-color="#dfe2e7"/><stop offset=".48" stop-color="#555b65"/><stop offset="1" stop-color="#111318"/></linearGradient>
  <linearGradient id="orbital"><stop stop-color="#b7bdc6" stop-opacity="0"/><stop offset=".45" stop-color="#b7bdc6"/><stop offset=".55" stop-color="#b7bdc6"/><stop offset="1" stop-color="#b7bdc6" stop-opacity="0"/></linearGradient>
  <linearGradient id="wordmarkChrome" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#ffffff"/><stop offset=".28" stop-color="#8d939e"/><stop offset=".5" stop-color="#f1f2f4"/><stop offset=".75" stop-color="#5b616c"/><stop offset="1" stop-color="#d7dae0"/></linearGradient>
  <linearGradient id="wordSweep" x1="0" y1="0" x2="1" y2="0"><stop stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
  <filter id="blur40"><feGaussianBlur stdDeviation="40"/></filter>
  <filter id="blur18"><feGaussianBlur stdDeviation="18"/></filter>
</defs>
<rect width="1200" height="900" rx="36" fill="{BG}"/>
<rect x="1" y="1" width="1198" height="898" rx="36" fill="none" stroke="url(#frame)" stroke-width="2"/>
<ellipse cx="600" cy="330" rx="430" ry="310" fill="url(#bgHalo)" filter="url(#blur18)"><animate attributeName="rx" values="420;455;420" dur="12s" repeatCount="indefinite"/></ellipse>
{stars('intro-v9', 58, 1200, 690, 0)}
<path d="M0,690 C180,640 250,710 420,666 C600,620 750,718 930,665 C1040,632 1110,646 1200,620 V900 H0 Z" fill="#08090b"/>
<path d="M0,744 C160,708 310,764 470,728 C650,688 800,768 990,720 C1080,696 1140,706 1200,690" fill="none" stroke="#20242b" stroke-width="2" opacity=".7"/>
<g opacity=".34"><animateTransform attributeName="transform" type="translate" values="0 0;20 0;0 0" dur="18s" repeatCount="indefinite"/>
  <path d="M42,790 C220,718 372,820 540,760 S882,760 1160,704" fill="none" stroke="#30343b"/>
  <path d="M-80,848 C190,760 352,874 610,812 S962,804 1280,748" fill="none" stroke="#181b20" stroke-width="3"/>
</g>
'''
    body += owl_art(static, 600, 310, 1.05)
    body += f'<g transform="translate(90 525)">{wordmark(static)}</g>'

    if static:
        text_op = '1'
        text_anim = ''
    else:
        text_op = '0'
        text_anim = '<animate attributeName="opacity" from="0" to="1" dur="1s" begin="4.75s" fill="freeze"/>'
    body += f'<text x="600" y="700" text-anchor="middle" class="mono" font-size="13" letter-spacing="4" opacity="{text_op}">{esc(identity.get("eyebrow", ""))}{text_anim}</text>'

    wrapped_lines = []
    for paragraph in lines[:3]:
        wrapped_lines.extend(textwrap.wrap(str(paragraph), width=108)[:2])
    y = 740
    for i, line in enumerate(wrapped_lines[:5]):
        if static:
            op = '1'; anim = ''
        else:
            op = '0'; anim = f'<animate attributeName="opacity" from="0" to="1" dur=".8s" begin="{5.25+i*.28:.2f}s" fill="freeze"/>'
        body += f'<text x="600" y="{y}" text-anchor="middle" class="text" font-size="16.5" opacity="{op}">{esc(line)}{anim}</text>'
        y += 27
    return svg(900, body)


def project_visual(project: dict, repo: dict | None, side: str) -> str:
    name = project.get("name", "PROJECT")
    status = "PUBLIC REPOSITORY" if repo else project.get("status", "IN DEVELOPMENT")
    subtitle = project.get("subtitle", "")
    desc = project.get("description", "") or (repo or {}).get("description") or ""
    is_thoth = project.get("id") == "thoth-browser"
    x = 62 if side == "left" else 636
    cx = 330 if side == "left" else 870
    text_anchor = "start"
    tx = x + 24
    out = []
    # Understated project zone: open field, no internal card rectangle.
    out.append(f'<text x="{tx}" y="170" class="mono" font-size="12" letter-spacing="3">{esc(status)}</text>')
    out.append(f'<text x="{tx}" y="232" class="display" font-size="45" font-weight="760">{esc(name)}</text>')
    out.append(f'<text x="{tx}" y="268" class="text" font-size="18">{esc(subtitle)}</text>')
    wrapped = textwrap.wrap(str(desc), width=58)[:3]
    yy = 620
    for line in wrapped:
        out.append(f'<text x="{tx}" y="{yy}" class="text" font-size="16">{esc(line)}</text>')
        yy += 26
    if is_thoth:
        # Large abstract browser/isolation mechanism.
        out.append(f'<g transform="translate({cx} 420)">')
        out.append('<ellipse rx="174" ry="120" fill="none" stroke="#2d323a" stroke-width="1.5"/>')
        out.append('<ellipse rx="132" ry="90" fill="none" stroke="#575e69" opacity=".6"><animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="26s" repeatCount="indefinite"/></ellipse>')
        out.append('<ellipse rx="88" ry="60" fill="none" stroke="#8d949f" opacity=".5"><animateTransform attributeName="transform" type="rotate" from="360" to="0" dur="16s" repeatCount="indefinite"/></ellipse>')
        for deg in range(0, 360, 60):
            rad = math.radians(deg)
            nx, ny = math.cos(rad)*132, math.sin(rad)*90
            out.append(f'<circle cx="{nx:.1f}" cy="{ny:.1f}" r="8" fill="#15181d" stroke="#a7adb6"><animate attributeName="r" values="7;10;7" dur="{3.2+deg/180:.1f}s" begin="{deg/360:.2f}s" repeatCount="indefinite"/></circle>')
        out.append('<circle r="38" fill="url(#coreMetal)" stroke="#e1e4e8" stroke-opacity=".45"/>')
        out.append('<path d="M-16,-10 L0,-24 L16,-10 L12,20 L0,32 L-12,20 Z" fill="#090a0c" stroke="#e5e7ea" stroke-opacity=".45"/>')
        out.append('</g>')
    else:
        # RelayX: 3D-ish relay lattice.
        nodes = [(-150,-40,-1),(-80,-110,0),(0,-55,1),(95,-130,0),(155,-30,1),(-95,70,1),(10,95,0),(120,62,-1)]
        out.append(f'<g transform="translate({cx} 420)">')
        edges = [(0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,4),(2,6),(1,5),(3,7)]
        for a,b in edges:
            x1,y1,_ = nodes[a]; x2,y2,_ = nodes[b]
            out.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#4a505a" stroke-width="1.4" opacity=".62"><animate attributeName="opacity" values=".25;.9;.25" dur="{3.5+(a+b)*.22:.1f}s" begin="{(a*.2):.1f}s" repeatCount="indefinite"/></line>')
        for i,(nx,ny,z) in enumerate(nodes):
            r = 7 + (z+1)*2
            out.append(f'<circle cx="{nx}" cy="{ny}" r="{r}" fill="#0b0c0f" stroke="#d4d8df" stroke-opacity="{.35+.2*(z+1):.2f}"><animate attributeName="r" values="{r};{r+3};{r}" dur="{3.0+i*.24:.1f}s" repeatCount="indefinite"/></circle>')
        out.append('<ellipse rx="188" ry="142" fill="none" stroke="#20242a" opacity=".7"><animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="34s" repeatCount="indefinite"/></ellipse>')
        out.append('</g>')
    return ''.join(out)


def scene_projects(cfg: dict, repos: list[dict]) -> tuple[str, list[dict]]:
    projects = cfg.get("projects", [])[:2]
    resolved = []
    for p in projects:
        resolved.append({"project": p, "repo": find_repo(p, repos)})
    defs = f'''
<defs>
 <linearGradient id="projectBg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#12151a"/><stop offset=".52" stop-color="#08090b"/><stop offset="1" stop-color="#101217"/></linearGradient>
 <radialGradient id="projectHalo"><stop stop-color="#79808c" stop-opacity=".18"/><stop offset="1" stop-color="#090a0c" stop-opacity="0"/></radialGradient>
 <linearGradient id="coreMetal"><stop stop-color="#e4e6ea"/><stop offset=".32" stop-color="#474d56"/><stop offset=".65" stop-color="#111318"/><stop offset="1" stop-color="#aeb4bd"/></linearGradient>
</defs>
'''
    body = defs + f'''
<rect width="1200" height="760" rx="36" fill="url(#projectBg)"/>
<rect x="1" y="1" width="1198" height="758" rx="36" fill="none" stroke="#383c45" stroke-width="1.5"/>
<ellipse cx="330" cy="410" rx="310" ry="300" fill="url(#projectHalo)"><animate attributeName="rx" values="290;330;290" dur="11s" repeatCount="indefinite"/></ellipse>
<ellipse cx="870" cy="410" rx="310" ry="300" fill="url(#projectHalo)"><animate attributeName="ry" values="280;320;280" dur="13s" repeatCount="indefinite"/></ellipse>
{stars('projects-v9', 28, 1200, 720, 20)}
<text x="60" y="82" class="display" font-size="20" font-weight="650" letter-spacing="2">BUILDS</text>
<text x="1140" y="82" text-anchor="end" class="mono" font-size="11" letter-spacing="3">TWO PROJECTS · ONE ACCOUNT</text>
<line x1="600" y1="126" x2="600" y2="704" stroke="#292d34"/>
'''
    if len(resolved) > 0:
        body += project_visual(resolved[0]["project"], resolved[0]["repo"], "left")
    if len(resolved) > 1:
        body += project_visual(resolved[1]["project"], resolved[1]["repo"], "right")
    body += '<path d="M540,420 C575,386 625,386 660,420" fill="none" stroke="#737a85" stroke-width="1.2" stroke-dasharray="5 9" opacity=".42"><animate attributeName="stroke-dashoffset" values="0;-28" dur="2.8s" repeatCount="indefinite"/></path>'
    return svg(760, body), resolved


def prepare_ascii(image: Image.Image | None, cols: int = 84) -> tuple[list[str], int, int]:
    if image is None:
        sample = [
            "                         .,:;iillllii;:,.",
            "                    .;itfXXUUUUUUUUXXfti;.",
            "                .;fXUUUUUUUUUUUUUUUUUUXf;.",
            "              :XUUUUUUUUU        UUUUUUUUUX:",
            "             XUUUUUUUU              UUUUUUUUX",
            "            XUUUUUUU    THOTH /FND    UUUUUUUUX",
            "             XUUUUUUU              UUUUUUUUX",
            "              :XUUUUUUUUU        UUUUUUUUUX:",
            "                .;fXUUUUUUUUUUUUUUUUUUXf;.",
            "                    .;itfXXUUUUUUUUXXfti;.",
            "                         .,:;iillllii;:,.",
        ]
        return sample, max(map(len, sample)), len(sample)
    im = ImageOps.exif_transpose(image).convert("L")
    # Center-crop to 4:5 portrait, then improve contrast.
    w, h = im.size
    target_ratio = 4 / 5
    if w / h > target_ratio:
        nw = int(h * target_ratio)
        left = (w - nw) // 2
        im = im.crop((left, 0, left + nw, h))
    else:
        nh = int(w / target_ratio)
        top = max(0, (h - nh) // 2)
        im = im.crop((0, top, w, min(h, top + nh)))
    im = ImageEnhance.Contrast(im).enhance(1.65)
    rows = max(30, int(cols * (im.height / im.width) * 0.46))
    im = im.resize((cols, rows))
    ramp = "@%#*+=-:. "
    lines = []
    for yy in range(rows):
        chars = []
        for xx in range(cols):
            px = im.getpixel((xx, yy))
            chars.append(ramp[int(px / 256 * len(ramp)) if int(px / 256 * len(ramp)) < len(ramp) else -1])
        lines.append(''.join(chars).rstrip())
    return lines, cols, rows


def scene_identity(cfg: dict, login: str, avatar: Image.Image | None, avatar_raw: bytes, static: bool) -> str:
    lines, cols, rows = prepare_ascii(avatar, 84)
    digest = hashlib.sha256(avatar_raw or b"no-avatar").hexdigest()[:16].upper()
    identity = cfg["identity"]
    interests = identity.get("interests", [])[:9]
    h = 760
    body = f'''
<defs>
 <linearGradient id="idBg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#070809"/><stop offset=".46" stop-color="#12141a"/><stop offset="1" stop-color="#070809"/></linearGradient>
 <radialGradient id="portraitHalo"><stop stop-color="#c7ccd4" stop-opacity=".11"/><stop offset="1" stop-color="#08090b" stop-opacity="0"/></radialGradient>
 <linearGradient id="scanV" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".6"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
</defs>
<rect width="1200" height="{h}" rx="36" fill="url(#idBg)"/>
<rect x="1" y="1" width="1198" height="{h-2}" rx="36" fill="none" stroke="#343842"/>
<ellipse cx="355" cy="395" rx="300" ry="315" fill="url(#portraitHalo)"/>
<text x="62" y="82" class="display" font-size="20" font-weight="650" letter-spacing="2">PROFILE</text>
<text x="1140" y="82" text-anchor="end" class="mono" font-size="11" letter-spacing="3">@{esc(login)}</text>
<line x1="650" y1="126" x2="650" y2="686" stroke="#2b2f36"/>
'''
    start_y = 164
    line_h = min(10.0, 470 / max(1, rows))
    for i, line in enumerate(lines):
        y = start_y + i * line_h
        if static:
            body += f'<text x="355" y="{y:.1f}" text-anchor="middle" class="mono" font-size="8.8" fill="{WHITE}" opacity=".9" xml:space="preserve">{esc(line)}</text>'
        else:
            delay = .25 + i * .028
            body += f'<text x="355" y="{y:.1f}" text-anchor="middle" class="mono" font-size="8.8" fill="{WHITE}" opacity="0" xml:space="preserve">{esc(line)}<animate attributeName="opacity" from="0" to=".9" dur=".24s" begin="{delay:.3f}s" fill="freeze"/></text>'
    body += '<rect x="78" y="140" width="554" height="3" fill="url(#scanV)" opacity=".38"><animate attributeName="y" values="140;625;140" dur="8s" repeatCount="indefinite"/></rect>'
    body += f'''
<text x="704" y="180" class="mono" font-size="11" letter-spacing="3">IDENTITY</text>
<text x="704" y="224" class="display" font-size="34" font-weight="720">{esc(identity.get('mark','THOTH /FND'))}</text>
<text x="704" y="258" class="text" font-size="16">Current GitHub identity, rendered as ASCII</text>
<text x="704" y="282" class="text" font-size="16">and kept in sync automatically.</text>
<line x1="704" y1="314" x2="1110" y2="314" stroke="#30343c"/>
<text x="704" y="352" class="mono" font-size="11">SOURCE</text><text x="826" y="352" class="text" font-size="14">github/avatar</text>
<text x="704" y="384" class="mono" font-size="11">DIGEST</text><text x="826" y="384" class="text" font-size="14">{digest}</text>
<text x="704" y="416" class="mono" font-size="11">GRID</text><text x="826" y="416" class="text" font-size="14">{cols} × {rows}</text>
<text x="704" y="474" class="display" font-size="20" font-weight="650">INTERESTS</text>
'''
    # interest constellation, not pills: typography + orbiting points.
    y = 518
    for i, item in enumerate(interests):
        col = i % 3
        row = i // 3
        x = 704 + col * 145
        yy = y + row * 54
        body += f'<circle cx="{x}" cy="{yy-5}" r="3" fill="#d9dde4"><animate attributeName="opacity" values=".35;1;.35" dur="{3.2+i*.3:.1f}s" repeatCount="indefinite"/></circle>'
        body += f'<text x="{x+14}" y="{yy}" class="text" font-size="13">{esc(item)}</text>'
    return svg(h, body)


def cta_svg(label: str, sublabel: str = "OPEN REPOSITORY") -> str:
    body = f'''
<defs><linearGradient id="cta" x1="0" y1="0" x2="1" y2="0"><stop stop-color="#0a0b0d"/><stop offset=".48" stop-color="#1b1e24"/><stop offset="1" stop-color="#08090a"/></linearGradient><linearGradient id="sheen"><stop stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".45"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient></defs>
<path d="M18,8 H566 L586,28 V78 L566,98 H18 L2,82 V24 Z" fill="url(#cta)" stroke="#4c515b"/>
<text x="30" y="45" class="display" font-size="18" font-weight="700">{esc(label)}</text>
<text x="30" y="72" class="mono" font-size="10" letter-spacing="2">{esc(sublabel)}</text>
<path d="M522,36 H552 V66 M552,36 L518,70" fill="none" stroke="#f4f5f7" stroke-width="3" stroke-linecap="square"/>
<rect x="-120" y="8" width="120" height="90" fill="url(#sheen)" opacity="0"><animate attributeName="x" values="-120;620" dur="3.8s" begin="1s" repeatCount="indefinite"/><animate attributeName="opacity" values="0;.35;0" dur="3.8s" begin="1s" repeatCount="indefinite"/></rect>
'''
    return svg(106, body).replace('width="1200"', 'width="590"').replace('viewBox="0 0 1200 106"', 'viewBox="0 0 590 106"')


def link_svg(label: str) -> str:
    body = f'''
<defs><linearGradient id="linkbg"><stop stop-color="#0a0b0d"/><stop offset=".5" stop-color="#17191e"/><stop offset="1" stop-color="#090a0c"/></linearGradient></defs>
<path d="M14,5 H274 L289,20 V70 L274,85 H14 L2,73 V18 Z" fill="url(#linkbg)" stroke="#3f444d"/>
<text x="22" y="45" class="display" font-size="15" font-weight="650">{esc(label)}</text>
<path d="M244,27 H268 V51 M268,27 L240,55" fill="none" stroke="#f4f5f7" stroke-width="2.4"/>
<line x1="22" y1="64" x2="22" y2="64" stroke="#d9dde4" stroke-width="2"><animate attributeName="x2" values="22;135;22" dur="4.2s" repeatCount="indefinite"/></line>
'''
    return svg(90, body).replace('width="1200"', 'width="292"').replace('viewBox="0 0 1200 90"', 'viewBox="0 0 292 90"')


def footer_svg() -> str:
    body = f'<line x1="32" y1="28" x2="1168" y2="28" stroke="#24272d"/><text x="32" y="65" class="display" font-size="14" font-weight="650">THOTH /FND</text><circle cx="1160" cy="60" r="3" fill="{CHROME}"><animate attributeName="opacity" values="1;.2;1" dur="1.8s" repeatCount="indefinite"/></circle>'
    return svg(90, body)


def render_readme(resolved_projects: list[dict], links: list[dict]) -> str:
    project_buttons = []
    for item in resolved_projects:
        repo = item["repo"]
        project = item["project"]
        if repo:
            src = f"assets/generated/cta-{project['id']}.svg"
            project_buttons.append(f'<a href="{esc(repo["html_url"])}"><img src="{src}" width="49%" alt="Open {esc(project["name"])} repository"></a>')
    projects_html = ''
    if project_buttons:
        projects_html = '<p align="center">' + '\n'.join(project_buttons) + '</p>\n'

    link_imgs = []
    for item in links:
        src = f"assets/generated/link-{item['id']}.svg"
        link_imgs.append(f'<a href="{esc(item["url"])}"><img src="{src}" width="24%" alt="{esc(item["label"])}"></a>')
    links_html = ''
    if link_imgs:
        links_html = '<p align="center">' + '\n'.join(link_imgs) + '</p>\n'

    return f'''<p align="center"><img src="assets/generated/scene-01-intro.svg" width="100%" alt="THOTH FND cinematic profile intro"></p>

<p align="center"><img src="assets/generated/scene-02-builds.svg" width="100%" alt="THOTH Browser and RelayX"></p>

{projects_html}<p align="center"><img src="assets/generated/scene-03-profile.svg" width="100%" alt="Profile identity and interests"></p>

{links_html}<p align="center"><img src="assets/generated/footer.svg" width="100%" alt="THOTH FND"></p>
'''


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--login", default=os.environ.get("GH_LOGIN", "thothfnd"))
    ap.add_argument("--token", default=os.environ.get("GITHUB_TOKEN", ""))
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--demo-empty", action="store_true")
    ap.add_argument("--static", action="store_true")
    args = ap.parse_args()

    cfg = json.loads(DATA.read_text(encoding="utf-8"))
    if args.demo or args.demo_empty:
        user, repos, avatar, raw = demo_data(args.login)
        if args.demo_empty:
            repos = []
    else:
        user = github_user(args.login, args.token)
        repos = github_repos(args.login, args.token)
        avatar, raw = download_avatar(user.get("avatar_url", ""), args.token)

    OUT.mkdir(parents=True, exist_ok=True)
    for stale in OUT.glob("*.svg"):
        stale.unlink()
    scene1 = scene_intro(cfg, args.static)
    scene2, resolved = scene_projects(cfg, repos)
    scene3 = scene_identity(cfg, args.login, avatar, raw, args.static)
    write(OUT / "scene-01-intro.svg", scene1)
    write(OUT / "scene-02-builds.svg", scene2)
    write(OUT / "scene-03-profile.svg", scene3)
    write(OUT / "footer.svg", footer_svg())

    for item in resolved:
        if item["repo"]:
            p = item["project"]
            write(OUT / f"cta-{p['id']}.svg", cta_svg(p["name"]))
    links = active_links(cfg, args.login)
    for item in links:
        write(OUT / f"link-{item['id']}.svg", link_svg(item["label"]))

    write(README, render_readme(resolved, links))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
