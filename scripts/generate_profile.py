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

BG = "#0a0a0b"
CARD = "#111214"
CARD2 = "#16181c"
STROKE = "#2a2d33"
TEXT = "#f5f7fa"
MUTED = "#a1a8b3"
SUBTLE = "#7b828d"
LIGHT = "#d4d7dc"
LIGHT2 = "#b8bec6"
GOOD = "#d9dde2"
ASCII_RAMP = " .`'^,:;Il!i~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"


def esc(v) -> str:
    return html.escape(str(v), quote=True)


def write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8")


def shell(width: int, height: int, body: str, extra: str = "") -> str:
    return f"""<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"{width}\" height=\"{height}\" viewBox=\"0 0 {width} {height}\">
<style>
.title{{font-family:ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,\"Segoe UI\",Arial,sans-serif;fill:{TEXT}}}
.sans{{font-family:ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,\"Segoe UI\",Arial,sans-serif;fill:{TEXT}}}
.mono{{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,\"Liberation Mono\",monospace;fill:{TEXT}}}
.muted{{fill:{MUTED}}}.subtle{{fill:{SUBTLE}}}.light{{fill:{LIGHT}}}
{extra}
</style>
{body}
</svg>"""


def api(url: str, token: str = "") -> bytes:
    headers = {"User-Agent": "github-profile-v5-chrome", "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def rest_user(login: str, token: str) -> dict:
    return json.loads(api(f"https://api.github.com/users/{login}", token).decode())


def graph_user(login: str, token: str) -> dict:
    query = r'''
query($login:String!){
 user(login:$login){
  login name bio location websiteUrl createdAt
  followers{totalCount} following{totalCount}
  repositories(first:60,privacy:PUBLIC,ownerAffiliations:OWNER,isFork:false,orderBy:{field:PUSHED_AT,direction:DESC}){
   totalCount
   nodes{name url stargazerCount forkCount languages(first:8,orderBy:{field:SIZE,direction:DESC}){edges{size node{name color}}}}
  }
  contributionsCollection{contributionCalendar{totalContributions weeks{contributionDays{contributionCount date weekday}}}}
 }
}'''
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": {"login": login}}).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "github-profile-v5-chrome",
            "Content-Type": "application/json",
        },
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
        d = today - dt.timedelta(days=364 - i)
        n = 0 if i % 5 else (i * 7) % 11
        if i % 17 == 0:
            n += 4
        ds.append({"date": d.isoformat(), "contributionCount": n, "weekday": (d.weekday() + 1) % 7})
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


def flatten_days(g: dict) -> list[dict]:
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


def top_languages(g: dict) -> list[tuple[str, int]]:
    totals: dict[str, int] = {}
    for repo in g["repositories"]["nodes"]:
        for edge in (repo.get("languages") or {}).get("edges", []):
            name = edge["node"]["name"]
            totals[name] = totals.get(name, 0) + int(edge["size"])
    return sorted(totals.items(), key=lambda x: x[1], reverse=True)[:6]


def header(label: str) -> str:
    body = f'''
<defs>
  <linearGradient id="metal" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{LIGHT}" stop-opacity=".9"/>
    <stop offset="1" stop-color="{LIGHT}" stop-opacity="0"/>
  </linearGradient>
</defs>
<text x="8" y="30" class="title" font-size="18" font-weight="700">{esc(label)}</text>
<line x1="150" y1="24" x2="870" y2="24" stroke="{STROKE}" stroke-width="1"/>
<rect x="150" y="23" width="0" height="2" fill="url(#metal)"><animate attributeName="width" from="0" to="150" dur="1.0s" begin=".12s" fill="freeze"/></rect>
<rect x="8" y="39" width="0" height="1.5" fill="{LIGHT2}"><animate attributeName="width" values="0;48;0" dur="3.2s" repeatCount="indefinite"/></rect>
'''
    return shell(880, 48, body)


def hero(login: str, g: dict, cfg: dict) -> str:
    name = (g.get("name") or login).upper()
    tagline = cfg.get("tagline") or g.get("bio") or "privacy engineering"
    repo_count = g["repositories"]["totalCount"]
    followers = g["followers"]["totalCount"]
    following = g["following"]["totalCount"]
    joined = (g.get("createdAt") or "")[:4] or "--"
    location = (g.get("location") or "NETWORK // PRIVATE")[:26].upper()
    body = f'''
<defs>
  <linearGradient id="heroBorder" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{LIGHT}" stop-opacity=".32"/>
    <stop offset="1" stop-color="{LIGHT}" stop-opacity=".08"/>
  </linearGradient>
  <linearGradient id="scan" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{LIGHT}" stop-opacity="0"/>
    <stop offset=".5" stop-color="{LIGHT}" stop-opacity=".7"/>
    <stop offset="1" stop-color="{LIGHT}" stop-opacity="0"/>
  </linearGradient>
</defs>
<rect x="1" y="1" width="878" height="298" rx="18" fill="{BG}" stroke="url(#heroBorder)"/>
<rect x="22" y="22" width="836" height="38" rx="10" fill="{CARD2}" stroke="{STROKE}"/>
<circle cx="42" cy="41" r="4" fill="{LIGHT}"><animate attributeName="opacity" values="1;.26;1" dur="2.1s" repeatCount="indefinite"/></circle>
<text x="56" y="45" class="mono muted" font-size="10">PROFILE // CHROME INTERFACE</text>
<text x="840" y="45" text-anchor="end" class="mono muted" font-size="9">SYNCED FROM GITHUB</text>

<text x="34" y="110" class="title" font-size="42" font-weight="800">{esc(name)}</text>
<text x="34" y="139" class="mono subtle" font-size="13">@{esc(login)}</text>
<text x="34" y="177" class="sans muted" font-size="15">{esc(tagline)}</text>
<line x1="34" y1="196" x2="846" y2="196" stroke="{STROKE}"/>
<rect x="34" y="195" width="0" height="2" fill="{LIGHT2}"><animate attributeName="width" from="0" to="300" dur="1.1s" begin=".15s" fill="freeze"/></rect>

<rect x="34" y="222" width="122" height="50" rx="12" fill="{CARD}" stroke="{STROKE}"/>
<rect x="172" y="222" width="122" height="50" rx="12" fill="{CARD}" stroke="{STROKE}"/>
<rect x="310" y="222" width="122" height="50" rx="12" fill="{CARD}" stroke="{STROKE}"/>
<rect x="448" y="222" width="122" height="50" rx="12" fill="{CARD}" stroke="{STROKE}"/>
<rect x="586" y="222" width="260" height="50" rx="12" fill="{CARD}" stroke="{STROKE}"/>

<text x="50" y="243" class="mono subtle" font-size="8">REPOS</text><text x="50" y="262" class="title" font-size="20" font-weight="700">{repo_count}</text>
<text x="188" y="243" class="mono subtle" font-size="8">FOLLOWERS</text><text x="188" y="262" class="title" font-size="20" font-weight="700">{followers}</text>
<text x="326" y="243" class="mono subtle" font-size="8">FOLLOWING</text><text x="326" y="262" class="title" font-size="20" font-weight="700">{following}</text>
<text x="464" y="243" class="mono subtle" font-size="8">JOINED</text><text x="464" y="262" class="title" font-size="20" font-weight="700">{esc(joined)}</text>
<text x="602" y="243" class="mono subtle" font-size="8">LOCATION / STATUS</text><text x="602" y="262" class="sans" font-size="11">{esc(location)}</text>
<text x="814" y="262" text-anchor="end" class="mono muted" font-size="10">ONLINE</text>

<rect x="-220" y="286" width="220" height="2" fill="url(#scan)"><animate attributeName="x" values="-220;900" dur="5.2s" repeatCount="indefinite"/></rect>
'''
    return shell(880, 300, body)


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
    gray = cv2.createCLAHE(clipLimit=2.8, tileGridSize=(8, 8)).apply(gray)
    gray = cv2.GaussianBlur(gray, (0, 0), 0.55)
    v = np.power(gray.astype(np.float32) / 255.0, 1.42)
    gray = np.clip(v * 255, 0, 255).astype(np.uint8)
    cols = 100
    ratio = gray.shape[0] / max(1, gray.shape[1])
    rows = max(30, min(76, int(cols * ratio * 0.49)))
    small = cv2.resize(gray, (cols, rows), interpolation=cv2.INTER_AREA)
    out = []
    for row in small:
        s = ''.join(ASCII_RAMP[int((255-int(px)) / 255 * (len(ASCII_RAMP)-1))] for px in row).rstrip()
        out.append(s)
    return out


def portrait(img: Image.Image | None, login: str) -> str:
    if img is None:
        ls = [
            "                             .,:iillllii:,.",
            "                        .:iIttfffjjjrrxxnnuuI;.",
            "                    .;tXXUUUUUUUUUUUUUUUUUUXXf,",
            "                  :fXUUUUUUUUUUUUUUUUUUUUUUUUXr",
            "                .nXUUUUU.    PROFILE      .UUXj",
            "                ;XUUUUUU     AVATAR        UUXt",
            "                ;XUUUUUU     READY         UUXt",
            "                .nXUUUUU.    SYNC         .UUXj",
            "                  :fXUUUUUUUUUUUUUUUUUUUUUUUUXr",
            "                    .;tXXUUUUUUUUUUUUUUUUUUXXf,",
            "                        .:iIttfffjjjrrxxnnuuI;.",
            "                             .,:iillllii:,.",
        ]
    else:
        ls = ascii_lines(img)
    line_h = 8.8
    top = 96
    h = int(top + len(ls) * line_h + 44)
    pills = [
        (36, 66, 160, "FETCH AVATAR"),
        (212, 66, 174, "ISOLATE SUBJECT"),
        (402, 66, 170, "MAP TO ASCII"),
        (588, 66, 160, "LIVE REVEAL"),
    ]
    parts = [f'''
<defs>
  <linearGradient id="chrome" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{LIGHT}" stop-opacity=".32"/>
    <stop offset="1" stop-color="{LIGHT}" stop-opacity=".08"/>
  </linearGradient>
  <linearGradient id="scanP" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{LIGHT}" stop-opacity="0"/>
    <stop offset=".5" stop-color="{LIGHT}" stop-opacity=".7"/>
    <stop offset="1" stop-color="{LIGHT}" stop-opacity="0"/>
  </linearGradient>
</defs>
<rect x="1" y="1" width="878" height="{h-2}" rx="18" fill="{BG}" stroke="url(#chrome)"/>
<rect x="20" y="18" width="840" height="38" rx="10" fill="{CARD2}" stroke="{STROKE}"/>
<circle cx="40" cy="37" r="4" fill="{LIGHT}"><animate attributeName="opacity" values="1;.25;1" dur="1.7s" repeatCount="indefinite"/></circle>
<text x="54" y="41" class="mono muted" font-size="10">IDENTITY PIPELINE // ASCII PORTRAIT</text>
<text x="840" y="41" text-anchor="end" class="mono muted" font-size="9">@{esc(login)}</text>
''']
    for idx, (x, y, w, label) in enumerate(pills):
        delay = 0.10 + idx * 0.18
        parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="24" rx="12" fill="{CARD}" stroke="{STROKE}"/>')
        parts.append(f'<text x="{x + w/2}" y="{y + 16}" text-anchor="middle" class="mono subtle" font-size="8">{esc(label)}</text>')
        parts.append(f'<rect x="{x+10}" y="{y+22}" width="0" height="1.4" fill="{LIGHT2}"><animate attributeName="width" from="0" to="{w-20}" dur=".7s" begin="{delay:.2f}s" fill="freeze"/></rect>')
    for i, line in enumerate(ls):
        y = top + i * line_h
        delay = 0.88 + i * 0.028
        parts.append(f'<clipPath id="cp{i}"><rect x="42" y="{y-7:.1f}" width="0" height="10"><animate attributeName="width" from="0" to="796" dur=".38s" begin="{delay:.3f}s" fill="freeze"/></rect></clipPath>')
        parts.append(f'<text x="440" y="{y:.1f}" text-anchor="middle" clip-path="url(#cp{i})" class="mono" style="font-size:7.5px;fill:{TEXT};opacity:.92" xml:space="preserve">{esc(line)}</text>')
    parts.append(f'<rect x="42" y="{h-18}" width="8" height="11" fill="{LIGHT2}"><animate attributeName="opacity" values="1;0;1" dur="1s" repeatCount="indefinite"/></rect>')
    parts.append(f'<rect x="-220" y="{h-26}" width="220" height="1.5" fill="url(#scanP)"><animate attributeName="x" values="-220;900" dur="5.0s" begin="1.2s" repeatCount="indefinite"/></rect>')
    return shell(880, h, '\n'.join(parts))


def activity(g: dict) -> str:
    total = g["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    ds = flatten_days(g)
    active_days = sum(1 for d in ds if d["contributionCount"] > 0)
    weeks = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in g["contributionsCollection"]["contributionCalendar"]["weeks"]]
    best = max(weeks or [0])
    maxv = max(weeks or [1]) or 1
    pts = []
    for i, v in enumerate(weeks):
        x = 40 + 800 * i / max(1, len(weeks) - 1)
        y = 220 - 78 * v / maxv
        pts.append((x, y))
    poly = ' '.join(f'{x:.1f},{y:.1f}' for x, y in pts)
    body = f'''
<rect x="1" y="1" width="878" height="270" rx="18" fill="{BG}" stroke="{STROKE}"/>
<text x="34" y="64" class="title" font-size="44" font-weight="800">{total}</text>
<text x="34" y="86" class="mono subtle" font-size="10">CONTRIBUTIONS // LAST YEAR</text>
<text x="822" y="52" text-anchor="end" class="title" font-size="18" font-weight="700">{active_days}</text><text x="822" y="70" text-anchor="end" class="mono subtle" font-size="9">ACTIVE DAYS</text>
<text x="822" y="104" text-anchor="end" class="title" font-size="18" font-weight="700">{best}</text><text x="822" y="122" text-anchor="end" class="mono subtle" font-size="9">BEST WEEK</text>
<polyline points="{poly}" fill="none" stroke="{LIGHT2}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="1200" stroke-dashoffset="1200"><animate attributeName="stroke-dashoffset" from="1200" to="0" dur="1.85s" begin=".15s" fill="freeze"/></polyline>
<line x1="40" y1="235" x2="840" y2="235" stroke="{STROKE}"/>
'''
    if pts:
        x, y = pts[-1]
        body += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{TEXT}"><animate attributeName="r" values="3;5;3" dur="1.8s" repeatCount="indefinite"/></circle>'
    return shell(880, 270, body)


def about(g: dict, cfg: dict) -> str:
    lines = list(cfg.get("about", []))
    if g.get("bio") and g["bio"] not in lines:
        lines = [g["bio"]] + lines
    wrapped = []
    for line in lines[:3]:
        cur = ""
        for word in line.split():
            if len(cur) + len(word) + 1 > 92:
                wrapped.append(cur)
                cur = word
            else:
                cur = (cur + ' ' + word).strip()
        if cur:
            wrapped.append(cur)
    h = 126 + 24 * len(wrapped)
    parts = [f'<rect x="1" y="1" width="878" height="{h-2}" rx="18" fill="{BG}" stroke="{STROKE}"/>', f'<rect x="28" y="32" width="2" height="{max(56, 24*len(wrapped))}" fill="{LIGHT2}" opacity=".9"/>']
    y = 52
    for c in wrapped:
        parts.append(f'<text x="48" y="{y}" class="sans" font-size="13">{esc(c)}</text>')
        y += 24
    parts.append(f'<text x="48" y="{h-24}" class="mono subtle" font-size="9">FOCUS // PRIVACY • SECURITY • SYSTEMS</text>')
    return shell(880, h, '\n'.join(parts))


def stack(cfg: dict) -> str:
    groups = cfg.get("stack_groups") or []
    groups = groups[:5]
    rows = [78, 126, 174, 222, 270]
    x_positions = [164, 286, 410, 540, 666]
    width, height = 880, 346
    body = [f'''
<defs>
  <linearGradient id="scan" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{LIGHT}" stop-opacity="0"/><stop offset=".5" stop-color="{LIGHT}" stop-opacity=".65"/><stop offset="1" stop-color="{LIGHT}" stop-opacity="0"/></linearGradient>
</defs>
<rect x="1" y="1" width="878" height="344" rx="18" fill="{BG}" stroke="{STROKE}"/>
<text x="28" y="26" class="mono muted" font-size="10">CAPABILITY MATRIX // CURATED SAMPLE</text>
<text x="852" y="26" text-anchor="end" class="mono muted" font-size="9">KNOWN → NICHE</text>
''']
    # total tile
    total = str(cfg.get("stack_total", "200+"))
    n = re.sub(r'[^0-9]', '', total) or '200'
    plus = '+' if '+' in total else ''
    body.append(f'<rect x="706" y="56" width="146" height="232" rx="16" fill="{CARD}" stroke="{STROKE}"/>')
    body.append(f'<text x="724" y="90" class="mono subtle" font-size="8">TOTAL RANGE</text>')
    body.append(f'<text x="724" y="148" class="title" font-size="42" font-weight="800">{esc(n)}{esc(plus)}</text>')
    body.append(f'<text x="724" y="176" class="sans" font-size="12">technologies</text>')
    body.append(f'<text x="724" y="197" class="mono subtle" font-size="8">languages // frameworks</text>')
    body.append(f'<text x="724" y="212" class="mono subtle" font-size="8">systems // network // data</text>')
    body.append(f'<text x="724" y="227" class="mono subtle" font-size="8">cloud // security // low-level</text>')
    body.append(f'<circle cx="830" cy="83" r="3.5" fill="{LIGHT}"><animate attributeName="opacity" values="1;.25;1" dur="1.8s" repeatCount="indefinite"/></circle>')
    # rows
    for gi, group in enumerate(groups):
        y = rows[gi]
        label = str(group.get("label", "GROUP"))
        items = [str(i) for i in group.get("items", [])][:5]
        body.append(f'<text x="28" y="{y+4}" class="mono subtle" font-size="9">{esc(label)}</text>')
        body.append(f'<line x1="98" y1="{y}" x2="136" y2="{y}" stroke="{STROKE}"/>')
        for ii, item in enumerate(items):
            x = x_positions[ii]
            w = 108 if ii < 4 else 96
            if gi == 0:
                htile = 38
                text_size = 10.5
                weight = '700'
            else:
                htile = 30
                text_size = 8.9
                weight = '500'
            yy = y - htile/2
            delay = 0.10 + (gi*5+ii)*0.05
            body.append(f'''
<g opacity="0">
 <animate attributeName="opacity" from="0" to="1" dur=".34s" begin="{delay:.2f}s" fill="freeze"/>
 <rect x="{x}" y="{yy:.1f}" width="{w}" height="{htile}" rx="{10 if gi==0 else 8}" fill="{CARD}" stroke="{STROKE}">
  <animate attributeName="stroke" values="{STROKE};{LIGHT2};{STROKE}" dur="4.0s" begin="{1.8 + (gi+ii)*0.13:.2f}s" repeatCount="indefinite"/>
 </rect>
 <text x="{x+w/2}" y="{y+4}" text-anchor="middle" class="sans" font-size="{text_size}" font-weight="{weight}">{esc(item)}</text>
</g>
''')
    body.append(f'<line x1="28" y1="318" x2="852" y2="318" stroke="{STROKE}"/>')
    body.append(f'<text x="28" y="337" class="mono subtle" font-size="8">VISIBLE ITEMS = CURATED SHOWCASE // THE 200+ TILE REPRESENTS THE WIDER A–Z COVERAGE</text>')
    body.append(f'<rect x="-220" y="317" width="220" height="1.8" fill="url(#scan)"><animate attributeName="x" values="-220;900" dur="4.8s" repeatCount="indefinite"/></rect>')
    return shell(width, height, '\n'.join(body))


def wrap_lines(text: str, max_chars: int, max_lines: int) -> list[str]:
    words = text.split()
    lines = []
    cur = ""
    for word in words:
        if len(cur) + len(word) + 1 > max_chars:
            lines.append(cur)
            cur = word
            if len(lines) >= max_lines:
                break
        else:
            cur = (cur + ' ' + word).strip()
    if cur and len(lines) < max_lines:
        lines.append(cur)
    # ellipsis if truncated
    if len(lines) == max_lines and words:
        joined = ' '.join(lines)
        if len(joined.split()) < len(words):
            lines[-1] = lines[-1].rstrip(' .') + '…'
    return lines


def project_card(p: dict, i: int) -> str:
    name = p.get("name", "PROJECT")
    status = p.get("status", "ACTIVE")
    tech = p.get("tech", "")
    desc_lines = wrap_lines(p.get("description", ""), 84, 3)
    body = f'''
<defs>
  <linearGradient id="projScan{i}" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{LIGHT}" stop-opacity="0"/><stop offset=".5" stop-color="{LIGHT}" stop-opacity=".38"/><stop offset="1" stop-color="{LIGHT}" stop-opacity="0"/></linearGradient>
</defs>
<rect x="1" y="1" width="878" height="188" rx="18" fill="{BG}" stroke="{STROKE}"/>
<rect x="24" y="22" width="832" height="144" rx="14" fill="{CARD2}" stroke="{STROKE}"/>
<text x="40" y="46" class="mono subtle" font-size="9">PROJECT // {i:02d}</text>
<rect x="748" y="31" width="86" height="22" rx="11" fill="{CARD}" stroke="{STROKE}"/>
<text x="791" y="45" text-anchor="middle" class="mono muted" font-size="8">{esc(status)}</text>
<text x="40" y="82" class="title" font-size="24" font-weight="800">{esc(name)}</text>
<text x="40" y="107" class="mono subtle" font-size="9">{esc(tech)}</text>
'''
    y = 132
    for line in desc_lines:
        body += f'<text x="40" y="{y}" class="sans muted" font-size="11.5">{esc(line)}</text>'
        y += 18
    body += f'<rect x="-220" y="176" width="220" height="2" fill="url(#projScan{i})"><animate attributeName="x" values="-220;900" dur="{4.2+i*.25:.1f}s" repeatCount="indefinite"/></rect>'
    return shell(880, 190, body)


def stats(g: dict) -> str:
    ds = flatten_days(g)
    current, longest = streaks(ds)
    repos = g["repositories"]["totalCount"]
    stars = sum(int(r.get("stargazerCount") or 0) for r in g["repositories"]["nodes"])
    forks = sum(int(r.get("forkCount") or 0) for r in g["repositories"]["nodes"])
    tops = top_languages(g)
    total_bytes = max(1, sum(v for _, v in tops))
    boxes = [("CURRENT STREAK", current), ("LONGEST STREAK", longest), ("PUBLIC REPOS", repos), ("STARS", stars), ("FORKS", forks)]
    body = [f'<rect x="1" y="1" width="878" height="326" rx="18" fill="{BG}" stroke="{STROKE}"/>']
    x = 28
    for label, val in boxes:
        body.append(f'<rect x="{x-8}" y="24" width="146" height="58" rx="12" fill="{CARD}" stroke="{STROKE}"/>')
        body.append(f'<text x="{x}" y="52" class="title" font-size="24" font-weight="800">{val}</text>')
        body.append(f'<text x="{x}" y="72" class="mono subtle" font-size="8.5">{label}</text>')
        x += 165
    body.append(f'<line x1="28" y1="106" x2="850" y2="106" stroke="{STROKE}"/>')
    y = 146
    if not tops:
        body.append(f'<text x="28" y="150" class="mono muted" font-size="10">language data appears after the first live refresh.</text>')
    for i, (name, size) in enumerate(tops):
        pct = size / total_bytes
        bw = 520 * pct
        delay = 0.35 + i * 0.10
        body.append(f'<text x="28" y="{y}" class="sans" font-size="11">{esc(name.lower())}</text>')
        body.append(f'<rect x="180" y="{y-10}" width="520" height="8" rx="4" fill="{STROKE}"/>')
        body.append(f'<rect x="180" y="{y-10}" width="0" height="8" rx="4" fill="{LIGHT2}"><animate attributeName="width" from="0" to="{bw:.1f}" dur=".75s" begin="{delay:.2f}s" fill="freeze"/></rect>')
        body.append(f'<text x="730" y="{y}" class="mono subtle" font-size="9">{pct*100:4.1f}%</text>')
        y += 28
    return shell(880, 328, '\n'.join(body))


def year(g: dict) -> str:
    weeks = g["contributionsCollection"]["contributionCalendar"]["weeks"][-53:]
    counts = [int(d["contributionCount"]) for w in weeks for d in w["contributionDays"]]
    maxc = max(counts or [1])
    body = [f'<rect x="1" y="1" width="878" height="190" rx="18" fill="{BG}" stroke="{STROKE}"/>', f'<text x="28" y="30" class="mono muted" font-size="10">THE YEAR // CONTRIBUTION SIGNAL</text>']
    cell = 10
    gap = 3
    x0 = 94
    y0 = 64
    for label, wd in [("mon", 1), ("wed", 3), ("fri", 5)]:
        body.append(f'<text x="28" y="{y0+wd*(cell+gap)+9}" class="mono subtle" font-size="8">{label}</text>')
    for wi, w in enumerate(weeks):
        for d in w["contributionDays"]:
            wd = int(d.get("weekday", 0))
            c = int(d["contributionCount"])
            x = x0 + wi * (cell + gap)
            y = y0 + wd * (cell + gap)
            delay = (wi * 7 + wd) * 0.003
            if c <= 0:
                fill = STROKE
                op = 0.35
            else:
                fill = LIGHT2
                op = 0.25 + 0.75 * (math.log1p(c) / math.log1p(maxc))
            body.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{fill}" opacity="0"><animate attributeName="opacity" from="0" to="{op:.2f}" dur=".16s" begin="{delay:.3f}s" fill="freeze"/></rect>')
    body.append(f'<text x="850" y="174" text-anchor="end" class="mono subtle" font-size="9">QUIET  ·  LOUD</text>')
    return shell(880, 192, '\n'.join(body))


def footer(cfg: dict) -> str:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    body = f'<line x1="8" y1="14" x2="872" y2="14" stroke="{STROKE}"/><text x="8" y="48" class="title" font-size="12" font-weight="700">{esc(cfg.get("footer", "BUILT FOR SIGNAL, NOT NOISE."))}</text><text x="8" y="72" class="mono subtle" font-size="8.5">GENERATED LOCALLY // NO THIRD-PARTY BADGE SERVICE // {esc(stamp)}</text><rect x="846" y="38" width="8" height="14" fill="{LIGHT2}"><animate attributeName="opacity" values="1;0;1" dur=".9s" repeatCount="indefinite"/></rect>'
    return shell(880, 90, body)


def update_readme(projects: list[dict]) -> None:
    path = ROOT / "README.md"
    s = path.read_text(encoding="utf-8")
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
    path.write_text(s, encoding="utf-8")


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
    for i, proj in enumerate(projs, 1):
        write(PROJECTS / f"project-{i:02d}.svg", project_card(proj, i))
    update_readme(projs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
