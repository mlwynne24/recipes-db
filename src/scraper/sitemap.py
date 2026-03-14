import urllib.request
import xml.etree.ElementTree as ET
from datetime import UTC, datetime

_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
_SITEMAP_URL = "https://www.bbcgoodfood.com/sitemaps/{year}-Q{quarter}-recipe.xml"


def current_quarter_sitemap_url() -> str:
    now = datetime.now(UTC)
    quarter = (now.month - 1) // 3 + 1
    return _SITEMAP_URL.format(year=now.year, quarter=quarter)


def sitemap_url_for(year: int, quarter: int) -> str:
    return _SITEMAP_URL.format(year=year, quarter=quarter)


def fetch_sitemap_entries(sitemap_url: str) -> list[tuple[str, datetime]]:
    """Fetch and parse a BBC Good Food quarterly sitemap, filtering out /premium/ URLs."""
    with urllib.request.urlopen(sitemap_url, timeout=30) as resp:
        content = resp.read()

    root = ET.fromstring(content)
    entries = []
    for url_el in root.findall("sm:url", _NS):
        loc = url_el.findtext("sm:loc", namespaces=_NS)
        lastmod = url_el.findtext("sm:lastmod", namespaces=_NS)
        if not loc or not lastmod or "/premium/" in loc:
            continue
        try:
            dt = datetime.fromisoformat(lastmod.replace("Z", "+00:00"))
        except ValueError:
            continue
        entries.append((loc, dt))
    return entries
