#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import io
import json
import math
import os
import re
import sys
import urllib.request
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "generated"
PROFILE_PATH = ROOT / "data" / "profile.json"

W = 880
BG = "#050506"
BG2 = "#0b0c0f"
LINE = "#2c2f35"
TEXT = "#f6f7f8"
SOFT = "#b6bbc3"
FAINT = "#777d87"
CHROME = "#e9ebee"
STEEL = "#9da3ab"
DARK_STEEL = "#565c64"
ASCII_RAMP = " .`'^,:;Il!i~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"
STATIC = False


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def anim(tag: str) -> str:
    return "" if STATIC else tag


def svg(height: int, body: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{height}" viewBox="0 0 {W} {height}">
<style>
.sans{{font-family:ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;fill:{TEXT}}}
.mono{{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,"Liberation Mono",monospace;fill:{TEXT}}}
.serif{{font-family:Georgia,"Times New Roman",serif;fill:{TEXT}}}
.soft{{fill:{SOFT}}}.faint{{fill:{FAINT}}}
</style>
{body}
</svg>'''


def api(url: str, token: str = "") -> bytes:
    headers = {"User-Agent": "thothfnd-profile-v8", "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=35) as response:
        return response.read()


def rest_user(login: str, token: str) -> dict:
    return json.loads(api(f"https://api.github.com/users/{login}", token).decode())


def graph_user(login: str, token: str) -> dict:
    query = r'''
query($login:String!){
 user(login:$login){
  login name bio createdAt
  repositories(first:100,privacy:PUBLIC,ownerAffiliations:OWNER,isFork:false,orderBy:{field:PUSHED_AT,direction:DESC}){
   totalCount nodes{name url stargazerCount forkCount languages(first:6,orderBy:{field:SIZE,direction:DESC}){edges{size node{name}}}}
  }
  contributionsCollection{contributionCalendar{totalContributions weeks{contributionDays{contributionCount date weekday}}}}
 }
}'''
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"Bearer {token}", "User-Agent": "thothfnd-profile-v8", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=45) as response:
        result = json.loads(response.read().decode())
    if result.get("errors"):
        raise RuntimeError(result["errors"])
    return result["data"]["user"]


def demo_user(login: str) -> tuple[dict, dict]:
    today = dt.date.today()
    days = []
    for i in range(365):
        date = today - dt.timedelta(days=364-i)
        count = 0 if i % 7 else (i * 5) % 8
        if i % 29 == 0:
            count += 5
        days.append({"date": date.isoformat(), "contributionCount": count, "weekday": (date.weekday()+1)%7})
    weeks = [{"contributionDays": days[i:i+7]} for i in range(0, len(days), 7)]
    return {"avatar_url": ""}, {
        "login": login,
        "name": login,
        "createdAt": "2026-01-01T00:00:00Z",
        "repositories": {"totalCount": 2, "nodes": []},
        "contributionsCollection": {"contributionCalendar": {"totalContributions": 72, "weeks": weeks}},
    }


def normalize_repo(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def resolve_projects(profile: dict, graph: dict, login: str) -> list[dict]:
    repos = graph.get("repositories", {}).get("nodes", [])
    by_name = {normalize_repo(r.get("name", "")): r.get("url", "") for r in repos}
    out = []
    for project in profile.get("projects", []):
        p = dict(project)
        explicit = str(p.get("url", "")).strip()
        if explicit:
            p["resolved_url"] = explicit
        else:
            found = ""
            for candidate in p.get("repo_names", []):
                found = by_name.get(normalize_repo(candidate), "")
                if found:
                    break
            p["resolved_url"] = found
        out.append(p)
    return out


def fetch_avatar(url: str, token: str) -> tuple[Image.Image | None, str]:
    if not url:
        return None, "DEMO00000000"
    try:
        raw = api(url + ("&" if "?" in url else "?") + "s=900", token)
        digest = hashlib.sha256(raw).hexdigest().upper()
        return Image.open(io.BytesIO(raw)).convert("RGBA"), digest
    except Exception as error:
        print(f"avatar fallback: {error}", file=sys.stderr)
        return None, "ERROR0000000"


def ascii_portrait(image: Image.Image, cols: int) -> list[str]:
    try:
        from rembg import remove
        cut = remove(image)
        if not isinstance(cut, Image.Image):
            cut = Image.open(io.BytesIO(cut)).convert("RGBA")
        image = cut
    except Exception as error:
        print(f"rembg fallback: {error}", file=sys.stderr)

    alpha = np.array(image.getchannel("A"))
    ys, xs = np.where(alpha > 18)
    if len(xs) > 10:
        pad_x, pad_y = 12, 10
        image = image.crop((
            max(0, int(xs.min())-pad_x), max(0, int(ys.min())-pad_y),
            min(image.width, int(xs.max())+pad_x), min(image.height, int(ys.max())+pad_y)
        ))
    canvas = Image.new("RGB", image.size, "white")
    canvas.paste(image.convert("RGB"), mask=image.getchannel("A"))
    gray = np.array(canvas.convert("L"))
    gray = cv2.createCLAHE(clipLimit=2.6, tileGridSize=(8,8)).apply(gray)
    gray = cv2.GaussianBlur(gray, (0,0), 0.5)
    gray = np.clip(np.power(gray.astype(np.float32)/255.0, 1.46)*255, 0, 255).astype(np.uint8)
    ratio = gray.shape[0] / max(1, gray.shape[1])
    rows = max(24, min(68, int(cols * ratio * 0.48)))
    small = cv2.resize(gray, (cols, rows), interpolation=cv2.INTER_AREA)
    return ["".join(ASCII_RAMP[int((255-int(px))/255*(len(ASCII_RAMP)-1))] for px in row).rstrip() for row in small]


def owl_pixels(cx: int, top: int, pixel: int = 12, prefix: str = "owl") -> str:
    # Original pixel owl silhouette. 1=steel, 2=chrome highlight, E=eye.
    pattern = [
        "1100000000011",
        "1110000000111",
        "1111000001111",
        "0111111111110",
        "0111222221110",
        "11122E2E22111",
        "1112222222111",
        "0111222221110",
        "0011122211100",
        "0001112111000",
        "0000112110000",
        "0000012100000",
        "0000011100000",
        "0000010100000",
    ]
    width = len(pattern[0]) * pixel
    left = cx - width//2
    pieces = []
    index = 0
    for row_i, row in enumerate(pattern):
        for col_i, ch in enumerate(row):
            if ch == "0":
                continue
            x = left + col_i*pixel
            y = top + row_i*pixel
            fill = CHROME if ch in ("2", "E") else STEEL
            delay = 0.12 + index*0.012
            base_opacity = "1" if STATIC else "0"
            extra = ""
            if ch == "E":
                fill = "#ffffff"
                extra = anim(f'<animate attributeName="opacity" values="1;.18;1" dur="2.6s" begin="{1.2+col_i*.05:.2f}s" repeatCount="indefinite"/>')
            reveal = anim(f'<animate attributeName="opacity" from="0" to="1" dur=".24s" begin="{delay:.3f}s" fill="freeze"/>')
            pieces.append(f'<rect x="{x}" y="{y}" width="{pixel-2}" height="{pixel-2}" rx="1.5" fill="{fill}" opacity="{base_opacity}">{reveal}{extra}</rect>')
            index += 1
    return "\n".join(pieces)


def vector_wordmark(x: int, y: int, scale: float = 1.0) -> tuple[str, int]:
    text = "THOTH"
    w, h, gap, sw = int(66*scale), int(62*scale), int(14*scale), max(4, int(6*scale))
    cursor = x
    pieces = []
    path_index = 0
    for char in text:
        x0, x1 = cursor, cursor+w
        y0, y1, ym = y, y+h, y+h/2
        d = ""
        if char == "T": d = f"M{x0},{y0} H{x1} M{(x0+x1)/2},{y0} V{y1}"
        elif char == "H": d = f"M{x0},{y0} V{y1} M{x1},{y0} V{y1} M{x0},{ym} H{x1}"
        elif char == "O": d = f"M{x0+8},{y0} H{x1-8} L{x1},{y0+8} V{y1-8} L{x1-8},{y1} H{x0+8} L{x0},{y1-8} V{y0+8} Z"
        draw = anim(f'<animate attributeName="stroke-dashoffset" from="1" to="0" dur=".8s" begin="{1.0+path_index*.12:.2f}s" fill="freeze"/>')
        dash = "0" if STATIC else "1"
        pieces.append(f'<path pathLength="1" d="{d}" fill="none" stroke="url(#chromeMark)" stroke-width="{sw}" stroke-linecap="square" stroke-linejoin="miter" stroke-dasharray="1" stroke-dashoffset="{dash}">{draw}</path>')
        cursor += w+gap
        path_index += 1
    slash_x = cursor + 2
    slash_draw = anim('<animate attributeName="stroke-dashoffset" from="1" to="0" dur=".45s" begin="1.65s" fill="freeze"/>')
    pieces.append(f'<path pathLength="1" d="M{slash_x},{y1+3} L{slash_x+30},{y0-3}" stroke="{CHROME}" stroke-width="{max(3,sw-1)}" stroke-dasharray="1" stroke-dashoffset="{"0" if STATIC else "1"}">{slash_draw}</path>')
    # FND as compact geometric text block; deliberately subordinate to THOTH.
    fnd_x = slash_x + 44
    fnd_op = "1" if STATIC else "0"
    fnd_anim = anim('<animate attributeName="opacity" from="0" to="1" dur=".45s" begin="1.78s" fill="freeze"/>')
    pieces.append(f'<text x="{fnd_x}" y="{y1-3}" class="mono" font-size="{int(31*scale)}" font-weight="800" letter-spacing="3" opacity="{fnd_op}">FND{fnd_anim}</text>')
    return "\n".join(pieces), fnd_x + int(75*scale) - x


def intro(login: str) -> str:
    height = 520
    stars = []
    for i in range(42):
        x = 22 + (i * 137) % 838
        y = 18 + (i * 71) % 310
        r = 0.7 + (i % 3)*0.45
        delay = (i % 11)*0.27
        pulse = anim(f'<animate attributeName="opacity" values=".12;.65;.12" dur="{3.2+(i%5)*.43:.2f}s" begin="{delay:.2f}s" repeatCount="indefinite"/>')
        stars.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{CHROME}" opacity=".22">{pulse}</circle>')

    grid = []
    horizon_y = 355
    for x in range(-160, 1041, 80):
        grid.append(f'<line x1="440" y1="{horizon_y}" x2="{x}" y2="520" stroke="#202329" stroke-width="1"/>')
    for i in range(8):
        y = horizon_y + int((i/7)**1.8 * 165)
        grid.append(f'<line x1="0" y1="{y}" x2="880" y2="{y}" stroke="#202329" stroke-width="1" opacity="{0.38+i*.045:.2f}"/>')
    mark, mark_w = vector_wordmark(176, 276, 0.82)
    owl = owl_pixels(440, 68, 13)
    body = f'''
<defs>
 <radialGradient id="voidGlow" cx="50%" cy="35%" r="65%"><stop offset="0" stop-color="#282b31" stop-opacity=".32"/><stop offset=".48" stop-color="#101217" stop-opacity=".13"/><stop offset="1" stop-color="#050506" stop-opacity="0"/></radialGradient>
 <linearGradient id="chromeMark" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#777d86"/><stop offset=".18" stop-color="#fafbfc"/><stop offset=".42" stop-color="#969ca5"/><stop offset=".68" stop-color="#ffffff"/><stop offset="1" stop-color="#6e747d"/></linearGradient>
 <linearGradient id="sweep" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".48" stop-color="#fff" stop-opacity=".75"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
</defs>
<rect width="880" height="520" fill="{BG}"/>
<rect width="880" height="520" fill="url(#voidGlow)"/>
{''.join(stars)}
<g opacity=".72">{''.join(grid)}{anim('<animateTransform attributeName="transform" type="translate" values="0 0;0 4;0 0" dur="7s" repeatCount="indefinite"/>')}</g>
<ellipse cx="440" cy="230" rx="170" ry="82" fill="#dfe2e6" opacity=".035"/>
<g>{owl}{anim('<animateTransform attributeName="transform" type="translate" values="0 0;0 -3;0 0" dur="4.2s" begin="1.4s" repeatCount="indefinite"/>')}</g>
<g>{mark}</g>
<rect x="130" y="267" width="0" height="82" fill="url(#sweep)" opacity=".25">{anim('<animate attributeName="x" values="130;760" dur="2.2s" begin="2.0s" repeatCount="indefinite"/><animate attributeName="width" values="0;84;0" dur="2.2s" begin="2.0s" repeatCount="indefinite"/>')}</rect>
<text x="440" y="394" text-anchor="middle" class="mono faint" font-size="12" letter-spacing="2">@{esc(login)}</text>
<text x="440" y="426" text-anchor="middle" class="sans soft" font-size="16">privacy · security · systems · anonymity · automation</text>
<circle cx="440" cy="476" r="2.8" fill="{CHROME}">{anim('<animate attributeName="opacity" values="1;.18;1" dur="1.8s" repeatCount="indefinite"/>')}</circle>
<line x1="395" y1="476" x2="429" y2="476" stroke="{LINE}"/><line x1="451" y1="476" x2="485" y2="476" stroke="{LINE}"/>
'''
    return svg(height, body)


def wrap_text(text: str, max_chars: int) -> list[str]:
    words = text.split()
    lines, current = [], ""
    for word in words:
        c = f"{current} {word}".strip()
        if current and len(c) > max_chars:
            lines.append(current)
            current = word
        else:
            current = c
    if current:
        lines.append(current)
    return lines


def about(profile: dict) -> str:
    lines = profile.get("identity", {}).get("lines", [])[:3]
    wrapped = []
    for paragraph in lines:
        wrapped.append(wrap_text(paragraph, 72))
    y = 80
    parts = [f'''
<defs><linearGradient id="aboutBeam" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".55" stop-color="#fff" stop-opacity=".30"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient></defs>
<rect width="880" height="360" fill="{BG}"/>
<circle cx="760" cy="180" r="118" fill="none" stroke="#22252b"/>
<circle cx="760" cy="180" r="76" fill="none" stroke="#1a1d22"/>
<path d="M640,180 H880 M760,60 V300" stroke="#17191e"/>
<circle cx="760" cy="180" r="4" fill="{CHROME}" opacity=".7">{anim('<animate attributeName="r" values="3;6;3" dur="3s" repeatCount="indefinite"/>')}</circle>
<text x="40" y="36" class="mono faint" font-size="12">ABOUT</text>
''']
    for p_i, para_lines in enumerate(wrapped):
        for l_i, line in enumerate(para_lines):
            size = 22 if p_i == 0 else 18
            weight = 680 if p_i == 0 else 500
            opacity = "1" if STATIC else "0"
            reveal = anim(f'<animate attributeName="opacity" from="0" to="1" dur=".5s" begin="{0.18+p_i*.55+l_i*.10:.2f}s" fill="freeze"/>')
            parts.append(f'<text x="40" y="{y}" class="sans" font-size="{size}" font-weight="{weight}" opacity="{opacity}">{esc(line)}{reveal}</text>')
            y += 31 if p_i == 0 else 27
        y += 18
    about_beam_anim = anim('<animate attributeName="x" values="-180;900" dur="6s" repeatCount="indefinite"/>')
    parts.append(f'<rect x="-180" y="338" width="180" height="2" fill="url(#aboutBeam)">{about_beam_anim}</rect>')
    return svg(360, "\n".join(parts))


def link_button(label: str, sub: str, index: int) -> str:
    h = 86
    # Slightly different perspective offset for each button to avoid clone feel.
    skew = 7 + (index % 3)*2
    body = f'''
<defs>
 <linearGradient id="edge" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#f7f8fa" stop-opacity=".50"/><stop offset=".35" stop-color="#6f757e" stop-opacity=".16"/><stop offset="1" stop-color="#24272d" stop-opacity=".55"/></linearGradient>
 <linearGradient id="shine" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".42"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
</defs>
<rect width="420" height="86" fill="{BG}"/>
<path d="M18,15 L398,15 L406,{15+skew} L406,67 L398,75 L18,75 L10,{67-skew//2} L10,24 Z" fill="#0d0f12" stroke="url(#edge)"/>
<line x1="30" y1="60" x2="390" y2="60" stroke="#25282e"/>
<text x="30" y="42" class="sans" font-size="20" font-weight="760">{esc(label)}</text>
<text x="390" y="42" text-anchor="end" class="mono faint" font-size="11">{esc(sub)}</text>
<rect x="-110" y="14" width="90" height="52" fill="url(#shine)" opacity=".20">{anim(f'<animate attributeName="x" values="-110;440" dur="{4.2+index*.4:.1f}s" begin="{index*.35:.2f}s" repeatCount="indefinite"/>')}</rect>
<path d="M382,28 l8,8 -8,8" fill="none" stroke="{CHROME}" stroke-width="2" opacity=".65"/>
'''
    return svg(h, body).replace('width="880"', 'width="420"').replace('viewBox="0 0 880 86"', 'viewBox="0 0 420 86"')


def identity(image: Image.Image | None, login: str, digest: str) -> str:
    fallback = [
        "                  .,:iillllii:,.",
        "              .;tXXUUUUUUUUUXXt;.",
        "            :XUUUUUUUUUUUUUUUUUUX:",
        "          .XUUUUUUU     UUUUUUUUUX.",
        "          XUUUUUUU       UUUUUUUUUX",
        "          XUUUUUUU       UUUUUUUUUX",
        "          .XUUUUUUU     UUUUUUUUUX.",
        "            :XUUUUUUUUUUUUUUUUUUX:",
        "              .;tXXUUUUUUUUUXXt;.",
        "                  .,:iillllii:,.",
    ]
    if image is None:
        coarse, final = fallback, fallback
    else:
        coarse = ascii_portrait(image, 46)
        final = ascii_portrait(image, 84)
    line_h = 9.8
    top = 92
    height = max(450, int(top + len(final)*line_h + 50))
    parts = [f'''
<defs>
 <linearGradient id="idBeam" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".62"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
 <radialGradient id="idGlow"><stop offset="0" stop-color="#dfe2e6" stop-opacity=".09"/><stop offset="1" stop-color="#050506" stop-opacity="0"/></radialGradient>
</defs>
<rect width="880" height="{height}" fill="{BG}"/>
<rect x="24" y="20" width="575" height="{height-40}" fill="url(#idGlow)"/>
<line x1="620" y1="20" x2="620" y2="{height-20}" stroke="{LINE}"/>
<text x="40" y="46" class="mono faint" font-size="12">IDENTITY / LIVE AVATAR RENDER</text>
<text x="654" y="76" class="mono faint" font-size="11">HANDLE</text><text x="654" y="101" class="sans" font-size="18" font-weight="700">@{esc(login)}</text>
<text x="654" y="145" class="mono faint" font-size="11">SOURCE</text><text x="654" y="170" class="sans soft" font-size="14">github/avatar</text>
<text x="654" y="214" class="mono faint" font-size="11">SHA256</text><text x="654" y="239" class="mono soft" font-size="13">{esc(digest[:16])}</text>
<text x="654" y="283" class="mono faint" font-size="11">GRID</text><text x="654" y="308" class="sans soft" font-size="14">84 × {len(final)}</text>
<text x="654" y="352" class="mono faint" font-size="11">STATE</text><text x="654" y="377" class="sans" font-size="14" font-weight="700">SYNCHRONIZED</text>
''']
    # Coarse silhouette is a short opening phase.
    coarse_op = "0" if not STATIC else "0"
    coarse_reveal_anim = anim('<animate attributeName="opacity" values="0;.75;.75;0" keyTimes="0;.12;.72;1" dur="1.2s" begin=".1s" fill="freeze"/>')
    coarse_group = [f'<g opacity="{coarse_op}">{coarse_reveal_anim}']
    c_top = top + max(0, len(final)-len(coarse))*line_h/2
    for i, line in enumerate(coarse):
        coarse_group.append(f'<text x="310" y="{c_top+i*line_h:.1f}" text-anchor="middle" class="mono" font-size="12" fill="{STEEL}" opacity=".82" xml:space="preserve">{esc(line)}</text>')
    coarse_group.append('</g>')
    parts.extend(coarse_group)
    for i, line in enumerate(final):
        y = top + i*line_h
        if STATIC:
            parts.append(f'<text x="310" y="{y:.1f}" text-anchor="middle" class="mono" font-size="8.8" fill="{TEXT}" opacity=".94" xml:space="preserve">{esc(line)}</text>')
        else:
            delay = 1.0 + i*.026
            parts.append(f'<clipPath id="id{i}"><rect x="42" y="{y-8:.1f}" width="0" height="11"><animate attributeName="width" from="0" to="540" dur=".32s" begin="{delay:.3f}s" fill="freeze"/></rect></clipPath>')
            parts.append(f'<text x="310" y="{y:.1f}" text-anchor="middle" clip-path="url(#id{i})" class="mono" font-size="8.8" fill="{TEXT}" opacity=".94" xml:space="preserve">{esc(line)}</text>')
    id_beam_anim = anim(f'<animate attributeName="y" values="54;{height-30};54" dur="5.2s" begin="1.2s" repeatCount="indefinite"/>')
    parts.append(f'<rect x="24" y="54" width="575" height="1.5" fill="url(#idBeam)" opacity=".45">{id_beam_anim}</rect>')
    return svg(height, "\n".join(parts))


def project_panel(project: dict, kind: str) -> str:
    h = 300
    url = project.get("resolved_url", "")
    status = "VIEW REPOSITORY ↗" if url else "REPOSITORY LINK ACTIVATES AUTOMATICALLY"
    title = project.get("name", "PROJECT")
    subtitle = project.get("subtitle", "")
    description = project.get("description", "")
    desc_lines = wrap_text(description, 61)[:3]
    deco = []
    if kind == "thoth":
        deco.append(owl_pixels(725, 72, 8, "powl"))
        for r in (52, 80, 108):
            deco.append(f'<circle cx="725" cy="142" r="{r}" fill="none" stroke="#22252b" opacity=".6"/>')
        ring_pulse_anim = anim('<animate attributeName="r" values="2;5;2" dur="2.8s" repeatCount="indefinite"/>')
        deco.append(f'<circle cx="725" cy="142" r="3" fill="{CHROME}">{ring_pulse_anim}</circle>')
    else:
        nodes = [(660,92),(762,74),(810,142),(742,206),(645,195),(708,146)]
        edges = [(0,5),(1,5),(2,5),(3,5),(4,5),(0,1),(1,2),(2,3),(3,4),(4,0)]
        for a,b in edges:
            x1,y1=nodes[a]; x2,y2=nodes[b]
            deco.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#343840" stroke-width="1.3"/>')
        for i,(x,y) in enumerate(nodes):
            pulse = anim(f'<animate attributeName="r" values="3;{5 if i==5 else 4};3" dur="{2.2+i*.2:.1f}s" repeatCount="indefinite"/>')
            deco.append(f'<circle cx="{x}" cy="{y}" r="3" fill="{CHROME}" opacity="{.9 if i==5 else .55}">{pulse}</circle>')
        ring_rotate_anim = anim('<animateTransform attributeName="transform" type="rotate" from="0 708 146" to="360 708 146" dur="18s" repeatCount="indefinite"/>')
        deco.append(f'<circle cx="708" cy="146" r="54" fill="none" stroke="#1d2025" stroke-dasharray="4 8">{ring_rotate_anim}</circle>')
    body = [f'''
<defs><linearGradient id="projBeam" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".45" stop-color="#fff" stop-opacity=".55"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient></defs>
<rect width="880" height="300" fill="{BG}"/>
<line x1="38" y1="34" x2="842" y2="34" stroke="{LINE}"/>
<text x="40" y="76" class="mono faint" font-size="12">{esc(project.get('status','IN DEVELOPMENT'))}</text>
<text x="40" y="128" class="sans" font-size="44" font-weight="820">{esc(title)}</text>
<text x="42" y="158" class="serif soft" font-size="18" font-style="italic">{esc(subtitle)}</text>
''']
    for i,line in enumerate(desc_lines):
        body.append(f'<text x="42" y="{204+i*24}" class="sans soft" font-size="14">{esc(line)}</text>')
    body.append(f'<text x="840" y="276" text-anchor="end" class="mono {"soft" if url else "faint"}" font-size="11">{esc(status)}</text>')
    body.extend(deco)
    project_beam_anim = anim('<animate attributeName="x" values="-180;900" dur="5.4s" repeatCount="indefinite"/>')
    body.append(f'<rect x="-180" y="286" width="180" height="2" fill="url(#projBeam)" opacity=".45">{project_beam_anim}</rect>')
    return svg(h, "\n".join(body))


def contribution_days(graph: dict) -> list[dict]:
    return [d for w in graph["contributionsCollection"]["contributionCalendar"]["weeks"] for d in w["contributionDays"]]


def top_languages(graph: dict) -> list[str]:
    totals = {}
    for repo in graph.get("repositories", {}).get("nodes", []):
        for edge in (repo.get("languages") or {}).get("edges", []):
            name = edge["node"]["name"]
            totals[name] = totals.get(name, 0) + int(edge["size"])
    return [name for name,_ in sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:4]]


def signal(graph: dict) -> str:
    total = int(graph["contributionsCollection"]["contributionCalendar"]["totalContributions"])
    repos = int(graph.get("repositories", {}).get("totalCount", 0))
    languages = top_languages(graph)
    ds = contribution_days(graph)
    active = sum(1 for d in ds if int(d["contributionCount"]) > 0)
    weeks = graph["contributionsCollection"]["contributionCalendar"]["weeks"][-53:]
    vals = [sum(int(d["contributionCount"]) for d in w["contributionDays"]) for w in weeks]
    maximum = max(vals or [1]) or 1
    pts = []
    for i,v in enumerate(vals):
        x = 42 + 790*i/max(1,len(vals)-1)
        y = 205 - 80*v/maximum
        pts.append((x,y))
    poly = " ".join(f"{x:.1f},{y:.1f}" for x,y in pts)
    early = total < 100
    headline = "PUBLIC TRACE / INITIALIZING" if early else "PUBLIC TRACE / ACTIVITY"
    lead = f"{repos} public repos" if early else f"{total} contributions"
    secondary = " / ".join(languages) if languages else "public language signal appears as repositories grow"
    body = f'''
<rect width="880" height="270" fill="{BG}"/>
<line x1="38" y1="34" x2="842" y2="34" stroke="{LINE}"/>
<text x="40" y="24" class="mono faint" font-size="12">{esc(headline)}</text>
<text x="40" y="92" class="sans" font-size="42" font-weight="800">{esc(lead)}</text>
<text x="42" y="122" class="sans soft" font-size="15">{esc(secondary)}</text>
<polyline points="{poly}" fill="none" stroke="{CHROME}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="1200" stroke-dashoffset="{"0" if STATIC else "1200"}">{anim('<animate attributeName="stroke-dashoffset" from="1200" to="0" dur="1.8s" begin=".2s" fill="freeze"/>')}</polyline>
<line x1="40" y1="224" x2="840" y2="224" stroke="{LINE}"/>
<text x="40" y="251" class="mono faint" font-size="11">{active} ACTIVE DAYS // GENERATED FROM PUBLIC GITHUB DATA</text>
'''
    return svg(270, body)


def footer(login: str) -> str:
    body = f'''
<rect width="880" height="104" fill="{BG}"/>
<line x1="38" y1="20" x2="842" y2="20" stroke="{LINE}"/>
<rect x="406" y="43" width="8" height="8" fill="{CHROME}" opacity=".9">{anim('<animate attributeName="opacity" values=".9;.14;.9" dur="2.4s" repeatCount="indefinite"/>')}</rect>
<rect x="466" y="43" width="8" height="8" fill="{CHROME}" opacity=".9">{anim('<animate attributeName="opacity" values=".9;.14;.9" dur="2.4s" begin=".08s" repeatCount="indefinite"/>')}</rect>
<text x="440" y="78" text-anchor="middle" class="mono soft" font-size="12" letter-spacing="2">THOTH /FND · @{esc(login)}</text>
'''
    return svg(104, body)


def write_readme(profile: dict, projects: list[dict], login: str) -> None:
    chunks = [
        '<p align="center"><img src="assets/generated/intro.svg" width="100%" alt="THOTH /FND animated owl identity"></p>',
        '<p align="center"><img src="assets/generated/about.svg" width="100%" alt="About thothfnd"></p>',
    ]
    links = []
    for item in profile.get("links", []):
        url = str(item.get("url", "")).strip()
        if url == "AUTO" and item.get("id") == "github":
            url = f"https://github.com/{login}"
        if not url:
            continue
        asset = f'assets/generated/link-{item.get("id")}.svg'
        links.append((url, asset, item.get("label", "LINK")))
    if links:
        chunks.append('<table align="center"><tr>')
        for url, asset, label in links[:2]:
            chunks.append(f'<td width="50%"><a href="{esc(url)}"><img src="{asset}" width="100%" alt="{esc(label)}"></a></td>')
        chunks.append('</tr>')
        if len(links) > 2:
            chunks.append('<tr>')
            for url, asset, label in links[2:4]:
                chunks.append(f'<td width="50%"><a href="{esc(url)}"><img src="{asset}" width="100%" alt="{esc(label)}"></a></td>')
            chunks.append('</tr>')
        chunks.append('</table>')
    chunks.append('<p align="center"><img src="assets/generated/identity.svg" width="100%" alt="ASCII portrait generated from the current GitHub avatar"></p>')
    for p in projects:
        asset = f'assets/generated/project-{p.get("id")}.svg'
        image = f'<img src="{asset}" width="100%" alt="{esc(p.get("name","Project"))}">'
        if p.get("resolved_url"):
            image = f'<a href="{esc(p["resolved_url"])}">{image}</a>'
        chunks.append(f'<p align="center">{image}</p>')
    chunks.append('<p align="center"><img src="assets/generated/signal.svg" width="100%" alt="Public GitHub activity signal"></p>')
    chunks.append('<p align="center"><img src="assets/generated/footer.svg" width="100%" alt="THOTH FND footer"></p>')
    write(ROOT / "README.md", "\n".join(chunks) + "\n")


def main() -> int:
    global STATIC
    parser = argparse.ArgumentParser()
    parser.add_argument("--login", default=os.environ.get("GH_LOGIN", "thothfnd"))
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN", ""))
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--static", action="store_true", help="Render final animation state for local previews")
    args = parser.parse_args()
    STATIC = args.static

    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    try:
        if args.demo or not args.token:
            rest, graph = demo_user(args.login)
        else:
            rest, graph = rest_user(args.login, args.token), graph_user(args.login, args.token)
    except Exception as error:
        print(f"live data fallback: {error}", file=sys.stderr)
        rest, graph = demo_user(args.login)

    projects = resolve_projects(profile, graph, args.login)
    image, digest = (None, "DEMO00000000") if args.demo else fetch_avatar(rest.get("avatar_url", ""), args.token)

    # Clear generated directory first so old V7 outputs cannot survive a V8 refresh.
    ASSETS.mkdir(parents=True, exist_ok=True)
    for old in ASSETS.glob("*.svg"):
        old.unlink()

    write(ASSETS / "intro.svg", intro(args.login))
    write(ASSETS / "about.svg", about(profile))
    link_index = 0
    for item in profile.get("links", []):
        url = str(item.get("url", "")).strip()
        if url == "AUTO" and item.get("id") == "github":
            url = f"https://github.com/{args.login}"
        if not url:
            continue
        write(ASSETS / f"link-{item.get('id')}.svg", link_button(item.get("label", "LINK"), "OPEN ↗", link_index))
        link_index += 1
    write(ASSETS / "identity.svg", identity(image, args.login, digest))
    for p in projects:
        kind = "thoth" if p.get("id") == "thoth-browser" else "relayx"
        write(ASSETS / f"project-{p.get('id')}.svg", project_panel(p, kind))
    write(ASSETS / "signal.svg", signal(graph))
    write(ASSETS / "footer.svg", footer(args.login))
    write_readme(profile, projects, args.login)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
