# umenu_scrape_all.py
import json, time, datetime as dt
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import requests
from bs4 import BeautifulSoup, Tag, NavigableString

UA  = "umenu-scraper/0.3 (+contact@example.com)"
CACHE_TTL_SECONDS = 60 * 60  # 1 hour
CACHE_DIR = Path.home() / ".cache" / "umenu"

HALLS: Dict[str, Tuple[str, str]] = {
    # slug: (Display Name, URL)
    "worcester": ("Worcester", "https://umassdining.com/locations-menus/worcester/menu"),
    "berkshire": ("Berkshire", "https://umassdining.com/locations-menus/berkshire/menu"),
    "franklin":  ("Franklin",  "https://umassdining.com/locations-menus/franklin/menu"),
    "hampshire": ("Hampshire", "https://umassdining.com/locations-menus/hampshire/menu"),
}

# ---------- cache helpers ----------
def _cache_key(hall_slug: str, date_iso: str) -> Path:
    return CACHE_DIR / hall_slug / f"{date_iso}.json"

def load_cache(hall_slug: str, date_iso: str) -> Optional[Dict[str, Any]]:
    p = _cache_key(hall_slug, date_iso)
    if not p.exists():
        return None
    try:
        if time.time() - p.stat().st_mtime > CACHE_TTL_SECONDS:
            return None  # stale
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def save_cache(hall_slug: str, date_iso: str, data: Dict[str, Any]) -> None:
    p = _cache_key(hall_slug, date_iso)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ---------- network ----------
def fetch_html(url: str) -> str:
    resp = requests.get(url, headers={"User-Agent": UA}, timeout=15)
    resp.raise_for_status()
    return resp.text

# ---------- parsing ----------
def _iter_category_items(category_h2: Tag):
    """
    Walk siblings after this <h2 class="menu_category_name"> until the next category <h2>.
    Yield each <li class="lightbox-nutrition"> found.
    """
    node = category_h2.next_sibling
    while node:
        if isinstance(node, NavigableString):
            node = node.next_sibling
            continue
        if isinstance(node, Tag):
            if node.name == "h2" and "menu_category_name" in (node.get("class") or []):
                break
            if node.name == "li" and "lightbox-nutrition" in (node.get("class") or []):
                yield node
        node = node.next_sibling

def _parse_item(li: Tag) -> Dict[str, Any]:
    a = li.find("a")
    if not a:
        return {}
    def g(attr, default=None): return a.get(attr, default)
    return {
        "name": (a.get_text(strip=True) or "").strip(),
        "calories": g("data-calories"),
        "protein": g("data-protein"),
        "allergens": g("data-allergens"),
        "diet": g("data-clean-diet-str"),
        "ingredients": g("data-ingredient-list"),
        # optional extras
        "sat_fat": g("data-sat-fat"),
        "sodium": g("data-sodium"),
        "carbs": g("data-total-carb"),
        "fat": g("data-total-fat"),
        "serving_size": g("data-serving-size"),
        "recipe_code": g("data-recipe-webcode"),
        "carbon_list": g("data-carbon-list"),
        "healthfulness": g("data-healthfulness"),
    }

def parse_all_meals(html: str, hall_name: str, date_iso: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    panel = soup.find("div", class_="panel-container")
    if not panel:
        return {"hall": hall_name, "date": date_iso, "meals": {}}

    meals: Dict[str, List[Dict[str, Any]]] = {}

    for meal_div in panel.select('div[id$="_menu"]'):
        meal_h2 = meal_div.find("h2")
        meal_name = (meal_h2.get_text(strip=True) if meal_h2 else "Unknown").strip()
        meal_key = meal_name.lower()

        categories = []
        for cat_h2 in meal_div.find_all("h2", class_="menu_category_name"):
            cat_name = cat_h2.get_text(strip=True)
            items = []
            for li in _iter_category_items(cat_h2):
                item = _parse_item(li)
                if item.get("name"):
                    items.append(item)
            if items:
                categories.append({"category": cat_name, "items": items})

        if categories:
            meals[meal_key] = categories

    return {"hall": hall_name, "date": date_iso, "meals": meals}

# ---------- public API ----------
def scrape_hall(hall_slug: str, date: Optional[str] = None, use_cache: bool = True) -> Dict[str, Any]:
    hall_name, url = HALLS[hall_slug]
    date_iso = date or dt.date.today().isoformat()

    if use_cache:
        cached = load_cache(hall_slug, date_iso)
        if cached:
            return cached

    html = fetch_html(url)
    data = parse_all_meals(html, hall_name, date_iso)

    if use_cache and data.get("meals"):
        save_cache(hall_slug, date_iso, data)

    return data

def scrape_all_halls(date: Optional[str] = None, use_cache: bool = True) -> Dict[str, Any]:
    """
    Returns:
    {
      "date": "YYYY-MM-DD",
      "halls": {
        "Worcester": {...},
        "Berkshire": {...},
        "Franklin": {...},
        "Hampshire": {...}
      }
    }
    """
    date_iso = date or dt.date.today().isoformat()
    result = {"date": date_iso, "halls": {}}
    for slug in HALLS.keys():
        try:
            result["halls"][HALLS[slug][0]] = scrape_hall(slug, date_iso, use_cache)
        except Exception as e:
            # Don’t fail the whole day if one hall is down
            result["halls"][HALLS[slug][0]] = {
                "hall": HALLS[slug][0],
                "date": date_iso,
                "meals": {},
                "error": f"{type(e).__name__}: {e}",
            }
    return result

# ---------- demo ----------
if __name__ == "__main__":
    data = scrape_all_halls()
    print(json.dumps(data, ensure_ascii=False, indent=2)[:8000])
