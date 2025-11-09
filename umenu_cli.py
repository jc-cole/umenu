import sys, json, shlex, datetime as dt
from typing import Optional, Dict, Any, List
import click

from umenu_scrape_all import scrape_all_halls, scrape_hall

HALL_ALIASES = {
    "worcester": "worcester",
    "wor": "worcester",
    "berkshire": "berkshire",
    "berk": "berkshire",
    "franklin": "franklin",
    "frank": "franklin",
    "hampshire": "hampshire",
    "hamp": "hampshire",
}

MEAL_ALIASES = {
    "breakfast": "breakfast",
    "lunch": "lunch",
    "dinner": "dinner",
    "late": "late night",
    "late-night": "late night",
    "late_night": "late night",
}

def _resolve_hall(s: Optional[str]) -> Optional[str]:
    if not s: return None
    key = s.strip().lower()
    return HALL_ALIASES.get(key)

def _resolve_meal(s: Optional[str]) -> Optional[str]:
    if not s: return None
    key = s.strip().lower()
    return MEAL_ALIASES.get(key, key)

def _today() -> str:
    return dt.date.today().isoformat()

def _print_json(obj: Any):
    click.echo(json.dumps(obj, ensure_ascii=False, indent=2))

def _print_items_as_list(items: List[Dict[str, Any]]):
    # Lightweight, SSH-safe formatting
    for it in items:
        name = it.get("name", "").strip()
        cal = it.get("calories") or "?"
        prot = it.get("protein") or "?"
        diet = (it.get("diet") or "").replace(",", " ·")
        click.echo(f"- {name}  (cal {cal}, protein {prot})")
        if diet:
            click.echo(f"    {diet}")

def _print_meal(meal_key: str, categories: List[Dict[str, Any]]):
    click.secho(meal_key.upper(), bold=True)
    for cat in categories:
        click.secho(f"  {cat['category']}", fg="cyan")
        _print_items_as_list(cat["items"])
        click.echo()

@click.group()
@click.version_option("0.1")
def cli():
    """UMass Dining, in your terminal. Minimal, SSH-friendly."""
    pass

@cli.command()
@click.option("--date", default=_today(), help="YYYY-MM-DD")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--no-cache", is_flag=True, help="Bypass cache")
def today(date, as_json, no_cache):
    """Show all halls for the given date (default: today)."""
    data = scrape_all_halls(date=date, use_cache=not no_cache)
    if as_json:
        _print_json(data)
        return

    click.secho(f"UMass Dining — {date}", bold=True)
    halls = data.get("halls", {})
    for hall_name, hall_data in halls.items():
        click.secho(f"\n== {hall_name} ==", bold=True)
        meals = (hall_data or {}).get("meals", {})
        if not meals:
            err = (hall_data or {}).get("error")
            click.echo(err or "No menu posted.")
            continue
        for meal_key, categories in meals.items():
            _print_meal(meal_key, categories)

@cli.command()
@click.argument("hall", metavar="<hall>")
@click.option("--meal", help="breakfast|lunch|dinner|late night")
@click.option("--date", default=_today(), help="YYYY-MM-DD")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--no-cache", is_flag=True, help="Bypass cache")
def hall(hall, meal, date, as_json, no_cache):
    """Show one hall (and optionally one meal)."""
    slug = _resolve_hall(hall)
    if not slug:
        click.echo("Unknown hall. Try: worcester|berkshire|franklin|hampshire")
        sys.exit(2)

    meal_key = _resolve_meal(meal) if meal else None
    hall_data = scrape_hall(slug, date=date, use_cache=not no_cache)

    if as_json:
        if meal_key:
            # filter JSON to a single meal
            filtered = {
                **hall_data,
                "meals": {meal_key: hall_data.get("meals", {}).get(meal_key, [])}
            }
            _print_json(filtered)
        else:
            _print_json(hall_data)
        return

    click.secho(f"{hall_data['hall']} — {date}", bold=True)
    meals = hall_data.get("meals", {})
    if not meals:
        click.echo(hall_data.get("error") or "No menu posted.")
        return
    if meal_key:
        cats = meals.get(meal_key)
        if not cats:
            click.echo(f"No '{meal_key}' menu.")
            return
        _print_meal(meal_key, cats)
    else:
        for mkey, cats in meals.items():
            _print_meal(mkey, cats)

@cli.command()
@click.argument("query", metavar="<query>")
@click.option("--hall", help="Limit to a hall")
@click.option("--meal", help="Limit to a meal")
@click.option("--date", default=_today(), help="YYYY-MM-DD")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--no-cache", is_flag=True, help="Bypass cache")
def search(query, hall, meal, date, as_json, no_cache):
    """Search items by substring (case-insensitive)."""
    q = query.lower()
    slug = _resolve_hall(hall) if hall else None
    meal_key = _resolve_meal(meal) if meal else None

    halls_data = {}
    if slug:
        one = scrape_hall(slug, date=date, use_cache=not no_cache)
        halls_data[one["hall"]] = one
    else:
        halls_data = scrape_all_halls(date=date, use_cache=not no_cache)["halls"]

    results = []
    for hall_name, hall_data in halls_data.items():
        for mkey, cats in (hall_data.get("meals") or {}).items():
            if meal_key and mkey != meal_key: 
                continue
            for cat in cats:
                for it in cat["items"]:
                    if q in it.get("name", "").lower():
                        results.append({
                            "hall": hall_name,
                            "meal": mkey,
                            "category": cat["category"],
                            "name": it["name"],
                            "calories": it.get("calories"),
                            "protein": it.get("protein"),
                            "diet": it.get("diet"),
                            "allergens": it.get("allergens"),
                        })

    if as_json:
        _print_json({"date": date, "query": query, "results": results})
        return

    if not results:
        click.echo("No matches.")
        return

    click.secho(f"Matches for '{query}' — {date}\n", bold=True)
    for r in results:
        click.secho(f"{r['hall']} / {r['meal']} / {r['category']}", fg="cyan")
        click.echo(f"- {r['name']}  (cal {r['calories'] or '?'}, protein {r['protein'] or '?'})")
        if r.get("diet"):
            click.echo(f"    {r['diet']}")
        if r.get("allergens"):
            click.echo(f"    Allergens: {r['allergens']}")
        click.echo()

@cli.command()
def shell():
    """
    Tiny REPL for SSH. Intended to be used via `ForceCommand umenu shell`.
    Type 'help' for commands, 'exit' to quit.
    """
    click.secho("Welcome to umenu shell. Try: today | hall worcester --meal dinner | search tofu", bold=True)
    while True:
        try:
            line = input("> ").strip()
        except EOFError:
            break
        if not line:
            continue
        if line in ("exit", "quit", ":q"):
            break
        if line in ("help", "?"):
            click.echo("Commands:\n  today [--json] [--date]\n  hall <name> [--meal] [--json] [--date]\n  search <query> [--hall] [--meal] [--json] [--date]\n  exit")
            continue
        # route through click’s parser so REPL uses the same commands
        try:
            argv = shlex.split(line)
            cli.main(args=argv, prog_name="umenu", standalone_mode=False)
        except SystemExit as e:
            # click uses SystemExit; swallow normal exit codes
            if e.code not in (0,):
                click.echo(f"(exit code {e.code})")
        except Exception as ex:
            click.echo(f"error: {ex}")

if __name__ == "__main__":
    cli()