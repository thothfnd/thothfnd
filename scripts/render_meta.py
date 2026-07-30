#!/usr/bin/env python3
from __future__ import annotations

import argparse
from html import escape
import json
import os
from pathlib import Path
import urllib.request

def fetch_profile(login: str) -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "auto-ascii-github-profile/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(f"https://api.github.com/users/{login}", headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)

def clip(text: str, maximum: int) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= maximum else text[: maximum - 1].rstrip() + "…"

def build_svg(profile: dict) -> str:
    login = escape(str(profile.get("login") or ""))
    display_name = escape(str(profile.get("name") or profile.get("login") or ""))
    bio = escape(clip(str(profile.get("bio") or "building in public"), 96))
    location = escape(clip(str(profile.get("location") or "github"), 38))

    repos = int(profile.get("public_repos") or 0)
    followers = int(profile.get("followers") or 0)
    following = int(profile.get("following") or 0)

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="126" '
        'viewBox="0 0 720 126" role="img" aria-label="GitHub profile metadata">'
        '<style>'
        ".t{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,'Liberation Mono',"
        "'Courier New',monospace;fill:#24292f}.m{fill:#57606a}"
        "@media(prefers-color-scheme:dark){.t{fill:#f0f6fc}.m{fill:#8b949e}}"
        '</style>'
        f'<text class="t" x="8" y="27" font-size="21" font-weight="700">{display_name}</text>'
        f'<text class="m" x="8" y="49" font-size="13">@{login}</text>'
        f'<text class="t" x="8" y="77" font-size="14">{bio}</text>'
        f'<text class="m" x="8" y="106" font-size="12">{repos} repos · {followers} followers · '
        f'{following} following · {location}</text>'
        '</svg>'
    )

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--login", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    profile = fetch_profile(args.login)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(build_svg(profile), encoding="utf-8")
    print(f"Wrote {args.output}")

if __name__ == "__main__":
    main()
