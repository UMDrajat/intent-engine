import asyncio
import logging
import re
from typing import Any

from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

logger = logging.getLogger(__name__)

# Common price patterns
PRICE_PATTERN = re.compile(r"(\$|£|€|₹|Rs\.?\s?)\s?(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)")


async def scrape_dynamic_product(url: str) -> dict[str, Any] | None:
    """
    Scrape a product page using Playwright for dynamic content.

    Args:
        url: The URL of the product page to scrape.

    Returns:
        A dictionary containing extracted product data or None if failed.
    """
    async with async_playwright() as p:
        # Launch headless browser
        browser = await p.chromium.launch(headless=True)

        # Create a new browser context with stealth
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )

        page = await context.new_page()
        # Apply stealth to avoid detection
        await stealth_async(page)

        # Block heavy assets to save bandwidth and time
        await page.route("**/*.{png,jpg,jpeg,gif,svg,mp4,webm,woff,woff2}", lambda route: route.abort())

        try:
            logger.info(f"Dynamically scraping {url}...")

            # Navigate to the URL
            await page.goto(url, wait_until="networkidle", timeout=30000)

            # Wait a bit more for JS to settle
            await asyncio.sleep(2)

            # Extract basic metadata
            title = await page.title()
            await page.content()

            # Extract price from common selectors or search in content
            price_data = await _extract_price_from_page(page)

            if not price_data:
                # Fallback to regex search in visible text
                text_content = await page.inner_text("body")
                price_data = _extract_price_from_text(text_content)

            result = {
                "url": url,
                "title": title,
                "price": price_data.get("price") if price_data else None,
                "currency": price_data.get("currency") if price_data else None,
                "is_dynamic": True,
                "scraped_at": asyncio.get_event_loop().time(),
            }

            logger.info(f"Successfully scraped {url}: {result}")
            return result

        except Exception as e:
            logger.error(f"Failed to scrape {url}: {str(e)}")
            return None
        finally:
            await browser.close()


async def _extract_price_from_page(page) -> dict[str, Any] | None:
    """Try to extract price using common CSS selectors."""
    # List of common price selectors
    selectors = [
        ".price",
        ".a-price-whole",
        ".product-price",
        "#priceblock_ourprice",
        "[data-testid='price']",
        ".current-price",
        ".price-value",
    ]

    for selector in selectors:
        try:
            element = await page.query_selector(selector)
            if element:
                text = await element.inner_text()
                price_data = _extract_price_from_text(text)
                if price_data:
                    return price_data
        except:
            continue
    return None


def _extract_price_from_text(text: str) -> dict[str, Any] | None:
    """Extract price and currency from text using regex."""
    match = PRICE_PATTERN.search(text)
    if match:
        currency_symbol = match.group(1)
        price_str = match.group(2).replace(",", "")

        # Normalize currency
        currency_map = {"$": "USD", "£": "GBP", "€": "EUR", "₹": "INR", "Rs": "INR"}

        currency = currency_map.get(currency_symbol.strip(), currency_symbol.strip())

        try:
            return {"price": float(price_str), "currency": currency}
        except ValueError:
            return None
    return None
