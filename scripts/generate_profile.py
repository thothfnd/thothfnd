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
CONFIG = ROOT / "profile.json"

# Monochrome chrome palette. No accent blue, no neon.
BG = "#090909"
BG2 = "#0e0e0f"
LINE = "#303034"
TEXT = "#f4f4f5"
SOFT = "#b7bac0"
FAINT = "#7f838b"
CHROME = "#dfe2e6"
CHROME_DARK = "#8e949c"
ASCII_RAMP = " .`'^,:;Il!i~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8")


def svg(width: int, height: int, body: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<style>
.display{{font-family:"Arial Black","Helvetica Neue",Arial,sans-serif;fill:{TEXT}}}
.sans{{font-family:"Helvetica Neue",Arial,system-ui,sans-serif;fill:{TEXT}}}
.serif{{font-family:Georgia,"Times New Roman",serif;fill:{SOFT}}}
.mono{{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,"Liberation Mono",monospace;fill:{TEXT}}}
.soft{{fill:{SOFT}}}.faint{{fill:{FAINT}}}.chrome{{fill:{CHROME}}}
</style>
{body}
</svg>'''


def api(url: str, token: str = "") -> bytes:
    headers = {"User-Agent": "github-profile-v6-bespoke", "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
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
   totalCount
   nodes{name url stargazerCount forkCount languages(first:8,orderBy:{field:SIZE,direction:DESC}){edges{size node{name color}}}}
  }
  contributionsCollection{contributionCalendar{totalContributions weeks{contributionDays{contributionCount date weekday}}}}
 }
}'''
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": {"login": login}}).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "github-profile-v6-bespoke",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=45) as response:
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
        ds.append({"date": date.isoformat(), "contributionCount": count, "weekday": (date.weekday() + 1) % 7})
    weeks = [{"contributionDays": ds[i:i+7]} for i in range(0, len(ds), 7)]
    graph = {
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
    return sorted(totals.items(), key=lambda item: item[1], reverse=True)[:6]


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


def fetch_avatar(url: str, token: str) -> Image.Image | None:
    if not url:
        return None
    try:
        raw = api(url + ("&" if "?" in url else "?") + "s=900", token)
        return Image.open(io.BytesIO(raw)).convert("RGBA")
    except Exception as error:
        print(f"avatar fallback: {error}", file=sys.stderr)
        return None


def ascii_portrait(image: Image.Image) -> list[str]:
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
        image = image.crop((
            max(0, int(xs.min()) - pad), max(0, int(ys.min()) - pad),
            min(image.width, int(xs.max()) + pad), min(image.height, int(ys.max()) + pad),
        ))

    canvas = Image.new("RGB", image.size, "white")
    canvas.paste(image.convert("RGB"), mask=image.getchannel("A"))
    gray = np.array(canvas.convert("L"))
    gray = cv2.createCLAHE(clipLimit=2.8, tileGridSize=(8, 8)).apply(gray)
    gray = cv2.GaussianBlur(gray, (0, 0), 0.55)
    gray = np.clip(np.power(gray.astype(np.float32) / 255.0, 1.42) * 255, 0, 255).astype(np.uint8)

    cols = 100
    ratio = gray.shape[0] / max(1, gray.shape[1])
    rows = max(30, min(76, int(cols * ratio * 0.49)))
    small = cv2.resize(gray, (cols, rows), interpolation=cv2.INTER_AREA)
    return ["".join(ASCII_RAMP[int((255 - int(pixel)) / 255 * (len(ASCII_RAMP) - 1))] for pixel in row).rstrip() for row in small]


def hero(login: str, graph: dict, cfg: dict) -> str:
    name = (graph.get("name") or login).upper()
    tagline = cfg.get("tagline") or graph.get("bio") or "privacy engineering"
    joined = (graph.get("createdAt") or "")[:4] or "--"
    location = (graph.get("location") or "NETWORK / PRIVATE")[:28].upper()
    body = f'''
<defs>
 <linearGradient id="chromeText" x1="0" y1="0" x2="1" y2="0">
  <stop offset="0" stop-color="#8c9198"/><stop offset=".28" stop-color="#f3f4f5"/><stop offset=".53" stop-color="#a0a5ac"/><stop offset=".78" stop-color="#ffffff"/><stop offset="1" stop-color="#858a91"/>
 </linearGradient>
 <linearGradient id="scan" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{CHROME}" stop-opacity="0"/><stop offset=".48" stop-color="{CHROME}" stop-opacity=".8"/><stop offset="1" stop-color="{CHROME}" stop-opacity="0"/></linearGradient>
 <clipPath id="tag"><rect x="36" y="0" width="0" height="240"><animate attributeName="width" from="0" to="810" dur="1.25s" begin=".25s" fill="freeze"/></rect></clipPath>
</defs>
<rect width="880" height="318" fill="{BG}"/>
<line x1="36" y1="34" x2="844" y2="34" stroke="{LINE}"/>
<text x="36" y="24" class="mono faint" font-size="9">THOTHFND / PROFILE INDEX</text>
<text x="844" y="24" text-anchor="end" class="mono faint" font-size="9">LIVE DATA / GENERATED</text>
<text x="34" y="128" class="display" font-size="72" font-weight="900" fill="url(#chromeText)">{esc(name)}</text>
<text x="38" y="159" class="mono soft" font-size="12">@{esc(login)}</text>
<g clip-path="url(#tag)"><text x="38" y="205" class="serif" font-size="21" font-style="italic">{esc(tagline)}</text></g>
<line x1="36" y1="232" x2="844" y2="232" stroke="{LINE}"/>
<text x="36" y="262" class="mono faint" font-size="8">REPOS</text><text x="36" y="290" class="display" font-size="25" font-weight="800">{graph['repositories']['totalCount']}</text>
<text x="170" y="262" class="mono faint" font-size="8">FOLLOWERS</text><text x="170" y="290" class="display" font-size="25" font-weight="800">{graph['followers']['totalCount']}</text>
<text x="326" y="262" class="mono faint" font-size="8">FOLLOWING</text><text x="326" y="290" class="display" font-size="25" font-weight="800">{graph['following']['totalCount']}</text>
<text x="482" y="262" class="mono faint" font-size="8">JOINED</text><text x="482" y="290" class="display" font-size="25" font-weight="800">{esc(joined)}</text>
<text x="638" y="262" class="mono faint" font-size="8">LOCATION</text><text x="638" y="290" class="sans" font-size="12">{esc(location)}</text>
<rect x="-240" y="307" width="240" height="1.5" fill="url(#scan)"><animate attributeName="x" values="-240;920" dur="5.6s" repeatCount="indefinite"/></rect>
'''
    return svg(880, 318, body)


def identity(image: Image.Image | None, login: str) -> str:
    lines = ascii_portrait(image) if image is not None else [
        "                           .,:iillllii,:.",
        "                      .:iIttfffjjjrrxxnnuuI;.",
        "                  .;tXXUUUUUUUUUUUUUUUUUUXXf,",
        "                :fXUUUUUUUUUUUUUUUUUUUUUUUUXr",
        "              .nXUUUUU.      PROFILE      .UUXj",
        "              ;XUUUUUU       AVATAR        UUXt",
        "              ;XUUUUUU        READY        UUXt",
        "              .nXUUUUU.       SYNC        .UUXj",
        "                :fXUUUUUUUUUUUUUUUUUUUUUUUUXr",
        "                  .;tXXUUUUUUUUUUUUUUUUUUXXf,",
        "                      .:iIttfffjjjrrxxnnuuI;.",
        "                           .,:iillllii,:.",
    ]
    line_h = 8.6
    top = 94
    height = int(top + len(lines) * line_h + 48)
    pieces = [f'''
<defs><linearGradient id="idscan" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{CHROME}" stop-opacity="0"/><stop offset=".5" stop-color="{CHROME}" stop-opacity=".78"/><stop offset="1" stop-color="{CHROME}" stop-opacity="0"/></linearGradient></defs>
<rect width="880" height="{height}" fill="{BG}"/>
<line x1="36" y1="30" x2="844" y2="30" stroke="{LINE}"/>
<text x="36" y="21" class="mono faint" font-size="9">IDENTITY / ASCII RENDER</text>
<text x="844" y="21" text-anchor="end" class="mono faint" font-size="9">@{esc(login)}</text>
<text x="36" y="61" class="mono soft" font-size="10">01 FETCH</text><line x1="104" y1="57" x2="182" y2="57" stroke="{LINE}"/>
<text x="202" y="61" class="mono soft" font-size="10">02 MASK</text><line x1="266" y1="57" x2="344" y2="57" stroke="{LINE}"/>
<text x="364" y="61" class="mono soft" font-size="10">03 MAP</text><line x1="424" y1="57" x2="502" y2="57" stroke="{LINE}"/>
<text x="522" y="61" class="mono soft" font-size="10">04 REVEAL</text>
<rect x="36" y="70" width="0" height="1.4" fill="{CHROME}"><animate attributeName="width" from="0" to="626" dur="1.45s" begin=".08s" fill="freeze"/></rect>
''']
    for index, line in enumerate(lines):
        y = top + index * line_h
        delay = 0.65 + index * 0.026
        pieces.append(f'<clipPath id="c{index}"><rect x="44" y="{y-7:.1f}" width="0" height="10"><animate attributeName="width" from="0" to="792" dur=".34s" begin="{delay:.3f}s" fill="freeze"/></rect></clipPath>')
        pieces.append(f'<text x="440" y="{y:.1f}" text-anchor="middle" clip-path="url(#c{index})" class="mono" style="font-size:7.35px;fill:{TEXT};opacity:.94" xml:space="preserve">{esc(line)}</text>')
    pieces.append(f'<rect x="44" y="{height-18}" width="8" height="11" fill="{CHROME}"><animate attributeName="opacity" values="1;0;1" dur="1s" repeatCount="indefinite"/></rect>')
    pieces.append(f'<rect x="-220" y="{height-28}" width="220" height="1.4" fill="url(#idscan)"><animate attributeName="x" values="-220;920" dur="5.2s" begin="1.1s" repeatCount="indefinite"/></rect>')
    return svg(880, height, "\n".join(pieces))


def stack(cfg: dict) -> str:
    groups = (cfg.get("stack_groups") or [])[:5]
    total = str(cfg.get("stack_total", "200+"))
    number = re.sub(r"[^0-9]", "", total) or "200"
    suffix = "+" if "+" in total else ""
    row_y = [92, 136, 180, 224, 268]
    body = [f'''
<defs><linearGradient id="stackchrome" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#8e949b"/><stop offset=".48" stop-color="#f7f7f8"/><stop offset="1" stop-color="#8b9097"/></linearGradient></defs>
<rect width="880" height="324" fill="{BG}"/>
<line x1="36" y1="30" x2="844" y2="30" stroke="{LINE}"/>
<text x="36" y="21" class="mono faint" font-size="9">STACK / CAPABILITY INDEX</text>
<text x="820" y="93" text-anchor="end" class="display" font-size="58" font-weight="900" fill="url(#stackchrome)">{esc(number)}{esc(suffix)}</text>
<text x="820" y="113" text-anchor="end" class="mono faint" font-size="8">TECHNOLOGIES / A–Z COVERAGE</text>
''']
    for index, group in enumerate(groups):
        y = row_y[index]
        label = str(group.get("label", "GROUP"))
        items = [str(item) for item in group.get("items", [])][:5]
        text = "   /   ".join(items)
        font = 19 if index == 0 else 13
        weight = 800 if index == 0 else 600
        body.append(f'<text x="36" y="{y}" class="mono faint" font-size="8">{esc(label)}</text>')
        body.append(f'<line x1="104" y1="{y-4}" x2="138" y2="{y-4}" stroke="{LINE}"/>')
        body.append(f'<text x="158" y="{y}" class="sans" font-size="{font}" font-weight="{weight}">{esc(text)}</text>')
        body.append(f'<line x1="36" y1="{y+17}" x2="690" y2="{y+17}" stroke="{LINE}" stroke-dasharray="654" stroke-dashoffset="654"><animate attributeName="stroke-dashoffset" from="654" to="0" dur=".75s" begin="{0.12+index*0.12:.2f}s" fill="freeze"/></line>')
    body.append(f'<text x="820" y="278" text-anchor="end" class="serif" font-size="15" font-style="italic">curated, not exhaustive.</text>')
    return svg(880, 324, "\n".join(body))


def works(cfg: dict) -> str:
    projects = cfg.get("projects", [])[:3]
    height = 122 + 138 * len(projects)
    body = [f'''
<rect width="880" height="{height}" fill="{BG}"/>
<line x1="36" y1="30" x2="844" y2="30" stroke="{LINE}"/>
<text x="36" y="21" class="mono faint" font-size="9">SELECTED WORKS / CURRENT</text>
<text x="844" y="21" text-anchor="end" class="serif" font-size="12" font-style="italic">systems under construction</text>
''']
    base = 76
    for index, project in enumerate(projects, 1):
        y = base + (index - 1) * 138
        desc = wrap(project.get("description", ""), 50, 2)
        body.append(f'<text x="36" y="{y+30}" class="display" font-size="42" font-weight="900" fill="{CHROME_DARK}">0{index}</text>')
        body.append(f'<line x1="96" y1="{y}" x2="96" y2="{y+98}" stroke="{LINE}"/>')
        body.append(f'<text x="122" y="{y+18}" class="mono faint" font-size="9">{esc(project.get("status", "ACTIVE"))}</text>')
        body.append(f'<text x="122" y="{y+52}" class="display" font-size="25" font-weight="900">{esc(project.get("name", "PROJECT"))}</text>')
        body.append(f'<text x="122" y="{y+76}" class="mono soft" font-size="9">{esc(project.get("tech", ""))}</text>')
        for line_index, line in enumerate(desc):
            body.append(f'<text x="450" y="{y+44+line_index*20}" class="sans soft" font-size="11.5">{esc(line)}</text>')
        body.append(f'<line x1="36" y1="{y+116}" x2="844" y2="{y+116}" stroke="{LINE}"/>')
    return svg(880, height, "\n".join(body))


def signal(graph: dict) -> str:
    ds = contribution_days(graph)
    current, longest = streaks(ds)
    total = graph["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    active = sum(1 for d in ds if int(d["contributionCount"]) > 0)
    stars = sum(int(repo.get("stargazerCount") or 0) for repo in graph["repositories"]["nodes"])
    weeks = [sum(int(d["contributionCount"]) for d in week["contributionDays"]) for week in graph["contributionsCollection"]["contributionCalendar"]["weeks"]]
    max_week = max(weeks or [1]) or 1
    points = []
    for index, value in enumerate(weeks):
        x = 300 + 530 * index / max(1, len(weeks) - 1)
        y = 184 - 94 * value / max_week
        points.append((x, y))
    polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    languages = top_languages(graph)
    dominant = languages[0][0] if languages else "—"
    body = f'''
<rect width="880" height="274" fill="{BG}"/>
<line x1="36" y1="30" x2="844" y2="30" stroke="{LINE}"/>
<text x="36" y="21" class="mono faint" font-size="9">SIGNAL / GITHUB ACTIVITY</text>
<text x="36" y="104" class="display" font-size="64" font-weight="900">{total}</text>
<text x="40" y="126" class="mono faint" font-size="8">CONTRIBUTIONS / LAST YEAR</text>
<text x="40" y="166" class="display" font-size="23" font-weight="800">{active}</text><text x="40" y="183" class="mono faint" font-size="8">ACTIVE DAYS</text>
<text x="128" y="166" class="display" font-size="23" font-weight="800">{current}</text><text x="128" y="183" class="mono faint" font-size="8">CURRENT STREAK</text>
<text x="224" y="166" class="display" font-size="23" font-weight="800">{longest}</text><text x="224" y="183" class="mono faint" font-size="8">LONGEST</text>
<polyline points="{polyline}" fill="none" stroke="{CHROME}" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="1000" stroke-dashoffset="1000"><animate attributeName="stroke-dashoffset" from="1000" to="0" dur="1.8s" begin=".1s" fill="freeze"/></polyline>
<line x1="300" y1="204" x2="830" y2="204" stroke="{LINE}"/>
<text x="300" y="233" class="mono faint" font-size="8">REPOS</text><text x="300" y="256" class="display" font-size="20" font-weight="800">{graph['repositories']['totalCount']}</text>
<text x="414" y="233" class="mono faint" font-size="8">STARS</text><text x="414" y="256" class="display" font-size="20" font-weight="800">{stars}</text>
<text x="526" y="233" class="mono faint" font-size="8">DOMINANT</text><text x="526" y="256" class="sans" font-size="12">{esc(dominant)}</text>
'''
    if points:
        x, y = points[-1]
        body += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{TEXT}"><animate attributeName="r" values="3;4.8;3" dur="1.9s" repeatCount="indefinite"/></circle>'
    return svg(880, 274, body)


def year(graph: dict) -> str:
    weeks = graph["contributionsCollection"]["contributionCalendar"]["weeks"][-53:]
    counts = [int(d["contributionCount"]) for week in weeks for d in week["contributionDays"]]
    maximum = max(counts or [1])
    body = [f'''
<rect width="880" height="184" fill="{BG}"/>
<line x1="36" y1="30" x2="844" y2="30" stroke="{LINE}"/>
<text x="36" y="21" class="mono faint" font-size="9">THE YEAR / CONTRIBUTION FIELD</text>
''']
    cell, gap, x0, y0 = 10, 3, 96, 55
    for label, weekday in [("MON", 1), ("WED", 3), ("FRI", 5)]:
        body.append(f'<text x="36" y="{y0+weekday*(cell+gap)+9}" class="mono faint" font-size="8">{label}</text>')
    for week_index, week in enumerate(weeks):
        for day in week["contributionDays"]:
            weekday = int(day.get("weekday", 0))
            count = int(day["contributionCount"])
            x = x0 + week_index * (cell + gap)
            y = y0 + weekday * (cell + gap)
            opacity = .24 if count <= 0 else .28 + .72 * (math.log1p(count) / math.log1p(maximum))
            fill = LINE if count <= 0 else CHROME
            delay = (week_index * 7 + weekday) * .003
            body.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{fill}" opacity="0"><animate attributeName="opacity" from="0" to="{opacity:.2f}" dur=".14s" begin="{delay:.3f}s" fill="freeze"/></rect>')
    body.append(f'<text x="844" y="166" text-anchor="end" class="serif" font-size="11" font-style="italic">quiet / loud</text>')
    return svg(880, 184, "\n".join(body))


def footer(cfg: dict) -> str:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    body = f'''
<rect width="880" height="84" fill="{BG}"/>
<line x1="36" y1="18" x2="844" y2="18" stroke="{LINE}"/>
<text x="36" y="51" class="display" font-size="12" font-weight="800">{esc(cfg.get('footer', 'BUILT FOR SIGNAL, NOT NOISE.'))}</text>
<text x="36" y="70" class="mono faint" font-size="8">LOCAL GENERATION / NO THIRD-PARTY BADGE SERVICE / {esc(stamp)}</text>
<rect x="832" y="38" width="8" height="13" fill="{CHROME}"><animate attributeName="opacity" values="1;0;1" dur="1s" repeatCount="indefinite"/></rect>
'''
    return svg(880, 84, body)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--login", default=os.environ.get("GH_LOGIN", "profile"))
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN", ""))
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()

    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    try:
        if args.demo or not args.token:
            rest, graph = demo_user(args.login)
        else:
            rest, graph = rest_user(args.login, args.token), graph_user(args.login, args.token)
    except Exception as error:
        print(f"live data fallback: {error}", file=sys.stderr)
        rest, graph = demo_user(args.login)

    image = None if args.demo else fetch_avatar(rest.get("avatar_url", ""), args.token)
    write(ASSETS / "hero.svg", hero(args.login, graph, cfg))
    write(ASSETS / "identity.svg", identity(image, args.login))
    write(ASSETS / "stack.svg", stack(cfg))
    write(ASSETS / "works.svg", works(cfg))
    write(ASSETS / "signal.svg", signal(graph))
    write(ASSETS / "year.svg", year(graph))
    write(ASSETS / "footer.svg", footer(cfg))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
