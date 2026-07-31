# Architecture

The profile is generated from four separate layers:

1. **Editorial configuration** — `data/profile.json`.
2. **Live GitHub data** — `scripts/collect_github.py` writes `data/runtime.json`.
3. **Visual source** — `source/` is rendered in Chromium.
4. **GitHub output** — generated GIF/PNG assets under `assets/generated/` and a generated `README.md`.

## Data flow

```text
GitHub APIs + profile config + repository metadata
                    ↓
             normalized runtime
                    ↓
              HTML/CSS/JS source
                    ↓
             deterministic capture
                    ↓
          GIF / PNG + README output
```

## Public pinned repositories

The collector reads the account's public pinned repositories through GitHub GraphQL and renders at most the number configured by `max_pinned_projects`.

A project repository can describe its own presentation with:

```text
.github/profile/
├── logo.png
├── cover-01.png
├── cover-02.png
├── cover-03.png
├── desc.md
└── profile.json
```

Real repository media is preferred. Missing media does not trigger fabricated artwork.

## Project metadata

`desc.md` can define:

- `# Headline`
- `# Overview`
- `# Pillars`

`profile.json` can define project status and arbitrary labelled links.

## Metrics

The live collector currently exposes:

- public commits authored by the profile account across accessible owned public repositories;
- published GitHub Releases across those repositories;
- GitHub followers;
- contribution-calendar total for the last 12 months;
- active contribution days for the last 12 months;
- recent public commits;
- public pinned repositories.

Metric labels describe their actual scope instead of implying private or lifetime coverage that cannot be proven.

## Rendering

`source/index.html`, `source/styles.css`, and `source/app.js` are the canonical visual source.

`scripts/render_assets.py` opens the generated source in Chromium, advances deterministic scene timelines, captures frames, and encodes GitHub-compatible assets.

The README is therefore static and GitHub-compatible even though the design source uses browser layout and motion logic.

## Cleanup

`scripts/cleanup_repo.py` uses a safety gate before deleting known legacy or generated files. It must not recursively delete arbitrary repository content.

Generated output is rebuilt from source on refresh.
