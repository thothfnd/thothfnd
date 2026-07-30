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
PROFILE = ROOT / "data" / "profile.json"
CAPS = ROOT / "data" / "capabilities.json"

BG = "#080808"
LINE = "#2c2d30"
TEXT = "#f5f5f6"
SOFT = "#b8bbc1"
FAINT = "#858991"
CHROME = "#e3e5e8"
CHROME_DARK = "#92979f"
ASCII_RAMP = " .`'^,:;Il!i~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8")


def svg(width: int, height: int, body: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<style>
.sans{{font-family:ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;fill:{TEXT}}}
.mono{{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,"Liberation Mono",monospace;fill:{TEXT}}}
.soft{{fill:{SOFT}}}.faint{{fill:{FAINT}}}.chrome{{fill:{CHROME}}}
</style>
{body}
</svg>'''


def api(url: str, token: str = "") -> bytes:
    headers = {"User-Agent": "github-profile-v7-final", "Accept": "application/vnd.github+json"}
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
        data=json.dumps({"query": query, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"Bearer {token}", "User-Agent": "github-profile-v7-final", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=45) as response:
        result = json.loads(response.read().decode())
    if result.get("errors"):
        raise RuntimeError(result["errors"])
    return result["data"]["user"]


def demo_user(login: str) -> tuple[dict, dict]:
    today = dt.date.today()
    ds = []
    for i in range(365):
        date = today - dt.timedelta(days=364 - i)
        count = 0 if i % 5 else (i * 7) % 11
        if i % 17 == 0:
            count += 4
        ds.append({"date": date.isoformat(), "contributionCount": count, "weekday": (date.weekday()+1)%7})
    weeks = [{"contributionDays": ds[i:i+7]} for i in range(0, len(ds), 7)]
    graph = {
        "login": login, "name": login, "bio": None, "location": None, "websiteUrl": None,
        "createdAt": "2024-01-01T00:00:00Z", "followers": {"totalCount": 0}, "following": {"totalCount": 0},
        "repositories": {"totalCount": 3, "nodes": []},
        "contributionsCollection": {"contributionCalendar": {"totalContributions": sum(d["contributionCount"] for d in ds), "weeks": weeks}},
    }
    return {"avatar_url": ""}, graph


def contribution_days(graph: dict) -> list[dict]:
    return [d for week in graph["contributionsCollection"]["contributionCalendar"]["weeks"] for d in week["contributionDays"]]


def streaks(ds: list[dict]) -> tuple[int, int]:
    seq = sorted((dt.date.fromisoformat(d["date"]), int(d["contributionCount"])) for d in ds)
    longest = run = 0
    for _, count in seq:
        run = run + 1 if count > 0 else 0
        longest = max(longest, run)
    current = 0
    for index, (_, count) in enumerate(reversed(seq)):
        if index == 0 and count == 0:
            continue
        if count > 0:
            current += 1
        else:
            break
    return current, longest


def top_languages(graph: dict) -> list[tuple[str, int]]:
    totals: dict[str, int] = {}
    for repo in graph["repositories"]["nodes"]:
        for edge in (repo.get("languages") or {}).get("edges", []):
            name = edge["node"]["name"]
            totals[name] = totals.get(name, 0) + int(edge["size"])
    return sorted(totals.items(), key=lambda item: item[1], reverse=True)[:4]


def wrap(text: str, max_chars: int, max_lines: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > max_chars and current:
            lines.append(current)
            current = word
            if len(lines) >= max_lines:
                break
        else:
            current = candidate
    if current and len(lines) < max_lines:
        lines.append(current)
    if len(lines) == max_lines and len(" ".join(lines).split()) < len(words):
        lines[-1] = lines[-1].rstrip(" .") + "…"
    return lines


def fetch_avatar(url: str, token: str) -> tuple[Image.Image | None, str]:
    if not url:
        return None, "DEMO-000000000000"
    try:
        raw = api(url + ("&" if "?" in url else "?") + "s=900", token)
        digest = hashlib.sha256(raw).hexdigest().upper()
        return Image.open(io.BytesIO(raw)).convert("RGBA"), digest
    except Exception as error:
        print(f"avatar fallback: {error}", file=sys.stderr)
        return None, "ERR-000000000000"


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
    ys, xs = np.where(alpha > 16)
    if len(xs) > 10:
        pad = 18
        image = image.crop((max(0, int(xs.min())-pad), max(0, int(ys.min())-pad), min(image.width, int(xs.max())+pad), min(image.height, int(ys.max())+pad)))
    canvas = Image.new("RGB", image.size, "white")
    canvas.paste(image.convert("RGB"), mask=image.getchannel("A"))
    gray = np.array(canvas.convert("L"))
    gray = cv2.createCLAHE(clipLimit=2.8, tileGridSize=(8, 8)).apply(gray)
    gray = cv2.GaussianBlur(gray, (0, 0), 0.55)
    gray = np.clip(np.power(gray.astype(np.float32)/255.0, 1.42)*255, 0, 255).astype(np.uint8)
    ratio = gray.shape[0] / max(1, gray.shape[1])
    rows = max(16, min(76, int(cols * ratio * 0.49)))
    small = cv2.resize(gray, (cols, rows), interpolation=cv2.INTER_AREA)
    return ["".join(ASCII_RAMP[int((255-int(pixel))/255*(len(ASCII_RAMP)-1))] for pixel in row).rstrip() for row in small]


# Bespoke vector wordmark: geometric strokes, no font dependency.
def wordmark(text: str, x: int, y: int, letter_w: int = 72, letter_h: int = 68, gap: int = 16) -> tuple[str, int]:
    pieces: list[str] = []
    cursor = x
    sw = 7
    for char in text:
        x0, x1 = cursor, cursor + letter_w
        y0, y1, ym = y, y + letter_h, y + letter_h / 2
        common = f'stroke="url(#wordChrome)" stroke-width="{sw}" stroke-linecap="square" stroke-linejoin="miter" fill="none"'
        if char == "T":
            pieces.append(f'<path d="M{x0},{y0} H{x1} M{(x0+x1)/2},{y0} V{y1}" {common}/>')
        elif char == "H":
            pieces.append(f'<path d="M{x0},{y0} V{y1} M{x1},{y0} V{y1} M{x0},{ym} H{x1}" {common}/>')
        elif char == "O":
            pieces.append(f'<rect x="{x0}" y="{y0}" width="{letter_w}" height="{letter_h}" rx="8" {common}/>')
        elif char == "F":
            pieces.append(f'<path d="M{x0},{y1} V{y0} H{x1} M{x0},{ym} H{x1-10}" {common}/>')
        elif char == "N":
            pieces.append(f'<path d="M{x0},{y1} V{y0} L{x1},{y1} V{y0}" {common}/>')
        elif char == "D":
            pieces.append(f'<path d="M{x0},{y0} V{y1} H{x0+20} C{x1},{y1} {x1},{y0} {x0+20},{y0} Z" {common}/>')
        cursor += letter_w + gap
    return "\n".join(pieces), cursor - x - gap

def hero(login: str, graph: dict, profile: dict) -> str:
    focus = profile.get("focus", [])[:4]
    mark, mark_width = wordmark("THOTHFND", 36, 72, letter_w=72, letter_h=68, gap=16)
    body = [f'''
<defs>
 <linearGradient id="wordChrome" gradientUnits="userSpaceOnUse" x1="36" y1="0" x2="{36+mark_width}" y2="0">
  <stop offset="0" stop-color="#868b92"/><stop offset=".18" stop-color="#f5f6f7"/><stop offset=".42" stop-color="#a2a7ae"/><stop offset=".67" stop-color="#ffffff"/><stop offset="1" stop-color="#858a91"/>
 </linearGradient>
 <linearGradient id="heroScan" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{CHROME}" stop-opacity="0"/><stop offset=".5" stop-color="{CHROME}" stop-opacity=".7"/><stop offset="1" stop-color="{CHROME}" stop-opacity="0"/></linearGradient>
</defs>
<rect width="880" height="322" fill="{BG}"/>
<line x1="36" y1="34" x2="844" y2="34" stroke="{LINE}"/>
<text x="36" y="23" class="mono faint" font-size="12">THOTHFND / SYSTEMS PROFILE</text>
<text x="844" y="23" text-anchor="end" class="mono faint" font-size="12">PUBLIC INTERFACE</text>
{mark}
<text x="38" y="177" class="mono soft" font-size="14">@{esc(login)}</text>
<text x="38" y="213" class="sans soft" font-size="18">{esc(profile.get('tagline',''))}</text>
<line x1="36" y1="238" x2="844" y2="238" stroke="{LINE}"/>
''']
    cols = [36, 240, 444, 648]
    for idx, item in enumerate(focus):
        x = cols[idx]
        body.append(f'<text x="{x}" y="267" class="mono faint" font-size="11">{esc(item.get("label",""))}</text>')
        body.append(f'<text x="{x}" y="294" class="sans" font-size="15" font-weight="650">{esc(item.get("value",""))}</text>')
    body.append(f'<rect x="-220" y="311" width="220" height="1.5" fill="url(#heroScan)"><animate attributeName="x" values="-220;920" dur="6s" repeatCount="indefinite"/></rect>')
    return svg(880, 322, "\n".join(body))


def identity(image: Image.Image | None, login: str, digest: str) -> str:
    fallback = [
        "                    .,:iillllii,.",
        "               .:iIttfffjjjrrxxnnuuI;.",
        "            .;tXXUUUUUUUUUUUUUUUUXXf,",
        "          :fXUUUUUUUUUUUUUUUUUUUUUUXr",
        "        .nXUUUUU.    PROFILE    .UUXj",
        "        ;XUUUUUU      READY      UUXt",
        "        .nXUUUUU.     SYNC      .UUXj",
        "          :fXUUUUUUUUUUUUUUUUUUUUUUXr",
        "            .;tXXUUUUUUUUUUUUUUUUXXf,",
        "               .:iIttfffjjjrrxxnnuuI;.",
        "                    .,:iillllii,.",
    ]
    if image is None:
        coarse = fallback
        dense = fallback
        final = fallback
    else:
        coarse = ascii_portrait(image, 44)
        dense = ascii_portrait(image, 70)
        final = ascii_portrait(image, 100)

    line_h = 8.6
    top = 126
    height = int(top + len(final) * line_h + 48)
    body: list[str] = [f'''
<defs>
 <linearGradient id="idScan" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{CHROME}" stop-opacity="0"/><stop offset=".5" stop-color="{CHROME}" stop-opacity=".8"/><stop offset="1" stop-color="{CHROME}" stop-opacity="0"/></linearGradient>
</defs>
<rect width="880" height="{height}" fill="{BG}"/>
<line x1="36" y1="34" x2="844" y2="34" stroke="{LINE}"/>
<text x="36" y="23" class="mono faint" font-size="12">IDENTITY / AVATAR → ASCII</text>
<text x="844" y="23" text-anchor="end" class="mono faint" font-size="12">SHA256 {esc(digest[:12])}</text>
<text x="36" y="68" class="mono soft" font-size="12">RAW</text><line x1="78" y1="64" x2="174" y2="64" stroke="{LINE}"/>
<text x="194" y="68" class="mono soft" font-size="12">COARSE</text><line x1="258" y1="64" x2="354" y2="64" stroke="{LINE}"/>
<text x="374" y="68" class="mono soft" font-size="12">DENSE</text><line x1="430" y1="64" x2="526" y2="64" stroke="{LINE}"/>
<text x="546" y="68" class="mono soft" font-size="12">FINAL</text>
<line x1="36" y1="84" x2="650" y2="84" stroke="{LINE}"/>
''']

    def phase(lines: list[str], font_size: float, begin: float, dur: float) -> str:
        local: list[str] = [f'<g opacity="0"><animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.12;.72;1" dur="{dur}s" begin="{begin}s" fill="freeze"/>']
        phase_top = top + max(0, len(final)-len(lines))*line_h/2
        for i, line in enumerate(lines):
            y = phase_top + i * line_h
            local.append(f'<text x="440" y="{y:.1f}" text-anchor="middle" class="mono" style="font-size:{font_size}px;fill:{TEXT};opacity:.92" xml:space="preserve">{esc(line)}</text>')
        local.append('</g>')
        return "\n".join(local)

    body.append(phase(coarse, 11.2, 0.15, 0.95))
    body.append(phase(dense, 8.9, 0.85, 0.95))
    for index, line in enumerate(final):
        y = top + index * line_h
        delay = 1.45 + index * 0.024
        body.append(f'<clipPath id="f{index}"><rect x="42" y="{y-7:.1f}" width="0" height="10"><animate attributeName="width" from="0" to="796" dur=".32s" begin="{delay:.3f}s" fill="freeze"/></rect></clipPath>')
        body.append(f'<text x="440" y="{y:.1f}" text-anchor="middle" clip-path="url(#f{index})" class="mono" style="font-size:7.25px;fill:{TEXT};opacity:.95" xml:space="preserve">{esc(line)}</text>')
    body.append(f'<text x="36" y="{height-19}" class="mono faint" font-size="11">GRID {len(final[0]) if final and final[0] else 100}×{len(final)} / MONOCHROME / SOURCE github/avatar</text>')
    body.append(f'<rect x="-220" y="{height-8}" width="220" height="1.4" fill="url(#idScan)"><animate attributeName="x" values="-220;920" dur="5.4s" begin="1.5s" repeatCount="indefinite"/></rect>')
    return svg(880, height, "\n".join(body))


def capability_count(catalog: dict) -> int:
    return len({item for values in catalog.values() for item in values})


def stack(caps: dict) -> str:
    catalog = caps.get("catalog", {})
    featured = [
        ("LANGUAGES", ["Python","C++","Rust","TypeScript","Go"]),
        ("BROWSER SYSTEMS", ["Gecko","XPCOM","Fission","Necko","WebExtensions"]),
        ("SECURITY", ["Threat Modeling","Cryptography","WebAuthn","PKI","Zero Trust"]),
        ("SYSTEMS", ["Linux","Windows","x86-64","ARM64","LLVM IR"]),
        ("INFRASTRUCTURE", ["Docker","Kubernetes","Terraform","PostgreSQL","GitHub Actions"]),
    ]
    count = capability_count(catalog)
    row_y = [102, 148, 194, 240, 286]
    body = [f'''
<defs><linearGradient id="capChrome" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#8f949b"/><stop offset=".48" stop-color="#fafafa"/><stop offset="1" stop-color="#8b9097"/></linearGradient></defs>
<rect width="880" height="338" fill="{BG}"/>
<line x1="36" y1="34" x2="844" y2="34" stroke="{LINE}"/>
<text x="36" y="23" class="mono faint" font-size="12">CAPABILITY INDEX / CURATED VIEW</text>
<text x="844" y="88" text-anchor="end" class="sans" font-size="58" font-weight="800" fill="url(#capChrome)">{count}</text>
<text x="844" y="111" text-anchor="end" class="mono faint" font-size="11">INDEXED CAPABILITIES</text>
''']
    for index, (label, items) in enumerate(featured):
        y = row_y[index]
        body.append(f'<text x="36" y="{y}" class="mono faint" font-size="11">{esc(label)}</text>')
        body.append(f'<line x1="156" y1="{y-4}" x2="190" y2="{y-4}" stroke="{LINE}"/>')
        body.append(f'<text x="212" y="{y}" class="sans" font-size="15" font-weight="600">{esc("   /   ".join(items))}</text>')
        body.append(f'<line x1="36" y1="{y+17}" x2="700" y2="{y+17}" stroke="{LINE}"/>')
    body.append(f'<text x="844" y="304" text-anchor="end" class="mono faint" font-size="11">COUNTED FROM data/capabilities.json</text>')
    return svg(880, 338, "\n".join(body))


def works(profile: dict) -> str:
    works_data = profile.get("works", [])[:3]
    height = 120 + 150 * len(works_data)
    body: list[str] = [f'''
<rect width="880" height="{height}" fill="{BG}"/>
<line x1="36" y1="34" x2="844" y2="34" stroke="{LINE}"/>
<text x="36" y="23" class="mono faint" font-size="12">SELECTED WORK / PRACTICE</text>
''']
    base = 76
    for idx, work in enumerate(works_data):
        y = base + idx * 150
        desc = wrap(work.get("description", ""), 54, 2)
        body.append(f'<text x="36" y="{y+34}" class="sans" font-size="44" font-weight="800" fill="{CHROME_DARK}">{esc(work.get("index", f"0{idx+1}"))}</text>')
        body.append(f'<line x1="105" y1="{y}" x2="105" y2="{y+112}" stroke="{LINE}"/>')
        body.append(f'<text x="132" y="{y+19}" class="mono faint" font-size="11">{esc(work.get("status",""))}</text>')
        body.append(f'<text x="132" y="{y+59}" class="sans" font-size="27" font-weight="800">{esc(work.get("name",""))}</text>')
        body.append(f'<text x="132" y="{y+84}" class="mono soft" font-size="11">{esc(work.get("discipline",""))}</text>')
        for line_index, line in enumerate(desc):
            body.append(f'<text x="468" y="{y+51+line_index*22}" class="sans soft" font-size="13">{esc(line)}</text>')
        url = work.get("url", "").strip()
        if url:
            body.append(f'<text x="844" y="{y+107}" text-anchor="end" class="mono soft" font-size="11">VIEW SOURCE ↗</text>')
        body.append(f'<line x1="36" y1="{y+126}" x2="844" y2="{y+126}" stroke="{LINE}"/>')
    return svg(880, height, "\n".join(body))


def signal(graph: dict) -> str:
    ds = contribution_days(graph)
    current, longest = streaks(ds)
    total = graph["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    active = sum(1 for d in ds if int(d["contributionCount"]) > 0)
    weeks = graph["contributionsCollection"]["contributionCalendar"]["weeks"][-53:]
    week_values = [sum(int(d["contributionCount"]) for d in w["contributionDays"]) for w in weeks]
    max_week = max(week_values or [1]) or 1
    points = []
    for index, value in enumerate(week_values):
        x = 330 + 500 * index / max(1, len(week_values)-1)
        y = 168 - 80 * value / max_week
        points.append((x, y))
    polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    languages = top_languages(graph)
    language_text = " / ".join(name for name, _ in languages[:3]) or "NO PUBLIC LANGUAGE SIGNAL YET"

    body: list[str] = [f'''
<rect width="880" height="356" fill="{BG}"/>
<line x1="36" y1="34" x2="844" y2="34" stroke="{LINE}"/>
<text x="36" y="23" class="mono faint" font-size="12">SIGNAL / GITHUB ACTIVITY</text>
<text x="36" y="111" class="sans" font-size="64" font-weight="800">{total}</text>
<text x="40" y="137" class="mono faint" font-size="11">CONTRIBUTIONS / LAST YEAR</text>
<text x="40" y="183" class="sans" font-size="25" font-weight="750">{active}</text><text x="40" y="204" class="mono faint" font-size="11">ACTIVE DAYS</text>
<text x="150" y="183" class="sans" font-size="25" font-weight="750">{current}</text><text x="150" y="204" class="mono faint" font-size="11">CURRENT STREAK</text>
<text x="262" y="183" class="sans" font-size="25" font-weight="750">{longest}</text><text x="262" y="204" class="mono faint" font-size="11">LONGEST</text>
<polyline points="{polyline}" fill="none" stroke="{CHROME}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="1000" stroke-dashoffset="1000"><animate attributeName="stroke-dashoffset" from="1000" to="0" dur="1.7s" begin=".1s" fill="freeze"/></polyline>
<line x1="330" y1="194" x2="830" y2="194" stroke="{LINE}"/>
<text x="330" y="219" class="mono faint" font-size="11">PUBLIC LANGUAGE SIGNAL</text>
<text x="330" y="244" class="sans soft" font-size="13">{esc(language_text)}</text>
<line x1="36" y1="266" x2="844" y2="266" stroke="{LINE}"/>
''']
    counts = [int(d["contributionCount"]) for w in weeks for d in w["contributionDays"]]
    maximum = max(counts or [1])
    cell, gap, x0, y0 = 10, 3, 110, 284
    for label, weekday in [("M",1),("W",3),("F",5)]:
        body.append(f'<text x="58" y="{y0+weekday*(cell+gap)+9}" class="mono faint" font-size="10">{label}</text>')
    for week_index, week in enumerate(weeks):
        for day in week["contributionDays"]:
            weekday = int(day.get("weekday",0)); count = int(day["contributionCount"])
            x = x0 + week_index*(cell+gap); y = y0 + weekday*(cell+gap)
            opacity = .20 if count <= 0 else .28 + .72*(math.log1p(count)/math.log1p(maximum))
            fill = LINE if count <= 0 else CHROME
            delay = (week_index*7+weekday)*.0025
            body.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{fill}" opacity="0"><animate attributeName="opacity" from="0" to="{opacity:.2f}" dur=".13s" begin="{delay:.3f}s" fill="freeze"/></rect>')
    return svg(880, 356, "\n".join(body))


def footer(profile: dict, caps: dict) -> str:
    count = capability_count(caps.get("catalog", {}))
    body = f'''
<rect width="880" height="92" fill="{BG}"/>
<line x1="36" y1="20" x2="844" y2="20" stroke="{LINE}"/>
<text x="36" y="54" class="sans" font-size="14" font-weight="700">{esc(profile.get('footer',''))}</text>
<text x="36" y="76" class="mono faint" font-size="11">LOCAL SVG GENERATION / {count} INDEXED CAPABILITIES / NO THIRD-PARTY BADGE SERVICE</text>
<rect x="832" y="41" width="8" height="14" fill="{CHROME}"><animate attributeName="opacity" values="1;0;1" dur="1s" repeatCount="indefinite"/></rect>
'''
    return svg(880, 92, body)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--login", default=os.environ.get("GH_LOGIN", "profile"))
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN", ""))
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()

    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    caps = json.loads(CAPS.read_text(encoding="utf-8"))
    try:
        if args.demo or not args.token:
            rest, graph = demo_user(args.login)
        else:
            rest, graph = rest_user(args.login, args.token), graph_user(args.login, args.token)
    except Exception as error:
        print(f"live data fallback: {error}", file=sys.stderr)
        rest, graph = demo_user(args.login)

    image, digest = (None, "DEMO-000000000000") if args.demo else fetch_avatar(rest.get("avatar_url", ""), args.token)
    write(ASSETS / "hero.svg", hero(args.login, graph, profile))
    write(ASSETS / "identity.svg", identity(image, args.login, digest))
    write(ASSETS / "capabilities.svg", stack(caps))
    write(ASSETS / "works.svg", works(profile))
    write(ASSETS / "signal.svg", signal(graph))
    write(ASSETS / "footer.svg", footer(profile, caps))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
