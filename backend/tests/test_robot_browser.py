import sys
import types

import pytest

from robot.worker import RobotExecution


class FakeLocator:
    def __init__(self, selector: str, calls: list[tuple]) -> None:
        self.selector = selector
        self.calls = calls

    def click(self, **kwargs):
        self.calls.append(("click", self.selector, kwargs))

    def fill(self, value, **kwargs):
        self.calls.append(("fill", self.selector, value, kwargs))

    def press(self, key, **kwargs):
        self.calls.append(("press", self.selector, key, kwargs))

    def select_option(self, **kwargs):
        self.calls.append(("select", self.selector, kwargs))
        return [kwargs["value"]]

    def wait_for(self, **kwargs):
        self.calls.append(("wait", self.selector, kwargs))

    def inner_text(self, **kwargs):
        self.calls.append(("inner_text", self.selector, kwargs))
        return "Automation ready"


class FakePage:
    def __init__(self, calls: list[tuple]) -> None:
        self.calls = calls
        self.url = "about:blank"
        self.keyboard = types.SimpleNamespace(
            press=lambda key: calls.append(("keyboard_press", key))
        )

    def locator(self, selector):
        return FakeLocator(selector, self.calls)

    def goto(self, url, **kwargs):
        self.calls.append(("goto", url, kwargs))
        self.url = url
        return types.SimpleNamespace(status=200)

    def set_default_timeout(self, timeout):
        self.calls.append(("default_timeout", timeout))

    def set_default_navigation_timeout(self, timeout):
        self.calls.append(("navigation_timeout", timeout))


class FakeContext:
    def __init__(self, page: FakePage, calls: list[tuple]) -> None:
        self.page = page
        self.calls = calls

    def new_page(self):
        return self.page

    def close(self):
        self.calls.append(("context_close",))


class FakeBrowser:
    def __init__(self, page: FakePage, calls: list[tuple]) -> None:
        self.page = page
        self.calls = calls

    def new_context(self, **kwargs):
        self.calls.append(("new_context", kwargs))
        return FakeContext(self.page, self.calls)

    def close(self):
        self.calls.append(("browser_close",))


class FakePlaywright:
    def __init__(self, calls: list[tuple]) -> None:
        self.calls = calls
        self.page = FakePage(calls)
        self.browser = FakeBrowser(self.page, calls)
        self.chromium = types.SimpleNamespace(launch=self.launch)
        self.stopped = False

    def launch(self, **kwargs):
        self.calls.append(("launch", kwargs))
        return self.browser

    def stop(self):
        self.stopped = True


@pytest.fixture()
def fake_playwright(monkeypatch):
    calls: list[tuple] = []
    playwright = FakePlaywright(calls)
    sync_api = types.ModuleType("playwright.sync_api")
    sync_api.sync_playwright = lambda: types.SimpleNamespace(start=lambda: playwright)
    package = types.ModuleType("playwright")
    package.__path__ = []
    monkeypatch.setitem(sys.modules, "playwright", package)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", sync_api)
    return playwright, calls


def test_browser_workflow_runs_and_saves_web_text_as_variable(fake_playwright):
    playwright, calls = fake_playwright
    execution = RobotExecution()

    output = execution.execute({
        "steps": [
            {"action": "browser_launch", "browser": "chrome"},
            {"action": "browser_navigate", "url": "https://example.com"},
            {"action": "browser_fill", "selector": "#email", "text": "robot@example.com"},
            {"action": "browser_get_text", "selector": "h1", "name": "heading"},
            {"action": "set_variable", "name": "result", "value": "${heading}"},
        ],
    })

    assert output["variables"] == {"heading": "Automation ready", "result": "Automation ready"}
    assert output["steps"][1]["output"]["status"] == 200
    assert ("launch", {"channel": "chrome", "headless": False, "timeout": 30_000}) in calls
    assert ("fill", "#email", "robot@example.com", {"timeout": 15_000}) in calls
    assert ("browser_close",) in calls
    assert playwright.stopped


def test_edge_can_run_headless_and_unsafe_urls_are_rejected(fake_playwright):
    _, calls = fake_playwright
    execution = RobotExecution()
    execution.execute_step({"action": "browser_launch", "browser": "edge", "headless": True})

    with pytest.raises(ValueError, match="http\\(s\\) URL"):
        execution.execute_step({"action": "browser_navigate", "url": "javascript:alert(1)"})

    assert ("launch", {"channel": "msedge", "headless": True, "timeout": 30_000}) in calls
    execution.browser.close()


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "file:///C:/Windows/win.ini",
        "https://user:password@example.com",
        "/relative/path",
    ],
)
def test_browser_navigation_rejects_non_http_or_credential_urls(fake_playwright, url):
    _, calls = fake_playwright
    execution = RobotExecution()
    execution.execute_step({"action": "browser_launch", "browser": "chrome"})

    with pytest.raises(ValueError, match="http\\(s\\) URL"):
        execution.execute_step({"action": "browser_navigate", "url": url})

    assert not any(call[0] == "goto" for call in calls)
    execution.browser.close()


def test_browser_assert_text_fails_when_expected_content_is_missing(fake_playwright):
    execution = RobotExecution()
    execution.execute_step({"action": "browser_launch", "browser": "chrome"})

    with pytest.raises(AssertionError, match="text assertion failed"):
        execution.execute_step({
            "action": "browser_assert_text",
            "selector": "#status",
            "text": "Completed",
        })

    execution.browser.close()


def test_browser_resources_are_closed_when_workflow_step_fails(fake_playwright):
    playwright, calls = fake_playwright
    execution = RobotExecution()

    with pytest.raises(ValueError, match="Unsupported Windows Robot action"):
        execution.execute({
            "steps": [
                {"action": "browser_launch", "browser": "chrome"},
                {"action": "not_allowed"},
            ],
        })

    assert ("context_close",) in calls
    assert ("browser_close",) in calls
    assert playwright.stopped
