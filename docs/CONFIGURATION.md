# Configuration

The public profile is configured primarily through `data/profile.json` and optional metadata stored inside pinned project repositories.

## Global identity

Edit `data/profile.json` to change the account identity and Hero copy.

Typical fields include:

```json
{
  "username": "thothfnd",
  "max_pinned_projects": 3,
  "identity": {
    "handle": "@thothfnd",
    "wordmark": "THOTH /FND",
    "hero_lines": [
      "systems",
      "built different."
    ],
    "console": [
      "..."
    ]
  }
}
```

## Global links

Global links are defined as labelled URLs:

```json
"global_links": [
  {
    "label": "Telegram Channel",
    "url": "https://..."
  },
  {
    "label": "Website",
    "url": "https://..."
  }
]
```

An empty URL is not rendered.

## Project content

For a public pinned repository, add:

```text
.github/profile/
├── logo.png
├── cover-01.png
├── cover-02.png
├── cover-03.png
├── desc.md
└── profile.json
```

### `desc.md`

Example:

```markdown
# Headline

Privacy as architecture, not a checklist of settings.

# Overview

A concise real description of the project.

# Pillars

- Isolation
- Identity
- Routing
- Verification
```

### `profile.json`

Example:

```json
{
  "status": "Active development",
  "links": [
    {
      "label": "Telegram",
      "url": "https://..."
    },
    {
      "label": "Website",
      "url": "https://..."
    }
  ]
}
```

The repository URL is added automatically when it is not already defined.

## Project media

Supported project artwork is read from the repository itself.

Preferred names:

```text
logo.png
logo.webp
icon.png
logo.jpg

cover-01.png
cover-02.png
cover-03.png
```

Cover images can also use WebP, JPG, or JPEG.

No placeholder project illustration should be added simply to fill empty space.

## Rendering settings

Render dimensions, scene durations, frame rate, and related settings live under the `render` object in `data/profile.json`.

Only change those values when intentionally changing output size or motion timing.
