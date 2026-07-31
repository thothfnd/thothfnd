# V3.0.1 — Activity Motion Validation Hotfix

Fixes the `activity.gif: motion imperceptible` false/near-failure seen with live GitHub data.

- Activity contribution rhythm now has a deterministic scan over the real contribution cells.
- Recent-commit path now draws progressively and carries a trace head.
- Commit nodes still reveal only from real commit data; no synthetic commits are added.
- Motion QA now uses both whole-frame mean difference and changed-pixel ratio so localized intentional motion is measured correctly.
- Truly static GIFs still fail validation.
