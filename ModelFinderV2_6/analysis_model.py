import os
import json
import re
import logging
from typing import Callable, Optional

# Import utilities and file manager directly, as Model handles core logic
from .model_config_manager import ModelConfigManager
from .search_service import SearchService
from .workflow_report_service import ALL_MISSING_BASENAME, WorkflowReportService


logger = logging.getLogger(__name__)

class AnalysisModel:
    """
    Handles the core logic for analyzing workflows, finding models,
    creating CSVs, searching links, and batch processing.
    处理分析工作流、查找模型、创建CSV、搜索链接和批量处理的核心逻辑。
    """

    def __init__(
        self,
        controller=None,
        name_corrector: Optional[Callable[[str], str]] = None,
        comfyui_path_provider: Optional[Callable[[], str]] = None,
        chrome_path_provider: Optional[Callable[[], str]] = None,
        report_service: Optional[WorkflowReportService] = None,
    ):
        """初始化分析模型"""
        self.controller = controller
        self.model_folder = None # Used to cache value
        self._name_corrector = name_corrector
        self._comfyui_path_provider = comfyui_path_provider
        self._chrome_path_provider = chrome_path_provider
        self.report_service = report_service or WorkflowReportService()

        if controller is not None:
            if self._name_corrector is None:
                irregular_names_model = getattr(controller, 'irregular_names_model', None)
                if irregular_names_model and hasattr(irregular_names_model, 'get_corrected_name'):
                    self._name_corrector = irregular_names_model.get_corrected_name

            if self._comfyui_path_provider is None:
                self._comfyui_path_provider = self._build_comfyui_path_provider(controller)

            if self._chrome_path_provider is None and hasattr(controller, 'get_loaded_chrome_path'):
                self._chrome_path_provider = controller.get_loaded_chrome_path
        
        # 初始化配置管理器
        self.config_manager = ModelConfigManager()
        
        # 使用配置管理器获取数据
        self.model_node_types = self.config_manager.get_model_node_types()
        self.node_model_indices = self.config_manager.get_node_model_indices()
        self.model_extensions = self.config_manager.get_model_extensions()
        self._chinese_char_pattern = re.compile(r'[\u4e00-\u9fff]')
        self.search_service = SearchService(
            process_name_for_search=self._process_name_for_search,
            contains_chinese=self._contains_chinese,
            chrome_path_provider=self._chrome_path_provider,
        )
        
        logger.info("AnalysisModel initialized.")

    def _build_comfyui_path_provider(self, controller):
        def provider():
            view = getattr(controller, 'view', None)
            if view and hasattr(view, 'get_comfyui_path'):
                comfyui_path = (view.get_comfyui_path() or '').strip()
                if comfyui_path:
                    return comfyui_path

            if hasattr(controller, 'get_loaded_comfyui_path'):
                return (controller.get_loaded_comfyui_path() or '').strip()

            return ''

        return provider

    @staticmethod
    def _read_path_from_provider(provider: Optional[Callable[[], str]]) -> str:
        if provider is None:
            return ''

        try:
            value = provider()
        except Exception:
            logger.warning("Path provider failed.", exc_info=True)
            return ''

        return (value or '').strip()

    def _get_corrected_name_if_possible(self, original_name):
        if self._name_corrector:
            corrected_name = self._name_corrector(original_name)
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

    def _get_active_comfyui_path(self):
        return self._read_path_from_provider(self._comfyui_path_provider)

    def _get_active_chrome_path(self):
        return self._read_path_from_provider(self._chrome_path_provider)

    def _get_comfyui_models_root(self):
        comfyui_path = self._get_active_comfyui_path()
        if not comfyui_path:
            return ''

        if os.path.isdir(comfyui_path) and os.path.basename(comfyui_path).lower() == 'models':
            return comfyui_path

        models_root = os.path.join(comfyui_path, 'models')
        return models_root if os.path.isdir(models_root) else ''

    def _build_comfyui_model_index(self, models_root):
        if not models_root or not os.path.isdir(models_root):
            self.model_folder = None
            return None

        cached_index = self.model_folder if isinstance(self.model_folder, dict) else None
        if cached_index and cached_index.get('root') == models_root:
            return cached_index

        file_names = set()
        file_stems = set()
        dir_names = set()

        for root, dirnames, filenames in os.walk(models_root):
            for dirname in dirnames:
                normalized_dir = dirname.strip().lower()
                if normalized_dir:
                    dir_names.add(normalized_dir)

            for filename in filenames:
                normalized_name = filename.strip().lower()
                if not normalized_name:
                    continue
                file_names.add(normalized_name)
                stem, _ = os.path.splitext(normalized_name)
                if stem:
                    file_stems.add(stem)

        self.model_folder = {
            'root': models_root,
            'file_names': file_names,
            'file_stems': file_stems,
            'dir_names': dir_names,
        }
        logger.debug(
            f"Indexed ComfyUI models root '{models_root}' with "
            f"{len(file_names)} files and {len(dir_names)} directories."
        )
        return self.model_folder

    def _model_exists_in_comfyui_index(self, filename, model_index):
        if not filename or not model_index:
            return False

        normalized_name = os.path.basename(filename).strip().lower()
        if not normalized_name:
            return False

        file_names = model_index.get('file_names', set())
        file_stems = model_index.get('file_stems', set())
        dir_names = model_index.get('dir_names', set())

        stem, ext = os.path.splitext(normalized_name)
        if ext:
            return normalized_name in file_names

        return (
            normalized_name in file_names
            or normalized_name in file_stems
            or normalized_name in dir_names
        )

    def _local_reference_exists(self, filename, base_dir, model_extensions):
        if not filename:
            return False

        if os.path.exists(filename) or os.path.exists(os.path.join(base_dir, filename)):
            return True

        _, ext = os.path.splitext(filename)
        if ext:
            return False

        for model_ext in model_extensions:
            if os.path.exists(f"{filename}{model_ext}") or os.path.exists(os.path.join(base_dir, f"{filename}{model_ext}")):
                return True

        return False

    def _get_search_url(self, name_for_decision, term_for_query_embedding, node_type=None):
        return self.search_service.get_search_url(name_for_decision, term_for_query_embedding, node_type)

    def _get_search_candidates(self, name_for_decision, term_for_query_embedding, node_type=None):
        return self.search_service.get_search_candidates(name_for_decision, term_for_query_embedding, node_type)

    def _get_search_cache_path(self):
        return self.search_service._get_search_cache_path()

    def _load_search_cache(self):
        return self.search_service._load_search_cache()

    def _save_search_cache(self, cache_data):
        return self.search_service._save_search_cache(cache_data)

    def _build_search_cache_key(self, search_site, search_term_query, node_type):
        return self.search_service._build_search_cache_key(search_site, search_term_query, node_type)

    def _is_cache_entry_valid(self, cache_entry):
        return self.search_service.is_cache_entry_valid(cache_entry)

    def _should_cache_result(self, found_url, status):
        return self.search_service._should_cache_result(found_url, status)

    def _apply_search_result_to_row(self, df, df_idx, search_site, found_url, status):
        self.search_service._apply_search_result_to_row(df, df_idx, search_site, found_url, status)

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
            comfyui_models_root = self._get_comfyui_models_root()
            comfyui_model_index = self._build_comfyui_model_index(comfyui_models_root)
            file_existence_cache = {}
            for ref in file_references:
                try:
                    filename_to_check_existence = ref['filename_for_check']
                    original_filename_for_report = ref['original_filename']
                    if filename_to_check_existence in file_existence_cache:
                        if not file_existence_cache[filename_to_check_existence]:
                            missing_files_list.append({'node_id': ref['node_id'], 'node_type': ref['node_type'], 'file_path': original_filename_for_report})
                        continue

                    exists = self._local_reference_exists(filename_to_check_existence, base_dir, model_extensions)
                    if not exists and comfyui_model_index:
                        exists = self._model_exists_in_comfyui_index(filename_to_check_existence, comfyui_model_index)

                    file_existence_cache[filename_to_check_existence] = exists
                    if not exists:
                        logger.debug(f"Missing file: Checked='{filename_to_check_existence}', Reported='{original_filename_for_report}'")
                        missing_files_list.append({'node_id': ref['node_id'], 'node_type': ref['node_type'], 'file_path': original_filename_for_report})
                except Exception as check_e: logger.error(f"Error checking existence (original: '{ref.get('original_filename')}', checked: '{ref.get('filename_for_check')}')", exc_info=True)
        except Exception as e: logger.error(f"Error in find_missing_models for {workflow_file}", exc_info=True); raise
        return sorted(missing_files_list, key=lambda x: x['file_path']) if missing_files_list else []

    def create_csv_file(self, missing_files, output_basename):
        result = self.report_service.create_missing_files_report(
            missing_files,
            output_basename,
            process_name_for_search=self._process_name_for_search,
            search_url_builder=self._get_search_url,
        )
        if not result.success:
            logger.error(f"Error creating CSV for {output_basename}: {result.message}")
            return None
        return result.data["csv_file"]


    def search_model_links(self, csv_file, progress_callback=None):
        return self.search_service.search_model_links(csv_file, progress_callback=progress_callback)


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
            summary_all_missing_path = self.create_csv_file(list(all_missing_dict.values()), ALL_MISSING_BASENAME)
        if results_summary:
            summary_result = self.report_service.create_batch_summary_report(results_summary)
            if summary_result.success:
                batch_results_path = summary_result.data["csv_file"]
            else:
                logger.error("Error creating batch results CSV: %s", summary_result.message)
                batch_results_path = None
        
        logger.info("Batch processing finished.")
        if not all_missing_dict: return True
        return batch_results_path or summary_all_missing_path or False
