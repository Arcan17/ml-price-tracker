from unittest.mock import AsyncMock, MagicMock, patch

from services.mercadolibre import (
    extract_item_id,
    format_price,
    parse_price,
)


def _make_page(
    *, title="", prices=None, items=None, url="https://example.com", status=200
):
    """Build a MagicMock page where sync methods are MagicMock and async are AsyncMock."""
    page = MagicMock()
    page.goto = AsyncMock(return_value=MagicMock(status=status))
    page.wait_for_timeout = AsyncMock()
    page.add_init_script = AsyncMock()
    page.close = AsyncMock()
    page.url = url

    locator = MagicMock()
    locator.all = AsyncMock(return_value=items or [])
    locator.all_text_contents = AsyncMock(return_value=prices or [])
    locator.first = MagicMock()
    locator.first.text_content = AsyncMock(return_value=title)
    locator.first.get_attribute = AsyncMock(return_value="")
    page.locator.return_value = locator
    return page


def _browser_context(page):
    browser = AsyncMock()
    context = AsyncMock()
    context.new_page = AsyncMock(return_value=page)
    return browser, context


# ── search_products ───────────────────────────────────────────────────────────


async def test_search_products_returns_results():
    from services.mercadolibre import search_products

    item_mock = MagicMock()
    title_loc = MagicMock()
    title_loc.text_content = AsyncMock(return_value="iPhone 15 128GB")
    price_loc = MagicMock()
    price_loc.first = MagicMock()
    price_loc.first.text_content = AsyncMock(return_value="749.990")
    link_loc = MagicMock()
    link_loc.first = MagicMock()
    link_loc.first.get_attribute = AsyncMock(
        return_value="https://articulo.mercadolibre.cl/MLC-1234567890-iphone"
    )

    def locator_side_effect(selector):
        if "title" in selector:
            return title_loc
        if "money" in selector:
            return price_loc
        if selector == "a":
            return link_loc
        return MagicMock()

    item_mock.locator.side_effect = locator_side_effect

    page = _make_page(items=[item_mock, item_mock])
    browser, context = _browser_context(page)

    with patch(
        "services.mercadolibre._make_context",
        new=AsyncMock(return_value=(browser, context)),
    ):
        results = await search_products("iphone 15")

    assert isinstance(results, list)
    assert len(results) == 2
    assert results[0]["id"] == "MLC1234567890"


async def test_search_products_empty_results():
    from services.mercadolibre import search_products

    page = _make_page(items=[])
    browser, context = _browser_context(page)

    with patch(
        "services.mercadolibre._make_context",
        new=AsyncMock(return_value=(browser, context)),
    ):
        results = await search_products("xyzzy_no_existe")

    assert results == []


# ── get_item ──────────────────────────────────────────────────────────────────


async def test_get_item_returns_item():
    from services.mercadolibre import get_item

    page = _make_page(
        title="iPhone 15 128GB Negro",
        prices=["749990"],
        url="https://www.mercadolibre.cl/p/MLC1234567890",
    )
    browser, context = _browser_context(page)

    with patch(
        "services.mercadolibre._make_context",
        new=AsyncMock(return_value=(browser, context)),
    ):
        item = await get_item("MLC1234567890")

    assert item is not None
    assert item["id"] == "MLC1234567890"
    assert item["price"] == 749_990.0


async def test_get_item_returns_none_on_404():
    from services.mercadolibre import get_item

    page = _make_page(status=404)
    browser, context = _browser_context(page)

    with patch(
        "services.mercadolibre._make_context",
        new=AsyncMock(return_value=(browser, context)),
    ):
        item = await get_item("MLCNONEXISTENT")

    assert item is None


# ── extract_item_id ───────────────────────────────────────────────────────────


def test_extract_item_id_from_raw_id():
    assert extract_item_id("MLC1234567890") == "MLC1234567890"


def test_extract_item_id_from_url_with_dash():
    url = "https://articulo.mercadolibre.cl/MLC-1234567890-titulo-del-producto"
    assert extract_item_id(url) == "MLC1234567890"


def test_extract_item_id_from_url_without_dash():
    url = "https://www.mercadolibre.cl/iphone/p/MLC1234567890"
    assert extract_item_id(url) == "MLC1234567890"


def test_extract_item_id_invalid_returns_none():
    assert extract_item_id("not-a-valid-id") is None
    assert extract_item_id("https://google.com") is None
    assert extract_item_id("") is None


# ── parse_price ───────────────────────────────────────────────────────────────


def test_parse_price_plain_number():
    assert parse_price("850000") == 850_000.0


def test_parse_price_chilean_dots():
    assert parse_price("850.000") == 850_000.0


def test_parse_price_with_dollar_sign():
    assert parse_price("$850.000") == 850_000.0


def test_parse_price_millions():
    assert parse_price("1.250.990") == 1_250_990.0


def test_parse_price_invalid_returns_none():
    assert parse_price("abc") is None
    assert parse_price("") is None


# ── format_price ──────────────────────────────────────────────────────────────


def test_format_price_standard():
    assert format_price(749_990) == "$749.990"


def test_format_price_millions():
    assert format_price(1_250_990) == "$1.250.990"


def test_format_price_round_number():
    assert format_price(100_000) == "$100.000"
