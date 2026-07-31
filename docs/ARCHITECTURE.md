# Architecture

V3 separates the profile into four layers:

1. **Editorial config** — `data/profile.json`.
2. **Live GitHub data** — `scripts/collect_github.py` → `data/runtime.json`.
3. **Web-quality visual source** — `source/` rendered in Chromium.
4. **GitHub-compatible output** — GIF/PNG under `assets/generated/` plus generated `README.md`.

## Public pinned repositories

The collector uses GitHub GraphQL pinned repositories and keeps a maximum of three public repository pins. Project content is read from each repository's `.github/profile/` directory when present.

## Repository self-description

Recommended project repository structure:

```text
.github/profile/
├── logo.png
├── cover-01.png
├── cover-02.png
├── cover-03.png
├── desc.md
└── profile.json
```

Real cover assets drive the project stack. No fabricated illustration is generated when media is absent.

## Metrics

- `PUBLIC COMMITS`: commits authored by the profile user reachable from the default branches of owned public repositories, aggregated using the REST commits endpoint.
- `RELEASES`: published GitHub Releases across owned public repositories.
- `CONTRIBUTIONS / 12M`: GitHub contribution calendar total.
- followers: GitHub user follower total.

Labels deliberately describe the scope instead of implying lifetime/private coverage that the workflow cannot prove.
