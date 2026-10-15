from typing import Any, Callable
from urllib.parse import urlsplit


class BrowserSession:
    _CHANNELS = {"chrome": "chrome", "edge": "msedge"}
    _MAX_TIMEOUT_MS = 120_000
    _MAX_TEXT_LENGTH = 10_000

    def __init__(self) -> None:
        self._playwright: Any = None
        self._browser: Any = None
        self._context: Any = None
        self._page: Any = None

    @property
    def active(self) -> bool:
        return self._page is not None

    def _require_page(self) -> Any:
        if self._page is None:
            raise RuntimeError("Launch a browser before using browser actions")
        return self._page

    @staticmethod
    def _timeout(step: dict[str, Any]) -> int:
        try:
            timeout = int(step.get("timeout", 15_000))
        except (TypeError, ValueError) as exc:
            raise ValueError("Browser timeout must be an integer in milliseconds") from exc
        if timeout < 100 or timeout > BrowserSession._MAX_TIMEOUT_MS:
            raise ValueError("Browser timeout must be between 100 and 120000 milliseconds")
        return timeout

    @staticmethod
    def _selector(step: dict[str, Any], render: Callable[[Any], Any]) -> str:
        selector = render(step.get("selector", ""))
        if not isinstance(selector, str) or not selector.strip():
            raise ValueError("Browser action requires a selector")
        return selector

    def _locator(self, step: dict[str, Any], render: Callable[[Any], Any]) -> Any:
        return self._require_page().locator(self._selector(step, render))

    def execute(self, step: dict[str, Any], render: Callable[[Any], Any]) -> Any:
        action = step.get("action")
        if action == "browser_launch":
            browser_name = str(step.get("browser", "chrome")).lower()
            channel = self._CHANNELS.get(browser_name)
            if channel is None:
                raise ValueError("Browser must be 'chrome' or 'edge'")
            headless = step.get("headless", False)
            if not isinstance(headless, bool):
                raise ValueError("Browser headless setting must be a boolean")
            if self._playwright is None:
                from playwright.sync_api import sync_playwright

                self._playwright = sync_playwright().start()
            self.close_browser()
            self._browser = self._playwright.chromium.launch(
                channel=channel,
                headless=headless,
                timeout=30_000,
            )
            self._context = self._browser.new_context(accept_downloads=False)
            self._page = self._context.new_page()
            self._page.set_default_timeout(15_000)
            self._page.set_default_navigation_timeout(30_000)
            return {"browser": browser_name, "headless": headless}

        if action == "browser_close":
            self.close_browser()
            return {"closed": True}

        timeout = self._timeout(step)
        if action == "browser_navigate":
            url = render(step.get("url", ""))
            if not isinstance(url, str):
                raise ValueError("Browser navigation URL must be text")
            parsed_url = urlsplit(url.strip())
            if (
                parsed_url.scheme not in {"http", "https"}
                or not parsed_url.hostname
                or parsed_url.username is not None
                or parsed_url.password is not None
            ):
                raise ValueError("Browser navigation requires an http(s) URL without embedded credentials")
            wait_until = step.get("wait_until", "domcontentloaded")
            if wait_until not in {"commit", "domcontentloaded", "load"}:
                raise ValueError("Browser navigation wait state must be commit, domcontentloaded or load")
            response = self._require_page().goto(
                url.strip(),
                wait_until=wait_until,
                timeout=timeout,
            )
            return {
                "url": self._require_page().url,
                "status": response.status if response is not None else None,
            }

        if action == "browser_click":
            self._locator(step, render).click(timeout=timeout)
            return {"clicked": True}

        if action == "browser_fill":
            text = render(step.get("text", ""))
            if not isinstance(text, (str, int, float, bool)):
                raise ValueError("Browser fill text must be a scalar value")
            text = str(text)
            self._locator(step, render).fill(text, timeout=timeout)
            return {"characters": len(text)}

        if action == "browser_press":
            key = str(render(step.get("key", ""))).strip()
            if not key:
                raise ValueError("Browser press action requires a key")
            selector = step.get("selector")
            if selector:
                self._locator(step, render).press(key, timeout=timeout)
            else:
                self._require_page().keyboard.press(key)
            return {"key": key}

        if action == "browser_select":
            value = render(step.get("value", ""))
            if not isinstance(value, str) or not value:
                raise ValueError("Browser select action requires a value")
            selected = self._locator(step, render).select_option(value=value, timeout=timeout)
            return {"selected": selected}

        if action == "browser_wait":
            state = step.get("state", "visible")
            if state not in {"attached", "detached", "visible", "hidden"}:
                raise ValueError("Browser wait state must be attached, detached, visible or hidden")
            self._locator(step, render).wait_for(state=state, timeout=timeout)
            return {"state": state}

        if action == "browser_get_text":
            text = self._locator(step, render).inner_text(timeout=timeout)
            truncated = len(text) > self._MAX_TEXT_LENGTH
            text = text[: self._MAX_TEXT_LENGTH]
            variable_name = str(step.get("name", "")).strip()
            if variable_name:
                if not variable_name.isidentifier():
                    raise ValueError("Browser text variable name must be a valid identifier")
            return {"text": text, "truncated": truncated, "variable": variable_name or None}

        if action == "browser_assert_text":
            expected = render(step.get("text", ""))
            if not isinstance(expected, str):
                raise ValueError("Browser assertion text must be text")
            actual = self._locator(step, render).inner_text(timeout=timeout)
            if step.get("exact", False):
                matched = actual == expected
            else:
                matched = expected in actual
            if not matched:
                raise AssertionError(
                    f"Browser text assertion failed for selector {self._selector(step, render)!r}"
                )
            return {"matched": True}

        raise ValueError(f"Unsupported browser action: {action}")

    def close_browser(self) -> None:
        context, browser = self._context, self._browser
        self._context = None
        self._browser = None
        self._page = None
        try:
            if context is not None:
                context.close()
        finally:
            if browser is not None:
                browser.close()

    def close(self) -> None:
        try:
            self.close_browser()
        finally:
            if self._playwright is not None:
                playwright, self._playwright = self._playwright, None
                playwright.stop()
