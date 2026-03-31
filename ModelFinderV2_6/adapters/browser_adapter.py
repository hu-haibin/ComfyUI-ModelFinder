import random
import time
from typing import Callable, Optional

try:
    from DrissionPage import ChromiumOptions, ChromiumPage
except ImportError:
    ChromiumOptions = None
    ChromiumPage = None


class BrowserAdapterError(RuntimeError):
    pass


class BrowserAdapter:
    def __init__(
        self,
        chrome_path: str,
        options_factory=None,
        page_factory=None,
        sleeper: Callable[[float], None] = time.sleep,
        delay_generator: Callable[[float, float], float] = random.uniform,
    ):
        self._chrome_path = (chrome_path or "").strip()
        self._options_factory = options_factory or ChromiumOptions
        self._page_factory = page_factory or ChromiumPage
        self._sleeper = sleeper
        self._delay_generator = delay_generator
        self._page = None

    def open(self):
        if self._page is not None:
            return self._page

        if not self._chrome_path:
            raise BrowserAdapterError("Chrome path is required.")
        if self._options_factory is None or self._page_factory is None:
            raise BrowserAdapterError("Browser dependencies are unavailable.")

        options = self._options_factory().set_browser_path(self._chrome_path)
        options.set_argument("--disable-infobars").set_argument("--no-sandbox").set_argument("--start-maximized")
        self._page = self._page_factory(options)
        return self._page

    def close(self) -> None:
        if self._page is None:
            return
        try:
            self._page.quit()
        finally:
            self._page = None

    def visit(self, url: str, timeout: int = 15) -> None:
        self.open().get(url, timeout=timeout)

    def sleep(self, minimum: float, maximum: float) -> None:
        self._sleeper(self._delay_generator(minimum, maximum))

    def find(self, locator: str, *, timeout: Optional[int] = None, root=None):
        target = root or self.open()
        kwargs = {}
        if timeout is not None:
            kwargs["timeout"] = timeout
        return target.ele(locator, **kwargs)

    def find_all(self, locator: str, *, root=None):
        target = root or self.open()
        return target.eles(locator)

    def clear_and_input(self, element, value: str) -> None:
        element.clear()
        element.input(value)

    def click(self, element) -> None:
        element.click()

    def run_js(self, script: str) -> None:
        self.open().run_js(script)

    def wait_for_load_start(self, timeout: int = 10) -> None:
        self.open().wait.load_start(timeout=timeout)

    def back(self) -> None:
        self.open().back()

    @property
    def current_url(self) -> str:
        if self._page is None:
            return ""
        return (self._page.url or "").strip()
