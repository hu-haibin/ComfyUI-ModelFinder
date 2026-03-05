import os
import json
import time
import csv
import re
import logging
import random

# Import utilities and file manager directly, as Model handles core logic
from .utils import get_mirror_link, create_html_view, find_chrome_path
from .file_manager import get_output_path, get_results_folder
from .model_config_manager import ModelConfigManager

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    from DrissionPage import ChromiumPage, ChromiumOptions
except ImportError:
    ChromiumPage = None


logger = logging.getLogger(__name__)

class AnalysisModel:
    """
    Handles the core logic for analyzing workflows, finding models,
    creating CSVs, searching links, and batch processing.
    处理分析工作流、查找模型、创建CSV、搜索链接和批量处理的核心逻辑。
    """

    def __init__(self, controller=None):
        """初始化分析模型"""
        self.controller = controller
        self.model_folder = None # Used to cache value
        
        # 初始化配置管理器
        self.config_manager = ModelConfigManager()
        
        # 使用配置管理器获取数据
        self.model_node_types = self.config_manager.get_model_node_types()
        self.node_model_indices = self.config_manager.get_node_model_indices()
        self.model_extensions = self.config_manager.get_model_extensions()
        
        logger.info("AnalysisModel initialized.")
        self._chinese_char_pattern = re.compile(r'[\u4e00-\u9fff]')
        if pd is None:
            logger.error("Pandas library is not installed, search/batch functionality might be affected.")
        if ChromiumPage is None:
            logger.error("DrissionPage library is not installed, search functionality will not work.")

    def _get_corrected_name_if_possible(self, original_name):
        if self.controller and hasattr(self.controller, 'irregular_names_model') and self.controller.irregular_names_model:
            corrected_name = self.controller.irregular_names_model.get_corrected_name(original_name)
            if corrected_name != original_name:
                logger.info(f"不规则名称映射应用 (Irregular name mapping applied)：'{original_name}' -> '{corrected_name}'")
            return corrected_name
        return original_name
    
    def _process_name_for_search(self, original_name):
        """
        Applies irregular name mapping and then removes Chinese prefix.
        返回一个字典包含处理过程中的各个阶段的名称。
        Returns a dictionary containing names at various stages of processing.
        'original': 原始输入名
        'mapped': 应用不规则映射后的名称
        'final_search_term': 应用映射并移除中文前缀后的最终搜索词
        """
        logger.debug(f"_process_name_for_search - 开始处理原始名称: '{original_name}'")
        
        # 应用不规则名称映射
        mapped_name = self._get_corrected_name_if_possible(original_name)
        logger.debug(f"_process_name_for_search - 映射后名称: '{mapped_name}'")
        
        # 移除中文前缀的逻辑 (直接从 mapped_name 处理)
        name_after_prefix_removal = mapped_name # 默认为映射后的名称
        if '_' in mapped_name:
            parts = mapped_name.split('_', 1)
            # (这里的特殊保留逻辑可以根据需要调整或简化)
            if len(parts) > 1:
                last_part_of_mapped = parts[-1]
                if len(last_part_of_mapped) <= 5 and not self._contains_chinese(last_part_of_mapped):
                    logger.debug(f"_process_name_for_search - 保留完整名称 (特殊后缀): '{mapped_name}'")
                    pass # 保留 mapped_name
                else: # 尝试移除前缀
                    prefix_pattern = re.compile(r"^[\u4e00-\u9fa5]+")
                    if re.search(r"^[\u4e00-\u9fa5]", mapped_name):
                        temp_name = re.sub(prefix_pattern, "", mapped_name).strip()
                        name_after_prefix_removal = re.sub(r"^[-_|\s]+", "", temp_name).strip()
                        logger.debug(f"_process_name_for_search - 移除中文前缀: '{mapped_name}' -> '{name_after_prefix_removal}'")
            # 如果没有下划线，但以中文开头
            elif re.search(r"^[\u4e00-\u9fa5]", mapped_name):
                 prefix_pattern = re.compile(r"^[\u4e00-\u9fa5]+")
                 temp_name = re.sub(prefix_pattern, "", mapped_name).strip()
                 name_after_prefix_removal = re.sub(r"^[-_|\s]+", "", temp_name).strip()
                 logger.debug(f"_process_name_for_search - 移除中文前缀: '{mapped_name}' -> '{name_after_prefix_removal}'")

        final_search_term = name_after_prefix_removal
        
        logger.debug(f"Name processing for search: Original='{original_name}', Mapped='{mapped_name}', FinalSearchTerm='{final_search_term}'")
        return {
            'original': original_name,
            'mapped': mapped_name, # 用于判断搜索策略 (HF/LibLib) 和特殊规则
            'final_search_term': final_search_term # 用于搜索引擎查询中的关键词
        }

    def remove_chinese_prefix(self, filename):
        """
        Removes ONLY the Chinese prefix from a filename, if it exists at the beginning.
        特殊处理：如果是类似"基础算法_F.1"这样的特殊格式，保留完整文件名。
        仅当文件名以中文开头时移除中文前缀。
        Special handling: If it's a special format like "基础算法_F.1", keep the full filename.
        """
        # 首先应用不规则名称映射
        # First, apply irregular name mapping
        filename_after_correction = self._get_corrected_name_if_possible(filename)

        if '_' in filename_after_correction:
            parts = filename_after_correction.split('_', 1) # 只分割一次，处理 "中文前缀_英文名_版本"
            # 重新考虑特殊保留逻辑：如果原始文件名（映射前的）符合特定模式，则不移除前缀
            # 例如，如果原始文件名是 "中文名_英文标识符.safetensors"
            # 这里的逻辑是，如果修正后的名称中包含下划线，并且下划线后的部分很短且不含中文，
            # 这可能意味着它是一个重要的标识符，此时不应该移除中文前缀。
            # 这个逻辑可能需要根据实际情况调整。
            # 目前的实现是：如果下划线后的部分短且无中文，则返回修正后的完整文件名。
            if len(parts) > 1: # 确保有下划线分割
                last_part_of_corrected = parts[-1] # 获取修正后名称的最后一部分
                if len(last_part_of_corrected) <= 5 and not self._contains_chinese(last_part_of_corrected):
                    return filename_after_correction # 保留修正后的完整名称

        # 如果不符合上述特殊保留条件，则尝试移除中文前缀
        prefix_pattern = re.compile(r"^[\u4e00-\u9fa5]+")
        if re.search(r"^[\u4e00-\u9fa5]", filename_after_correction): # 对修正后的名称判断和操作
            filename_no_prefix = re.sub(prefix_pattern, "", filename_after_correction).strip()
            filename_no_prefix = re.sub(r"^[-_|\s]+", "", filename_no_prefix).strip() # 移除前导分隔符
            return filename_no_prefix
        
        return filename_after_correction # 如果没有中文前缀，返回修正后的名称

    def _contains_chinese(self, text):
        if not isinstance(text, str): return False
        return bool(self._chinese_char_pattern.search(text))

    def _get_search_url(self, name_for_decision, term_for_query_embedding, node_type=None):
        """
        Generates search URLs.
        name_for_decision: Name after mapping, before prefix removal. Used for search strategy.
        term_for_query_embedding: Final term (after mapping and prefix removal) to be embedded in the site query.
        """
        logger.debug(f"Generating search URL. Decision Name: '{name_for_decision}', Query Embedding Term: '{term_for_query_embedding}', Node Type: {node_type}")

        if name_for_decision == "ip-adapter.bin" and node_type == "InstantIDModelLoader": # 特殊规则判断
             logger.debug("Applying special rule for ip-adapter.bin + InstantIDModelLoader")
             return ("https://www.bing.com/?setlang=en-US", 'site:huggingface.co "ip-adapter.bin InstantID"')

        if self._contains_chinese(name_for_decision): # 用映射后的名称（但未移除中文前缀的）判断是否搜LibLib
            logger.debug(f"Decision name '{name_for_decision}' suggests Chinese model, using LibLib search with query term '{term_for_query_embedding}'.")
            return f"https://www.bing.com/?setlang=en-US", f'site:liblib.art "{term_for_query_embedding}"'
        else:
            logger.debug(f"Decision name '{name_for_decision}' suggests non-Chinese model, using Hugging Face search with query term '{term_for_query_embedding}'.")
            return f"https://www.bing.com/?setlang=en-US", f'site:huggingface.co "{term_for_query_embedding}"'

    def _get_search_cache_path(self):
        """Returns a persistent cache file path for search results."""
        try:
            cache_root = get_results_folder()
            os.makedirs(cache_root, exist_ok=True)
            return os.path.join(cache_root, "search_cache.json")
        except Exception:
            # Fallback to module directory if results directory resolution fails.
            return os.path.join(os.path.dirname(os.path.abspath(__file__)), "search_cache.json")

    def _load_search_cache(self):
        cache_path = self._get_search_cache_path()
        if not os.path.exists(cache_path):
            return {}

        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
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
            with open(tmp_path, 'w', encoding='utf-8') as f:
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

    def _build_search_cache_key(self, search_site, search_term_query, node_type):
        site = "liblib" if search_site == "liblib" else "hf"
        normalized_term = (search_term_query or "").strip().lower()
        normalized_node_type = (node_type or "").strip().lower()
        return f"{site}|{normalized_term}|{normalized_node_type}"

    def _is_cache_entry_valid(self, cache_entry):
        if not isinstance(cache_entry, dict):
            return False

        updated_at = cache_entry.get('updated_at')
        if not isinstance(updated_at, (int, float)):
            return False

        # Keep successful entries longer than misses.
        has_url = bool((cache_entry.get('url') or '').strip())
        ttl_seconds = 30 * 24 * 3600 if has_url else 12 * 3600
        return (time.time() - float(updated_at)) <= ttl_seconds

    def _apply_search_result_to_row(self, df, df_idx, search_site, found_url, status):
        """Applies one search result row update in a normalized way."""
        found_url = (found_url or '').strip()
        status = (status or '').strip()

        if search_site == 'liblib':
            df.loc[df_idx, '下载链接'] = ''
            df.loc[df_idx, '镜像链接'] = ''
            df.loc[df_idx, '搜索链接'] = found_url
            df.loc[df_idx, '状态'] = status or ('已处理' if found_url else '未找到LibLib')
            return

        # Hugging Face branch
        df.loc[df_idx, '搜索链接'] = ''
        if found_url:
            resolved_url = found_url.replace("/blob/", "/resolve/") if "/blob/" in found_url else found_url
            df.loc[df_idx, '下载链接'] = resolved_url
            df.loc[df_idx, '镜像链接'] = get_mirror_link(found_url)
            df.loc[df_idx, '状态'] = status or '已处理'
        else:
            df.loc[df_idx, '下载链接'] = ''
            df.loc[df_idx, '镜像链接'] = ''
            df.loc[df_idx, '状态'] = status or '未找到HF'

    def find_missing_models(self, workflow_file):
        logger.info(f"Analyzing workflow file: {workflow_file}")
        base_dir = os.path.dirname(os.path.abspath(workflow_file))
        missing_files_list = []
        try:
            with open(workflow_file, 'r', encoding='utf-8', errors='ignore') as f:
                workflow_json = json.load(f)
            if not isinstance(workflow_json, dict) or 'nodes' not in workflow_json:
                logger.error(f"Invalid workflow format in {workflow_file}")
                return []

            # 使用配置管理器获取配置数据，而不是硬编码
            node_model_indices = self.node_model_indices
            model_extensions = self.model_extensions
            model_node_types = self.model_node_types

            file_references = []
            nodes = workflow_json.get('nodes', [])
            if len(nodes) > 1000: nodes = nodes[:1000]

            for node in nodes:
                try:
                    node_type = node.get('type', '')
                    widgets_values = node.get('widgets_values', [])
                    # ... (其他节点属性获取和类型判断逻辑不变) ...
                    if not (node_type in model_node_types or "Loader" in node_type) or not widgets_values: continue
                    
                    indices_to_check = node_model_indices.get(node_type, node_model_indices["default"])
                    for index in indices_to_check:
                        if len(widgets_values) > index and isinstance(widgets_values[index], str):
                            original_value_from_widget = widgets_values[index].strip()
                            if not original_value_from_widget or original_value_from_widget.lower() in ["default", "none", "empty", "auto", "off", "on"]: continue
                            
                            original_filename = os.path.basename(original_value_from_widget.replace('\\', '/')) if '\\' in original_value_from_widget or '/' in original_value_from_widget else original_value_from_widget
                            
                            # 使用 _process_name_for_search 获取处理后的名称
                            processed_names = self._process_name_for_search(original_filename)
                            
                            file_references.append({
                                'node_id': node.get('id'), 'node_type': node_type,
                                'original_filename': original_filename, # 用于报告
                                'filename_for_check': processed_names['final_search_term'] # 用于文件存在性检查
                            })
                except Exception as node_e: logger.error(f"Error processing node ID {node.get('id', 'N/A')}", exc_info=True)
            
            if not file_references: return []
            file_existence_cache = {}
            for ref in file_references:
                try:
                    filename_to_check_existence = ref['filename_for_check']
                    original_filename_for_report = ref['original_filename']
                    name, ext = os.path.splitext(filename_to_check_existence)
                    if filename_to_check_existence in file_existence_cache:
                        if not file_existence_cache[filename_to_check_existence]:
                            missing_files_list.append({'node_id': ref['node_id'], 'node_type': ref['node_type'], 'file_path': original_filename_for_report})
                        continue
                    exists = os.path.exists(filename_to_check_existence) or os.path.exists(os.path.join(base_dir, filename_to_check_existence))
                    if not exists and not ext:
                         for model_ext in model_extensions:
                             if os.path.exists(f"{filename_to_check_existence}{model_ext}") or os.path.exists(os.path.join(base_dir, f"{filename_to_check_existence}{model_ext}")):
                                 exists = True; break
                    file_existence_cache[filename_to_check_existence] = exists
                    if not exists:
                        logger.debug(f"Missing file: Checked='{filename_to_check_existence}', Reported='{original_filename_for_report}'")
                        missing_files_list.append({'node_id': ref['node_id'], 'node_type': ref['node_type'], 'file_path': original_filename_for_report})
                except Exception as check_e: logger.error(f"Error checking existence (original: '{ref.get('original_filename')}', checked: '{ref.get('filename_for_check')}')", exc_info=True)
        except Exception as e: logger.error(f"Error in find_missing_models for {workflow_file}", exc_info=True); raise
        return sorted(missing_files_list, key=lambda x: x['file_path']) if missing_files_list else []

    def create_csv_file(self, missing_files, output_basename):
        if not missing_files: return None
        csv_file_path = get_output_path(output_basename, "csv")
        try:
            merged_files_for_csv = {}
            for item_data in missing_files:
                original_file_path = item_data['file_path'] # 这是用于报告的原始文件名
                processed_names = self._process_name_for_search(original_file_path)
                
                if original_file_path not in merged_files_for_csv:
                    merged_files_for_csv[original_file_path] = {
                        'node_id': str(item_data['node_id']), 'node_type': item_data['node_type'],
                        'original_file_path': original_file_path,
                        'name_for_decision': processed_names['mapped'],       # 用于_get_search_url的第一个参数
                        'name_for_query_embedding': processed_names['final_search_term'] # 用于_get_search_url的第二个参数
                    }
                else: # 合并节点ID和类型
                    existing = merged_files_for_csv[original_file_path]
                    existing['node_id'] = f"{existing['node_id']},{item_data['node_id']}"
                    if item_data['node_type'] not in existing['node_type'].split(','):
                        existing['node_type'] = f"{existing['node_type']},{item_data['node_type']}"
            
            final_list_for_csv = sorted(list(merged_files_for_csv.values()), key=lambda x: x['original_file_path'])
            with open(csv_file_path, 'w', newline='', encoding='utf-8-sig') as f:
                fieldnames = ['序号', '节点ID', '节点类型', '文件名', '状态', '下载链接', '镜像链接', '搜索链接']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for i, csv_item in enumerate(final_list_for_csv, 1):
                    base_url, site_query = self._get_search_url(
                        csv_item['name_for_decision'],
                        csv_item['name_for_query_embedding'],
                        csv_item['node_type']
                    )
                    query_param = site_query.replace(' ', '+').replace('"', '%22')
                    search_link_url = f"https://www.bing.com/search?q={query_param}"
                    writer.writerow({
                        '序号': i, '节点ID': csv_item['node_id'], '节点类型': csv_item['node_type'],
                        '文件名': csv_item['original_file_path'], # 显示原始文件名
                        '状态': '', '下载链接': '', '镜像链接': '', '搜索链接': search_link_url
                    })
            logger.info(f"CSV file successfully saved to: {os.path.abspath(csv_file_path)}")
            return csv_file_path
        except Exception as e: logger.error(f"Error creating CSV for {output_basename}", exc_info=True); return None


    def search_model_links(self, csv_file, progress_callback=None):
        logger.info(f"Starting model link search for CSV: {csv_file}")
        if pd is None or ChromiumPage is None:
            logger.error("Search cannot proceed: Missing pandas or DrissionPage.")
            return False

        col_status = '\u72b6\u6001'
        col_download = '\u4e0b\u8f7d\u94fe\u63a5'
        col_mirror = '\u955c\u50cf\u94fe\u63a5'
        col_search = '\u641c\u7d22\u94fe\u63a5'
        col_file = '\u6587\u4ef6\u540d'
        col_node_type = '\u8282\u70b9\u7c7b\u578b'

        status_processed = '\u5df2\u5904\u7406'
        status_no_search_box = '\u641c\u7d22\u9519\u8bef(\u65e0\u641c\u7d22\u6846)'
        status_no_result_area = '\u672a\u627e\u5230(\u65e0\u7ed3\u679c\u533a)'
        status_no_link = '\u672a\u627e\u5230(\u65e0\u94fe\u63a5)'
        status_search_exception = '\u641c\u7d22\u9519\u8bef(\u5f02\u5e38)'
        status_not_found_liblib = '\u672a\u627e\u5230LibLib'
        status_not_found_hf = '\u672a\u627e\u5230HF'
        status_non_direct_liblib = '\u627e\u5230\u641c\u7d22\u94fe\u63a5\u4f46\u975e\u76f4\u63a5LibLib\u94fe\u63a5'
        status_browser_unavailable = '\u641c\u7d22\u9519\u8bef(\u6d4f\u89c8\u5668\u4e0d\u53ef\u7528)'

        try:
            string_cols = [col_status, col_download, col_mirror, col_search, col_file, col_node_type]
            df = pd.read_csv(
                csv_file,
                encoding='utf-8-sig',
                dtype={col: str for col in string_cols},
                keep_default_na=False,
                na_values=['']
            )
            for col in string_cols:
                if col not in df.columns:
                    df[col] = ''
                df[col] = df[col].fillna('').astype(str)

            save_interval = 20
            rows_since_save = 0
            cache = self._load_search_cache()
            cache_dirty = False

            grouped_tasks = {}
            cache_hits = 0

            for index, row in df.iterrows():
                original_name_from_csv = row.get(col_file, '')
                if not original_name_from_csv:
                    continue

                status = row.get(col_status, '')
                hf_link = row.get(col_download, '')
                search_or_liblib_link = row.get(col_search, '')
                is_processed = (status == status_processed)
                has_valid_link = hf_link or (search_or_liblib_link.startswith('http') and 'liblib.art' in search_or_liblib_link)
                if is_processed and has_valid_link:
                    continue

                processed_names = self._process_name_for_search(original_name_from_csv)
                search_site = 'liblib' if self._contains_chinese(processed_names['mapped']) else 'hf'
                node_type = row.get(col_node_type, '')
                cache_key = self._build_search_cache_key(search_site, processed_names['final_search_term'], node_type)

                cached_entry = cache.get(cache_key)
                if self._is_cache_entry_valid(cached_entry):
                    self._apply_search_result_to_row(
                        df,
                        index,
                        search_site,
                        cached_entry.get('url', ''),
                        cached_entry.get('status', '')
                    )
                    cache_hits += 1
                    rows_since_save += 1
                    continue
                elif cached_entry is not None:
                    cache.pop(cache_key, None)
                    cache_dirty = True

                if cache_key not in grouped_tasks:
                    grouped_tasks[cache_key] = {
                        'cache_key': cache_key,
                        'search_site': search_site,
                        'name_for_decision': processed_names['mapped'],
                        'search_term_query': processed_names['final_search_term'],
                        'node_type': node_type,
                        'original_name_csv': original_name_from_csv,
                        'df_indices': [index],
                    }
                else:
                    grouped_tasks[cache_key]['df_indices'].append(index)

            if rows_since_save >= save_interval:
                df.to_csv(csv_file, index=False, encoding='utf-8-sig')
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

            chrome_path_to_use = (
                self.controller.get_loaded_chrome_path()
                if self.controller and hasattr(self.controller, 'get_loaded_chrome_path')
                else None
            ) or find_chrome_path()

            if not chrome_path_to_use and search_tasks:
                logger.error("Chrome browser not found. Cannot perform search.")
                for task in search_tasks:
                    for df_idx in task['df_indices']:
                        self._apply_search_result_to_row(df, df_idx, task['search_site'], '', status_browser_unavailable)
                        rows_since_save += 1
            else:
                page = None
                if chrome_path_to_use and search_tasks:
                    co = ChromiumOptions().set_browser_path(chrome_path_to_use)
                    co.set_argument('--disable-infobars').set_argument('--no-sandbox').set_argument('--start-maximized')
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

                        bing_url, site_query = self._get_search_url(
                            task['name_for_decision'],
                            task['search_term_query'],
                            task['node_type']
                        )

                        found_url = ''
                        status_text = status_not_found_liblib if task['search_site'] == 'liblib' else status_not_found_hf

                        try:
                            page.get(bing_url, timeout=15)
                            time.sleep(random.uniform(0.2, 0.5))

                            search_box = page.ele("#sb_form_q", timeout=5)
                            if not search_box:
                                status_text = status_no_search_box
                            else:
                                search_box.clear()
                                search_box.input(site_query)
                                time.sleep(random.uniform(0.1, 0.25))

                                s_button = page.ele('#search_icon', timeout=3) or page.ele('xpath://button[@type="submit"]', timeout=3)
                                if s_button:
                                    s_button.click()
                                else:
                                    page.run_js("document.querySelector('#sb_form').submit();")

                                page.wait.load_start(timeout=10)
                                results_container = page.ele('#b_results', timeout=10)

                                if not results_container:
                                    status_text = status_no_result_area
                                else:
                                    first_link = results_container.ele("xpath:.//h2/a")
                                    if not first_link:
                                        status_text = status_no_link
                                    else:
                                        candidate_url = (first_link.attr("href") or '').strip()
                                        logger.info(f"Found: '{first_link.text}' -> {candidate_url}")

                                        if task['search_site'] == 'liblib':
                                            if candidate_url and 'liblib.art' in candidate_url:
                                                if 'bing.com' in candidate_url or 'search' in candidate_url.lower():
                                                    liblib_url = ''
                                                    try:
                                                        first_link.click()
                                                        page.wait.load_start(timeout=10)
                                                        current_url = (page.url or '').strip()
                                                        if 'liblib.art' in current_url:
                                                            liblib_url = current_url
                                                        else:
                                                            page.back()
                                                            liblib_links = results_container.eles("xpath:.//a[contains(@href, 'liblib.art')]")
                                                            for item in liblib_links:
                                                                direct_url = (item.attr("href") or '').strip()
                                                                if direct_url and 'liblib.art' in direct_url:
                                                                    liblib_url = direct_url
                                                                    break
                                                    except Exception:
                                                        logger.debug("Failed to resolve LibLib redirect URL.", exc_info=True)

                                                    if liblib_url:
                                                        found_url = liblib_url
                                                        status_text = status_processed
                                                    else:
                                                        found_url = candidate_url
                                                        status_text = status_non_direct_liblib
                                                else:
                                                    found_url = candidate_url
                                                    status_text = status_processed
                                            else:
                                                liblib_links = results_container.eles("xpath:.//a[contains(@href, 'liblib.art')]")
                                                for item in liblib_links:
                                                    direct_url = (item.attr("href") or '').strip()
                                                    if direct_url and 'liblib.art' in direct_url:
                                                        found_url = direct_url
                                                        break
                                                status_text = status_processed if found_url else status_not_found_liblib
                                        else:
                                            if candidate_url and 'huggingface.co' in candidate_url:
                                                found_url = candidate_url
                                                status_text = status_processed
                                            else:
                                                status_text = status_not_found_hf
                        except Exception:
                            logger.error(f"Error searching for '{task['search_term_query']}'", exc_info=True)
                            status_text = status_search_exception
                        finally:
                            for df_idx in task['df_indices']:
                                self._apply_search_result_to_row(df, df_idx, task['search_site'], found_url, status_text)
                            rows_since_save += len(task['df_indices'])

                            cache[task['cache_key']] = {
                                'site': task['search_site'],
                                'url': found_url,
                                'status': status_text,
                                'updated_at': time.time(),
                            }
                            cache_dirty = True

                            if rows_since_save >= save_interval:
                                df.to_csv(csv_file, index=False, encoding='utf-8-sig')
                                rows_since_save = 0

                            time.sleep(random.uniform(0.15, 0.35))

                    page.quit()

            df.to_csv(csv_file, index=False, encoding='utf-8-sig')
            if cache_dirty:
                self._save_search_cache(cache)

            html_file = create_html_view(csv_file)
            return html_file if html_file else True
        except Exception:
            logger.error(f"Critical error in search_model_links for {csv_file}", exc_info=True)
            return False


    def batch_process_workflows(self, directory, file_pattern="*.json", progress_callback=None):
        """Processes all workflow files in a directory. 处理目录中的所有工作流文件。"""
        logger.info(f"Starting batch process for directory: {directory}, pattern: {file_pattern}")
        import glob
        patterns = file_pattern.split(';')
        all_files = [f for p_item in patterns if p_item.strip() for f in glob.glob(os.path.join(directory, p_item.strip()))]
        if not all_files: logger.warning(f"No files found for patterns in {directory}"); return False
        
        workflow_files = []
        for file_path in all_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f: json.load(f)
                workflow_files.append(file_path)
            except: logger.debug(f"Skipping non-JSON or invalid JSON: {file_path}")
        if not workflow_files: logger.info("No valid JSON workflows found."); return True

        results_summary = []
        all_missing_dict = {}
        for i, wf_path in enumerate(sorted(workflow_files)):
            if progress_callback: progress_callback(i + 1, len(workflow_files))
            logger.info(f"Batch processing ({i+1}/{len(workflow_files)}): {os.path.basename(wf_path)}")
            try:
                missing_in_wf = self.find_missing_models(wf_path)
                if missing_in_wf:
                    csv_path = self.create_csv_file(missing_in_wf, os.path.basename(wf_path))
                    if csv_path:
                        results_summary.append({'workflow': wf_path, 'csv': csv_path, 'missing_count': len(missing_in_wf)})
                        for item in missing_in_wf: # item['file_path'] is original name
                            if item['file_path'] not in all_missing_dict: all_missing_dict[item['file_path']] = item
            except Exception as e: logger.error(f"Error processing {wf_path} in batch", exc_info=True)

        summary_all_missing_path, batch_results_path = None, None
        if all_missing_dict:
            summary_all_missing_path = self.create_csv_file(list(all_missing_dict.values()), "汇总缺失文件")
        if results_summary:
            try:
                batch_results_path = get_output_path("批量处理结果", "csv")
                with open(batch_results_path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.DictWriter(f, fieldnames=['工作流文件', 'CSV文件', '缺失数量'])
                    writer.writeheader()
                    for res in sorted(results_summary, key=lambda x: x['workflow']):
                        writer.writerow({'工作流文件': os.path.basename(res['workflow']), 'CSV文件': os.path.basename(res['csv']), '缺失数量': res['missing_count']})
                logger.info(f"Batch results summary saved to {os.path.abspath(batch_results_path)}")
            except Exception as e: logger.error("Error creating batch results CSV", exc_info=True); batch_results_path = None
        
        logger.info("Batch processing finished.")
        if not all_missing_dict: return True
        return batch_results_path or summary_all_missing_path or False
