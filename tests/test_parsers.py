from src.scraper.parsers import (
    normalize_ingredient_name,
    parse_collection_page,
    parse_ingredient,
    parse_next_page,
    parse_recipe_page,
)


def test_parse_recipe_json_ld(sample_recipe_html):
    recipe = parse_recipe_page(sample_recipe_html, "https://www.bbcgoodfood.com/recipes/carbonara")
    assert recipe is not None
    assert recipe.title == "Spaghetti Carbonara"
    assert recipe.description == "A classic Roman pasta dish."
    assert recipe.prep_time == "10 mins"
    assert recipe.cook_time == "20 mins"
    assert recipe.serves == "2 servings"
    assert "pasta" in recipe.tags
    assert len(recipe.ingredients) == 3


def test_parse_recipe_returns_none_on_empty():
    result = parse_recipe_page("<html><body></body></html>", "https://x.com")
    assert result is None


def test_parse_collection_page(sample_collection_html):
    urls = parse_collection_page(sample_collection_html)
    assert len(urls) == 2
    assert all("/recipes/" in u for u in urls)
    # Collection links should be excluded
    assert not any("/collection/" in u for u in urls)


def test_parse_next_page_rel():
    html = '<html><body><a href="/page/2" rel="next">Next</a></body></html>'
    url = parse_next_page(html)
    assert url is not None
    assert "page/2" in url


def test_parse_next_page_none():
    html = "<html><body><p>No pagination</p></body></html>"
    assert parse_next_page(html) is None


def test_normalize_ingredient_name():
    assert normalize_ingredient_name("Fresh Large Chicken Breasts") == "chicken breast"
    assert normalize_ingredient_name("finely chopped onions") == "onion"
    assert normalize_ingredient_name("dried thyme") == "thyme"


def test_parse_ingredient_with_quantity_and_unit():
    ing = parse_ingredient("200g spaghetti")
    assert ing.quantity == "200"
    assert ing.unit == "g"
    assert "spaghetti" in ing.name
    assert ing.original_text == "200g spaghetti"


def test_parse_ingredient_no_quantity():
    ing = parse_ingredient("salt and pepper")
    assert ing.quantity is None
    assert ing.unit is None
    assert ing.original_text == "salt and pepper"


def test_parse_ingredient_fraction():
    ing = parse_ingredient("½ tsp cumin")
    assert ing.quantity == "½"
    assert ing.unit == "tsp"
