# umenu — UMass Dining in your terminal

A goofy, actually-useful CLI for UMass Dining menus. Scrapes the official pages,
caches locally, and can be accessed with SSH for zero-install demos.

## Features
- `umenu today` — all halls for today
- `umenu hall worcester --meal dinner`
- `umenu search "tofu"`
- Optional: `umenu vibes` / `umenu recommend` (Gemini)

## Quickstart (local)
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python umenu_cli.py today
