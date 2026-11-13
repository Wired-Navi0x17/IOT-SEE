# Poster (DesignCraft)

`UCIS_Poster.designcraft` / `.pdf` / `.png` in `docs/poster/` are built by `build_poster.py`.

1. Fonts: Barlow Condensed (SemiBold/Bold/ExtraBold), IBM Plex Sans, IBM Plex Mono installed.
2. Start DesignCraft with its control port: `designcraft --control 47815`.
3. `python3 docs/poster/dc/build_poster.py` (talks to the app through `dc.py`).

Data: `sim.json` is one match from the hub simulator (MI v CSK, seed 25, tied 129–129).
Team colours are read from `hub/src/cricket_hub/ipl.py`.
