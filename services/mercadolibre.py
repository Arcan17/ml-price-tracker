import re
import time
from typing import Optional

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_INIT_SCRIPT = "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"

# Cookies cached in memory; refresh every 30 min
_cookie_cache: dict = {"cookies": None, "fetched_at": 0}
_COOKIE_TTL = 1800


def _get_pw_cookies() -> list[dict]:
    now = time.time()
    if (
        _cookie_cache["cookies"] is not None
        and now - _cookie_cache["fetched_at"] < _COOKIE_TTL
    ):
        return _cookie_cache["cookies"]
    try:
        from pycookiecheat import chrome_cookies

        raw: dict = {}
        for url in (
            "https://listado.mercadolibre.cl",
            "https://api.mercadolibre.com",
            "https://www.mercadolibre.cl",
        ):
            try:
                raw.update(chrome_cookies(url))
            except Exception:
                pass
        cookies = [
            {"name": k, "value": v, "domain": ".mercadolibre.cl", "path": "/"}
            for k, v in raw.items()
        ]
        _cookie_cache["cookies"] = cookies
        _cookie_cache["fetched_at"] = now
        return cookies
    except Exception:
        _cookie_cache["cookies"] = []
        _cookie_cache["fetched_at"] = now
        return []


async def _make_context(playwright):
    browser = await playwright.chromium.launch(
        headless=True,
        args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
    )
    context = await browser.new_context(
        user_agent=_UA,
        locale="es-CL",
        extra_http_headers={"Accept-Language": "es-CL,es;q=0.9"},
    )
    cookies = _get_pw_cookies()
    if cookies:
        await context.add_cookies(cookies)
    return browser, context


async def search_products(query: str, limit: int = 5) -> list[dict]:
    from playwright.async_api import async_playwright

    slug = query.strip().lower().replace(" ", "-")
    url = f"https://listado.mercadolibre.cl/{slug}"
    results: list[dict] = []

    async with async_playwright() as p:
        browser, context = await _make_context(p)
        page = await context.new_page()
        await page.add_init_script(_INIT_SCRIPT)
        try:
            await page.goto(url, timeout=25000)
            await page.wait_for_timeout(3000)
            items = await page.locator("li.ui-search-layout__item").all()
            for item in items[:limit]:
                try:
                    title = (
                        await item.locator(".poly-component__title").text_content(
                            timeout=3000
                        )
                        or ""
                    )
                    price_str = (
                        await item.locator(
                            ".andes-money-amount__fraction"
                        ).first.text_content(timeout=2000)
                        or "0"
                    )
                    price_clean = re.sub(r"[^\d]", "", price_str)
                    price_val = float(price_clean) if price_clean else 0.0
                    link = (
                        await item.locator("a").first.get_attribute(
                            "href", timeout=2000
                        )
                        or ""
                    )
                    link_clean = link.split("#")[0].split("?")[0]
                    m = re.search(r"MLC-?(\d+)", link)
                    item_id = f"MLC{m.group(1)}" if m else ""
                    if title and item_id:
                        results.append(
                            {
                                "id": item_id,
                                "title": title.strip(),
                                "price": price_val,
                                "permalink": link_clean,
                            }
                        )
                except Exception:
                    continue
        finally:
            await page.close()
            await context.close()
            await browser.close()
    return results


async def get_item(item_id: str) -> Optional[dict]:
    from playwright.async_api import async_playwright

    url = f"https://www.mercadolibre.cl/p/{item_id}"

    async with async_playwright() as p:
        browser, context = await _make_context(p)
        page = await context.new_page()
        await page.add_init_script(_INIT_SCRIPT)
        try:
            resp = await page.goto(url, timeout=25000)
            if resp and resp.status == 404:
                return None
            await page.wait_for_timeout(3000)
            title = (await page.locator("h1").first.text_content(timeout=5000)) or ""
            prices = await page.locator(
                ".andes-money-amount__fraction"
            ).all_text_contents()
            if not prices:
                return None
            price_clean = re.sub(r"[^\d]", "", prices[0])
            price_val = float(price_clean) if price_clean else 0.0
            permalink = page.url.split("#")[0].split("?")[0]
            return {
                "id": item_id,
                "title": title.strip(),
                "price": price_val,
                "permalink": permalink,
            }
        except Exception:
            return None
        finally:
            await page.close()
            await context.close()
            await browser.close()


def extract_item_id(text: str) -> Optional[str]:
    """Extract MLC item ID from a URL or raw ID string (e.g. MLC-1234 or MLC1234)."""
    match = re.search(r"\bMLC-?(\d+)\b", text, re.IGNORECASE)
    if match:
        return f"MLC{match.group(1)}"
    return None


def parse_price(text: str) -> Optional[float]:
    """Parse Chilean price input: 850000, 850.000, and $850.000 all → 850000.0"""
    cleaned = re.sub(r"[.,\s$]", "", text)
    if not cleaned:
        return None
    try:
        value = float(cleaned)
        return value if value > 0 else None
    except ValueError:
        return None


def format_price(price: float) -> str:
    """Format as Chilean pesos: 1250990 → $1.250.990"""
    return "$" + f"{int(price):,}".replace(",", ".")
