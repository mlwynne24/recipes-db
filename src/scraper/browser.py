import asyncio
from contextlib import asynccontextmanager

from playwright.async_api import Browser, Page, async_playwright

from src.config.settings import settings

_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


@asynccontextmanager
async def get_browser():
    async with async_playwright() as pw:
        browser: Browser = await pw.chromium.launch(headless=settings.headless)
        try:
            yield browser
        finally:
            await browser.close()


@asynccontextmanager
async def get_page():
    async with get_browser() as browser:
        context = await browser.new_context(
            user_agent=_USER_AGENT,
            locale="en-GB",
            viewport={"width": 1280, "height": 800},
        )
        page: Page = await context.new_page()
        await page.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2}", lambda r: r.abort())
        try:
            yield page
        finally:
            await context.close()


async def fetch_html(page: Page, url: str) -> str:
    await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
    # Dismiss Sourcepoint GDPR consent modal (BBC Good Food uses CMP account 1742)
    try:
        accept_btn = page.locator('button[title="Accept all"]').first
        if await accept_btn.is_visible(timeout=3_000):
            await accept_btn.click()
            await asyncio.sleep(0.5)
    except Exception:
        pass
    return await page.content()
