# V7 — FINAL DESIGN SYSTEM

## Replace / add

- `README.md`
- `requirements.txt`
- `scripts/generate_profile.py`
- `data/profile.json`
- `data/capabilities.json`
- `assets/generated/`
- `.github/workflows/refresh-profile.yml`

Then run **Actions → Refresh profile interface → Run workflow**.

## Remove old V1–V6 files

Once V7 is live, delete legacy generated files and helper scripts that are no longer referenced:

- `assets/about.svg`
- `assets/activity.svg`
- `assets/avatar-ascii.svg`
- `assets/footer.svg`
- `assets/hero.svg`
- `assets/identity.svg`
- `assets/portrait.svg`
- `assets/profile-meta.svg`
- `assets/signal.svg`
- `assets/stack.svg`
- `assets/stats.svg`
- `assets/works.svg`
- `assets/year.svg`
- `assets/hd-*.svg`
- `assets/projects/`
- old `scripts/render_ascii.py`, `render_meta.py`, `sync_avatar.py`
- old setup/paste helper files no longer needed

Keep only files referenced by V7.

## Design rules

- No repeated card grid.
- No decorative badges or pills.
- Monochrome chrome palette only.
- Minimum visible text is intentionally larger than previous releases.
- Wordmark is custom SVG geometry, not a font.
- Avatar identity animates coarse → dense → final and shows the avatar SHA-256 prefix.
- Capability total is calculated from `data/capabilities.json`; it is not hard-coded.
- The footer contains no current timestamp, so scheduled runs do not create meaningless commits.
