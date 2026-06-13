from __future__ import annotations

import random
import time
from pathlib import Path
from playwright.sync_api import BrowserContext, Page, sync_playwright


AUTH_DIR = Path(".auth")
AUTH_DIR.mkdir(exist_ok=True)

# Realistic desktop Chrome UA — headless/automation fingerprints get Cloudflare-blocked,
# so scrapers run headed against the real `chrome` channel by default (see __enter__).
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
)


class BaseScraper:
    """Base helper for Playwright-driven scrapers.

    Subclasses set `name` and implement `scrape(...)`. Use `_human_delay()`
    between page loads. Sessions persist to `.auth/<name>.json`.

    IMPORTANT: Cloudflare (SimplyHired) and similar anti-bot layers block
    headless browsers. By default scrapers launch HEADED using the installed
    real Chrome (`channel="chrome"`) with a realistic context. Pass
    `headless=True` only for sites without bot protection.
    """
    name: str = "base"

    def __init__(self, headless: bool = False):
        self.headless = headless
        self._playwright = None
        self._browser = None
        self._context: BrowserContext | None = None

    def _launch(self):
        # Prefer the installed real Chrome; fall back to bundled chromium if absent.
        try:
            return self._playwright.chromium.launch(
                headless=self.headless,
                channel="chrome",
                args=["--disable-blink-features=AutomationControlled"],
            )
        except Exception:
            return self._playwright.chromium.launch(
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled"],
            )

    def __enter__(self):
        self._playwright = sync_playwright().start()
        self._browser = self._launch()
        state_file = AUTH_DIR / f"{self.name}.json"
        ctx_kwargs = {
            "user_agent": _USER_AGENT,
            "viewport": {"width": 1366, "height": 768},
            "locale": "en-US",
        }
        if state_file.exists():
            ctx_kwargs["storage_state"] = str(state_file)
        self._context = self._browser.new_context(**ctx_kwargs)
        return self

    def __exit__(self, *args):
        try:
            state_file = AUTH_DIR / f"{self.name}.json"
            self._context.storage_state(path=str(state_file))
        except Exception:
            pass
        try:
            self._browser.close()
        finally:
            self._playwright.stop()

    @property
    def context(self) -> BrowserContext:
        return self._context

    def new_page(self) -> Page:
        return self._context.new_page()

    def _human_delay(self, min_s: float = 2.0, max_s: float = 5.0) -> None:
        time.sleep(random.uniform(min_s, max_s))
