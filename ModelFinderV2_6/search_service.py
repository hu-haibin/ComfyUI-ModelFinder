import json
import logging
import os
import random
import time
from typing import Callable, Optional

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    from DrissionPage import ChromiumOptions, ChromiumPage
except ImportError:
    ChromiumOptions = None
    ChromiumPage = None

from .file_manager import get_results_folder
from .utils import create_html_view, find_chrome_path, get_mirror_link


logger = logging.getLogger(__name__)


class SearchService:
    def __init__(
        self,
        process_name_for_search: Callable[[str], dict],
        contains_chinese: Callable[[str], bool],
        chrome_path_provider: Optional[Callable[[], str]] = None,
    ):
        self._process_name_for_search = process_name_for_search
        self._contains_chinese = contains_chinese
        self._chrome_path_provider = chrome_path_provider

    @staticmethod
    def _read_path_from_provider(provider: Optional[Callable[[], str]]) -> str:
        if provider is None:
            return ""

        try:
            value = provider()
        except Exception:
            logger.warning("Path provider failed.", exc_info=True)
            return ""

        return (value or "").strip()

    def get_search_url(self, name_for_decision, term_for_query_embedding, node_type=None):
        logger.debug(
            f"Generating search URL. Decision Name: '{name_for_decision}', "
            f"Query Embedding Term: '{term_for_query_embedding}', Node Type: {node_type}"
        )

        if name_for_decision == "ip-adapter.bin" and node_type == "InstantIDModelLoader":
            logger.debug("Applying special rule for ip-adapter.bin + InstantIDModelLoader")
            return ("https://www.bing.com/?setlang=en-US", 'site:huggingface.co "ip-adapter.bin InstantID"')

        if self._contains_chinese(name_for_decision):
            logger.debug(
                f"Decision name '{name_for_decision}' suggests Chinese model, "
                f"using LibLib search with query term '{term_for_query_embedding}'."
            )
            return "https://www.bing.com/?setlang=en-US", f'site:liblib.art "{term_for_query_embedding}"'

        logger.debug(
            f"Decision name '{name_for_decision}' suggests non-Chinese model, "
            f"using Hugging Face search with query term '{term_for_query_embedding}'."
        )
        return "https://www.bing.com/?setlang=en-US", f'site:huggingface.co "{term_for_query_embedding}"'

    def get_search_candidates(self, name_for_decision, term_for_query_embedding, node_type=None):
        bing_url, primary_query = self.get_search_url(name_for_decision, term_for_query_embedding, node_type)
        primary_site = "liblib" if "site:liblib.art" in primary_query else "hf"

        if name_for_decision == "ip-adapter.bin" and node_type == "InstantIDModelLoader":
            return [{"search_site": "hf", "bing_url": bing_url, "site_query": primary_query}]

        normalized_term = (term_for_query_embedding or "").strip()
        term_candidates = []
        if normalized_term:
            term_candidates.append(normalized_term)
            stem, _ = os.path.splitext(normalized_term)
            stem = stem.strip()
            if stem and stem != normalized_term:
                term_candidates.append(stem)
        else:
            term_candidates.append(normalized_term)

        def build_query(search_site, query_term):
            if search_site == "liblib":
                return f'site:liblib.art "{query_term}"'
            return f'site:huggingface.co "{query_term}"'

        candidates = []
        seen = set()
        site_order = [primary_site, "hf" if primary_site == "liblib" else "liblib"]
        for search_site in site_order:
            for query_term in term_candidates:
                site_query = (
                    primary_query
                    if (search_site == primary_site and query_term == normalized_term)
                    else build_query(search_site, query_term)
                )
                if not site_query:
                    continue
                candidate_key = (search_site, site_query)
                if candidate_key in seen:
                    continue
                seen.add(candidate_key)
                candidates.append(
                    {
                        "search_site": search_site,
                        "bing_url": bing_url,
                        "site_query": site_query,
                    }
                )

        return candidates

    def _get_search_cache_path(self):
        try:
            cache_root = get_results_folder()
            os.makedirs(cache_root, exist_ok=True)
            return os.path.join(cache_root, "search_cache.json")
        except Exception:
            return os.path.join(os.path.dirname(os.path.abspath(__file__)), "search_cache.json")

    def _load_search_cache(self):
        cache_path = self._get_search_cache_path()
        if not os.path.exists(cache_path):
            return {}

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            logger.warning("Failed to load search cache, cache will be recreated.", exc_info=True)
        return {}

    def _save_search_cache(self, cache_data):
        cache_path = self._get_search_cache_path()
        tmp_path = f"{cache_path}.tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, cache_path)
            return True
        except Exception:
            logger.warning("Failed to save search cache.", exc_info=True)
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
            return False

    @staticmethod
    def _build_search_cache_key(search_site, search_term_query, node_type):
        site = "liblib" if search_site == "liblib" else "hf"
        normalized_term = (search_term_query or "").strip().lower()
        normalized_node_type = (node_type or "").strip().lower()
        return f"{site}|{normalized_term}|{normalized_node_type}"

    @staticmethod
    def is_cache_entry_valid(cache_entry):
        if not isinstance(cache_entry, dict):
            return False

        updated_at = cache_entry.get("updated_at")
        if not isinstance(updated_at, (int, float)):
            return False

        cached_url = (cache_entry.get("url") or "").strip()
        if not cached_url:
            return False

        ttl_seconds = 30 * 24 * 3600
        return (time.time() - float(updated_at)) <= ttl_seconds

    @staticmethod
    def _should_cache_result(found_url, status):
        del status
        return bool((found_url or "").strip())

    @staticmethod
    def _apply_search_result_to_row(df, df_idx, search_site, found_url, status):
        col_status = "\u72b6\u6001"
        col_download = "\u4e0b\u8f7d\u94fe\u63a5"
        col_mirror = "\u955c\u50cf\u94fe\u63a5"
        col_search = "\u641c\u7d22\u94fe\u63a5"

        found_url = (found_url or "").strip()
        status = (status or "").strip()

        if search_site == "liblib":
            df.loc[df_idx, col_download] = ""
            df.loc[df_idx, col_mirror] = ""
            df.loc[df_idx, col_search] = found_url
            df.loc[df_idx, col_status] = status or ("\u5df2\u5904\u7406" if found_url else "\u672a\u627e\u5230LibLib")
            return

        df.loc[df_idx, col_search] = ""
        if found_url:
            resolved_url = found_url.replace("/blob/", "/resolve/") if "/blob/" in found_url else found_url
            df.loc[df_idx, col_download] = resolved_url
            df.loc[df_idx, col_mirror] = get_mirror_link(found_url)
            df.loc[df_idx, col_status] = status or "\u5df2\u5904\u7406"
        else:
            df.loc[df_idx, col_download] = ""
            df.loc[df_idx, col_mirror] = ""
            df.loc[df_idx, col_status] = status or "\u672a\u627e\u5230HF"

    def search_model_links(self, csv_file, progress_callback=None):
        logger.info(f"Starting model link search for CSV: {csv_file}")
        if pd is None or ChromiumPage is None or ChromiumOptions is None:
            logger.error("Search cannot proceed: Missing pandas or DrissionPage.")
            return False

        col_status = "\u72b6\u6001"
        col_download = "\u4e0b\u8f7d\u94fe\u63a5"
        col_mirror = "\u955c\u50cf\u94fe\u63a5"
        col_search = "\u641c\u7d22\u94fe\u63a5"
        col_file = "\u6587\u4ef6\u540d"
        col_node_type = "\u8282\u70b9\u7c7b\u578b"

        status_processed = "\u5df2\u5904\u7406"
        status_no_search_box = "\u641c\u7d22\u9519\u8bef(\u65e0\u641c\u7d22\u6846)"
        status_no_result_area = "\u672a\u627e\u5230(\u65e0\u7ed3\u679c\u533a)"
        status_no_link = "\u672a\u627e\u5230(\u65e0\u94fe\u63a5)"
        status_search_exception = "\u641c\u7d22\u9519\u8bef(\u5f02\u5e38)"
        status_not_found_liblib = "\u672a\u627e\u5230LibLib"
        status_not_found_hf = "\u672a\u627e\u5230HF"
        status_non_direct_liblib = "\u627e\u5230\u641c\u7d22\u94fe\u63a5\u4f46\u975e\u76f4\u63a5LibLib\u94fe\u63a5"
        status_browser_unavailable = "\u641c\u7d22\u9519\u8bef(\u6d4f\u89c8\u5668\u4e0d\u53ef\u7528)"

        try:
            string_cols = [col_status, col_download, col_mirror, col_search, col_file, col_node_type]
            df = pd.read_csv(
                csv_file,
                encoding="utf-8-sig",
                dtype={col: str for col in string_cols},
                keep_default_na=False,
                na_values=[""],
            )
            for col in string_cols:
                if col not in df.columns:
                    df[col] = ""
                df[col] = df[col].fillna("").astype(str)

            save_interval = 20
            rows_since_save = 0
            cache = self._load_search_cache()
            cache_dirty = False

            grouped_tasks = {}
            cache_hits = 0

            for index, row in df.iterrows():
                original_name_from_csv = row.get(col_file, "")
                if not original_name_from_csv:
                    continue

                status = row.get(col_status, "")
                hf_link = row.get(col_download, "")
                search_or_liblib_link = row.get(col_search, "")
                is_processed = status == status_processed
                has_valid_link = hf_link or (
                    search_or_liblib_link.startswith("http") and "liblib.art" in search_or_liblib_link
                )
                if is_processed and has_valid_link:
                    continue

                processed_names = self._process_name_for_search(original_name_from_csv)
                search_site = "liblib" if self._contains_chinese(processed_names["mapped"]) else "hf"
                node_type = row.get(col_node_type, "")
                cache_key = self._build_search_cache_key(search_site, processed_names["final_search_term"], node_type)

                cached_entry = cache.get(cache_key)
                if self.is_cache_entry_valid(cached_entry):
                    cached_result_site = cached_entry.get("result_site") or cached_entry.get("site") or search_site
                    self._apply_search_result_to_row(
                        df,
                        index,
                        cached_result_site,
                        cached_entry.get("url", ""),
                        cached_entry.get("status", ""),
                    )
                    cache_hits += 1
                    rows_since_save += 1
                    continue
                if cached_entry is not None:
                    cache.pop(cache_key, None)
                    cache_dirty = True

                if cache_key not in grouped_tasks:
                    grouped_tasks[cache_key] = {
                        "cache_key": cache_key,
                        "search_site": search_site,
                        "name_for_decision": processed_names["mapped"],
                        "search_term_query": processed_names["final_search_term"],
                        "node_type": node_type,
                        "original_name_csv": original_name_from_csv,
                        "df_indices": [index],
                    }
                else:
                    grouped_tasks[cache_key]["df_indices"].append(index)

            if rows_since_save >= save_interval:
                df.to_csv(csv_file, index=False, encoding="utf-8-sig")
                rows_since_save = 0

            search_tasks = list(grouped_tasks.values())
            if not search_tasks:
                logger.info(f"No keywords require searching. Cache hits={cache_hits}.")
                if progress_callback:
                    progress_callback(1, 1)
            else:
                logger.info(
                    f"Unique search tasks: {len(search_tasks)}, cache hits: {cache_hits}, "
                    f"deduped rows: {sum(len(t['df_indices']) for t in search_tasks)}"
                )

            chrome_path_to_use = self._read_path_from_provider(self._chrome_path_provider) or find_chrome_path()

            if not chrome_path_to_use and search_tasks:
                logger.error("Chrome browser not found. Cannot perform search.")
                for task in search_tasks:
                    for df_idx in task["df_indices"]:
                        self._apply_search_result_to_row(df, df_idx, task["search_site"], "", status_browser_unavailable)
                        rows_since_save += 1
            else:
                page = None
                if chrome_path_to_use and search_tasks:
                    co = ChromiumOptions().set_browser_path(chrome_path_to_use)
                    co.set_argument("--disable-infobars").set_argument("--no-sandbox").set_argument("--start-maximized")
                    try:
                        page = ChromiumPage(co)
                        logger.info("Browser page initialized.")
                    except Exception as browser_e:
                        logger.error(f"Failed to initialize browser: {browser_e}")
                        page = None

                if page:
                    total_tasks = len(search_tasks)
                    for i, task in enumerate(search_tasks):
                        if progress_callback:
                            progress_callback(i + 1, total_tasks)
                        logger.info(
                            f"Searching ({i + 1}/{total_tasks}): Query='{task['search_term_query']}' "
                            f"(Original: '{task['original_name_csv']}')"
                        )

                        found_url = ""
                        result_site = task["search_site"]
                        status_text = status_not_found_liblib if task["search_site"] == "liblib" else status_not_found_hf
                        search_candidates = self.get_search_candidates(
                            task["name_for_decision"],
                            task["search_term_query"],
                            task["node_type"],
                        )

                        for search_candidate in search_candidates:
                            candidate_site = search_candidate["search_site"]
                            candidate_status = (
                                status_not_found_liblib if candidate_site == "liblib" else status_not_found_hf
                            )

                            try:
                                page.get(search_candidate["bing_url"], timeout=15)
                                time.sleep(random.uniform(0.2, 0.5))

                                search_box = page.ele("#sb_form_q", timeout=5)
                                if not search_box:
                                    candidate_status = status_no_search_box
                                else:
                                    search_box.clear()
                                    search_box.input(search_candidate["site_query"])
                                    time.sleep(random.uniform(0.1, 0.25))

                                    s_button = page.ele("#search_icon", timeout=3) or page.ele(
                                        'xpath://button[@type="submit"]',
                                        timeout=3,
                                    )
                                    if s_button:
                                        s_button.click()
                                    else:
                                        page.run_js("document.querySelector('#sb_form').submit();")

                                    page.wait.load_start(timeout=10)
                                    results_container = page.ele("#b_results", timeout=10)

                                    if not results_container:
                                        candidate_status = status_no_result_area
                                    else:
                                        first_link = results_container.ele("xpath:.//h2/a")
                                        if not first_link:
                                            candidate_status = status_no_link
                                        else:
                                            candidate_url = (first_link.attr("href") or "").strip()
                                            logger.info(
                                                f"Found ({candidate_site}): '{first_link.text}' -> {candidate_url}"
                                            )

                                            if candidate_site == "liblib":
                                                if candidate_url and "liblib.art" in candidate_url:
                                                    if "bing.com" in candidate_url or "search" in candidate_url.lower():
                                                        liblib_url = ""
                                                        try:
                                                            first_link.click()
                                                            page.wait.load_start(timeout=10)
                                                            current_url = (page.url or "").strip()
                                                            if "liblib.art" in current_url:
                                                                liblib_url = current_url
                                                            else:
                                                                page.back()
                                                                liblib_links = results_container.eles(
                                                                    "xpath:.//a[contains(@href, 'liblib.art')]"
                                                                )
                                                                for item in liblib_links:
                                                                    direct_url = (item.attr("href") or "").strip()
                                                                    if direct_url and "liblib.art" in direct_url:
                                                                        liblib_url = direct_url
                                                                        break
                                                        except Exception:
                                                            logger.debug(
                                                                "Failed to resolve LibLib redirect URL.",
                                                                exc_info=True,
                                                            )

                                                        if liblib_url:
                                                            found_url = liblib_url
                                                            candidate_status = status_processed
                                                        else:
                                                            found_url = candidate_url
                                                            candidate_status = status_non_direct_liblib
                                                    else:
                                                        found_url = candidate_url
                                                        candidate_status = status_processed
                                                else:
                                                    liblib_links = results_container.eles(
                                                        "xpath:.//a[contains(@href, 'liblib.art')]"
                                                    )
                                                    for item in liblib_links:
                                                        direct_url = (item.attr("href") or "").strip()
                                                        if direct_url and "liblib.art" in direct_url:
                                                            found_url = direct_url
                                                            break
                                                    candidate_status = (
                                                        status_processed if found_url else status_not_found_liblib
                                                    )
                                            else:
                                                if candidate_url and "huggingface.co" in candidate_url:
                                                    found_url = candidate_url
                                                    candidate_status = status_processed
                                                else:
                                                    candidate_status = status_not_found_hf
                            except Exception:
                                logger.error(
                                    f"Error searching for '{task['search_term_query']}' via {candidate_site}",
                                    exc_info=True,
                                )
                                candidate_status = status_search_exception

                            status_text = candidate_status
                            if found_url:
                                result_site = candidate_site
                                break

                        for df_idx in task["df_indices"]:
                            self._apply_search_result_to_row(df, df_idx, result_site, found_url, status_text)
                        rows_since_save += len(task["df_indices"])

                        if self._should_cache_result(found_url, status_text):
                            cache[task["cache_key"]] = {
                                "site": task["search_site"],
                                "result_site": result_site,
                                "url": found_url,
                                "status": status_text,
                                "updated_at": time.time(),
                            }
                            cache_dirty = True
                        elif task["cache_key"] in cache:
                            cache.pop(task["cache_key"], None)
                            cache_dirty = True

                        if rows_since_save >= save_interval:
                            df.to_csv(csv_file, index=False, encoding="utf-8-sig")
                            rows_since_save = 0

                        time.sleep(random.uniform(0.15, 0.35))

                    page.quit()
                elif search_tasks:
                    for task in search_tasks:
                        for df_idx in task["df_indices"]:
                            self._apply_search_result_to_row(df, df_idx, task["search_site"], "", status_browser_unavailable)
                            rows_since_save += 1

            df.to_csv(csv_file, index=False, encoding="utf-8-sig")
            if cache_dirty:
                self._save_search_cache(cache)

            html_file = create_html_view(csv_file)
            return html_file if html_file else True
        except Exception:
            logger.error(f"Critical error in search_model_links for {csv_file}", exc_info=True)
            return False
