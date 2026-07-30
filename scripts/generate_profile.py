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

BG = "#0d1117"
PANEL = "#111820"
FG = "#e6edf3"
MUTED = "#7d8590"
DIM = "#30363d"
ACCENT = "#58a6ff"
ACCENT2 = "#79c0ff"
GOOD = "#3fb950"
RAMP = " .`:-=+*cs#%@"


def esc(v) -> str:
    return html.escape(str(v), quote=True)


def write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8")


def shell(width: int, height: int, body: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<style>
text{{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,"Liberation Mono",monospace}}
.fg{{fill:{FG}}}.muted{{fill:{MUTED}}}.accent{{fill:{ACCENT}}}.good{{fill:{GOOD}}}
</style>
{body}
</svg>'''


def api(url: str, token: str = "") -> bytes:
    headers = {"User-Agent": "animated-profile-generator", "Accept": "application/vnd.github+json"}
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
        headers={"Authorization": f"Bearer {token}", "User-Agent": "animated-profile-generator", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=45) as r:
        obj = json.loads(r.read().decode())
    if obj.get("errors"):
        raise RuntimeError(obj["errors"])
    return obj["data"]["user"]


def demo(login: str) -> tuple[dict, dict]:
    today = dt.date.today()
    days = []
    for i in range(365):
        d = today - dt.timedelta(days=364-i)
        n = 0 if i % 5 else (i * 7) % 11
        if i % 17 == 0:
            n += 4
        days.append({"date": d.isoformat(), "contributionCount": n, "weekday": (d.weekday()+1)%7})
    weeks = [{"contributionDays": days[i:i+7]} for i in range(0, len(days), 7)]
    g = {
        "login": login, "name": login, "bio": None, "location": None, "websiteUrl": None,
        "createdAt": "2024-01-01T00:00:00Z", "followers": {"totalCount": 0}, "following": {"totalCount": 0},
        "repositories": {"totalCount": 3, "nodes": []},
        "contributionsCollection": {"contributionCalendar": {"totalContributions": sum(d["contributionCount"] for d in days), "weeks": weeks}}
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
    body = f'''<text x="8" y="30" class="fg" font-size="19" font-weight="700">{esc(label)}</text>
<line x1="150" y1="24" x2="870" y2="24" stroke="{DIM}" stroke-width="1">
 <animate attributeName="x2" from="150" to="870" dur=".85s" begin=".15s" fill="freeze"/>
</line>
<rect x="8" y="39" width="0" height="2" fill="{ACCENT}">
 <animate attributeName="width" values="0;56;0" dur="2.8s" repeatCount="indefinite"/>
</rect>'''
    return shell(880, 48, body)


def hero(login: str, g: dict, cfg: dict) -> str:
    name = (g.get("name") or login).upper()
    tagline = cfg.get("tagline") or g.get("bio") or "systems // security // engineering"
    repo_count = g["repositories"]["totalCount"]
    followers = g["followers"]["totalCount"]
    joined = (g.get("createdAt") or "")[:4] or "—"
    location = (g.get("location") or "NETWORK // PRIVATE")[:28].upper()
    body = f'''<defs>
<clipPath id="type"><rect x="34" y="0" width="812" height="290"><animate attributeName="width" from="0" to="812" dur="1.6s" begin=".35s" fill="freeze"/></rect></clipPath>
<linearGradient id="scan" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{ACCENT}" stop-opacity="0"/><stop offset=".5" stop-color="{ACCENT}" stop-opacity=".55"/><stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/></linearGradient>
</defs>
<rect x="1" y="1" width="878" height="288" rx="14" fill="{BG}" stroke="{DIM}"/>
<circle cx="28" cy="24" r="4" fill="{GOOD}"><animate attributeName="opacity" values="1;.3;1" dur="2.2s" repeatCount="indefinite"/></circle>
<text x="42" y="30" class="muted" font-size="12">PROFILE // LIVE</text>
<text x="846" y="30" text-anchor="end" class="muted" font-size="11">AUTO-SYNC</text>
<g clip-path="url(#type)"><text x="34" y="94" class="fg" font-size="38" font-weight="700">{esc(name)}</text><text x="34" y="124" class="accent" font-size="15">@{esc(login)}</text><text x="34" y="165" class="muted" font-size="14">{esc(tagline)}</text></g>
<line x1="34" y1="194" x2="846" y2="194" stroke="{DIM}"/>
<text x="34" y="226" class="fg" font-size="15">{repo_count}</text><text x="68" y="226" class="muted" font-size="12">REPOS</text>
<text x="170" y="226" class="fg" font-size="15">{followers}</text><text x="205" y="226" class="muted" font-size="12">FOLLOWERS</text>
<text x="358" y="226" class="fg" font-size="15">{esc(joined)}</text><text x="402" y="226" class="muted" font-size="12">JOINED</text>
<text x="520" y="226" class="fg" font-size="14">{esc(location)}</text>
<text x="34" y="264" class="muted" font-size="11">STATUS</text><text x="90" y="264" class="good" font-size="11">ONLINE</text>
<rect x="-240" y="282" width="240" height="1.5" fill="url(#scan)"><animate attributeName="x" values="-240;880" dur="4.5s" repeatCount="indefinite"/></rect>'''
    return shell(880, 290, body)


def avatar(url: str, token: str) -> Image.Image | None:
    if not url:
        return None
    try:
        raw = api(url + ("&" if "?" in url else "?") + "s=800", token)
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
    ys, xs = np.where(alpha > 18)
    if len(xs) > 10:
        pad = 14
        img = img.crop((max(0,int(xs.min())-pad), max(0,int(ys.min())-pad), min(img.width,int(xs.max())+pad), min(img.height,int(ys.max())+pad)))
    canvas = Image.new("RGB", img.size, "white")
    canvas.paste(img.convert("RGB"), mask=img.getchannel("A"))
    gray = np.array(canvas.convert("L"))
    gray = cv2.createCLAHE(clipLimit=2.6, tileGridSize=(8,8)).apply(gray)
    v = np.power(gray.astype(np.float32)/255.0, 1.65)
    gray = np.clip(v*255,0,255).astype(np.uint8)
    cols = 96
    ratio = gray.shape[0] / max(1,gray.shape[1])
    rows = max(24,min(76,int(cols*ratio*.47)))
    small = cv2.resize(gray,(cols,rows),interpolation=cv2.INTER_AREA)
    out=[]
    for row in small:
        s="".join(RAMP[int((255-int(px))/255*(len(RAMP)-1))] for px in row).rstrip()
        out.append(s)
    return out


def portrait(img: Image.Image | None, login: str) -> str:
    if img is None:
        ls=["                         .........","                    ..::+++++++++::..","                 .:+###############+:.","               .+#####++++++++++#####+.","              :####+:            :+####:","             +###:      PROFILE      :###+","             ###         AVATAR         ###","             +###:       SYNC         :###+","              :####+:            :+####:","               .+#####++++++++++#####+.","                 .:+###############+:.","                    ..::+++++++++::.."]
    else:
        ls=ascii_lines(img)
    line_h=8.8; top=30; h=int(top+len(ls)*line_h+30)
    parts=[f'<rect x="1" y="1" width="878" height="{h-2}" rx="10" fill="{BG}" stroke="{DIM}"/>',f'<text x="18" y="18" class="muted" font-size="9">ASCII IDENTITY // @{esc(login)}</text>']
    for i,line in enumerate(ls):
        y=top+i*line_h; delay=i*.035
        parts.append(f'<clipPath id="cp{i}"><rect x="35" y="{y-7:.1f}" width="810" height="10"><animate attributeName="width" from="0" to="810" dur=".55s" begin="{delay:.3f}s" fill="freeze"/></rect></clipPath>')
        parts.append(f'<text x="440" y="{y:.1f}" text-anchor="middle" clip-path="url(#cp{i})" fill="{FG}" fill-opacity=".88" font-size="7.8" xml:space="preserve">{esc(line)}</text>')
    parts.append(f'<rect x="35" y="{h-15}" width="6" height="10" fill="{ACCENT}"><animate attributeName="opacity" values="1;0;1" dur="1s" repeatCount="indefinite"/></rect>')
    return shell(880,h,"\n".join(parts))


def activity(g: dict) -> str:
    total=g["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    ds=days(g); active=sum(1 for d in ds if d["contributionCount"]>0)
    ws=[sum(d["contributionCount"] for d in w["contributionDays"]) for w in g["contributionsCollection"]["contributionCalendar"]["weeks"]]
    best=max(ws or [0]); maxv=max(ws or [1]) or 1
    pts=[]
    for i,v in enumerate(ws):
        x=40+800*i/max(1,len(ws)-1); y=220-78*v/maxv; pts.append((x,y))
    poly=" ".join(f"{x:.1f},{y:.1f}" for x,y in pts)
    body=f'''<rect x="1" y="1" width="878" height="268" rx="12" fill="{BG}" stroke="{DIM}"/>
<text x="34" y="64" class="fg" font-size="44" font-weight="700">{total}</text><text x="34" y="86" class="muted" font-size="11">CONTRIBUTIONS // LAST YEAR</text>
<text x="822" y="51" text-anchor="end" class="fg" font-size="18" font-weight="700">{active}</text><text x="822" y="69" text-anchor="end" class="muted" font-size="10">ACTIVE DAYS</text>
<text x="822" y="103" text-anchor="end" class="fg" font-size="18" font-weight="700">{best}</text><text x="822" y="121" text-anchor="end" class="muted" font-size="10">BEST WEEK</text>
<polyline points="{poly}" fill="none" stroke="{ACCENT2}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="1100" stroke-dashoffset="0"><animate attributeName="stroke-dashoffset" from="1100" to="0" dur="1.8s" begin=".25s" fill="freeze"/></polyline><line x1="40" y1="235" x2="840" y2="235" stroke="{DIM}"/>'''
    if pts:
        x,y=pts[-1]; body+=f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{FG}"><animate attributeName="r" values="3;5;3" dur="1.8s" repeatCount="indefinite"/></circle>'
    return shell(880,270,body)


def about(g: dict,cfg: dict) -> str:
    lines=list(cfg.get("about",[]))
    if g.get("bio") and g["bio"] not in lines:
        lines=[g["bio"]]+lines
    chunks=[]
    for line in lines[:3]:
        cur=""
        for word in line.split():
            if len(cur)+len(word)+1>92:
                chunks.append(cur); cur=word
            else: cur=(cur+" "+word).strip()
        if cur: chunks.append(cur)
    h=120+24*len(chunks)
    parts=[f'<rect x="1" y="1" width="878" height="{h-2}" rx="12" fill="{BG}" stroke="{DIM}"/>',f'<rect x="28" y="30" width="2" height="{max(55,24*len(chunks))}" fill="{ACCENT}" opacity=".75"/>']
    y=52
    for c in chunks:
        parts.append(f'<text x="48" y="{y}" class="fg" font-size="13">{esc(c)}</text>'); y+=24
    parts.append(f'<text x="48" y="{h-24}" class="muted" font-size="10">FOCUS // PRIVACY • SECURITY • SYSTEMS</text>')
    return shell(880,h,"\n".join(parts))


def stack(cfg: dict) -> str:
    groups = cfg.get("stack_groups") or [{"label": "STACK", "items": cfg.get("stack", [])}]
    total = str(cfg.get("stack_total", "200+"))

    width = 880
    left = 28
    top = 28
    row_h = 64
    gap = 9
    label_w = 106
    tile_h = 36
    counter_w = 166
    height = top + len(groups) * row_h + 78

    parts = [f"""
<defs>
  <linearGradient id="stack-scan" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{ACCENT}" stop-opacity="0"/>
    <stop offset=".5" stop-color="{ACCENT}" stop-opacity=".8"/>
    <stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/>
  </linearGradient>
  <filter id="stack-glow" x="-50%" y="-50%" width="200%" height="200%">
    <feGaussianBlur stdDeviation="2.4" result="blur"/>
    <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
</defs>
<rect x="1" y="1" width="878" height="{height-2}" rx="14" fill="{BG}" stroke="{DIM}"/>
<text x="28" y="24" class="muted" font-size="9">CAPABILITY MATRIX // CURATED SIGNAL</text>
<text x="852" y="24" text-anchor="end" class="muted" font-size="9">FAMILIAR → SPECIALIZED</text>
"""]

    seq = 0
    y = top + 35

    for gi, group in enumerate(groups):
        label = str(group.get("label", f"L{gi+1}"))
        items = [str(x) for x in group.get("items", [])]
        parts.append(f"""
<g opacity="0">
  <animate attributeName="opacity" from="0" to="1" dur=".35s" begin="{0.10 + gi*0.12:.2f}s" fill="freeze"/>
  <rect x="{left}" y="{y-25}" width="{label_w}" height="{tile_h}" rx="6" fill="{PANEL}" stroke="{DIM}"/>
  <rect x="{left}" y="{y-25}" width="3" height="{tile_h}" rx="1.5" fill="{ACCENT}" opacity="{0.95 - gi*0.1:.2f}"/>
  <text x="{left+14}" y="{y-3}" class="muted" font-size="9" font-weight="700">{esc(label)}</text>
</g>
""")

        x = left + label_w + gap
        usable_right = 852
        if gi == len(groups) - 1:
            usable_right -= counter_w + 12

        remaining = max(1, len(items))
        available = usable_right - x - gap * (remaining - 1)
        base_w = available / remaining

        for item in items:
            delay = 0.18 + seq * 0.045
            seq += 1
            w = base_w
            tx = x + w / 2
            pulse_begin = 2.2 + (seq % 12) * 0.12
            parts.append(f"""
<g opacity="0">
  <animate attributeName="opacity" from="0" to="1" dur=".32s" begin="{delay:.3f}s" fill="freeze"/>
  <rect x="{x:.1f}" y="{y-25}" width="{w:.1f}" height="{tile_h}" rx="6"
        fill="{PANEL}" stroke="{DIM}" stroke-width="1">
    <animate attributeName="stroke" values="{DIM};{ACCENT};{DIM}" dur="3.8s"
             begin="{pulse_begin:.2f}s" repeatCount="indefinite"/>
  </rect>
  <text x="{tx:.1f}" y="{y-3}" text-anchor="middle" class="fg" font-size="9.3">{esc(item.upper())}</text>
  <rect x="{x+6:.1f}" y="{y+6}" width="0" height="1.4" rx=".7" fill="{ACCENT2}" opacity=".72">
    <animate attributeName="width" from="0" to="{max(0,w-12):.1f}" dur=".55s"
             begin="{delay+0.07:.3f}s" fill="freeze"/>
  </rect>
</g>
""")
            x += w + gap

        y += row_h

    cy = top + (len(groups)-1)*row_h + 35
    cx = 852 - counter_w
    number = re.sub(r"[^0-9]", "", total) or "200"
    plus = "+" if "+" in total else ""

    parts.append(f"""
<g opacity="0">
  <animate attributeName="opacity" from="0" to="1" dur=".45s" begin="{0.35 + seq*0.045:.3f}s" fill="freeze"/>
  <rect x="{cx}" y="{cy-25}" width="{counter_w}" height="{tile_h}" rx="7"
        fill="{PANEL}" stroke="{ACCENT}" stroke-opacity=".65"/>
  <text x="{cx+16}" y="{cy-3}" class="accent" font-size="16" font-weight="700">{esc(number)}{esc(plus)}</text>
  <text x="{cx+67}" y="{cy-5}" class="fg" font-size="8.5">TECH</text>
  <text x="{cx+67}" y="{cy+7}" class="muted" font-size="7.5">A–Z COVERAGE</text>
  <circle cx="{cx+counter_w-16}" cy="{cy-8}" r="3.2" fill="{GOOD}" filter="url(#stack-glow)">
    <animate attributeName="opacity" values="1;.22;1" dur="1.6s" repeatCount="indefinite"/>
    <animate attributeName="r" values="2.6;4;2.6" dur="1.6s" repeatCount="indefinite"/>
  </circle>
</g>
""")

    rail_y = height - 30
    parts.append(f"""
<line x1="28" y1="{rail_y}" x2="852" y2="{rail_y}" stroke="{DIM}"/>
<text x="28" y="{rail_y+19}" class="muted" font-size="8.5">LANGUAGES · FRAMEWORKS · SYSTEMS · NETWORK · SECURITY · CLOUD · DATA · LOW-LEVEL</text>
<text x="852" y="{rail_y+19}" text-anchor="end" class="muted" font-size="8.5">EXPAND // ON DEMAND</text>
<rect x="-210" y="{rail_y-1}" width="210" height="2" fill="url(#stack-scan)" filter="url(#stack-glow)">
  <animate attributeName="x" values="-210;880" dur="4.2s" repeatCount="indefinite"/>
</rect>
""")

    return shell(width, height, "\n".join(parts))


def project_card(p:dict,i:int)->str:
    words=p.get("description","").split(); lines=[]; cur=""
    for word in words:
        if len(cur)+len(word)+1>96: lines.append(cur); cur=word
        else: cur=(cur+" "+word).strip()
    if cur: lines.append(cur)
    body=f'''<defs><linearGradient id="s" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{ACCENT}" stop-opacity="0"/><stop offset=".5" stop-color="{ACCENT}" stop-opacity=".18"/><stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/></linearGradient></defs>
<rect x="1" y="1" width="878" height="164" rx="12" fill="{BG}" stroke="{DIM}"/><text x="28" y="38" class="muted" font-size="10">PROJECT // {i:02d}</text><text x="28" y="72" class="fg" font-size="22" font-weight="700">{esc(p.get("name","PROJECT"))}</text>
<circle cx="822" cy="35" r="4" fill="{GOOD}"><animate attributeName="opacity" values="1;.25;1" dur="2.1s" begin="{i*.25:.2f}s" repeatCount="indefinite"/></circle><text x="810" y="39" text-anchor="end" class="muted" font-size="9">{esc(p.get("status","ACTIVE"))}</text><text x="28" y="101" class="accent" font-size="10">{esc(p.get("tech",""))}</text>'''
    y=127
    for line in lines[:2]: body+=f'<text x="28" y="{y}" class="muted" font-size="11">{esc(line)}</text>'; y+=18
    body+=f'<rect x="-220" y="158" width="220" height="1" fill="url(#s)"><animate attributeName="x" values="-220;880" dur="{4+i*.4:.1f}s" repeatCount="indefinite"/></rect>'
    return shell(880,166,body)


def stats(g:dict)->str:
    ds=days(g); cur,longest=streaks(ds); repos=g["repositories"]["totalCount"]; stars=sum(int(r.get("stargazerCount") or 0) for r in g["repositories"]["nodes"]); forks=sum(int(r.get("forkCount") or 0) for r in g["repositories"]["nodes"])
    tops=langs(g); total=max(1,sum(v for _,v in tops)); boxes=[("CURRENT STREAK",cur),("LONGEST STREAK",longest),("PUBLIC REPOS",repos),("STARS",stars),("FORKS",forks)]
    body=f'<rect x="1" y="1" width="878" height="310" rx="12" fill="{BG}" stroke="{DIM}"/>'; x=28
    for i,(lab,val) in enumerate(boxes):
        body+=f'<g opacity="1"><animate attributeName="opacity" from="0" to="1" dur=".4s" begin="{i*.09:.2f}s" fill="freeze"/><text x="{x}" y="54" class="fg" font-size="24" font-weight="700">{val}</text><text x="{x}" y="75" class="muted" font-size="9">{lab}</text></g>'; x+=165
    body+=f'<line x1="28" y1="100" x2="850" y2="100" stroke="{DIM}"/>'; y=140
    if not tops: body+=f'<text x="28" y="150" class="muted" font-size="11">language data appears after the first live refresh.</text>'
    for i,(name,size) in enumerate(tops):
        pct=size/total; bw=520*pct; d=.5+i*.1
        body+=f'<text x="28" y="{y}" class="fg" font-size="11">{esc(name.lower())}</text><rect x="180" y="{y-10}" width="520" height="7" rx="3.5" fill="{DIM}"/><rect x="180" y="{y-10}" width="0" height="7" rx="3.5" fill="{ACCENT2}"><animate attributeName="width" from="0" to="{bw:.1f}" dur=".8s" begin="{d:.2f}s" fill="freeze"/></rect><text x="730" y="{y}" class="muted" font-size="10">{pct*100:4.1f}%</text>'; y+=28
    return shell(880,312,body)


def year(g:dict)->str:
    weeks=g["contributionsCollection"]["contributionCalendar"]["weeks"][-53:]; counts=[int(d["contributionCount"]) for w in weeks for d in w["contributionDays"]]; maxc=max(counts or [1]); body=f'<rect x="1" y="1" width="878" height="190" rx="12" fill="{BG}" stroke="{DIM}"/><text x="28" y="30" class="muted" font-size="10">THE YEAR // CONTRIBUTION SIGNAL</text>'
    cell=10; gap=3; x0=94; y0=64
    for label,wd in [("mon",1),("wed",3),("fri",5)]: body+=f'<text x="28" y="{y0+wd*(cell+gap)+9}" class="muted" font-size="8">{label}</text>'
    for wi,w in enumerate(weeks):
        for d in w["contributionDays"]:
            wd=int(d.get("weekday",0)); c=int(d["contributionCount"]); x=x0+wi*(cell+gap); y=y0+wd*(cell+gap); delay=(wi*7+wd)*.003
            if c<=0: fill=DIM; op=.38
            else: fill=ACCENT2; op=.28+.72*(math.log1p(c)/math.log1p(maxc))
            body+=f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{fill}" opacity="{op:.2f}"><animate attributeName="opacity" from="0" to="{op:.2f}" dur=".16s" begin="{delay:.3f}s" fill="freeze"/></rect>'
    body+=f'<text x="850" y="174" text-anchor="end" class="muted" font-size="9">QUIET  ·  LOUD</text>'
    return shell(880,192,body)


def footer(cfg:dict)->str:
    stamp=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    body=f'<line x1="8" y1="14" x2="872" y2="14" stroke="{DIM}"/><text x="8" y="48" class="fg" font-size="12">{esc(cfg.get("footer","VERIFY EVERYTHING."))}</text><text x="8" y="72" class="muted" font-size="9">GENERATED LOCALLY // NO THIRD-PARTY BADGE SERVICE // {esc(stamp)}</text><rect x="846" y="38" width="8" height="14" fill="{ACCENT}"><animate attributeName="opacity" values="1;0;1" dur=".9s" repeatCount="indefinite"/></rect>'
    return shell(880,90,body)


def update_readme(projects:list[dict])->None:
    p=ROOT/"README.md"; s=p.read_text(encoding="utf-8"); start="<!-- PROJECT_CARDS_START -->"; end="<!-- PROJECT_CARDS_END -->"
    cards=[]
    for i,proj in enumerate(projects,1):
        alt=esc(proj.get("name","project")); img=f'assets/projects/project-{i:02d}.svg'; url=proj.get("url","").strip()
        core=f'<img src="{img}" width="100%" alt="{alt}">'
        if url: core=f'<a href="{esc(url)}">{core}</a>'
        cards.append(f'<p align="center">{core}</p>')
    s=re.sub(re.escape(start)+r'.*?'+re.escape(end),start+'\n'+'\n'.join(cards)+'\n'+end,s,flags=re.S)
    p.write_text(s,encoding="utf-8")


def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--login",default=os.environ.get("GH_LOGIN","profile")); ap.add_argument("--token",default=os.environ.get("GITHUB_TOKEN","")); ap.add_argument("--demo",action="store_true"); a=ap.parse_args()
    cfg=json.loads(CONFIG.read_text(encoding="utf-8"))
    try:
        if a.demo or not a.token: rest,g=demo(a.login)
        else: rest,g=rest_user(a.login,a.token),graph_user(a.login,a.token)
    except Exception as exc:
        print(f"live data fallback: {exc}",file=sys.stderr); rest,g=demo(a.login)
    img=None if a.demo else avatar(rest.get("avatar_url",""),a.token)
    write(ASSETS/"hero.svg",hero(a.login,g,cfg)); write(ASSETS/"portrait.svg",portrait(img,a.login)); write(ASSETS/"activity.svg",activity(g)); write(ASSETS/"about.svg",about(g,cfg)); write(ASSETS/"stack.svg",stack(cfg)); write(ASSETS/"stats.svg",stats(g)); write(ASSETS/"year.svg",year(g)); write(ASSETS/"footer.svg",footer(cfg))
    for title in ("about","stack","projects","stats"): write(ASSETS/f"hd-{title}.svg",header(title))
    PROJECTS.mkdir(parents=True,exist_ok=True)
    for p in PROJECTS.glob("project-*.svg"): p.unlink()
    projs=cfg.get("projects",[])
    for i,p in enumerate(projs,1): write(PROJECTS/f"project-{i:02d}.svg",project_card(p,i))
    update_readme(projs)
    return 0

if __name__=="__main__": raise SystemExit(main())
