#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import urllib.error
import urllib.request

API = "https://api.github.com/users/{login}"
USER_AGENT = "auto-ascii-github-profile/1.0"

def request_bytes(url: str, token: str | None = None) -> bytes:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub request failed: HTTP {exc.code}: {body}") from exc

def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--login", required=True)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--hash-file", required=True, type=Path)
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()

    token = os.getenv("GITHUB_TOKEN")
    profile = json.loads(request_bytes(API.format(login=args.login), token))
    avatar_url = profile.get("avatar_url")
    if not avatar_url:
        raise RuntimeError("GitHub API response did not contain avatar_url")

    separator = "&" if "?" in avatar_url else "?"
    avatar = request_bytes(f"{avatar_url}{separator}s=1024")
    digest = hashlib.sha256(avatar).hexdigest()

    previous = args.hash_file.read_text(encoding="utf-8").strip() if args.hash_file.exists() else ""
    changed = digest != previous

    atomic_write(args.image, avatar)
    if changed:
        atomic_write(args.hash_file, (digest + "\n").encode("utf-8"))

    print(f"login={args.login}")
    print(f"avatar_sha256={digest}")
    print(f"changed={'true' if changed else 'false'}")

    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as out:
            out.write(f"changed={'true' if changed else 'false'}\n")
            out.write(f"sha256={digest}\n")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
