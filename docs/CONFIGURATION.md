# Configuration

## Global links

Edit `data/profile.json`:

```json
"global_links": [
  {"label": "Telegram Channel", "url": "https://..."},
  {"label": "Website", "url": "https://..."}
]
```

Empty URLs stay hidden.

## Project links/content

Add `.github/profile/profile.json` to a pinned repository:

```json
{
  "status": "Active development",
  "links": [
    {"label": "Telegram", "url": "https://..."},
    {"label": "Website", "url": "https://..."}
  ]
}
```

The repository link is added automatically.

`desc.md` may contain `# Headline`, `# Overview`, and `# Pillars` sections.
