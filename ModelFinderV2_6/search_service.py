import logging
import os
import time
from typing import Callable, Optional

try:
    import pandas as pd
except ImportError:
    pd = None

from .adapters.browser_adapter import BrowserAdapter
from .adapters.filesystem_adapter import FileSystemAdapter
from .operation_result import OperationResult
from .repositories.search_cache_repository import SearchCacheRepository
from .search_match_evidence import build_match_evidence
from .search_provider import BingSearchProvider
from .utils import create_html_view, find_chrome_path, get_mirror_link
from .workflow_report_service import (
    COL_ACTUAL_SEARCH_TERM,
    COL_CONFIDENCE,
    COL_DOWNLOAD,
    COL_FILE,
    COL_HIT_IDENTIFIER,
    COL_HIT_LINK,
    COL_HIT_SOURCE,
    COL_HIT_TITLE,
    COL_MATCH_REASON,
    COL_MIRROR,
    COL_NODE_TYPE,
    COL_NORMALIZED_FILE,
    COL_ORIGINAL_FILE,
    COL_REMOTE_FILE,
    COL_SEARCH,
    COL_STATUS,
    COL_SUSPICIOUS,
    COL_SUSPICIOUS_REASON,
)


logger = logging.getLogger(__name__)


class SearchService:
    def __init__(
        self,
        process_name_for_search: Callable[[str], dict],
        contains_chinese: Callable[[str], bool],
        chrome_path_provider: Optional[Callable[[], str]] = None,
        search_cache_repository: Optional[SearchCacheRepository] = None,
        chrome_path_finder: Callable[[], str] = find_chrome_path,
        html_view_builder: Callable[[str], str] = create_html_view,
        filesystem: Optional[FileSystemAdapter] = None,
        search_provider_factory: Optional[Callable[[str], object]] = None,
    ):
        self._process_name_for_search = process_name_for_search
        self._contains_chinese = contains_chinese
        self._chrome_path_provider = chrome_path_provider
        self._search_cache_repository = search_cache_repository or SearchCacheRepository()
        self._chrome_path_finder = chrome_path_finder
        self._html_view_builder = html_view_builder
        self._filesystem = filesystem or FileSystemAdapter()
        self._search_provider_factory = search_provider_factory or self._build_default_search_provider

    @staticmethod
    def _build_default_search_provider(chrome_path: str):
        return BingSearchProvider(BrowserAdapter(chrome_path))

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
            "Generating search URL. Decision Name: %r, Query Embedding Term: %r, Node Type: %s",
            name_for_decision,
            term_for_query_embedding,
            node_type,
        )

        if name_for_decision == "ip-adapter.bin" and node_type == "InstantIDModelLoader":
            return "https://www.bing.com/?setlang=en-US", 'site:huggingface.co "ip-adapter.bin InstantID"'

        if self._contains_chinese(name_for_decision):
            return "https://www.bing.com/?setlang=en-US", f'site:liblib.art "{term_for_query_embedding}"'

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
                    if search_site == primary_site and query_term == normalized_term
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
        return self._search_cache_repository.get_cache_path()

    def _load_search_cache(self):
        return self._search_cache_repository.load()

    def _save_search_cache(self, cache_data):
        return self._search_cache_repository.save(cache_data)

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
    def _build_row_evidence(task, result_site, found_url, provider_result=None, cached_evidence=None):
        provider_result = provider_result or object()
        evidence = {
            COL_ORIGINAL_FILE: task.get("original_name_csv", ""),
            COL_NORMALIZED_FILE: task.get("normalized_name", ""),
            COL_ACTUAL_SEARCH_TERM: getattr(provider_result, "executed_query", "") or task.get("search_term_query", ""),
        }

        if cached_evidence:
            evidence.update({key: (value or "") for key, value in dict(cached_evidence).items()})

        computed = build_match_evidence(
            original_name=task.get("original_name_csv", ""),
            normalized_name=task.get("normalized_name", ""),
            search_term=evidence[COL_ACTUAL_SEARCH_TERM],
            node_type=task.get("node_type", ""),
            result_site=result_site,
            hit_title=evidence.get(COL_HIT_TITLE) or getattr(provider_result, "hit_title", ""),
            hit_link=evidence.get(COL_HIT_LINK) or getattr(provider_result, "hit_link", ""),
            found_url=found_url,
        )

        for key, value in computed.items():
            evidence[key] = evidence.get(key) or value

        return {key: (value or "") for key, value in evidence.items()}

    @staticmethod
    def _apply_search_result_to_row(df, df_idx, search_site, found_url, status, evidence=None):
        col_status = COL_STATUS
        col_download = COL_DOWNLOAD
        col_mirror = COL_MIRROR
        col_search = COL_SEARCH

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

        if evidence:
            for key, value in evidence.items():
                if key not in df.columns:
                    df[key] = ""
                df.loc[df_idx, key] = (value or "").strip() if isinstance(value, str) else value

    def search_model_links(self, csv_file, progress_callback=None):
        logger.info("Starting model link search for CSV: %s", csv_file)
        if pd is None:
            logger.error("Search cannot proceed: Missing pandas.")
            return OperationResult(False, "Search dependencies are unavailable.", code="search_dependencies_missing")

        col_status = COL_STATUS
        col_download = COL_DOWNLOAD
        col_mirror = COL_MIRROR
        col_search = COL_SEARCH
        col_file = COL_FILE
        col_node_type = COL_NODE_TYPE

        status_processed = "\u5df2\u5904\u7406"
        status_browser_unavailable = "\u641c\u7d22\u9519\u8bef(\u6d4f\u89c8\u5668\u4e0d\u53ef\u7528)"

        try:
            string_cols = [
                col_status,
                col_download,
                col_mirror,
                col_search,
                col_file,
                col_node_type,
                COL_ORIGINAL_FILE,
                COL_NORMALIZED_FILE,
                COL_REMOTE_FILE,
                COL_ACTUAL_SEARCH_TERM,
                COL_HIT_SOURCE,
                COL_HIT_TITLE,
                COL_HIT_LINK,
                COL_HIT_IDENTIFIER,
                COL_MATCH_REASON,
                COL_CONFIDENCE,
                COL_SUSPICIOUS,
                COL_SUSPICIOUS_REASON,
            ]
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
                    row_evidence = self._build_row_evidence(
                        {
                            "original_name_csv": original_name_from_csv,
                            "normalized_name": processed_names["mapped"],
                            "search_term_query": processed_names["final_search_term"],
                            "node_type": node_type,
                        },
                        cached_result_site,
                        cached_entry.get("url", ""),
                        cached_evidence=cached_entry.get("evidence"),
                    )
                    self._apply_search_result_to_row(
                        df,
                        index,
                        cached_result_site,
                        cached_entry.get("url", ""),
                        cached_entry.get("status", ""),
                        row_evidence,
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
                        "normalized_name": processed_names["mapped"],
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
                logger.info("No keywords require searching. Cache hits=%s.", cache_hits)
                if progress_callback:
                    progress_callback(1, 1)
            else:
                logger.info(
                    "Unique search tasks: %s, cache hits: %s, deduped rows: %s",
                    len(search_tasks),
                    cache_hits,
                    sum(len(task["df_indices"]) for task in search_tasks),
                )

            chrome_path_to_use = self._read_path_from_provider(self._chrome_path_provider) or self._chrome_path_finder()

            if not chrome_path_to_use and search_tasks:
                logger.error("Chrome browser not found. Cannot perform search.")
                for task in search_tasks:
                    row_evidence = self._build_row_evidence(task, task["search_site"], "", None)
                    for df_idx in task["df_indices"]:
                        self._apply_search_result_to_row(
                            df,
                            df_idx,
                            task["search_site"],
                            "",
                            status_browser_unavailable,
                            row_evidence,
                        )
                        rows_since_save += 1
            else:
                search_provider = None
                if chrome_path_to_use and search_tasks:
                    try:
                        search_provider = self._search_provider_factory(chrome_path_to_use)
                        logger.info("Search provider initialized.")
                    except Exception as provider_error:
                        logger.error("Failed to initialize search provider: %s", provider_error, exc_info=True)
                        search_provider = None

                if search_provider:
                    total_tasks = len(search_tasks)
                    try:
                        for index, task in enumerate(search_tasks):
                            if progress_callback:
                                progress_callback(index + 1, total_tasks)
                            logger.info(
                                "Searching (%s/%s): Query=%r (Original=%r)",
                                index + 1,
                                total_tasks,
                                task["search_term_query"],
                                task["original_name_csv"],
                            )

                            search_candidates = self.get_search_candidates(
                                task["name_for_decision"],
                                task["search_term_query"],
                                task["node_type"],
                            )
                            provider_result = search_provider.search(search_candidates)
                            found_url = (provider_result.found_url or "").strip()
                            result_site = provider_result.result_site or task["search_site"]
                            status_text = provider_result.status or (
                                status_processed if found_url else status_browser_unavailable
                            )
                            row_evidence = self._build_row_evidence(task, result_site, found_url, provider_result)

                            for df_idx in task["df_indices"]:
                                self._apply_search_result_to_row(
                                    df,
                                    df_idx,
                                    result_site,
                                    found_url,
                                    status_text,
                                    row_evidence,
                                )
                            rows_since_save += len(task["df_indices"])

                            if self._should_cache_result(found_url, status_text):
                                cache[task["cache_key"]] = {
                                    "site": task["search_site"],
                                    "result_site": result_site,
                                    "url": found_url,
                                    "status": status_text,
                                    "evidence": row_evidence,
                                    "updated_at": time.time(),
                                }
                                cache_dirty = True
                            elif task["cache_key"] in cache:
                                cache.pop(task["cache_key"], None)
                                cache_dirty = True

                            if rows_since_save >= save_interval:
                                df.to_csv(csv_file, index=False, encoding="utf-8-sig")
                                rows_since_save = 0
                    finally:
                        if hasattr(search_provider, "close"):
                            search_provider.close()
                elif search_tasks:
                    for task in search_tasks:
                        row_evidence = self._build_row_evidence(task, task["search_site"], "", None)
                        for df_idx in task["df_indices"]:
                            self._apply_search_result_to_row(
                                df,
                                df_idx,
                                task["search_site"],
                                "",
                                status_browser_unavailable,
                                row_evidence,
                            )
                            rows_since_save += 1

            df.to_csv(csv_file, index=False, encoding="utf-8-sig")
            if cache_dirty:
                self._save_search_cache(cache)

            html_file = self._html_view_builder(csv_file)
            if html_file and self._filesystem.exists(html_file):
                return OperationResult(
                    True,
                    "Search finished and HTML output is ready.",
                    {"html_file": html_file},
                    code="html_ready",
                )

            if not search_tasks:
                return OperationResult(
                    True,
                    "No additional search was required.",
                    {"html_file": None},
                    code="nothing_to_search",
                )

            return OperationResult(
                False,
                "Search completed but no HTML output was generated.",
                {"html_file": None},
                code="completed_without_html",
            )
        except Exception:
            logger.error("Critical error in search_model_links for %s", csv_file, exc_info=True)
            return OperationResult(False, "Search failed unexpectedly.", code="search_failed")
