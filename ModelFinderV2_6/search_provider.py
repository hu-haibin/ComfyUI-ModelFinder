import logging
from dataclasses import dataclass
from typing import Iterable, List

from .adapters.browser_adapter import BrowserAdapter, BrowserAdapterError


logger = logging.getLogger(__name__)


@dataclass
class SearchProviderResult:
    found_url: str = ""
    result_site: str = ""
    status: str = ""


class BingSearchProvider:
    STATUS_PROCESSED = "\u5df2\u5904\u7406"
    STATUS_NO_SEARCH_BOX = "\u641c\u7d22\u9519\u8bef(\u65e0\u641c\u7d22\u6846)"
    STATUS_NO_RESULT_AREA = "\u672a\u627e\u5230(\u65e0\u7ed3\u679c\u533a)"
    STATUS_NO_LINK = "\u672a\u627e\u5230(\u65e0\u94fe\u63a5)"
    STATUS_SEARCH_EXCEPTION = "\u641c\u7d22\u9519\u8bef(\u5f02\u5e38)"
    STATUS_NOT_FOUND_LIBLIB = "\u672a\u627e\u5230LibLib"
    STATUS_NOT_FOUND_HF = "\u672a\u627e\u5230HF"
    STATUS_NON_DIRECT_LIBLIB = "\u627e\u5230\u641c\u7d22\u94fe\u63a5\u4f46\u975e\u76f4\u63a5LibLib\u94fe\u63a5"
    STATUS_BROWSER_UNAVAILABLE = "\u641c\u7d22\u9519\u8bef(\u6d4f\u89c8\u5668\u4e0d\u53ef\u7528)"

    def __init__(self, browser_adapter: BrowserAdapter):
        self._browser = browser_adapter

    def close(self) -> None:
        self._browser.close()

    def search(self, search_candidates: Iterable[dict]) -> SearchProviderResult:
        candidates: List[dict] = list(search_candidates)
        if not candidates:
            return SearchProviderResult()

        result_site = candidates[0]["search_site"]
        status_text = (
            self.STATUS_NOT_FOUND_LIBLIB if result_site == "liblib" else self.STATUS_NOT_FOUND_HF
        )

        for search_candidate in candidates:
            candidate_site = search_candidate["search_site"]
            candidate_status = (
                self.STATUS_NOT_FOUND_LIBLIB if candidate_site == "liblib" else self.STATUS_NOT_FOUND_HF
            )

            try:
                self._browser.visit(search_candidate["bing_url"], timeout=15)
                self._browser.sleep(0.2, 0.5)

                search_box = self._browser.find("#sb_form_q", timeout=5)
                if not search_box:
                    candidate_status = self.STATUS_NO_SEARCH_BOX
                else:
                    self._browser.clear_and_input(search_box, search_candidate["site_query"])
                    self._browser.sleep(0.1, 0.25)

                    search_button = self._browser.find("#search_icon", timeout=3) or self._browser.find(
                        'xpath://button[@type="submit"]',
                        timeout=3,
                    )
                    if search_button:
                        self._browser.click(search_button)
                    else:
                        self._browser.run_js("document.querySelector('#sb_form').submit();")

                    self._browser.wait_for_load_start(timeout=10)
                    results_container = self._browser.find("#b_results", timeout=10)

                    if not results_container:
                        candidate_status = self.STATUS_NO_RESULT_AREA
                    else:
                        first_link = self._browser.find("xpath:.//h2/a", root=results_container)
                        if not first_link:
                            candidate_status = self.STATUS_NO_LINK
                        else:
                            candidate_url = (first_link.attr("href") or "").strip()
                            logger.info(
                                "Found (%s): %r -> %s",
                                candidate_site,
                                first_link.text,
                                candidate_url,
                            )

                            if candidate_site == "liblib":
                                found_url, candidate_status = self._resolve_liblib_result(
                                    results_container,
                                    first_link,
                                    candidate_url,
                                )
                                if found_url:
                                    return SearchProviderResult(
                                        found_url=found_url,
                                        result_site=candidate_site,
                                        status=candidate_status,
                                    )
                            else:
                                if candidate_url and "huggingface.co" in candidate_url:
                                    return SearchProviderResult(
                                        found_url=candidate_url,
                                        result_site=candidate_site,
                                        status=self.STATUS_PROCESSED,
                                    )
                                candidate_status = self.STATUS_NOT_FOUND_HF
            except BrowserAdapterError:
                return SearchProviderResult(
                    found_url="",
                    result_site=result_site,
                    status=self.STATUS_BROWSER_UNAVAILABLE,
                )
            except Exception:
                logger.error(
                    "Error searching for %r via %s",
                    search_candidate.get("site_query", ""),
                    candidate_site,
                    exc_info=True,
                )
                candidate_status = self.STATUS_SEARCH_EXCEPTION

            status_text = candidate_status

        return SearchProviderResult(found_url="", result_site=result_site, status=status_text)

    def _resolve_liblib_result(self, results_container, first_link, candidate_url: str):
        if candidate_url and "liblib.art" in candidate_url:
            if "bing.com" in candidate_url or "search" in candidate_url.lower():
                liblib_url = ""
                try:
                    self._browser.click(first_link)
                    self._browser.wait_for_load_start(timeout=10)
                    current_url = self._browser.current_url
                    if "liblib.art" in current_url:
                        liblib_url = current_url
                    else:
                        self._browser.back()
                        for item in self._browser.find_all(
                            "xpath:.//a[contains(@href, 'liblib.art')]",
                            root=results_container,
                        ):
                            direct_url = (item.attr("href") or "").strip()
                            if direct_url and "liblib.art" in direct_url:
                                liblib_url = direct_url
                                break
                except Exception:
                    logger.debug("Failed to resolve LibLib redirect URL.", exc_info=True)

                if liblib_url:
                    return liblib_url, self.STATUS_PROCESSED
                return candidate_url, self.STATUS_NON_DIRECT_LIBLIB

            return candidate_url, self.STATUS_PROCESSED

        for item in self._browser.find_all("xpath:.//a[contains(@href, 'liblib.art')]", root=results_container):
            direct_url = (item.attr("href") or "").strip()
            if direct_url and "liblib.art" in direct_url:
                return direct_url, self.STATUS_PROCESSED

        return "", self.STATUS_NOT_FOUND_LIBLIB
