# THOTH /FND V3.0.2 — UX & Motion Repair

This patch targets the four visual defects reported after V3.0.1.

## 1. Stats strip
- Removes the repeated six-copy ticker.
- Keeps one real three-item sequence: commits, releases, followers.
- Uses a very slow seamless horizontal drift instead of a fast stock-ticker effect.
- Rendering duration is intentionally extended for a calmer loop.

## 2. Hero / “systems built different.”
- Replaces the whole-line spawn/reveal with a per-character ink/reveal sequence.
- Adds a subtle moving reveal head so the text resolves progressively rather than appearing as one block.
- Hero rasterization uses higher temporal resolution for smoother lettering.

## 3. Console
- Console text is now revealed character-by-character.
- Lines are typed sequentially with a real active-line cursor.
- The final cursor remains visible after the typing sequence completes.

## 4. Development Trace
- Replaces the free-floating Bézier commit layout with a structured connected plan.
- Commit labels are anchored to fixed rows and cannot drift away from their route nodes.
- Uses straight connected segments rather than an arbitrary curve.
- Adds a proper 53-week contribution calendar.
- Adds month labels, MON/WED/FRI axis labels, active-day count and LESS→MORE legend.
- Live collection now preserves week/day/date/count/level data from GitHub instead of only a flattened intensity array.
- Calendar and commit route still animate, but the actual data remains unchanged.

## Files replaced

- `source/app.js`
- `source/styles.css`
- `scripts/collect_github.py`
- `scripts/render_assets.py`
- `data/sample-runtime.json` (QA/demo only)

No changes are required to `data/profile.json`, project `.github/profile/` metadata, project covers, project logos, or configured links.

## Validation performed

Demo render passed:

- `hero.gif`: 60 frames
- `stats.gif`: 108 frames
- `activity.gif`: 60 frames
- project scenes: 48 frames each
- `BUILD_VALIDATION=PASS`
