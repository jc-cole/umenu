# ssh umenu.tech - Mass Dining in your terminal - Hack UMass 2025

A goofy, shockingly useful CLI for UMass Dining menus. Scrapes the official pages,
caches locally, and can be accessed with SSH for zero-install demos.

Previously publicly hosted at ssh umenu.tech 

> "Beauty fades. That is why it is beautiful."

## Features
- `umenu today` — all halls for today
- `umenu hall worcester --meal dinner`
- `umenu search "tofu"`

## Quickstart (local)
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python umenu_cli.py today
