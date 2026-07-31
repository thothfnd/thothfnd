# Install / update

1. Copy the files into the profile repository ex: (`thothfnd/thothfnd`).
2. Edit `data/profile.json` for global links/copy.
3. Add `.github/profile/` metadata/assets to public pinned project repositories as desired.
4. Run `python scripts/cleanup_repo.py` first (dry run), then `python scripts/cleanup_repo.py --apply`.
5. Install dependencies and Chromium, collect data, build and render.
6. Push. The scheduled workflow refreshes every six hours and also supports manual runs.

Local demo without GitHub token:

```bash
python scripts/collect_github.py --demo
python scripts/build_profile.py
python scripts/render_assets.py
python scripts/validate_build.py
```
