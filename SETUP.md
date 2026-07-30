# Setup

This repository is username-agnostic.

## 1. Create the profile repository

Create a **public** GitHub repository whose name is exactly your GitHub username.
GitHub renders `README.md` from that special repository on your profile.

## 2. Upload these files

Copy the complete contents of this kit into that repository and push to `main`.

## 3. Enable Actions

Open **Actions** and run **Refresh profile visuals** once.

The workflow uses the repository owner automatically:

```yaml
GH_LOGIN: ${{ github.repository_owner }}
```

There is no username to edit.

## 4. What becomes automatic

Every scheduled run:

1. reads the repository owner;
2. queries the GitHub user API;
3. downloads the owner's current GitHub avatar;
4. hashes the raw avatar bytes;
5. regenerates the ASCII portrait only when the hash changes;
6. regenerates the profile metadata graphic;
7. commits only changed generated files.

Changing the profile picture on GitHub is enough.

## Refresh frequency

Every 3 hours, plus manual `workflow_dispatch`.

## Generated files

- `assets/avatar-ascii.svg`
- `assets/profile-meta.svg`
- `.avatar.sha256`

Do not hand-edit them.

## Portrait behavior

The renderer tries to detect the largest face automatically and crop around it.
If no face is detected, it falls back to a centered square crop.
It removes the background, improves contrast, converts the image to ASCII,
and writes an animated SVG that works in a GitHub README.
