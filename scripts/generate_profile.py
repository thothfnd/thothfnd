#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
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
ASSETS = ROOT / "assets"
PROJECTS = ASSETS / "projects"
CONFIG = ROOT / "profile.json"

BG = "#0b0f16"
PANEL = "#111723"
PANEL2 = "#0f1520"
FG = "#edf2f8"
MUTED = "#7d8796"
DIM = "#2b3340"
ACCENT = "#6aa8ff"
ACCENT2 = "#8fd3ff"
GOOD = "#3fb950"
RAMP = " .`'^,:;Il!i~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"


def esc(v) -> str:
    return html.escape(str(v), quote=True)


def write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8")


def shell(width: int, height: int, body: str, extra: str = "") -> str:
    return f"""<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"{width}\" height=\"{height}\" viewBox=\"0 0 {width} {height}\">
<style>
text{{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,\"Liberation Mono\",monospace}}
.fg{{fill:{FG}}}.muted{{fill:{MUTED}}}.accent{{fill:{ACCENT}}}.good{{fill:{GOOD}}}
.small{{font-size:10px}} .tiny{{font-size:8px}} .label{{font-size:9px;letter-spacing:.18em}}
{extra}
</style>
{body}
</svg>"""


def api(url: str, token: str = "") -> bytes:
    headers = {"User-Agent": "animated-profile-generator-v4", "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def rest_user(login: str, token: str) -> dict:
    return json.loads(api(f"https://api.github.com/users/{login}", token).decode())


def graph_user(login: str, token: str) -> dict:
    q = r'''
query($login:String!){
 user(login:$login){
  login name bio location websiteUrl createdAt
  followers{totalCount} following{totalCount}
  repositories(first:60,privacy:PUBLIC,ownerAffiliations:OWNER,isFork:false,orderBy:{field:PUSHED_AT,direction:DESC}){
   totalCount nodes{name url stargazerCount forkCount languages(first:8,orderBy:{field:SIZE,direction:DESC}){edges{size node{name color}}}}
  }
  contributionsCollection{contributionCalendar{totalContributions weeks{contributionDays{contributionCount date weekday}}}}
 }
}'''
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": q, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"Bearer {token}", "User-Agent": "animated-profile-generator-v4", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=45) as r:
        obj = json.loads(r.read().decode())
    if obj.get("errors"):
        raise RuntimeError(obj["errors"])
    return obj["data"]["user"]


def demo(login: str) -> tuple[dict, dict]:
    today = dt.date.today()
    ds = []
    for i in range(365):
        d = today - dt.timedelta(days=364-i)
        n = 0 if i % 5 else (i * 7) % 11
        if i % 17 == 0:
            n += 4
        ds.append({"date": d.isoformat(), "contributionCount": n, "weekday": (d.weekday()+1)%7})
    weeks = [{"contributionDays": ds[i:i+7]} for i in range(0, len(ds), 7)]
    g = {
        "login": login,
        "name": login,
        "bio": None,
        "location": None,
        "websiteUrl": None,
        "createdAt": "2024-01-01T00:00:00Z",
        "followers": {"totalCount": 12},
        "following": {"totalCount": 3},
        "repositories": {"totalCount": 3, "nodes": []},
        "contributionsCollection": {"contributionCalendar": {"totalContributions": sum(d["contributionCount"] for d in ds), "weeks": weeks}},
    }
    return {"avatar_url": ""}, g


def days(g: dict) -> list[dict]:
    return [d for w in g["contributionsCollection"]["contributionCalendar"]["weeks"] for d in w["contributionDays"]]


def streaks(ds: list[dict]) -> tuple[int, int]:
    seq = sorted((dt.date.fromisoformat(d["date"]), int(d["contributionCount"])) for d in ds)
    longest = run = 0
    for _, c in seq:
        run = run + 1 if c > 0 else 0
        longest = max(longest, run)
    current = 0
    for i, (_, c) in enumerate(reversed(seq)):
        if i == 0 and c == 0:
            continue
        if c > 0:
            current += 1
        else:
            break
    return current, longest


def langs(g: dict) -> list[tuple[str, int]]:
    totals: dict[str, int] = {}
    for repo in g["repositories"]["nodes"]:
        for edge in (repo.get("languages") or {}).get("edges", []):
            name = edge["node"]["name"]
            totals[name] = totals.get(name, 0) + int(edge["size"])
    return sorted(totals.items(), key=lambda x: x[1], reverse=True)[:6]


def header(label: str) -> str:
    body = f'''
<defs>
  <linearGradient id="hdr" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{ACCENT}" stop-opacity=".75"/>
    <stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/>
  </linearGradient>
</defs>
<text x="8" y="30" class="fg" font-size="18" font-weight="700">{esc(label)}</text>
<line x1="150" y1="24" x2="870" y2="24" stroke="{DIM}" stroke-width="1"/>
<rect x="150" y="23" width="0" height="2" fill="url(#hdr)">
 <animate attributeName="width" from="0" to="180" dur="1.1s" begin=".1s" fill="freeze"/>
</rect>
<rect x="8" y="39" width="0" height="1.5" fill="{ACCENT}">
 <animate attributeName="width" values="0;52;0" dur="3s" repeatCount="indefinite"/>
</rect>'''
    return shell(880, 48, body)


def hero(login: str, g: dict, cfg: dict) -> str:
    name = (g.get("name") or login).upper()
    tagline = cfg.get("tagline") or g.get("bio") or "systems // security // engineering"
    repo_count = g["repositories"]["totalCount"]
    followers = g["followers"]["totalCount"]
    following = g["following"]["totalCount"]
    joined = (g.get("createdAt") or "")[:4] or "--"
    location = (g.get("location") or "NETWORK // PRIVATE")[:24].upper()
    body = f'''
<defs>
 <linearGradient id="scan" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{ACCENT}" stop-opacity="0"/><stop offset=".5" stop-color="{ACCENT}" stop-opacity=".45"/><stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/></linearGradient>
 <linearGradient id="heroLine" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{ACCENT}" stop-opacity="0"/><stop offset=".35" stop-color="{ACCENT}" stop-opacity=".95"/><stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/></linearGradient>
</defs>
<rect x="1" y="1" width="878" height="308" rx="16" fill="{BG}" stroke="{DIM}"/>
<rect x="22" y="20" width="836" height="42" rx="8" fill="{PANEL2}" stroke="{DIM}"/>
<circle cx="40" cy="41" r="4" fill="{GOOD}"><animate attributeName="opacity" values="1;.28;1" dur="1.9s" repeatCount="indefinite"/></circle>
<text x="54" y="45" class="muted" font-size="11">PROFILE // LIVE INTERFACE</text>
<text x="840" y="45" text-anchor="end" class="muted" font-size="10">SYNCED FROM GITHUB</text>
<text x="34" y="110" class="fg" font-size="40" font-weight="700">{esc(name)}</text>
<text x="34" y="140" class="accent" font-size="15">@{esc(login)}</text>
<text x="34" y="182" class="muted" font-size="14">{esc(tagline)}</text>
<line x1="34" y1="202" x2="846" y2="202" stroke="{DIM}"/>
<rect x="34" y="201" width="0" height="2" fill="url(#heroLine)">
 <animate attributeName="width" from="0" to="350" dur="1.25s" begin=".2s" fill="freeze"/>
</rect>
<rect x="34" y="228" width="122" height="52" rx="10" fill="{PANEL}" stroke="{DIM}"/>
<rect x="172" y="228" width="122" height="52" rx="10" fill="{PANEL}" stroke="{DIM}"/>
<rect x="310" y="228" width="122" height="52" rx="10" fill="{PANEL}" stroke="{DIM}"/>
<rect x="448" y="228" width="122" height="52" rx="10" fill="{PANEL}" stroke="{DIM}"/>
<rect x="586" y="228" width="260" height="52" rx="10" fill="{PANEL}" stroke="{DIM}"/>
<text x="50" y="250" class="muted tiny">REPOS</text><text x="50" y="270" class="fg" font-size="20" font-weight="700">{repo_count}</text>
<text x="188" y="250" class="muted tiny">FOLLOWERS</text><text x="188" y="270" class="fg" font-size="20" font-weight="700">{followers}</text>
<text x="326" y="250" class="muted tiny">FOLLOWING</text><text x="326" y="270" class="fg" font-size="20" font-weight="700">{following}</text>
<text x="464" y="250" class="muted tiny">JOINED</text><text x="464" y="270" class="fg" font-size="20" font-weight="700">{esc(joined)}</text>
<text x="602" y="250" class="muted tiny">LOCATION / STATUS</text><text x="602" y="270" class="fg small">{esc(location)}</text>
<text x="788" y="270" text-anchor="end" class="good small">ONLINE</text>
<rect x="-220" y="294" width="220" height="2" fill="url(#scan)"><animate attributeName="x" values="-220;880" dur="4.8s" repeatCount="indefinite"/></rect>
'''
    return shell(880, 310, body)


def avatar(url: str, token: str) -> Image.Image | None:
    if not url:
        return None
    try:
        raw = api(url + ("&" if "?" in url else "?") + "s=900", token)
        return Image.open(io.BytesIO(raw)).convert("RGBA")
    except Exception as exc:
        print(f"avatar fallback: {exc}", file=sys.stderr)
        return None


def ascii_lines(img: Image.Image) -> list[str]:
    try:
        from rembg import remove
        cut = remove(img)
        if not isinstance(cut, Image.Image):
            cut = Image.open(io.BytesIO(cut)).convert("RGBA")
        img = cut
    except Exception as exc:
        print(f"rembg fallback: {exc}", file=sys.stderr)
    alpha = np.array(img.getchannel("A"))
    ys, xs = np.where(alpha > 16)
    if len(xs) > 10:
        pad = 18
        img = img.crop((max(0, int(xs.min())-pad), max(0, int(ys.min())-pad), min(img.width, int(xs.max())+pad), min(img.height, int(ys.max())+pad)))
    canvas = Image.new("RGB", img.size, "white")
    canvas.paste(img.convert("RGB"), mask=img.getchannel("A"))
    gray = np.array(canvas.convert("L"))
    gray = cv2.createCLAHE(clipLimit=2.6, tileGridSize=(8, 8)).apply(gray)
    gray = cv2.GaussianBlur(gray, (0, 0), 0.6)
    v = np.power(gray.astype(np.float32) / 255.0, 1.45)
    gray = np.clip(v * 255, 0, 255).astype(np.uint8)
    cols = 100
    ratio = gray.shape[0] / max(1, gray.shape[1])
    rows = max(28, min(78, int(cols * ratio * 0.50)))
    small = cv2.resize(gray, (cols, rows), interpolation=cv2.INTER_AREA)
    out = []
    for row in small:
        s = ''.join(RAMP[int((255-int(px)) / 255 * (len(RAMP)-1))] for px in row).rstrip()
        out.append(s)
    return out


def portrait(img: Image.Image | None, login: str) -> str:
    if img is None:
        ls = [
            "                           .,:iillllii:,.",
            "                      .:iIttfffjjjrrxxnnuuI;.",
            "                  .;tXXUUUUUUUUUUUUUUUUUUXXf,",
            "                :fXUUUUUUUUUUUUUUUUUUUUUUUUXr",
            "              .nXUUUUU.   PROFILE   .UUUUUUXj",
            "              ;XUUUUUU    AVATAR     UUUUUUXt",
            "              ;XUUUUUU      SYNC      UUUUUUXt",
            "              .nXUUUUU.    READY     .UUUUUUXj",
            "                :fXUUUUUUUUUUUUUUUUUUUUUUUUXr",
            "                  .;tXXUUUUUUUUUUUUUUUUUUXXf,",
            "                      .:iIttfffjjjrrxxnnuuI;.",
            "                           .,:iillllii:,.",
        ]
    else:
        ls = ascii_lines(img)
    line_h = 8.8
    top = 92
    h = int(top + len(ls) * line_h + 46)
    parts = [f'''
<defs>
 <linearGradient id="scanP" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{ACCENT}" stop-opacity="0"/><stop offset=".5" stop-color="{ACCENT}" stop-opacity=".65"/><stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/></linearGradient>
 <filter id="glow"><feGaussianBlur stdDeviation="2" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
</defs>
<rect x="1" y="1" width="878" height="{h-2}" rx="14" fill="{BG}" stroke="{DIM}"/>
<rect x="20" y="18" width="840" height="38" rx="8" fill="{PANEL2}" stroke="{DIM}"/>
<circle cx="38" cy="37" r="3.5" fill="{GOOD}" filter="url(#glow)"><animate attributeName="opacity" values="1;.25;1" dur="1.5s" repeatCount="indefinite"/></circle>
<text x="52" y="41" class="muted" font-size="10">IDENTITY SCAN // BUILDING ASCII PORTRAIT</text>
<text x="840" y="41" text-anchor="end" class="muted" font-size="9">@{esc(login)}</text>
<text x="36" y="68" class="muted" font-size="8.5">STEP 01  FETCH AVATAR</text>
<text x="174" y="68" class="muted" font-size="8.5">STEP 02  EXTRACT SUBJECT</text>
<text x="354" y="68" class="muted" font-size="8.5">STEP 03  MAP TO RAMP</text>
<text x="510" y="68" class="muted" font-size="8.5">STEP 04  REVEAL</text>
<rect x="35" y="78" width="0" height="1.4" fill="{ACCENT}"><animate attributeName="width" from="0" to="180" dur=".9s" begin=".05s" fill="freeze"/></rect>
<rect x="215" y="78" width="0" height="1.4" fill="{ACCENT}"><animate attributeName="width" from="0" to="150" dur=".9s" begin=".28s" fill="freeze"/></rect>
<rect x="365" y="78" width="0" height="1.4" fill="{ACCENT}"><animate attributeName="width" from="0" to="125" dur=".9s" begin=".53s" fill="freeze"/></rect>
<rect x="490" y="78" width="0" height="1.4" fill="{ACCENT}"><animate attributeName="width" from="0" to="110" dur=".9s" begin=".76s" fill="freeze"/></rect>
''']
    for i, line in enumerate(ls):
        y = top + i * line_h
        delay = 0.78 + i * 0.030
        parts.append(f'<clipPath id="cp{i}"><rect x="39" y="{y-7:.1f}" width="0" height="10"><animate attributeName="width" from="0" to="800" dur=".42s" begin="{delay:.3f}s" fill="freeze"/></rect></clipPath>')
        parts.append(f'<text x="440" y="{y:.1f}" text-anchor="middle" clip-path="url(#cp{i})" fill="{FG}" fill-opacity=".90" font-size="7.6" xml:space="preserve">{esc(line)}</text>')
    parts.append(f'<rect x="39" y="{h-18}" width="8" height="11" fill="{ACCENT}"><animate attributeName="opacity" values="1;0;1" dur="1s" repeatCount="indefinite"/></rect>')
    parts.append(f'<rect x="-240" y="{h-26}" width="240" height="1.5" fill="url(#scanP)"><animate attributeName="x" values="-240;890" dur="5s" begin="1.3s" repeatCount="indefinite"/></rect>')
    return shell(880, h, "\n".join(parts))


def activity(g: dict) -> str:
    total = g["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    ds = days(g)
    active = sum(1 for d in ds if d["contributionCount"] > 0)
    ws = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in g["contributionsCollection"]["contributionCalendar"]["weeks"]]
    best = max(ws or [0])
    maxv = max(ws or [1]) or 1
    pts = []
    for i, v in enumerate(ws):
        x = 40 + 800 * i / max(1, len(ws)-1)
        y = 220 - 78 * v / maxv
        pts.append((x, y))
    poly = ' '.join(f'{x:.1f},{y:.1f}' for x, y in pts)
    body = f'''
<rect x="1" y="1" width="878" height="270" rx="14" fill="{BG}" stroke="{DIM}"/>
<text x="34" y="64" class="fg" font-size="44" font-weight="700">{total}</text>
<text x="34" y="86" class="muted" font-size="11">CONTRIBUTIONS // LAST YEAR</text>
<text x="822" y="51" text-anchor="end" class="fg" font-size="18" font-weight="700">{active}</text><text x="822" y="69" text-anchor="end" class="muted" font-size="10">ACTIVE DAYS</text>
<text x="822" y="103" text-anchor="end" class="fg" font-size="18" font-weight="700">{best}</text><text x="822" y="121" text-anchor="end" class="muted" font-size="10">BEST WEEK</text>
<polyline points="{poly}" fill="none" stroke="{ACCENT2}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="1200" stroke-dashoffset="1200"><animate attributeName="stroke-dashoffset" from="1200" to="0" dur="1.95s" begin=".15s" fill="freeze"/></polyline>
<line x1="40" y1="235" x2="840" y2="235" stroke="{DIM}"/>
'''
    if pts:
        x, y = pts[-1]
        body += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{FG}"><animate attributeName="r" values="3;5.1;3" dur="1.9s" repeatCount="indefinite"/></circle>'
    return shell(880, 270, body)


def about(g: dict, cfg: dict) -> str:
    lines = list(cfg.get("about", []))
    if g.get("bio") and g["bio"] not in lines:
        lines = [g["bio"]] + lines
    chunks = []
    for line in lines[:3]:
        cur = ""
        for word in line.split():
            if len(cur) + len(word) + 1 > 92:
                chunks.append(cur)
                cur = word
            else:
                cur = (cur + ' ' + word).strip()
        if cur:
            chunks.append(cur)
    h = 126 + 24 * len(chunks)
    parts = [f'<rect x="1" y="1" width="878" height="{h-2}" rx="14" fill="{BG}" stroke="{DIM}"/>', f'<rect x="28" y="32" width="2" height="{max(56, 24*len(chunks))}" fill="{ACCENT}" opacity=".85"/>']
    y = 52
    for c in chunks:
        parts.append(f'<text x="48" y="{y}" class="fg" font-size="13">{esc(c)}</text>')
        y += 24
    parts.append(f'<text x="48" y="{h-24}" class="muted" font-size="10">FOCUS // PRIVACY • SECURITY • SYSTEMS</text>')
    return shell(880, h, "\n".join(parts))


def stack(cfg: dict) -> str:
    groups = cfg.get("stack_groups") or [{"label": "STACK", "items": cfg.get("stack", [])}]
    total = str(cfg.get("stack_total", "200+"))
    width, height = 880, 348
    body = [f'''
<defs>
 <linearGradient id="stackScan" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{ACCENT}" stop-opacity="0"/><stop offset=".5" stop-color="{ACCENT}" stop-opacity=".8"/><stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/></linearGradient>
</defs>
<rect x="1" y="1" width="878" height="346" rx="14" fill="{BG}" stroke="{DIM}"/>
<text x="28" y="24" class="muted" font-size="9">CAPABILITY MATRIX // CURATED SIGNAL</text>
<text x="852" y="24" text-anchor="end" class="muted" font-size="9">KNOWN → NICHE</text>
''']
    row_y = [70, 124, 178, 232, 286]
    specs = [
        [(118, 62), (112, 62), (138, 62), (104, 62), (86, 62), (86, 62), (70, 62)],
        [(106, 38), (114, 38), (112, 38), (98, 38), (88, 38), (118, 38), (70, 38)],
        [(100, 38), (140, 38), (120, 38), (104, 38), (86, 38), (86, 38), (70, 38)],
        [(92, 38), (90, 38), (126, 38), (112, 38), (88, 38), (92, 38), (118, 38)],
        [(92, 38), (88, 38), (88, 38), (86, 38), (88, 38), (90, 38), (78, 38)],
    ]
    body.append(f'<rect x="706" y="58" width="146" height="214" rx="12" fill="{PANEL}" stroke="{ACCENT}" stroke-opacity=".55"/>')
    body.append(f'<text x="724" y="94" class="muted" font-size="9">TOTAL RANGE</text>')
    num = re.sub(r'[^0-9]', '', total) or '200'
    plus = '+' if '+' in total else ''
    body.append(f'<text x="724" y="152" class="accent" font-size="42" font-weight="700">{esc(num)}{esc(plus)}</text>')
    body.append(f'<text x="724" y="176" class="fg" font-size="11">TECHNOLOGIES</text>')
    body.append(f'<text x="724" y="196" class="muted" font-size="9">LANGUAGES // FRAMEWORKS</text>')
    body.append(f'<text x="724" y="212" class="muted" font-size="9">SYSTEMS // NETWORK // DATA</text>')
    body.append(f'<text x="724" y="228" class="muted" font-size="9">CLOUD // SECURITY // LOW-LEVEL</text>')
    body.append(f'<circle cx="832" cy="86" r="3.5" fill="{GOOD}"><animate attributeName="opacity" values="1;.25;1" dur="1.8s" repeatCount="indefinite"/></circle>')
    body.append(f'<text x="820" y="90" text-anchor="end" class="muted" font-size="9">A–Z</text>')
    for gi, group in enumerate(groups[:5]):
        gy = row_y[gi]
        body.append(f'<text x="28" y="{gy-14}" class="muted label">{esc(group.get("label", "GROUP"))}</text>')
        items = [str(i) for i in group.get("items", [])][:7]
        x = 118
        alpha = 1.0 - gi * 0.10
        for ii, item in enumerate(items):
            w, h = specs[gi][ii]
            delay = 0.12 + (gi*7+ii) * 0.045
            stroke = ACCENT if gi == 0 and ii < 3 else DIM
            text_size = 10.8 if gi == 0 else 9.3
            weight = '700' if gi == 0 else '400'
            body.append(f'''
<g opacity="0">
 <animate attributeName="opacity" from="0" to="1" dur=".34s" begin="{delay:.3f}s" fill="freeze"/>
 <rect x="{x}" y="{gy-h/2:.1f}" width="{w}" height="{h}" rx="8" fill="{PANEL}" stroke="{stroke}" stroke-opacity="{alpha:.2f}">
  <animate attributeName="stroke" values="{stroke};{ACCENT};{stroke}" dur="3.8s" begin="{1.6 + (gi+ii)*0.12:.2f}s" repeatCount="indefinite"/>
 </rect>
 <text x="{x+12}" y="{gy+4}" class="fg" font-size="{text_size}" font-weight="{weight}">{esc(item.upper())}</text>
 <rect x="{x+10}" y="{gy+h/2-9:.1f}" width="0" height="1.4" rx=".7" fill="{ACCENT2}" opacity=".75">
  <animate attributeName="width" from="0" to="{max(20, w-20)}" dur=".55s" begin="{delay+0.08:.3f}s" fill="freeze"/>
 </rect>
</g>''')
            x += w + 10
    body.append(f'<line x1="28" y1="320" x2="852" y2="320" stroke="{DIM}"/>')
    body.append(f'<text x="28" y="339" class="muted" font-size="8.5">VISIBLE SET = CURATED SAMPLE // THE BIG TILE REPRESENTS THE REST OF THE COVERAGE</text>')
    body.append(f'<rect x="-220" y="319" width="220" height="2" fill="url(#stackScan)"><animate attributeName="x" values="-220;890" dur="4.4s" repeatCount="indefinite"/></rect>')
    return shell(width, height, "\n".join(body))


def project_card(p: dict, i: int) -> str:
    words = p.get("description", "").split()
    lines = []
    cur = ""
    for word in words:
        if len(cur) + len(word) + 1 > 94:
            lines.append(cur)
            cur = word
        else:
            cur = (cur + ' ' + word).strip()
    if cur:
        lines.append(cur)
    body = f'''
<defs>
 <linearGradient id="projScan{i}" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{ACCENT}" stop-opacity="0"/><stop offset=".5" stop-color="{ACCENT}" stop-opacity=".22"/><stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/></linearGradient>
</defs>
<rect x="1" y="1" width="878" height="174" rx="14" fill="{BG}" stroke="{DIM}"/>
<rect x="24" y="24" width="830" height="126" rx="10" fill="{PANEL2}" stroke="{DIM}"/>
<text x="40" y="48" class="muted" font-size="9">PROJECT // {i:02d}</text>
<text x="40" y="84" class="fg" font-size="24" font-weight="700">{esc(p.get("name", "PROJECT"))}</text>
<text x="40" y="111" class="accent" font-size="10">{esc(p.get("tech", ""))}</text>
<circle cx="820" cy="41" r="4" fill="{GOOD}"><animate attributeName="opacity" values="1;.24;1" dur="2s" begin="{i*.18:.2f}s" repeatCount="indefinite"/></circle>
<text x="808" y="45" text-anchor="end" class="muted" font-size="9">{esc(p.get("status", "ACTIVE"))}</text>
'''
    y = 134
    for line in lines[:2]:
        body += f'<text x="40" y="{y}" class="muted" font-size="11">{esc(line)}</text>'
        y += 18
    body += f'<rect x="-220" y="162" width="220" height="2" fill="url(#projScan{i})"><animate attributeName="x" values="-220;900" dur="{4.1+i*.25:.1f}s" repeatCount="indefinite"/></rect>'
    return shell(880, 176, body)


def stats(g: dict) -> str:
    ds = days(g)
    cur, longest = streaks(ds)
    repos = g["repositories"]["totalCount"]
    stars = sum(int(r.get("stargazerCount") or 0) for r in g["repositories"]["nodes"])
    forks = sum(int(r.get("forkCount") or 0) for r in g["repositories"]["nodes"])
    tops = langs(g)
    total = max(1, sum(v for _, v in tops))
    boxes = [("CURRENT STREAK", cur), ("LONGEST STREAK", longest), ("PUBLIC REPOS", repos), ("STARS", stars), ("FORKS", forks)]
    body = [f'<rect x="1" y="1" width="878" height="326" rx="14" fill="{BG}" stroke="{DIM}"/>']
    x = 28
    for lab, val in boxes:
        body.append(f'<rect x="{x-8}" y="24" width="146" height="58" rx="10" fill="{PANEL}" stroke="{DIM}"/>')
        body.append(f'<text x="{x}" y="52" class="fg" font-size="24" font-weight="700">{val}</text>')
        body.append(f'<text x="{x}" y="72" class="muted" font-size="8.5">{lab}</text>')
        x += 165
    body.append(f'<line x1="28" y1="106" x2="850" y2="106" stroke="{DIM}"/>')
    y = 146
    if not tops:
        body.append(f'<text x="28" y="150" class="muted" font-size="11">language data appears after the first live refresh.</text>')
    for i, (name, size) in enumerate(tops):
        pct = size / total
        bw = 520 * pct
        d = .35 + i * .10
        body.append(f'<text x="28" y="{y}" class="fg" font-size="11">{esc(name.lower())}</text>')
        body.append(f'<rect x="180" y="{y-10}" width="520" height="8" rx="4" fill="{DIM}"/>')
        body.append(f'<rect x="180" y="{y-10}" width="0" height="8" rx="4" fill="{ACCENT2}"><animate attributeName="width" from="0" to="{bw:.1f}" dur=".8s" begin="{d:.2f}s" fill="freeze"/></rect>')
        body.append(f'<text x="730" y="{y}" class="muted" font-size="10">{pct*100:4.1f}%</text>')
        y += 28
    return shell(880, 328, "\n".join(body))


def year(g: dict) -> str:
    weeks = g["contributionsCollection"]["contributionCalendar"]["weeks"][-53:]
    counts = [int(d["contributionCount"]) for w in weeks for d in w["contributionDays"]]
    maxc = max(counts or [1])
    body = [f'<rect x="1" y="1" width="878" height="190" rx="14" fill="{BG}" stroke="{DIM}"/>', f'<text x="28" y="30" class="muted" font-size="10">THE YEAR // CONTRIBUTION SIGNAL</text>']
    cell = 10
    gap = 3
    x0 = 94
    y0 = 64
    for label, wd in [("mon", 1), ("wed", 3), ("fri", 5)]:
        body.append(f'<text x="28" y="{y0+wd*(cell+gap)+9}" class="muted" font-size="8">{label}</text>')
    for wi, w in enumerate(weeks):
        for d in w["contributionDays"]:
            wd = int(d.get("weekday", 0))
            c = int(d["contributionCount"])
            x = x0 + wi*(cell+gap)
            y = y0 + wd*(cell+gap)
            delay = (wi*7+wd)*.003
            if c <= 0:
                fill = DIM
                op = .35
            else:
                fill = ACCENT2
                op = .26 + .74 * (math.log1p(c)/math.log1p(maxc))
            body.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{fill}" opacity="0"><animate attributeName="opacity" from="0" to="{op:.2f}" dur=".16s" begin="{delay:.3f}s" fill="freeze"/></rect>')
    body.append(f'<text x="850" y="174" text-anchor="end" class="muted" font-size="9">QUIET  ·  LOUD</text>')
    return shell(880, 192, "\n".join(body))


def footer(cfg: dict) -> str:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    body = f'<line x1="8" y1="14" x2="872" y2="14" stroke="{DIM}"/><text x="8" y="48" class="fg" font-size="12">{esc(cfg.get("footer", "VERIFY EVERYTHING."))}</text><text x="8" y="72" class="muted" font-size="9">GENERATED LOCALLY // NO THIRD-PARTY BADGE SERVICE // {esc(stamp)}</text><rect x="846" y="38" width="8" height="14" fill="{ACCENT}"><animate attributeName="opacity" values="1;0;1" dur=".9s" repeatCount="indefinite"/></rect>'
    return shell(880, 90, body)


def update_readme(projects: list[dict]) -> None:
    p = ROOT / "README.md"
    s = p.read_text(encoding="utf-8")
    start = "<!-- PROJECT_CARDS_START -->"
    end = "<!-- PROJECT_CARDS_END -->"
    cards = []
    for i, proj in enumerate(projects, 1):
        alt = esc(proj.get("name", "project"))
        img = f'assets/projects/project-{i:02d}.svg'
        url = proj.get("url", "").strip()
        core = f'<img src="{img}" width="100%" alt="{alt}">'
        if url:
            core = f'<a href="{esc(url)}">{core}</a>'
        cards.append(f'<p align="center">{core}</p>')
    s = re.sub(re.escape(start) + r'.*?' + re.escape(end), start + "\n" + "\n".join(cards) + "\n" + end, s, flags=re.S)
    p.write_text(s, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--login", default=os.environ.get("GH_LOGIN", "profile"))
    ap.add_argument("--token", default=os.environ.get("GITHUB_TOKEN", ""))
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    try:
        if a.demo or not a.token:
            rest, g = demo(a.login)
        else:
            rest, g = rest_user(a.login, a.token), graph_user(a.login, a.token)
    except Exception as exc:
        print(f"live data fallback: {exc}", file=sys.stderr)
        rest, g = demo(a.login)
    img = None if a.demo else avatar(rest.get("avatar_url", ""), a.token)
    write(ASSETS / "hero.svg", hero(a.login, g, cfg))
    write(ASSETS / "portrait.svg", portrait(img, a.login))
    write(ASSETS / "activity.svg", activity(g))
    write(ASSETS / "about.svg", about(g, cfg))
    write(ASSETS / "stack.svg", stack(cfg))
    write(ASSETS / "stats.svg", stats(g))
    write(ASSETS / "year.svg", year(g))
    write(ASSETS / "footer.svg", footer(cfg))
    for title in ("about", "stack", "projects", "stats"):
        write(ASSETS / f"hd-{title}.svg", header(title))
    PROJECTS.mkdir(parents=True, exist_ok=True)
    for p in PROJECTS.glob("project-*.svg"):
        p.unlink()
    projs = cfg.get("projects", [])
    for i, p in enumerate(projs, 1):
        write(PROJECTS / f"project-{i:02d}.svg", project_card(p, i))
    update_readme(projs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
