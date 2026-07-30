# Installation — V2 Animated Profile

1. Upload/overwrite everything in the root of your profile repository.
2. Confirm `.github/workflows/refresh-profile.yml` exists exactly at that path.
3. Repository → Settings → Actions → General → Workflow permissions → **Read and write permissions**.
4. Actions → **Refresh animated profile** → **Run workflow**.
5. Wait for the green check, then reload your GitHub profile.

## The only file you normally edit

`profile.json`

It controls the tagline, About text, stack, project cards and footer phrase.
Your GitHub username, name, avatar, followers, repositories, contribution calendar,
streaks, stars and language data are pulled automatically.

The current GitHub profile picture is downloaded on every scheduled run. The generator
tries background removal, boosts local contrast, converts the picture to ASCII, then
builds an animated SVG portrait.

The refresh runs every six hours and can also be launched manually.
