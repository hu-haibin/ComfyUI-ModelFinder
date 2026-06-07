import csv
from pathlib import Path

import pytest

from ModelFinderV2_6.repositories.search_cache_repository import SearchCacheRepository
from ModelFinderV2_6.search_provider import BingSearchProvider, SearchProviderResult
from ModelFinderV2_6.search_service import SearchService
from ModelFinderV2_6.workflow_report_service import (
    COL_ACTUAL_SEARCH_TERM,
    COL_HIT_LINK,
    COL_HIT_SOURCE,
    COL_HIT_TITLE,
    COL_MATCH_REASON,
    COL_NORMALIZED_FILE,
    COL_ORIGINAL_FILE,
    COL_REMOTE_FILE,
    COL_SUSPICIOUS,
    MISSING_FILES_HEADERS,
)


pytestmark = pytest.mark.unit


class _FakeElement:
    def __init__(self, *, text="", href="", click_callback=None):
        self.text = text
        self._href = href
        self._click_callback = click_callback
        self.inputs = []
        self.cleared = False

    def attr(self, name):
        if name == "href":
            return self._href
        return ""

    def clear(self):
        self.cleared = True

    def input(self, value):
        self.inputs.append(value)

    def click(self):
        if self._click_callback is not None:
            self._click_callback()


class _FakeResultsContainer:
    def __init__(self, *, first_link=None, secondary_links=None):
        self.first_link = first_link
        self.secondary_links = secondary_links or []

    def ele(self, locator, **kwargs):
        if locator == "xpath:.//h2/a":
            return self.first_link
        return None

    def eles(self, locator):
        if "liblib.art" in locator:
            return list(self.secondary_links)
        return []


class _FakeBrowserAdapter:
    def __init__(self, *, current_url="", results_container=None):
        self.current_url = current_url
        self.results_container = results_container
        self.search_box = _FakeElement()
        self.search_button = _FakeElement()
        self.visited = []
        self.closed = False
        self.back_calls = 0

    def visit(self, url, timeout=15):
        self.visited.append((url, timeout))

    def sleep(self, minimum, maximum):
        return None

    def find(self, locator, *, timeout=None, root=None):
        if root is not None:
            return root.ele(locator)
        if locator == "#sb_form_q":
            return self.search_box
        if locator == "#search_icon":
            return self.search_button
        if locator == 'xpath://button[@type="submit"]':
            return None
        if locator == "#b_results":
            return self.results_container
        return None

    def find_all(self, locator, *, root=None):
        if root is not None:
            return root.eles(locator)
        return []

    def clear_and_input(self, element, value):
        element.clear()
        element.input(value)

    def click(self, element):
        element.click()

    def run_js(self, script):
        return None

    def wait_for_load_start(self, timeout=10):
        return None

    def back(self):
        self.back_calls += 1

    def close(self):
        self.closed = True


def _write_missing_csv(csv_path: Path, file_name: str = "demo.safetensors") -> None:
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=MISSING_FILES_HEADERS)
        writer.writeheader()
        writer.writerow(
            {
                MISSING_FILES_HEADERS[0]: "1",
                MISSING_FILES_HEADERS[1]: "1",
                MISSING_FILES_HEADERS[2]: "CheckpointLoaderSimple",
                MISSING_FILES_HEADERS[3]: file_name,
                MISSING_FILES_HEADERS[4]: "",
                MISSING_FILES_HEADERS[5]: "",
                MISSING_FILES_HEADERS[6]: "",
                MISSING_FILES_HEADERS[7]: "",
            }
        )


def test_search_service_delegates_search_execution_to_provider(tmp_path: Path) -> None:
    csv_path = tmp_path / "missing.csv"
    _write_missing_csv(csv_path)

    created_providers = []

    class _FakeProvider:
        def __init__(self, chrome_path):
            self.chrome_path = chrome_path
            self.calls = []
            self.closed = False

        def search(self, search_candidates):
            self.calls.append(list(search_candidates))
            return SearchProviderResult(
                found_url="https://huggingface.co/foo/bar/blob/main/demo.safetensors",
                result_site="hf",
                status="已处理",
                executed_query='site:huggingface.co "demo.safetensors"',
                hit_title="Demo safetensors",
                hit_link="https://huggingface.co/foo/bar/blob/main/demo.safetensors",
            )

        def close(self):
            self.closed = True

    def _provider_factory(chrome_path):
        provider = _FakeProvider(chrome_path)
        created_providers.append(provider)
        return provider

    html_path = tmp_path / "missing.html"

    def _html_builder(_csv_path):
        html_path.write_text("<html></html>", encoding="utf-8")
        return str(html_path)

    service = SearchService(
        process_name_for_search=lambda name: {"mapped": name, "final_search_term": name},
        contains_chinese=lambda text: False,
        chrome_path_finder=lambda: "C:/Chrome/chrome.exe",
        html_view_builder=_html_builder,
        search_provider_factory=_provider_factory,
        search_cache_repository=SearchCacheRepository(results_folder_provider=lambda: str(tmp_path / "results")),
    )

    result = service.search_model_links(str(csv_path))

    assert result.success
    assert result.code == "html_ready"
    assert created_providers[0].chrome_path == "C:/Chrome/chrome.exe"
    assert len(created_providers[0].calls) == 1
    assert created_providers[0].closed is True

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        row = next(csv.DictReader(handle))
    assert row[MISSING_FILES_HEADERS[5]] == "https://huggingface.co/foo/bar/resolve/main/demo.safetensors"
    assert row[MISSING_FILES_HEADERS[6]] == "https://hf-mirror.com/foo/bar/resolve/main/demo.safetensors"
    assert row[MISSING_FILES_HEADERS[4]] == "已处理"
    assert row[COL_ORIGINAL_FILE] == "demo.safetensors"
    assert row[COL_NORMALIZED_FILE] == "demo.safetensors"
    assert row[COL_ACTUAL_SEARCH_TERM] == 'site:huggingface.co "demo.safetensors"'
    assert row[COL_HIT_SOURCE] == "HuggingFace"
    assert row[COL_HIT_TITLE] == "Demo safetensors"
    assert row[COL_HIT_LINK] == "https://huggingface.co/foo/bar/blob/main/demo.safetensors"
    assert row[COL_REMOTE_FILE] == "demo.safetensors"
    assert row[COL_MATCH_REASON]
    assert row[COL_SUSPICIOUS] == "否"


def test_bing_search_provider_returns_direct_hf_result() -> None:
    first_link = _FakeElement(text="hf", href="https://huggingface.co/foo/bar")
    results_container = _FakeResultsContainer(first_link=first_link)
    browser = _FakeBrowserAdapter(results_container=results_container)
    provider = BingSearchProvider(browser)

    result = provider.search(
        [
            {
                "search_site": "hf",
                "bing_url": "https://www.bing.com/?setlang=en-US",
                "site_query": 'site:huggingface.co "demo"',
            }
        ]
    )

    assert result == SearchProviderResult(
        found_url="https://huggingface.co/foo/bar",
        result_site="hf",
        status="已处理",
        executed_query='site:huggingface.co "demo"',
        hit_title="hf",
        hit_link="https://huggingface.co/foo/bar",
    )
    assert browser.search_box.cleared is True
    assert browser.search_box.inputs == ['site:huggingface.co "demo"']


def test_bing_search_provider_resolves_liblib_secondary_link_when_first_result_is_redirect() -> None:
    direct_link = _FakeElement(href="https://www.liblib.art/modelinfo/demo")
    first_link = _FakeElement(text="redirect", href="https://www.bing.com/ck/a")
    results_container = _FakeResultsContainer(first_link=first_link, secondary_links=[direct_link])
    browser = _FakeBrowserAdapter(results_container=results_container)
    provider = BingSearchProvider(browser)

    result = provider.search(
        [
            {
                "search_site": "liblib",
                "bing_url": "https://www.bing.com/?setlang=en-US",
                "site_query": 'site:liblib.art "demo"',
            }
        ]
    )

    assert result == SearchProviderResult(
        found_url="https://www.liblib.art/modelinfo/demo",
        result_site="liblib",
        status="已处理",
        executed_query='site:liblib.art "demo"',
        hit_title="redirect",
        hit_link="https://www.liblib.art/modelinfo/demo",
    )
    assert browser.back_calls == 0
