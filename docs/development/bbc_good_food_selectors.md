# BBC Good Food – Scraper Reference

Explored: 2026-03-14
Example recipe: https://www.bbcgoodfood.com/recipes/ultimate-spaghetti-carbonara-recipe
Example collection: https://www.bbcgoodfood.com/recipes/collection/chicken-recipes

---

## Cookies / Consent Popup

BBC Good Food uses **Sourcepoint** (a CMP) for GDPR consent. In a real browser session a modal will appear before any content is usable. Key details:

- The CMP config is served from `https://consent.bbcgoodfood.com`
- Account ID: `1742`
- The consent state is stored as a cookie and managed via `window.__tcfapi`
- The popup is **fully JS-rendered** — it does not appear in the raw HTML response
- When scraping with `requests`/`httpx` (no JS execution) the consent popup is absent and the full page HTML is returned intact, including all recipe data
- If using a headless browser, dismiss the modal by clicking "Accept all" before interacting with the page. The button can be found via:
  - `button[title="Accept all"]` (most common Sourcepoint pattern)
  - Or wait for `window.__tcfapi` to confirm consent status `tcData.eventStatus === 'tcloaded'`

---

## Primary Data Source: JSON-LD (`<script type="application/ld+json">`)

**Recommended approach.** Every recipe page contains multiple JSON-LD blocks. The most useful is `@type: "Recipe"`.

### How to extract

```python
import json
from bs4 import BeautifulSoup

soup = BeautifulSoup(html, "html.parser")
scripts = soup.find_all("script", type="application/ld+json")
recipe_ld = next(
    (json.loads(s.string) for s in scripts if '"Recipe"' in (s.string or "")),
    None,
)
```

### Full example (spaghetti carbonara)

```json
{
  "@context": "https://schema.org",
  "@id": "https://www.bbcgoodfood.com/recipes/ultimate-spaghetti-carbonara-recipe#Recipe",
  "@type": "Recipe",
  "name": "Ultimate spaghetti carbonara recipe",
  "url": "https://www.bbcgoodfood.com/recipes/ultimate-spaghetti-carbonara-recipe",
  "description": "Discover how to make traditional spaghetti carbonara. This classic Italian pasta dish combines a silky cheese sauce with crisp pancetta and black pepper.",
  "headline": "Ultimate spaghetti carbonara recipe",
  "author": [
    {
      "@type": "Person",
      "name": "Angela Nilsen",
      "url": "https://www.bbcgoodfood.com/author/angelanilsen"
    }
  ],
  "datePublished": "2025-03-31T18:05:13+01:00",
  "dateModified": "2025-03-31T18:05:13+01:00",
  "prepTime": "PT20M",
  "cookTime": "PT15M",
  "totalTime": "PT35M",
  "recipeYield": 4,
  "recipeCategory": "Dinner, Main course",
  "recipeCuisine": "Italian",
  "keywords": "Angela Nilsen, Authentic Italian, Carbonara, Creamy, Pancetta, Parmesan, Pasta, Pecorino, Spaghetti",
  "image": [
    {
      "@type": "ImageObject",
      "url": "https://images.immediate.co.uk/production/volatile/sites/30/2020/08/recipe-image-legacy-id-1001491_11-2e0fa5c.jpg?resize=440,400",
      "width": 440,
      "height": 400
    }
  ],
  "recipeIngredient": [
    "100g pancetta",
    "50g pecorino cheese",
    "50g parmesan",
    "3 large eggs",
    "350g spaghetti",
    "2 plump garlic cloves peeled and left whole",
    "50g unsalted butter",
    "sea salt and freshly ground black pepper"
  ],
  "recipeInstructions": [
    { "@type": "HowToStep", "text": "Put a large saucepan of water on to boil." },
    { "@type": "HowToStep", "text": "Finely chop the 100g pancetta..." },
    "..."
  ],
  "nutrition": {
    "@type": "NutritionInformation",
    "calories": "656 calories",
    "fatContent": "30.03 grams fat",
    "saturatedFatContent": "15 grams saturated fat",
    "carbohydrateContent": "66 grams carbohydrates",
    "sugarContent": "4 grams sugar",
    "fiberContent": "4 grams fiber",
    "proteinContent": "29 grams protein",
    "sodiumContent": "1.65 milligram of sodium"
  },
  "publisher": {
    "@type": "Organization",
    "name": "Good Food",
    "url": "https://www.bbcgoodfood.com"
  }
}
```

A **separate** JSON-LD block contains the aggregate rating (not merged into the Recipe block):

```json
{
  "@context": "https://schema.org/",
  "@id": "https://www.bbcgoodfood.com/recipes/ultimate-spaghetti-carbonara-recipe#Recipe",
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": 5,
    "reviewCount": 1017,
    "bestRating": 5,
    "worstRating": 1
  }
}
```

To merge them, match on the shared `@id` value.

### JSON-LD field reliability

| Field | Reliability | Notes |
|---|---|---|
| `name` | Very high | Always present |
| `description` | Very high | Always present |
| `recipeIngredient` | Very high | Plain strings, quantity and name concatenated |
| `recipeInstructions` | Very high | Array of `HowToStep` objects |
| `prepTime` / `cookTime` / `totalTime` | High | ISO 8601 duration format (`PT20M`) |
| `recipeYield` | High | Integer (number of servings) |
| `recipeCuisine` | Medium | Not always set |
| `recipeCategory` | Medium | Comma-separated string |
| `nutrition` | Medium | Present on most recipes, values are strings with units |
| `keywords` | Medium | Comma-separated tag string |
| `author` | High | Array; may have multiple authors |
| `aggregateRating` | Medium | In a separate JSON-LD block; may not exist on new recipes |
| `image` | High | Array of ImageObject; first entry is canonical |

---

## Secondary Data Source: `__NEXT_DATA__`

The page is built with Next.js. A `<script id="__NEXT_DATA__">` tag contains the full SSR props. On recipe pages, `props.pageProps` contains:

- `taxonomies` — structured array with `display` (e.g. `"Tags"`, `"Cuisines"`, `"Diets"`, `"Meal types"`, `"Occasions"`, `"Difficulties"`) and `terms` arrays, each with `slug` and `display`
- `postMeta.entity` — confirms whether the page is a `"recipe"`
- `postMeta.clientId` — internal numeric ID for the recipe
- `isPremium` — boolean; premium recipes may require a subscription
- `contentWallExperience.enabled` — boolean; if `true`, content may be gated

```python
import json
from bs4 import BeautifulSoup

soup = BeautifulSoup(html, "html.parser")
next_data = json.loads(soup.find("script", id="__NEXT_DATA__").string)
page_props = next_data["props"]["pageProps"]
taxonomies = page_props.get("taxonomies", [])
```

This is the most reliable source for structured taxonomy data (cuisines, diets, occasions, etc.) compared to the comma-separated strings in JSON-LD.

---

## CSS Selectors (HTML Fallbacks)

Use these only if JSON-LD is absent or incomplete.

### Recipe page

#### Title

```css
h1.heading-1
```
Returns: `"Ultimate spaghetti carbonara recipe"`

#### Description

```css
.recipe-masthead__description
```
Note: The element has class `line-clamper` alongside `recipe-masthead__description`. The full (un-clamped) text is in the element; clamping is CSS-only.
Returns: `"Discover how to make traditional spaghetti carbonara..."`

#### Hero image

```css
.post-header--masthead__hero img.image__img
```
Attributes: `src` contains the CDN URL (`images.immediate.co.uk`). No `srcset` is present in the static HTML; the URL includes `?quality=90&resize=500,454`.

#### Author

```css
a[rel="author"]
```
Returns the author name as text; `href` links to the author profile.

#### Timing and servings

Container: `.recipe-cook-and-prep-details`

Individual items: `.recipe-cook-and-prep-details__item`

Each item's text starts with a label (`Prep:`, `Cook:`) followed by `<time>` elements with `datetime` attributes in ISO 8601 format:

```css
.recipe-cook-and-prep-details__item time
```
`datetime` attribute values: `PT0H15M`, `PT0H20M`, etc.

Servings and difficulty are in the first two `.recipe-cook-and-prep-details__item` elements (no `<time>` element — plain text only).

Example structure:
```
Serves 4      → .recipe-cook-and-prep-details__item (text only)
Easy          → .recipe-cook-and-prep-details__item (text only)
Prep: 15-20m  → .recipe-cook-and-prep-details__item > time[datetime="PT0H15M"], time[datetime="PT0H20M"]
Cook: 15m     → .recipe-cook-and-prep-details__item > time[datetime="PT0H15M"]
```

#### Ingredients

List container:
```css
ul.ingredients-list.list
```

Individual items:
```css
li.ingredients-list__item
```

Within each `<li>`:
- Quantity: `.ingredients-list__item-quantity` (may be empty for "to taste" items)
- Ingredient name: `.ingredients-list__item-ingredient`
- Optional prep note: `.ingredients-list__item-note` (e.g., `" peeled and left whole"`)
- Some ingredients link to glossary pages via `<a href="/glossary/...">` wrapping the name span

Recommended parsing:
```python
for li in soup.select("li.ingredients-list__item"):
    qty = li.select_one(".ingredients-list__item-quantity")
    name = li.select_one(".ingredients-list__item-ingredient")
    note = li.select_one(".ingredients-list__item-note")
    quantity = qty.get_text(strip=True) if qty else ""
    ingredient = name.get_text(strip=True) if name else ""
    prep_note = note.get_text(strip=True) if note else ""
```

#### Method / Steps

List container:
```css
ul.method-steps__list
```

Individual steps:
```css
li.method-steps__list-item
```

Within each step:
- Step label: `.method-steps__item-heading` (e.g., `"step 1"`)
- Step text: `.editor-content` (may contain `<a>` links to glossary terms and `<strong>` emphasis)

#### Nutrition

Container:
```css
ul.nutrition-list
```

Each `<li>` contains a `<span class="nutrition-list__label">` for the nutrient name, followed by the value as a text node. Some items also have `.nutrition-list__additional-text` for qualifiers like `"low"`.

```python
for li in soup.select(".nutrition-list li"):
    label = li.select_one(".nutrition-list__label")
    nutrient = label.get_text(strip=True) if label else ""
    value = li.get_text(strip=True).replace(nutrient, "", 1).strip()
```

Nutrients present: `kcal`, `fat`, `saturates`, `carbs`, `sugars`, `fibre`, `protein`, `salt`

#### Tags / Diet labels

```css
.post-header--masthead__tags-item
```
Returns individual tag strings (e.g., `"Low sugar"`). Note: this appears to show only diet-related tags. For the full taxonomy, use `__NEXT_DATA__`.

#### Rating display

```css
.rating__stars
```
The numeric rating value is not directly in the HTML text — it is rendered as stars via CSS. Prefer the `aggregateRating` JSON-LD block for the numeric value.

---

## Collection / Category Page

Example: https://www.bbcgoodfood.com/recipes/collection/chicken-recipes

### Recipe card structure

Cards are `<article>` elements with key data attributes:

```css
article.card[data-item-type="recipe"]
```

Data attributes on each card:
- `data-item-id` — internal numeric recipe ID
- `data-item-name` — recipe title
- `data-item-type` — `"recipe"` for recipe cards; also `"editorialList"` for sub-collection cards (filter to `"recipe"`)
- `data-index` — position in the list (1-based)

To get the recipe URL from a card:
```css
article.card[data-item-type="recipe"] a[aria-label]
```
The `aria-label` is `"View {Recipe Title}"` and the `href` is the canonical recipe URL.

Alternatively, the title text link:
```css
article.card[data-item-type="recipe"] a:not([aria-label])
```

Example card data:
- `data-item-id="233479"`
- `data-item-name="Chicken & chorizo jambalaya"`
- `href="https://www.bbcgoodfood.com/recipes/chicken-chorizo-jambalaya"`

### Number of recipes per page

A collection page typically contains **~64 recipe cards** in the static HTML (across multiple `card` blocks in the page builder layout). There is no pagination UI — all curated recipes for that collection are rendered on a single page.

The "Explore more" button at the bottom of a collection page links to a search page (`/search?q={collection-name}`), which does support pagination (see below).

### __NEXT_DATA__ on collection pages

The `props.pageProps.blocks` array contains block objects. Recipe cards are in blocks with `"type": "card"`. Each block has an `items` array of card objects with:
- `title`, `url`, `id`, `description`, `rating`, `image`, `postType`, `terms`

Filter by `item["postType"] == "recipe"` (vs `"page"` for sub-collection cards).

---

## Search Page Pagination

URL pattern: `https://www.bbcgoodfood.com/search?q={query}&page={n}`

The `__NEXT_DATA__` on search pages exposes `props.pageProps.searchResults`:

```json
{
  "items": [...],
  "totalItems": 2665,
  "limit": 30,
  "nextUrl": "https://www.bbcgoodfood.com/api/search-frontend/search?page=2&search=chicken",
  "previousUrl": null
}
```

- `totalItems` — total number of results
- `limit` — results per page (30)
- `nextUrl` / `previousUrl` — API endpoint URLs for adjacent pages

The `nextUrl` field points to an internal API (`/api/search-frontend/search`) that requires the `Referer` header set to the BBC Good Food domain to return JSON data. Alternatively, just increment `?page=N` on the HTML search URL directly.

There are no visible pagination `<a>` tags in the HTML; pagination is handled client-side via JS. Use the `__NEXT_DATA__` values to determine page count:

```python
total_pages = math.ceil(search_results["totalItems"] / search_results["limit"])
```

Recipe cards on search pages use the same `article.card[data-item-type="recipe"]` selector and data attributes as collection pages.

---

## Notes

- **Static HTML is sufficient** for all recipe data. No JS execution is required when using `requests`/`httpx`.
- The CMP consent popup only appears when running a real browser; it does not affect static HTML scraping.
- Recipe slugs follow the pattern `/recipes/{slug}` with no sub-paths. URLs with `/collection/`, `/category/`, `/technique/` in them are not recipe pages.
- The ingredient `recipeIngredient` strings in JSON-LD concatenate quantity and name without a separator (e.g., `"100g pancetta"`). The HTML provides them in separate elements for clean parsing.
- Some ingredient names are hyperlinked to glossary pages (`/glossary/{slug}`); use `.get_text()` to get clean names regardless.
- Step text in `.editor-content` may contain inline links to glossary terms — call `.get_text()` to strip them.
- The `nutrition` values in JSON-LD include the unit as part of the string (e.g., `"30.03 grams fat"`). The HTML `nutrition-list` is cleaner: label and value are in separate elements.
- `datePublished` in the JSON-LD may be the last modified date rather than the original publish date; treat as `last_updated`.
- There is no "next page" link on collection pages — they are curated single-page lists. Use the search endpoint for exhaustive crawling.
