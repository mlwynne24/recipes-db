import json
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin

from bs4 import BeautifulSoup


@dataclass
class ScrapedIngredient:
    original_text: str
    name: str
    quantity: str | None = None
    unit: str | None = None


@dataclass
class ScrapedRecipe:
    url: str
    title: str
    description: str | None = None
    method: str | None = None
    tags: list[str] = field(default_factory=list)
    prep_time: str | None = None
    cook_time: str | None = None
    serves: str | None = None
    ingredients: list[ScrapedIngredient] = field(default_factory=list)


_UNITS = {
    "g", "kg", "ml", "l", "litre", "litres", "liter", "liters",
    "tsp", "tbsp", "teaspoon", "teaspoons", "tablespoon", "tablespoons",
    "cup", "cups", "oz", "lb", "lbs", "bunch", "bunches", "handful",
    "pinch", "dash", "can", "cans", "tin", "tins", "pack", "packs",
    "bag", "bags", "jar", "jars", "sachet", "sachets", "sheet", "sheets",
    "sprig", "sprigs", "slice", "slices", "clove", "cloves",
}

_STRIP_WORDS = {
    "fresh", "dried", "frozen", "tinned", "canned", "organic",
    "large", "small", "medium", "baby", "young",
    "finely", "roughly", "coarsely", "thinly", "thickly",
    "chopped", "sliced", "diced", "grated", "peeled", "crushed",
    "halved", "quartered", "deseeded", "trimmed", "washed",
}


def normalize_ingredient_name(text: str) -> str:
    """Lowercase, strip adjectives, and naively singularize."""
    text = text.lower().strip()
    # Remove content in parentheses
    text = re.sub(r"\(.*?\)", "", text).strip()
    # Remove comma-separated qualifiers at the end (e.g. "chicken, skinless")
    text = text.split(",")[0].strip()
    tokens = text.split()
    tokens = [t for t in tokens if t not in _STRIP_WORDS]
    text = " ".join(tokens)
    # Naive singularization for common endings
    for suffix, replacement in [("atoes", "ato"), ("ies", "y"), ("ves", "f"), ("ses", "s"), ("s", "")]:
        if text.endswith(suffix) and len(text) > len(suffix) + 2:
            candidate = text[: -len(suffix)] + replacement
            if len(candidate) >= 3:
                text = candidate
                break
    return text.strip()


def _parse_quantity_unit(raw: str) -> tuple[str | None, str | None, str]:
    """Split raw ingredient text into (quantity, unit, name)."""
    raw = raw.strip()
    # Match leading number (int, fraction, decimal, or unicode fraction)
    qty_pattern = re.compile(
        r"^([\d½¼¾⅓⅔⅛⅜⅝⅞]+(?:[./\s][\d]+)?)\s*"
    )
    m = qty_pattern.match(raw)
    quantity = m.group(1).strip() if m else None
    rest = raw[m.end():].strip() if m else raw

    # Check for unit at start of rest
    first_word = rest.split()[0].lower().rstrip(".") if rest.split() else ""
    if first_word in _UNITS:
        unit = first_word
        rest = rest[len(first_word):].strip()
    else:
        unit = None

    return quantity, unit, rest


def parse_ingredient(raw: str) -> ScrapedIngredient:
    quantity, unit, name_raw = _parse_quantity_unit(raw)
    name = normalize_ingredient_name(name_raw)
    return ScrapedIngredient(
        original_text=raw,
        name=name,
        quantity=quantity,
        unit=unit,
    )


def _extract_json_ld(soup: BeautifulSoup) -> dict | None:
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, AttributeError):
            continue
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "Recipe" in item.get("@type", ""):
                    return item
        elif isinstance(data, dict):
            if "Recipe" in data.get("@type", ""):
                return data
            # @graph pattern
            for node in data.get("@graph", []):
                if isinstance(node, dict) and "Recipe" in node.get("@type", ""):
                    return node
    return None


def _iso_duration_to_str(duration: str | None) -> str | None:
    """Convert PT1H30M → '1 hour 30 mins', etc."""
    if not duration:
        return None
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?", duration)
    if not m:
        return duration
    hours, mins = m.group(1), m.group(2)
    parts = []
    if hours:
        parts.append(f"{hours} hour{'s' if int(hours) > 1 else ''}")
    if mins:
        parts.append(f"{mins} min{'s' if int(mins) > 1 else ''}")
    return " ".join(parts) if parts else None


def _instructions_to_text(instructions) -> str | None:
    if not instructions:
        return None
    if isinstance(instructions, str):
        return instructions
    if isinstance(instructions, list):
        steps = []
        for item in instructions:
            if isinstance(item, str):
                steps.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("name") or ""
                if text:
                    steps.append(text)
        return "\n\n".join(steps) if steps else None
    return None


def parse_recipe_page(html: str, url: str) -> ScrapedRecipe | None:
    """Parse a BBC Good Food recipe page. Returns None if not a recipe page."""
    soup = BeautifulSoup(html, "html.parser")
    ld = _extract_json_ld(soup)

    if ld:
        title = ld.get("name") or ""
        description = ld.get("description")
        prep_time = _iso_duration_to_str(ld.get("prepTime"))
        cook_time = _iso_duration_to_str(ld.get("cookTime"))
        serves = str(ld.get("recipeYield") or "").strip() or None
        raw_ingredients = ld.get("recipeIngredient") or []
        method = _instructions_to_text(ld.get("recipeInstructions"))
        keywords = ld.get("keywords") or ""
        tags = [k.strip() for k in keywords.split(",") if k.strip()] if keywords else []
        # recipeCategory may be a comma-separated string like "Dinner, Main course"
        category_raw = ld.get("recipeCategory") or ""
        for cat in category_raw.split(","):
            cat = cat.strip()
            if cat and cat not in tags:
                tags.append(cat)
    else:
        # DOM fallback (selectors verified against live site 2026-03-14)
        h1 = soup.select_one("h1.heading-1, h1")
        title = h1.get_text(strip=True) if h1 else ""
        desc_el = soup.select_one(".recipe-masthead__description")
        description = desc_el.get_text(strip=True) if desc_el else None
        prep_time = cook_time = serves = method = None
        raw_ingredients = []
        tags = []
        for li in soup.select("li.ingredients-list__item"):
            text = li.get_text(strip=True)
            if text:
                raw_ingredients.append(text)
        steps = []
        for li in soup.select("li.method-steps__list-item .editor-content"):
            step = li.get_text(strip=True)
            if step:
                steps.append(step)
        method = "\n\n".join(steps) if steps else None

    if not title:
        return None

    ingredients = [parse_ingredient(raw) for raw in raw_ingredients if raw.strip()]

    return ScrapedRecipe(
        url=url,
        title=title,
        description=description,
        method=method,
        tags=tags,
        prep_time=prep_time,
        cook_time=cook_time,
        serves=serves,
        ingredients=ingredients,
    )


def parse_collection_page(html: str, base_url: str = "https://www.bbcgoodfood.com") -> list[str]:
    """Extract recipe URLs from a collection/category listing page.

    Collection pages serve all recipes at once (~64) with no pagination.
    For search pages (/search?q=...) use parse_next_page for pagination.
    """
    soup = BeautifulSoup(html, "html.parser")
    urls: list[str] = []
    seen: set[str] = set()

    # Primary: recipe cards (data-item-type="recipe" excludes sub-collection cards)
    for card in soup.select('article.card[data-item-type="recipe"]'):
        a = card.select_one("a[href]")
        if a:
            full = urljoin(base_url, a["href"]).split("?")[0].rstrip("/")
            if full not in seen:
                seen.add(full)
                urls.append(full)

    # Fallback: generic recipe href scan (for search pages and other layouts)
    if not urls:
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/recipes/" in href and "/collection/" not in href and "/category/" not in href:
                full = urljoin(base_url, href).split("?")[0].rstrip("/")
                if full not in seen and full.startswith("https://www.bbcgoodfood.com/recipes/"):
                    seen.add(full)
                    urls.append(full)

    return urls


def parse_next_page(html: str, base_url: str = "https://www.bbcgoodfood.com") -> str | None:
    """Extract the 'next page' URL from a collection page, if present."""
    soup = BeautifulSoup(html, "html.parser")
    # Common patterns: rel="next", aria-label="next", text containing "Next"
    for a in soup.find_all("a", href=True):
        rel = a.get("rel", [])
        if "next" in rel:
            return urljoin(base_url, a["href"])
        aria = a.get("aria-label", "").lower()
        if "next" in aria:
            return urljoin(base_url, a["href"])
    # Fallback: look for pagination with "Next" text
    for a in soup.find_all("a", href=True):
        if a.get_text(strip=True).lower() in ("next", "next page", "›", "»"):
            return urljoin(base_url, a["href"])
    return None
