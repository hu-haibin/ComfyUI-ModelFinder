# model_finder/controller.py
import os
import random
import threading
import time
import webbrowser
import tkinter as tk
from tkinter import filedialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import logging # Import logging
from .irregular_names_model import IrregularNamesModel

# Import other parts of the application
from .settings_model import SettingsModel
from .analysis_model import AnalysisModel
from .application_runtime_service import ApplicationRuntimeService
from .comfyui_launcher_service import ComfyUILauncherService
from .comfyui_manager_api_service import ComfyUIManagerApiService
from .comfyui_runtime_api_service import ComfyUIRuntimeApiService
from .dependency_environment_service import DependencyEnvironmentService
from .dependency_install_planner import DependencyInstallPlanner
from .dependency_preflight_service import DependencyPreflightService
from .dependency_rule_service import DependencyRuleService
from .irregular_mapping_service import IrregularMappingService
from .missing_node_install_orchestrator import MissingNodeInstallOrchestrator
from .model_config_service import ModelConfigService
from .plugin_repair import PluginRepairModel  # 导入插件修复模型
from .plugin_repair_service import PluginRepairService
from .result_view_service import ResultViewService
from .workflow_missing_node_service import WorkflowMissingNodeService
from .workflow_processing_service import WorkflowProcessingService
from . import __version__, __author__

logger = logging.getLogger(__name__) # Get logger for this module

class AppController:
    def __init__(self, root, view, version, author):
        self.root = root
        self.view = view
        self.__version__ = version
        self.__author__ = author
        self.settings_model = SettingsModel()
        self.irregular_names_model = IrregularNamesModel()
        self.analysis_model = AnalysisModel(
            controller=self,
            name_corrector=self.irregular_names_model.get_corrected_name,
            comfyui_path_provider=self.get_active_comfyui_path,
            chrome_path_provider=self.get_loaded_chrome_path,
        )
        self.plugin_repair_model = PluginRepairModel()
        self.irregular_mapping_service = IrregularMappingService(self.irregular_names_model)
        self.model_config_service = ModelConfigService(self.analysis_model.config_manager)
        self.workflow_processing_service = WorkflowProcessingService(self.analysis_model)
        self.plugin_repair_service = PluginRepairService(self.plugin_repair_model)
        self.comfyui_launcher_service = ComfyUILauncherService()
        self.comfyui_runtime_api_service = ComfyUIRuntimeApiService(
            base_url_provider=self.comfyui_launcher_service.get_launch_url,
        )
        self.comfyui_manager_api_service = ComfyUIManagerApiService(
            base_url_provider=self.comfyui_launcher_service.get_launch_url,
            comfyui_path_provider=self.get_active_comfyui_path,
        )
        self.workflow_missing_node_service = WorkflowMissingNodeService()
        self.missing_node_install_orchestrator = MissingNodeInstallOrchestrator(
            self.comfyui_runtime_api_service,
            self.comfyui_manager_api_service,
            self.workflow_missing_node_service,
        )
        self.dependency_rule_service = DependencyRuleService()
        self.dependency_environment_service = DependencyEnvironmentService(
            python_path_provider=self.get_active_comfyui_python_path,
            comfyui_path_provider=self.get_active_comfyui_path,
        )
        self.dependency_preflight_service = DependencyPreflightService(
            environment_service=self.dependency_environment_service,
            rule_service=self.dependency_rule_service,
        )
        self.dependency_install_planner = DependencyInstallPlanner()
        self.result_view_service = ResultViewService()
        self.runtime_service = ApplicationRuntimeService()

        self.html_file_path = None
        self.batch_summary_file_path = None

        self.auto_open_html = tk.BooleanVar()
        self.random_theme = tk.BooleanVar()
        self._loaded_theme = "cosmo"
        self._loaded_chrome_path = ""
        self._loaded_comfyui_path = ""
        self._loaded_comfyui_python_path = ""
        self._loaded_retention_days = 30
        self._comfyui_runtime_poll_scheduled = False
        self._last_comfyui_runtime_state = "idle"
        self._comfyui_browser_opened = False
        self._manager_queue_poll_scheduled = False
        self._missing_installer_step = 0
        self._missing_installer_completed_steps = set()
        self._missing_installer_selected_paths = []
        self._missing_installer_analysis_result = None
        self._missing_installer_install_plan = []
        self._missing_installer_preflight_result = None
        self._missing_installer_manual_items = []
        self._missing_installer_recheck_paths = []
        self._pending_missing_analysis = False
        self._pending_missing_recheck = False
        self._missing_installer_restart_available = False
        self._missing_installer_launch_mode = ComfyUILauncherService.DEFAULT_MODE
        self._is_shutting_down = False
        self._manager_runtime_status_label = "未启动"
        self._manager_runtime_ready = False
        self._manager_runtime_check_inflight = False
        self._manager_runtime_last_check = 0.0
        self._pending_runtime_wait_deadline = 0.0
        self._missing_runtime_wait_logged = False

        self.status_var = tk.StringVar(value="初始化...")
        logger.info("AppController initialized.")

    def initialize(self):
        """Final setup after view and controller are created."""
        logger.debug("Controller initialize sequence started.")
        self.load_settings()          # Load settings first
        
        # 调试映射文件
        mapping_count = self.irregular_names_model.dump_all_mappings_debug()
        logger.info(f"已加载 {mapping_count} 条不规则名称映射")
        
        # 刷新模型配置视图
        self.refresh_model_config_view()
        
        
        # 初始化插件修复标签页
        self.refresh_plugin_repair_view()
        
        self.view.set_controller(self) # Then set controller in view (triggers view update)
        self.refresh_comfyui_launch_runtime()
        self.refresh_missing_node_installer_runtime()
        self._sync_missing_node_installer_view()
        self.show_welcome_message()   # Then show welcome message
        logger.debug("Controller initialize sequence finished.")

    # --- Getters for View Initialization/Update ---
    def get_loaded_theme_preference(self): return self._loaded_theme
    def get_loaded_chrome_path(self): return self._loaded_chrome_path
    def get_loaded_comfyui_path(self): return self._loaded_comfyui_path
    def get_loaded_comfyui_python_path(self): return self._loaded_comfyui_python_path
    def get_loaded_retention_days(self): return self._loaded_retention_days

    def get_active_comfyui_path(self):
        comfyui_path = self.view.get_comfyui_path().strip() if self.view else ""
        return comfyui_path or self._loaded_comfyui_path

    def get_active_comfyui_python_path(self):
        python_path = self.view.get_comfyui_python_path().strip() if self.view else ""
        return python_path or self._loaded_comfyui_python_path

    # --- Core Logic Methods ---

    def show_welcome_message(self):
        logger.debug("Displaying welcome message.")
        welcome_text = f"欢迎使用模型查找器 - Model Finder v{self.__version__}\n(WeChat: {self.__author__})\n\n" \
                       "使用方法:\n" \
                       "1. 选择工作流JSON文件并分析\n" \
                       "2. 等待自动搜索下载链接\n" \
                       "3. 查看HTML结果获取下载链接\n"
        self.view.clear_log()
        self.view.update_log(welcome_text) # Keep this for user visible log
        self.view.set_window_title(f"ComfyUI模型查找器 - Model Finder v{self.__version__} (WeChat: {self.__author__})")

    def update_status(self, message):
        current_status = self.status_var.get()
        if current_status == message:
            return
        logger.debug(f"Updating status bar to: {message}")
        self.status_var.set(message)

    # --- UI Event Handlers ---

    def browse_workflow(self):
        logger.debug("Browse workflow button clicked.")
        file_path = filedialog.askopenfilename(
            title="选择工作流JSON文件",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        if file_path:
            logger.info(f"Workflow file selected: {file_path}")
            self.view.set_workflow_path(file_path)
        else:
            logger.debug("Workflow file selection cancelled.")

    def browse_workflow_dir(self):
        logger.debug("Browse workflow directory button clicked.")
        dir_path = filedialog.askdirectory(title="选择工作流目录")
        if dir_path:
            logger.info(f"Workflow directory selected: {dir_path}")
            self.view.set_workflow_dir(dir_path)
        else:
            logger.debug("Workflow directory selection cancelled.")

    def browse_chrome(self):
        logger.debug("Browse Chrome path button clicked.")
        initial_dir = "C:/Program Files/Google/Chrome/Application"
        if not os.path.exists(initial_dir): initial_dir = "C:/Program Files (x86)/Google/Chrome/Application"
        chrome_path = filedialog.askopenfilename(
            title="选择Chrome浏览器", filetypes=[("可执行文件", "*.exe")],
            initialdir=initial_dir if os.path.exists(initial_dir) else "/"
        )
        if chrome_path:
            logger.info(f"Chrome path selected: {chrome_path}")
            self.view.set_chrome_path(chrome_path)
        else:
            logger.debug("Chrome path selection cancelled.")

    def browse_comfyui_launch_path(self):
        logger.debug("Browse ComfyUI launch path button clicked.")
        dir_path = filedialog.askdirectory(title="选择 ComfyUI 安装目录")
        if not dir_path:
            logger.debug("ComfyUI launch path selection cancelled.")
            return

        logger.info(f"ComfyUI launch path selected: {dir_path}")
        self._loaded_comfyui_path = dir_path
        if hasattr(self.view, "set_comfyui_path"):
            self.view.set_comfyui_path(dir_path)

    def browse_comfyui_python_path(self):
        logger.debug("Browse ComfyUI Python path button clicked.")
        python_path = filedialog.askopenfilename(
            title="选择 Python 可执行文件",
            filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")],
        )
        if not python_path:
            logger.debug("ComfyUI Python path selection cancelled.")
            return

        logger.info(f"ComfyUI Python path selected: {python_path}")
        self._loaded_comfyui_python_path = python_path
        if hasattr(self.view, "set_comfyui_python_path"):
            self.view.set_comfyui_python_path(python_path)

    def _get_workflow_mode(self):
        mode = self.view.get_workflow_mode() if hasattr(self.view, "get_workflow_mode") else "single"
        return "batch" if mode == "batch" else "single"

    def browse_workflow_input(self):
        if self._get_workflow_mode() == "batch":
            self.browse_workflow_dir()
            return
        self.browse_workflow()

    def start_workflow_processing(self):
        if self._get_workflow_mode() == "batch":
            self.batch_process()
            return
        self.analyze_and_search()

    def view_workflow_result(self):
        if self._get_workflow_mode() == "batch":
            self.view_batch_html()
            return
        self.view_result()

    def analyze_and_search(self):
        logger.info("Analyze and Search button clicked.")
        workflow_file = self.view.get_workflow_path()
        if not workflow_file:
            logger.warning("Analyze cancelled: No workflow file selected.")
            self.view.show_error("错误", "请选择工作流JSON文件")
            return
        if not os.path.exists(workflow_file):
            logger.error(f"Analyze cancelled: Workflow file not found at {workflow_file}")
            self.view.show_error("错误", f"文件不存在: {workflow_file}")
            return

        self.view.clear_log() # Keep UI log clear for user messages
        self.update_status("正在分析...")
        self.view.enable_view_result_button(False)
        self.html_file_path = None
        self.view.update_log(f"开始分析: {os.path.basename(workflow_file)}") # User message

        try:
            logger.debug("Starting analysis thread...")
            threading.Thread(target=self._analyze_workflow_thread, args=(workflow_file,), daemon=True).start()
        except Exception as e:
             logger.error("启动分析线程时出错", exc_info=True)
             self.view.update_log("启动分析线程时出错，请查看日志文件。") # User message
             self.update_status("分析失败")
             self.view.show_error("错误", f"启动分析线程时出错: {e}")

    def _analyze_workflow_thread(self, workflow_file):
        logger.info(f"Analysis thread started for: {workflow_file}")
        try:
            analysis_result = self.workflow_processing_service.analyze_workflow(workflow_file)
            result_data = analysis_result.data if isinstance(analysis_result.data, dict) else {}

            if analysis_result.code == "no_missing":
                self.root.after(0, logger.info, "分析完成: 没有发现缺失文件。")
                self.root.after(0, self.view.update_log, "分析完成: 没有发现缺失文件。")
                self.root.after(0, self.update_status, "分析完成: 没有缺失文件")
                self.root.after(0, self.view.show_info, "完成", "没有发现缺失文件")
                return

            if analysis_result.code == "csv_failed":
                self.root.after(0, logger.error, "创建CSV文件失败。")
                self.root.after(0, self.view.update_log, "创建CSV文件失败。")
                self.root.after(0, self.update_status, "分析完成，但创建CSV失败")
                self.root.after(0, self.view.show_error, "错误", "创建CSV文件失败")
                return

            if not analysis_result.success:
                self.root.after(0, self.view.update_log, analysis_result.message or "分析失败，请查看日志文件。")
                self.root.after(0, self.update_status, "分析失败")
                self.root.after(0, self.view.show_error, "分析错误", analysis_result.message or "分析失败")
                return

            csv_file = result_data.get("csv_file")
            missing_count = result_data.get("missing_count", 0)
            self.root.after(0, logger.info, f"发现 {missing_count} 个缺失文件。正在创建CSV...")
            self.root.after(0, self.view.update_log, f"发现 {missing_count} 个缺失文件。正在创建CSV...")
            self.root.after(0, logger.info, f"CSV文件已创建: {csv_file}")
            self.root.after(0, self.view.update_log, f"CSV文件已创建: {os.path.basename(csv_file)}")
            self.root.after(0, self.update_status, "分析完成，准备搜索链接...")
            self.root.after(0, self.search_links, csv_file)

        except Exception as e:
             # Log detailed error from thread
             logger.error(f"分析线程执行过程中出错: {workflow_file}", exc_info=True)
             # Update UI thread safely
             self.root.after(0, self.view.update_log, f"分析过程中出错，请查看日志文件: {os.path.basename(workflow_file)}") # User message
             self.root.after(0, self.update_status, "分析失败")
             self.root.after(0, self.view.show_error, "分析错误", f"分析文件时出错:\n{e}")


    def search_links(self, csv_file):
        logger.info(f"Search links initiated for: {csv_file}")
        if not os.path.exists(csv_file):
             logger.error(f"Search cancelled: CSV file not found at {csv_file}")
             self.root.after(0, self.view.show_error, "错误", f"搜索失败：CSV文件不存在 {os.path.basename(csv_file)}")
             return

        self.root.after(0, self.update_status, "正在搜索链接...")
        self.root.after(0, self.view.set_progress, 0, "0%")

        # --- Search Thread ---
        def search_thread_func():
            logger.debug(f"Search thread started for: {csv_file}")
            update_progress_callback = lambda current, total: \
                self.root.after(0, self.view.set_progress, int((current / total) * 100), f"{int((current / total) * 100)}%") if total > 0 else None

            html_result = None
            try:
                self.root.after(0, self.view.update_log, f"开始搜索模型链接: {os.path.basename(csv_file)}") # User message
                search_result = self.workflow_processing_service.search_links(
                    csv_file,
                    progress_callback=update_progress_callback,
                )
                result_data = search_result.data if isinstance(search_result.data, dict) else {}
                html_file = result_data.get("html_file")

                if search_result.code == "html_ready" and html_file:
                    self.html_file_path = html_file
                    logger.info(f"搜索成功！HTML结果: {html_file}")
                    self.root.after(0, self.view.update_log, f"搜索完成！HTML结果: {os.path.basename(html_file)}")
                    self.root.after(0, self.update_status, "搜索完成")
                    self.root.after(0, self.view.set_progress, 100, "100%")
                    self.root.after(0, self.view.enable_view_result_button, True)

                    if self.auto_open_html.get():
                        self.root.after(0, logger.info,"自动打开HTML结果...")
                        self.root.after(0, self.view.update_log,"自动打开HTML结果...") # User message
                        self.root.after(100, lambda: webbrowser.open(f"file:///{self.html_file_path}"))

                    self.root.after(0, self.view.show_info, "完成", "搜索完成，可以查看HTML结果")

                elif search_result.code == "nothing_to_search":
                    logger.info("搜索完成: 无需搜索，模型已处理或存在。")
                    self.root.after(0, self.view.update_log,"无需搜索，所有模型均已处理或存在。")
                    self.root.after(0, self.update_status,"无需搜索")
                    self.root.after(0, self.view.set_progress, 100, "100%")
                elif not search_result.success and search_result.code != "completed_without_html":
                    logger.error("搜索失败: %s", search_result.message)
                    self.root.after(0, self.view.update_log, search_result.message or "搜索失败，请查看日志文件。")
                    self.root.after(0, self.update_status, "搜索失败")
                    self.root.after(0, self.view.show_error, "搜索错误", search_result.message or "搜索失败")
                else:
                    logger.warning(f"搜索完成，但未能生成HTML结果 for {csv_file}")
                    self.root.after(0, self.view.update_log,"搜索完成，但未能生成HTML结果。") # User message
                    self.root.after(0, self.update_status,"搜索未生成HTML")
                    self.root.after(0, self.view.show_info, "完成", "搜索完成，但未生成HTML。")

            except Exception as e:
                logger.error(f"搜索线程执行过程中出错: {csv_file}", exc_info=True)
                self.root.after(0, self.view.update_log, f"搜索过程中出错，请查看日志文件: {os.path.basename(csv_file)}") # User message
                self.root.after(0, self.update_status, "搜索失败")
                self.root.after(0, self.view.show_error, "搜索错误", f"搜索时出错:\n{e}")
            finally:
                logger.debug(f"Search thread finished for: {csv_file}")
                 # Enable buttons?

        threading.Thread(target=search_thread_func, daemon=True).start()

    def view_result(self):
        logger.debug("View result button clicked.")
        path_to_open = self.html_file_path
        if path_to_open and os.path.exists(path_to_open):
            logger.info(f"Opening single result HTML: {path_to_open}")
            webbrowser.open(f"file:///{path_to_open}")
        else:
            logger.warning(f"View result failed: HTML file path '{path_to_open}' not valid or not set.")
            # Try to infer path
            workflow_file = self.view.get_workflow_path()
            inferred_path = None
            if workflow_file:
                 try:
                     output_dir = get_results_folder()
                     if output_dir and os.path.isdir(output_dir): # Check if output_dir is valid
                         date_folders = sorted([d for d in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, d))], reverse=True)
                         if date_folders:
                              latest_date_dir = os.path.join(output_dir, date_folders[0])
                              base_name = os.path.splitext(os.path.basename(workflow_file))[0]
                              potential_html = os.path.join(latest_date_dir, f"{base_name}.html")
                              if os.path.exists(potential_html):
                                  inferred_path = potential_html
                                  logger.debug(f"Inferred HTML path: {inferred_path}")
                 except Exception as e:
                     logger.error(f"Error inferring result path: {e}", exc_info=True)

            if inferred_path:
                 logger.info(f"Opening inferred single result HTML: {inferred_path}")
                 webbrowser.open(f"file:///{inferred_path}")
            else:
                 logger.warning("Could not find or infer HTML result file.")
                 self.view.show_error("错误", "未能找到HTML结果文件。请先成功运行一次分析和搜索。")

    def batch_process(self):
        logger.info("Batch process button clicked.")
        directory = self.view.get_workflow_dir()
        if not directory:
            logger.warning("Batch process cancelled: No directory selected.")
            self.view.show_error("错误", "请选择工作流目录")
            return
        if not os.path.isdir(directory):
            logger.error(f"Batch process cancelled: Directory not found at {directory}")
            self.view.show_error("错误", f"目录不存在: {directory}")
            return

        file_pattern = self.view.get_file_pattern()
        if not file_pattern: file_pattern = "*.json;*"
        logger.debug(f"Batch processing directory: {directory} with pattern: {file_pattern}")

        self.view.clear_batch_results()
        self.update_status("准备批量处理...")
        self.view.set_batch_progress(0,"0%")
        self.batch_summary_file_path = None

        # --- Batch Thread ---
        def batch_thread_func():
            logger.info(f"Batch processing thread started for directory: {directory}")
            update_batch_progress = lambda current, total: \
                 self.root.after(0, self.view.set_batch_progress, int((current / total) * 100), f"{int((current / total) * 100)}%") if total > 0 else None

            try:
                self.root.after(0, self.view.update_log, f"开始批量处理目录: {directory}") # User message
                batch_result = self.workflow_processing_service.batch_process(
                    directory,
                    file_pattern,
                    progress_callback=update_batch_progress,
                )
                batch_data = batch_result.data if isinstance(batch_result.data, dict) else {}
                all_missing_summary_csv = batch_data.get("all_missing_summary_csv")
                processed_summary_csv = batch_data.get("processed_summary_csv")
                batch_rows = batch_data.get("batch_rows", [])

                if all_missing_summary_csv:
                    self.batch_summary_file_path = all_missing_summary_csv
                    self.root.after(0, logger.info, f"找到汇总缺失文件: {all_missing_summary_csv}")
                    self.root.after(0, self.view.update_log, f"找到汇总缺失文件: {os.path.basename(all_missing_summary_csv)}")

                if batch_result.code == "no_missing":
                    logger.info("Batch process complete: No missing files found.")
                    self.root.after(0, self.view.update_log,"批量处理完成，所有工作流均未发现缺失文件。")
                    self.root.after(0, self.update_status,"批量处理完成: 无缺失")
                    self.root.after(0, self.view.set_batch_progress, 100, "100%")
                    self.root.after(0, self.view.show_info, "完成", "批量处理完成，未发现缺失文件。")

                elif batch_result.code == "summary_ready" and processed_summary_csv:
                    logger.info(f"批量处理完成，结果摘要: {processed_summary_csv}")
                    self.root.after(0, self.view.update_log,f"批量处理完成，结果摘要: {os.path.basename(processed_summary_csv)}")
                    self.root.after(0, self.update_status,"批量处理完成，准备搜索...")
                    self.root.after(0, self.view.set_batch_progress, 100, "100%")

                    self.root.after(0, self.view.clear_batch_results)
                    for workflow_name, missing_count in batch_rows:
                        self.root.after(0, self.view.add_batch_result, workflow_name, missing_count, "已分析")

                    if all_missing_summary_csv:
                        self.root.after(0, self.update_status,"开始搜索汇总链接...")
                        self.root.after(0, self.view.set_batch_progress, 0, "0%")

                        update_search_progress = lambda current, total: \
                            self.root.after(0, self.view.set_batch_progress, int((current / total) * 100), f"{int((current / total) * 100)}%") if total > 0 else None

                        logger.info(f"Starting summary search for: {all_missing_summary_csv}")
                        search_result = self.workflow_processing_service.search_links(
                            all_missing_summary_csv,
                            progress_callback=update_search_progress,
                        )
                        search_data = search_result.data if isinstance(search_result.data, dict) else {}
                        summary_html_file = search_data.get("html_file")

                        if search_result.code == "html_ready" and summary_html_file:
                            self.batch_summary_file_path = summary_html_file
                            logger.info(f"汇总搜索成功！HTML结果: {summary_html_file}")
                            self.root.after(0, self.view.update_log,f"汇总搜索完成！HTML结果: {os.path.basename(summary_html_file)}")
                            self.root.after(0, self.update_status,"批量搜索完成")
                            self.root.after(0, self.view.set_batch_progress, 100, "100%")
                            if self.auto_open_html.get():
                                self.root.after(0, logger.info,"自动打开HTML结果...")
                                self.root.after(0, self.view.update_log,"自动打开HTML结果...")
                                self.root.after(100, lambda: webbrowser.open(f"file:///{summary_html_file}"))
                            self.root.after(0, self.view.show_info, "完成", "批量处理和搜索完成")
                        elif not search_result.success and search_result.code != "completed_without_html":
                            logger.error("汇总搜索失败: %s", search_result.message)
                            self.root.after(0, self.view.update_log, search_result.message or "汇总搜索失败。")
                            self.root.after(0, self.update_status,"汇总搜索失败")
                            self.root.after(0, self.view.show_error, "错误", search_result.message or "汇总搜索失败。")
                        else:
                            logger.warning(f"汇总搜索完成，但未能生成HTML结果 for {all_missing_summary_csv}")
                            self.root.after(0, self.view.update_log,"汇总搜索完成，但未能生成HTML结果。")
                            self.root.after(0, self.update_status,"汇总搜索未生成HTML")
                            self.root.after(0, self.view.show_info, "完成", "批量搜索完成，但未生成HTML。")
                    else:
                        logger.warning("未找到'汇总缺失文件.csv'，无法执行搜索。")
                        self.root.after(0, self.view.update_log,"未找到'汇总缺失文件.csv'，无法执行搜索。")
                        self.root.after(0, self.update_status,"批量处理完成，未找到汇总文件")
                        self.root.after(0, self.view.show_warning, "警告", "未找到汇总缺失文件，无法进行链接搜索。")
                elif not batch_result.success:
                    logger.error(f"批量处理失败: {batch_result.message}")
                    self.root.after(0, self.view.update_log, batch_result.message or "批量处理失败。")
                    self.root.after(0, self.update_status,"批量处理失败")
                    self.root.after(0, self.view.show_error, "错误", batch_result.message or "批量处理失败。")
                else:
                    logger.error(f"批量处理失败或未生成预期的结果文件. Result: {batch_result.code}")
                    self.root.after(0, self.view.update_log,"批量处理失败或未生成预期的结果文件。")
                    self.root.after(0, self.update_status,"批量处理失败")
                    self.root.after(0, self.view.show_error, "错误", "批量处理失败。")

            except Exception as e:
                 logger.error(f"批量处理线程执行过程中发生严重错误: {directory}", exc_info=True)
                 self.root.after(0, self.view.update_log, f"批量处理过程中发生严重错误，请查看日志文件。") # User message
                 self.root.after(0, self.update_status, "批量处理失败")
                 self.root.after(0, self.view.show_error, "严重错误", f"批量处理时出错:\n{e}")
            finally:
                logger.info(f"Batch processing thread finished for directory: {directory}")
                 # Enable buttons?

        threading.Thread(target=batch_thread_func, daemon=True).start()

    def view_batch_html(self):
        logger.debug("View batch HTML button clicked.")
        result_path = self.batch_summary_file_path
        logger.info(f"Attempting to view batch result: {result_path}")

        if result_path and result_path.lower().endswith(".csv"):
            self.view.update_log(f"尝试为 {os.path.basename(result_path)} 生成HTML视图...")

        try:
            result = self.result_view_service.resolve_viewable_result(result_path)
        except Exception as e:
            logger.error("生成HTML视图时出错: %s", result_path, exc_info=True)
            self.view.update_log(f"生成HTML视图时出错: {e}")
            self.view.show_error("错误", f"生成HTML视图时出错: {e}")
            return

        if result.success:
            open_path = result.data["open_path"]
            logger.info("Opening batch result: %s", open_path)
            webbrowser.open(f"file:///{open_path}")
            return

        result_data = result.data if isinstance(result.data, dict) else {}
        source_path = result_data.get("source_path", result_path)
        extension = result_data.get("extension", "")

        if not source_path:
            logger.warning("View batch HTML failed: Path not valid or not set.")
            self.view.show_error("错误", "未找到可查看的结果文件。请先运行批量处理。")
            return

        if extension:
            logger.error("Cannot view batch result: Unknown file type: %s", source_path)
            self.view.show_error("错误", f"未知的文件类型: {os.path.basename(source_path)}")
            return

        logger.error("无法生成或找到HTML视图 for %s", source_path)
        self.view.update_log("无法生成或找到HTML视图。")
        self.view.show_error("错误", "无法生成HTML视图。")

    def apply_theme(self):
        theme = self.view.get_selected_theme()
        logger.info(f"Applying theme: {theme}")
        try:
            style = ttk.Style()
            if theme in style.theme_names():
                style.theme_use(theme)
                self._loaded_theme = theme # Update internal state
                self.view.update_log(f"主题已应用: {theme}") # User message
            else:
                 logger.warning(f"Cannot apply theme: Unknown theme name '{theme}'")
                 self.view.show_warning("主题错误", f"未知主题: {theme}")
        except Exception as e:
             logger.error(f"应用主题时出错: {theme}", exc_info=True)
             self.view.show_error("主题错误", f"应用主题时出错: {e}")

    def save_settings(self):
        logger.info("Save settings button clicked.")
        try:
            settings_to_save = self._collect_settings_for_save()

            self.view.update_log("正在保存设置...") # User message
            success = self.settings_model.save(settings_to_save)

            if success:
                self.root.after(0, self.view.show_info, "成功", "设置已保存")
                self.root.after(0, self.view.update_log, "设置已保存。") # User message
            else:
                # SettingsModel already logs the detailed error
                self.root.after(0, self.view.show_error, "错误", "保存设置失败，请查看日志或控制台输出。")
                self.root.after(0, self.view.update_log, "保存设置失败。") # User message

        except Exception as e:
            logger.error("保存设置时发生意外错误", exc_info=True)
            self.root.after(0, self.view.show_error, "错误", f"保存设置时发生意外错误: {e}")
            self.root.after(0, self.view.update_log, "保存设置时发生意外错误。") # User message

    def load_settings(self):
        logger.info("Loading settings...")
        # Use root.after(0,...) for UI updates in case this is called later from non-main thread?
        # For now, assume it's called safely from initialize() in main thread.
        self.view.update_log("正在加载设置...") # User message
        loaded_settings = self.settings_model.load()

        # Update controller state variables
        self.auto_open_html.set(loaded_settings.get('auto_open_html', True))
        self.random_theme.set(loaded_settings.get('random_theme', True))
        self._loaded_theme = loaded_settings.get('theme', 'cosmo')
        self._loaded_chrome_path = loaded_settings.get('chrome_path', '')
        self._loaded_comfyui_path = loaded_settings.get('comfyui_path', '')
        self._loaded_comfyui_python_path = loaded_settings.get('comfyui_python_path', '')
        self._loaded_retention_days = loaded_settings.get('retention_days', 30)
        logger.debug(
            f"Loaded settings values: AutoOpen={self.auto_open_html.get()}, "
            f"RandomTheme={self.random_theme.get()}, Theme={self._loaded_theme}, "
            f"Chrome='{self._loaded_chrome_path}', ComfyUI='{self._loaded_comfyui_path}', "
            f"ComfyUIPython='{self._loaded_comfyui_python_path}', "
            f"Days={self._loaded_retention_days}"
        )

        chrome_result = self.runtime_service.resolve_chrome_path(self._loaded_chrome_path)
        if chrome_result.success:
            self._loaded_chrome_path = chrome_result.data["chrome_path"]
            if chrome_result.data.get("source") == "detected":
                logger.info(f"自动检测到Chrome路径: {self._loaded_chrome_path}")
                self.view.update_log(f"自动检测到Chrome路径: {self._loaded_chrome_path}") # User message

        # Determine and apply theme
        theme_to_apply = self._loaded_theme
        if self.random_theme.get():
             valid_themes = ["cosmo", "flatly", "litera", "minty", "lumen", "sandstone",
                           "yeti", "pulse", "united", "morph", "journal", "darkly",
                           "superhero", "solar", "cyborg"]
             try: theme_to_apply = random.choice(valid_themes); self._loaded_theme = theme_to_apply # Store choice
             except IndexError: theme_to_apply = "cosmo"
             logger.info(f"加载设置：启用随机主题，应用: {theme_to_apply}")
             self.view.update_log(f"加载设置：启用随机主题，选择: {theme_to_apply}") # User message
        else:
             logger.info(f"加载设置：使用上次保存/默认的主题: {theme_to_apply}")
             self.view.update_log(f"加载设置：使用上次保存/默认的主题: {theme_to_apply}") # User message

        # Apply theme immediately (view should be ready via initialize sequence)
        self.view.set_selected_theme(theme_to_apply)
        self.apply_theme()

        self.view.update_log("设置加载完成。") # User message
        # Don't set status to "Ready" here, let initialize do it after welcome msg.

    def _collect_settings_for_save(self):
        retention_days_from_view = self.view.get_retention_days()
        logger.debug(f"Value from view for retention_days: {retention_days_from_view}")

        settings_to_save = {
            'auto_open_html': self.auto_open_html.get(),
            'chrome_path': self.view.get_chrome_path(),
            'comfyui_path': self.view.get_comfyui_path(),
            'comfyui_python_path': self.view.get_comfyui_python_path() if hasattr(self.view, "get_comfyui_python_path") else "",
            'random_theme': self.random_theme.get(),
            'theme': self.view.get_selected_theme(),
            'retention_days': retention_days_from_view
        }
        logger.debug(f"Data to be saved: {settings_to_save}")
        return settings_to_save

    def save_comfyui_launch_settings(self):
        logger.info("Save ComfyUI launch settings button clicked.")
        try:
            settings_to_save = self._collect_settings_for_save()
            self.view.append_comfyui_launch_log("正在保存 ComfyUI 启动配置...")
            success = self.settings_model.save(settings_to_save)
            if success:
                self._loaded_comfyui_path = settings_to_save["comfyui_path"]
                self._loaded_comfyui_python_path = settings_to_save["comfyui_python_path"]
                self.update_status("ComfyUI 启动配置已保存")
                self.view.append_comfyui_launch_log("ComfyUI 启动配置已保存。")
            else:
                self.update_status("保存 ComfyUI 启动配置失败")
                self.view.append_comfyui_launch_log("保存 ComfyUI 启动配置失败。")
        except Exception as e:
            logger.error("保存 ComfyUI 启动配置时发生意外错误", exc_info=True)
            self.update_status("保存 ComfyUI 启动配置时发生意外错误")
            self.view.append_comfyui_launch_log("保存 ComfyUI 启动配置时发生意外错误。")
            self.view.append_comfyui_launch_log(str(e))

    def validate_comfyui_launch_paths(self):
        logger.info("Validate ComfyUI launch paths button clicked.")
        result = self.comfyui_launcher_service.validate_paths(
            self.view.get_comfyui_path(),
            self.view.get_comfyui_python_path(),
        )
        if result.success:
            self.view.append_comfyui_launch_log("路径校验通过。")
            self.update_status("ComfyUI 路径校验通过")
            return True

        self.view.append_comfyui_launch_log(result.message)
        self.update_status("ComfyUI 路径校验失败")
        return False

    def start_comfyui(self):
        logger.info("Start ComfyUI button clicked.")
        self._start_comfyui_with_mode(ComfyUILauncherService.DEFAULT_MODE)

    def _start_comfyui_with_mode(self, launch_mode):
        validation_result = self.comfyui_launcher_service.validate_paths(
            self.view.get_comfyui_path(),
            self.view.get_comfyui_python_path(),
            launch_mode=launch_mode,
        )
        if not validation_result.success:
            self.view.append_comfyui_launch_log(validation_result.message)
            self.update_status("ComfyUI 启动前校验失败")
            self.refresh_comfyui_launch_runtime()
            return

        command_text = " ".join(validation_result.data["command"])
        self.view.clear_comfyui_launch_log()
        self.view.append_comfyui_launch_log(f"启动命令: {command_text}")
        self.view.append_comfyui_launch_log(f"访问地址: {validation_result.data['url']}")
        if launch_mode == ComfyUILauncherService.MANAGER_ONLY_MODE:
            self.view.append_comfyui_launch_log("启动模式: 仅加载 ComfyUI-Manager")
        self.view.set_comfyui_launch_status("启动中")
        self.view.set_comfyui_launch_details(pid="", command=command_text)
        self.view.set_comfyui_launch_button_states(start_enabled=False, stop_enabled=False)
        self.update_status("ComfyUI 启动中...")
        self._comfyui_browser_opened = False

        result = self.comfyui_launcher_service.start(
            validation_result.data["comfyui_path"],
            validation_result.data["python_path"],
            launch_mode=launch_mode,
        )
        if not result.success:
            self.view.append_comfyui_launch_log(result.message)
            self.update_status("ComfyUI 启动失败")
            self.refresh_comfyui_launch_runtime()
            return

        self.view.append_comfyui_launch_log("ComfyUI 已启动，正在读取日志...")
        self.refresh_comfyui_launch_runtime(snapshot=result.data)
        self._schedule_comfyui_runtime_poll()

    def stop_comfyui(self):
        logger.info("Stop ComfyUI button clicked.")
        result = self.comfyui_launcher_service.stop()
        self.view.append_comfyui_launch_log(result.message)
        self.update_status("ComfyUI 已停止" if result.code == "stop_completed" else "当前没有运行中的 ComfyUI")
        self._comfyui_browser_opened = False
        self.refresh_comfyui_launch_runtime(snapshot=result.data)

    def clear_comfyui_launch_log(self):
        self.view.clear_comfyui_launch_log()

    def clear_missing_installer_log(self):
        self.view.clear_missing_installer_log()

    def add_missing_installer_quick_path(self, auto_analyze=False):
        raw_path = self.view.get_missing_installer_quick_path()
        self._add_missing_installer_input_path(raw_path, auto_analyze=auto_analyze)

    def paste_missing_installer_path(self):
        try:
            raw_path = self.root.clipboard_get()
        except tk.TclError:
            self.view.append_missing_installer_log("剪贴板中没有可用路径。")
            return

        self.view.set_missing_installer_quick_path(raw_path)
        self._add_missing_installer_input_path(raw_path, auto_analyze=True)

    def browse_missing_installer_workflow_files(self):
        file_paths = filedialog.askopenfilenames(
            title="选择工作流 JSON 文件",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
        )
        if not file_paths:
            return

        existing_count = len(self._missing_installer_selected_paths)
        selected_paths = list(dict.fromkeys(self._missing_installer_selected_paths + list(file_paths)))
        self._set_missing_installer_paths(selected_paths)
        self.view.append_missing_installer_log(f"已选择 {len(file_paths)} 个工作流文件。")
        if existing_count == 0 and len(file_paths) == 1:
            self.view.append_missing_installer_log("已自动开始分析单个工作流。")
            self.analyze_missing_installer_workflows()

    def browse_missing_installer_workflow_folder(self):
        directory = filedialog.askdirectory(title="选择工作流目录")
        if not directory:
            return

        existing_count = len(self._missing_installer_selected_paths)
        selected_paths = list(dict.fromkeys(self._missing_installer_selected_paths + [directory]))
        self._set_missing_installer_paths(selected_paths)
        self.view.append_missing_installer_log(f"已添加工作流目录: {directory}")
        if existing_count == 0:
            self.view.append_missing_installer_log("已自动开始分析当前目录。")
            self.analyze_missing_installer_workflows()

    def clear_missing_installer_workflow_inputs(self):
        self._set_missing_installer_paths([])
        self.view.append_missing_installer_log("已清空待分析的工作流。")

    def go_to_missing_installer_step(self, step_index):
        if step_index == self._missing_installer_step:
            return
        if step_index not in self._missing_installer_completed_steps:
            return

        self._missing_installer_step = step_index
        self._sync_missing_node_installer_view()

    def analyze_missing_installer_workflows(self):
        if not self._missing_installer_selected_paths:
            self.update_status("请先选择工作流")
            self.view.append_missing_installer_log("请先选择一个或多个工作流 JSON 文件。")
            return

        runtime_status = self.refresh_missing_node_installer_runtime()
        if not runtime_status["comfyui_ready"] or not runtime_status["manager_ready"]:
            was_pending = self._pending_missing_analysis
            self._pending_missing_analysis = True
            self._pending_runtime_wait_deadline = time.monotonic() + 60.0
            self.update_status("正在启动 ComfyUI 并等待 Manager 就绪")
            if not self._missing_runtime_wait_logged:
                self.view.append_missing_installer_log("ComfyUI 或 Manager 尚未就绪，正在尝试启动后继续分析。")
                self._missing_runtime_wait_logged = True
            if runtime_status["comfyui_ready"] and not runtime_status["manager_ready"]:
                self._schedule_manager_runtime_check(force=True)
            elif not self.comfyui_launcher_service.is_running() and not self.comfyui_launcher_service.is_service_port_open():
                if not was_pending:
                    self.start_comfyui_for_missing_installer()
            return

        result = self.missing_node_install_orchestrator.prepare_install_plan(self._missing_installer_selected_paths)
        if not result.success:
            self.update_status("缺失节点分析失败")
            self.view.append_missing_installer_log(result.message)
            return

        self._pending_missing_analysis = False
        self._pending_runtime_wait_deadline = 0.0
        self._missing_runtime_wait_logged = False
        self._missing_installer_analysis_result = result.data["analysis"]
        self._missing_installer_install_plan = result.data["install_plan"]
        self._missing_installer_preflight_result = None
        self._missing_installer_manual_items = result.data["manual_items"]
        self._missing_installer_recheck_paths = list(result.data["workflow_files"])
        self._missing_installer_completed_steps = {0}
        self._missing_installer_step = 1
        self._missing_installer_restart_available = False

        self._sync_missing_node_installer_view()
        self.update_status("缺失节点分析完成")
        self.view.append_missing_installer_log(
            f"分析完成：{result.data['analysis']['total_workflows']} 个工作流，"
            f"{result.data['analysis']['missing_count']} 个缺失节点，"
            f"{self._count_missing_installer_actionable_items()} 个可执行候选项。"
        )

    def advance_missing_installer_to_selection(self):
        if self._missing_installer_analysis_result is None:
            self.view.append_missing_installer_log("请先完成缺失节点分析。")
            return

        self._missing_installer_completed_steps = {0, 1}
        self._missing_installer_step = 2
        self._sync_missing_node_installer_view()

    def run_missing_installer_dependency_preflight(self):
        if not self._missing_installer_install_plan:
            self.view.append_missing_installer_log("当前没有可预检的插件包。")
            return

        result = self.dependency_preflight_service.evaluate(self._missing_installer_install_plan)
        if not result.success:
            self.update_status("依赖预检失败")
            self.view.append_missing_installer_log(result.message)
            return

        self._missing_installer_preflight_result = result.data
        blocked_ids = set(result.data.get("blocked_package_ids", []))
        preflight_rows = {item["id"]: item for item in result.data.get("rows", [])}

        for item in self._missing_installer_install_plan:
            preflight_row = preflight_rows.get(item["id"], {})
            item["preflight_strategy"] = preflight_row.get("strategy", "install")
            item["preflight_risk_level"] = preflight_row.get("risk_level", "低")
            item["preflight_conclusion"] = preflight_row.get("conclusion", "safe")
            item["preflight_conclusion_label"] = preflight_row.get("conclusion_label", "可直接安装")
            item["preflight_reasons"] = list(preflight_row.get("reasons") or [])
            if item["id"] in blocked_ids:
                item["selected"] = False
                item["status"] = "阻断安装"

        self._missing_installer_completed_steps = {0, 1, 2}
        self._missing_installer_step = 3
        self._sync_missing_node_installer_view()
        self.update_status("依赖预检完成")
        for line in result.data.get("logs", []):
            self.view.append_missing_installer_log(line)

    def toggle_missing_installer_package_selection(self):
        package_id = self.view.get_selected_missing_installer_package_id()
        if not package_id:
            return

        for item in self._missing_installer_install_plan:
            if item["id"] == package_id:
                if not item.get("selectable", False):
                    return
                item["selected"] = not item.get("selected", True)
                break

        self._sync_missing_node_installer_view()

    def start_missing_installer_installation(self, *, safe_only=False, ignore_preflight=False):
        if not self._missing_installer_install_plan:
            self.view.append_missing_installer_log("当前没有可安装的插件包。")
            return

        if safe_only and not self._missing_installer_preflight_result:
            self.view.append_missing_installer_log("仅安装安全项需要先完成依赖预检。")
            return

        selected_packages = [
            item
            for item in self._missing_installer_install_plan
            if item.get("selected", True) and item.get("queue_action")
        ]
        if not selected_packages:
            self.view.append_missing_installer_log("请至少保留一个可执行的候选项。")
            return

        if self._missing_installer_preflight_result and not ignore_preflight:
            execution_plan_result = self.dependency_install_planner.build_execution_plan(
                selected_packages,
                self._missing_installer_preflight_result,
                safe_only=safe_only,
            )
            for blocked in execution_plan_result.data.get("blocked_packages", []) if execution_plan_result.data else []:
                self.view.append_missing_installer_log(
                    f"{blocked['title']} 被依赖预检拦截：{'；'.join(blocked.get('reasons') or [])}"
                )
            for skipped in execution_plan_result.data.get("skipped_packages", []) if execution_plan_result.data else []:
                self.view.append_missing_installer_log(f"{skipped['title']} 已从“仅安装安全项”中跳过。")
            if not execution_plan_result.success:
                self.update_status("依赖预检阻断安装")
                self.view.append_missing_installer_log(execution_plan_result.message)
                self._sync_missing_node_installer_view()
                return

            executable_packages = execution_plan_result.data.get("executable_packages", [])
        else:
            executable_packages = list(selected_packages)
            self.view.append_missing_installer_log("已跳过依赖预检，直接交给 ComfyUI-Manager 安装。")

        self._missing_installer_completed_steps = {0, 1, 2, 3}
        self._missing_installer_step = 4

        selected_ids = {item["id"] for item in executable_packages}
        self._update_missing_installer_package_status(selected_ids, "已排队")
        result = self.missing_node_install_orchestrator.execute_install_plan(executable_packages)

        for failed in result.data.get("failed_packages", []) if result.data else []:
            self._update_missing_installer_package_status({failed["id"]}, "失败")
            self.view.append_missing_installer_log(f"{failed['title']} 入队失败：{failed['message']}")

        if not result.success:
            self.update_status("批量安装入队失败")
            self.view.append_missing_installer_log(result.message)
            self._sync_missing_node_installer_view()
            return

        self._missing_installer_restart_available = False
        self._sync_missing_node_installer_view()
        self.update_status("缺失节点安装已提交")
        self.view.append_missing_installer_log(result.message)
        self.view.set_missing_installer_queue_progress("安装队列处理中...")
        self._schedule_manager_queue_poll()

    def restart_comfyui_and_recheck_missing_nodes(self):
        if not self._missing_installer_recheck_paths:
            self.view.append_missing_installer_log("没有可复检的工作流。")
            return

        self._pending_missing_recheck = True
        self._pending_runtime_wait_deadline = time.monotonic() + 60.0
        self._missing_runtime_wait_logged = False
        self._missing_installer_restart_available = False
        self.view.set_missing_installer_restart_button_visible(False)
        self.view.append_missing_installer_log("正在重启 ComfyUI，重启完成后将自动复检。")
        self.update_status("正在重启 ComfyUI")
        self.stop_comfyui()
        self._start_comfyui_with_mode(self._missing_installer_launch_mode)

    def refresh_missing_node_installer_runtime(self, snapshot=None):
        runtime_data = snapshot or self.comfyui_launcher_service.get_runtime_snapshot().data
        comfyui_state = runtime_data.get("state", "idle")
        port_open = self.comfyui_launcher_service.is_service_port_open()
        waiting_runtime = self._is_waiting_for_runtime()
        comfyui_label = self._map_comfyui_runtime_state(comfyui_state)
        manager_label = "未启动"
        manager_ready = False

        comfyui_ready = port_open or comfyui_state == "running"
        if port_open and comfyui_state != "running":
            comfyui_label = "运行中"
        elif waiting_runtime and not port_open:
            comfyui_label = "启动中"

        if port_open:
            manager_label = self._manager_runtime_status_label
            manager_ready = self._manager_runtime_ready
            self._schedule_manager_runtime_check()
        else:
            self._manager_runtime_status_label = "未启动"
            self._manager_runtime_ready = False
            self._manager_runtime_check_inflight = False
            self._manager_runtime_last_check = 0.0

        self.view.set_missing_installer_runtime_status(
            comfyui_status=comfyui_label,
            manager_status=manager_label,
            start_enabled=not comfyui_ready and not waiting_runtime,
        )
        return {"comfyui_ready": comfyui_ready, "manager_ready": manager_ready}

    def start_comfyui_for_missing_installer(self):
        self._pending_missing_analysis = True
        self._pending_runtime_wait_deadline = time.monotonic() + 60.0
        self._missing_runtime_wait_logged = False
        self.view.append_missing_installer_log("正在以完整模式启动 ComfyUI，以便按 Manager 的缺失语义进行分析。")
        self._start_comfyui_with_mode(self._missing_installer_launch_mode)

    def _sync_missing_node_installer_view(self):
        self.view.set_missing_installer_steps(
            current_step=self._missing_installer_step,
            completed_steps=self._missing_installer_completed_steps,
        )
        self.view.show_missing_installer_step(self._missing_installer_step)
        self.view.set_missing_installer_selected_paths(self._missing_installer_selected_paths)
        self.view.set_missing_installer_analysis_summary(self._build_missing_installer_summary())
        self.view.load_missing_installer_packages(self._missing_installer_install_plan)
        self.view.set_missing_installer_preflight_summary(self._build_missing_installer_preflight_summary())
        self.view.load_missing_installer_preflight_rows(
            (self._missing_installer_preflight_result or {}).get("rows", [])
        )
        self.view.set_missing_installer_preflight_actions(
            can_install=bool(self._missing_installer_install_plan) and bool(self._missing_installer_preflight_result),
            safe_only_enabled=bool(
                self._missing_installer_preflight_result
                and any(
                    item.get("conclusion") in {"safe", "safe_with_policy"}
                    for item in self._missing_installer_preflight_result.get("rows", [])
                )
            ),
            blocked_count=len((self._missing_installer_preflight_result or {}).get("blocked_package_ids", [])),
        )
        self.view.load_missing_installer_manual_items(self._missing_installer_manual_items)
        self.view.load_missing_installer_install_rows(self._missing_installer_install_plan)
        self.view.set_missing_installer_restart_button_visible(self._missing_installer_restart_available)

    def _build_missing_installer_summary(self):
        analysis = self._missing_installer_analysis_result or {}
        return {
            "total_workflows": analysis.get("total_workflows", 0),
            "total_node_types": analysis.get("total_node_types", 0),
            "missing_count": analysis.get("missing_count", 0),
            "installable_count": self._count_missing_installer_actionable_items(),
            "manual_count": len(self._missing_installer_manual_items),
        }

    def _build_missing_installer_preflight_summary(self):
        summary = (self._missing_installer_preflight_result or {}).get("summary", {})
        return {
            "safe": summary.get("safe", 0),
            "safe_with_policy": summary.get("safe_with_policy", 0),
            "warning": summary.get("warning", 0),
            "blocked": summary.get("blocked", 0),
        }

    def _count_missing_installer_actionable_items(self):
        return sum(1 for item in self._missing_installer_install_plan if item.get("queue_action"))

    def _set_missing_installer_paths(self, paths):
        self._missing_installer_selected_paths = list(paths or [])
        self._missing_installer_analysis_result = None
        self._missing_installer_install_plan = []
        self._missing_installer_preflight_result = None
        self._missing_installer_manual_items = []
        self._missing_installer_recheck_paths = []
        self._missing_installer_restart_available = False
        self._missing_installer_completed_steps = set()
        self._missing_installer_step = 0
        self._sync_missing_node_installer_view()

    def _add_missing_installer_input_path(self, raw_path, *, auto_analyze=False):
        path = os.path.abspath((raw_path or "").strip().strip('"'))
        if not path:
            self.view.append_missing_installer_log("请输入或粘贴工作流文件/目录路径。")
            return

        if not os.path.exists(path):
            self.view.append_missing_installer_log(f"路径不存在: {path}")
            return

        if not os.path.isdir(path) and not path.lower().endswith(".json"):
            self.view.append_missing_installer_log("只支持 JSON 工作流文件或目录路径。")
            return

        selected_paths = list(dict.fromkeys(self._missing_installer_selected_paths + [path]))
        if selected_paths == self._missing_installer_selected_paths:
            self.view.append_missing_installer_log(f"已存在路径: {path}")
        else:
            self._set_missing_installer_paths(selected_paths)
            if os.path.isdir(path):
                self.view.append_missing_installer_log(f"已添加工作流目录: {path}")
            else:
                self.view.append_missing_installer_log(f"已添加工作流文件: {os.path.basename(path)}")

        if auto_analyze and len(selected_paths) == 1:
            self.view.append_missing_installer_log("已自动开始分析单个输入。")
            self.analyze_missing_installer_workflows()

    def _update_missing_installer_package_status(self, package_ids, status):
        for item in self._missing_installer_install_plan:
            if item["id"] in package_ids:
                item["status"] = status

    def _schedule_manager_queue_poll(self):
        if self._manager_queue_poll_scheduled:
            return
        self._manager_queue_poll_scheduled = True
        self.root.after(500, self._poll_manager_queue)

    def _poll_manager_queue(self):
        self._manager_queue_poll_scheduled = False
        result = self.comfyui_manager_api_service.get_queue_status()
        if not result.success:
            self.view.append_missing_installer_log(result.message)
            return

        status = result.data
        total_count = status.get("total_count", 0)
        done_count = status.get("done_count", 0)
        is_processing = status.get("is_processing", False)
        in_progress_count = status.get("in_progress_count", 0)

        if in_progress_count > 0:
            queued_ids = {
                item["id"]
                for item in self._missing_installer_install_plan
                if item.get("status") in {"已排队", "待安装", "待修复"}
            }
            self._update_missing_installer_package_status(queued_ids, "安装中")

        self.view.set_missing_installer_queue_progress(f"安装队列进度：{done_count}/{total_count}")
        self._sync_missing_node_installer_view()

        if is_processing:
            self._schedule_manager_queue_poll()
            return

        finished_ids = {
            item["id"]
            for item in self._missing_installer_install_plan
            if item.get("status") in {"已排队", "安装中"}
        }
        if finished_ids:
            self._update_missing_installer_package_status(finished_ids, "需重启生效")
            self._missing_installer_restart_available = True
            self.view.append_missing_installer_log("安装队列已完成，请重启 ComfyUI 后复检。")
            self._sync_missing_node_installer_view()

    def _run_missing_node_recheck(self):
        result = self.missing_node_install_orchestrator.recheck_after_restart(self._missing_installer_recheck_paths)
        if not result.success:
            self.view.append_missing_installer_log(result.message)
            self.update_status("复检失败")
            return

        self._pending_missing_recheck = False
        self._pending_runtime_wait_deadline = 0.0
        self._missing_runtime_wait_logged = False
        self._missing_installer_analysis_result = result.data["analysis"]
        self._missing_installer_install_plan = result.data["install_plan"]
        self._missing_installer_preflight_result = None
        self._missing_installer_manual_items = result.data["manual_items"]
        self._missing_installer_completed_steps = {0, 1, 2, 3, 4}
        self._missing_installer_step = 4
        self._missing_installer_restart_available = False
        self._sync_missing_node_installer_view()

        if not self._missing_installer_analysis_result.get("missing_count") and not self._missing_installer_manual_items:
            self.view.append_missing_installer_log("复检完成，缺失节点已全部解决。")
            self.update_status("缺失节点已解决")
        else:
            self.view.append_missing_installer_log("复检完成，仍有部分节点需要继续处理。")
            self.update_status("复检完成")

    def refresh_comfyui_launch_runtime(self, snapshot=None):
        runtime_data = snapshot or self.comfyui_launcher_service.get_runtime_snapshot().data
        state = runtime_data.get("state", "idle")
        state_label = self._map_comfyui_runtime_state(state)
        pid = runtime_data.get("pid") or ""
        command = runtime_data.get("command") or []
        command_text = " ".join(command) if isinstance(command, (list, tuple)) else str(command or "")

        self.view.set_comfyui_launch_status(state_label)
        self.view.set_comfyui_launch_details(pid=pid, command=command_text)
        self.view.set_comfyui_launch_button_states(
            start_enabled=state not in {"running"},
            stop_enabled=state in {"running"},
        )
        if state == "running" and self._last_comfyui_runtime_state != "running":
            self.update_status("ComfyUI 运行中")

        if state != self._last_comfyui_runtime_state:
            if state == "stopped" and self._last_comfyui_runtime_state == "running":
                self.view.append_comfyui_launch_log("ComfyUI 已停止。")
                self.update_status("ComfyUI 已停止")
            elif state == "failed":
                exit_code = runtime_data.get("exit_code")
                self.view.append_comfyui_launch_log(f"ComfyUI 已退出，退出码: {exit_code}")
                self.update_status("ComfyUI 启动失败")
            self._last_comfyui_runtime_state = state

        self.refresh_missing_node_installer_runtime(snapshot=runtime_data)

    def _schedule_comfyui_runtime_poll(self):
        if self._comfyui_runtime_poll_scheduled:
            return
        self._comfyui_runtime_poll_scheduled = True
        self.root.after(self._get_comfyui_runtime_poll_delay(), self._poll_comfyui_runtime)

    def _poll_comfyui_runtime(self):
        if self._is_shutting_down:
            self._comfyui_runtime_poll_scheduled = False
            return
        self._comfyui_runtime_poll_scheduled = False
        deferred_missing_installer_lines = []
        for line in self.comfyui_launcher_service.drain_output():
            self.view.append_comfyui_launch_log(line)
            classification = self._classify_missing_installer_log_line(line)
            if classification == "priority":
                self.view.append_missing_installer_log(line)
            elif classification == "normal":
                deferred_missing_installer_lines.append(line)

        for line in deferred_missing_installer_lines:
            self.view.append_missing_installer_log(line)

        snapshot = self.comfyui_launcher_service.get_runtime_snapshot().data
        self.refresh_comfyui_launch_runtime(snapshot=snapshot)
        self._maybe_open_comfyui_browser(snapshot)
        runtime_status = {
            "comfyui_ready": self.comfyui_launcher_service.is_service_port_open() or snapshot.get("state") == "running",
            "manager_ready": self._manager_runtime_ready,
        }

        if runtime_status["manager_ready"]:
            if self._pending_missing_analysis:
                self._pending_missing_analysis = False
                self.root.after(0, self.analyze_missing_installer_workflows)
            elif self._pending_missing_recheck:
                self._pending_missing_recheck = False
                self.root.after(0, self._run_missing_node_recheck)

        if snapshot.get("state") == "running" or self._is_waiting_for_runtime() or self.comfyui_launcher_service.is_service_port_open():
            self._schedule_comfyui_runtime_poll()
        elif self._pending_runtime_wait_deadline and time.monotonic() >= self._pending_runtime_wait_deadline:
            self._clear_pending_runtime_wait("等待 ComfyUI/Manager 重启超时，请手动重试。")

    def _get_comfyui_runtime_poll_delay(self):
        if self._is_waiting_for_runtime():
            return 250
        return 100 if self._is_missing_installer_install_active() else 250

    def _is_waiting_for_runtime(self):
        if not (self._pending_missing_analysis or self._pending_missing_recheck):
            return False
        if not self._pending_runtime_wait_deadline:
            return False
        return time.monotonic() < self._pending_runtime_wait_deadline

    def _clear_pending_runtime_wait(self, log_message=""):
        self._pending_runtime_wait_deadline = 0.0
        self._pending_missing_analysis = False
        self._pending_missing_recheck = False
        self._missing_runtime_wait_logged = False
        if log_message:
            self.view.append_missing_installer_log(log_message)
            self.update_status("ComfyUI/Manager 未就绪")

    def _schedule_manager_runtime_check(self, force=False):
        if self._is_shutting_down:
            return

        now = time.monotonic()
        if self._manager_runtime_check_inflight:
            return
        if not force and self._manager_runtime_last_check and now - self._manager_runtime_last_check < 1.5:
            return

        self._manager_runtime_check_inflight = True
        self._manager_runtime_last_check = now
        self._manager_runtime_status_label = "检测中"
        threading.Thread(target=self._run_manager_runtime_check, daemon=True).start()

    def _run_manager_runtime_check(self):
        result = self.comfyui_manager_api_service.get_version()
        self.root.after(0, self._apply_manager_runtime_check_result, result)

    def _apply_manager_runtime_check_result(self, result):
        self._manager_runtime_check_inflight = False
        if self._is_shutting_down:
            return

        if result.success:
            self._manager_runtime_status_label = "可用"
            self._manager_runtime_ready = True
        else:
            self._manager_runtime_status_label = "不可用"
            self._manager_runtime_ready = False

        runtime_status = self.refresh_missing_node_installer_runtime()
        if runtime_status["manager_ready"]:
            self._pending_runtime_wait_deadline = 0.0
            self._missing_runtime_wait_logged = False
            if self._pending_missing_analysis:
                self._pending_missing_analysis = False
                self.root.after(0, self.analyze_missing_installer_workflows)
            elif self._pending_missing_recheck:
                self._pending_missing_recheck = False
                self.root.after(0, self._run_missing_node_recheck)

    def _is_missing_installer_install_active(self):
        if self._missing_installer_step != 4 or self._missing_installer_restart_available:
            return False

        active_statuses = {"已排队", "安装中"}
        return any(
            item.get("status") in active_statuses
            for item in self._missing_installer_install_plan
        )

    @staticmethod
    def _map_comfyui_runtime_state(state):
        state_map = {
            "idle": "未启动",
            "running": "运行中",
            "stopped": "已停止",
            "failed": "启动失败",
        }
        return state_map.get(state, "未启动")

    def _maybe_open_comfyui_browser(self, snapshot):
        if self._comfyui_browser_opened or self._is_shutting_down:
            return
        if snapshot.get("state") != "running":
            return
        if not self.comfyui_launcher_service.is_service_port_open():
            return

        launch_url = snapshot.get("url") or self.comfyui_launcher_service.get_launch_url()
        threading.Thread(target=webbrowser.open, args=(launch_url,), daemon=True).start()
        self._comfyui_browser_opened = True
        self.view.append_comfyui_launch_log(f"已打开浏览器: {launch_url}")

    def shutdown(self):
        if self._is_shutting_down:
            return
        self._is_shutting_down = True
        self._pending_missing_analysis = False
        self._pending_missing_recheck = False
        try:
            self.comfyui_launcher_service.shutdown()
        except Exception:
            logger.exception("Error while shutting down ComfyUI launcher service.")

    @staticmethod
    def _classify_missing_installer_log_line(line):
        normalized = (line or "").strip().lower()
        if not normalized:
            return "ignore"

        if "fetch comfyregistry data:" in normalized:
            return "ignore"

        if "default cache updated:" in normalized:
            return "ignore"

        # tqdm-style progress lines are high-frequency and do not help confirm
        # whether git clone/install actually succeeded.
        if "%|" in normalized and "git clone" not in normalized:
            return "ignore"

        priority_keywords = (
            "git clone",
            "installation was successful",
            "installation failed",
            "install: pip packages",
            "install: install script",
            "security",
            "failed",
            "error",
            "traceback",
        )
        if any(keyword in normalized for keyword in priority_keywords):
            return "priority"

        keywords = (
            "comfyui-manager",
            "manager",
            "install",
            "reinstall",
            "uninstall",
            "git",
            "clone",
            "fetch",
            "pull",
            "pip",
            "security",
            "failed",
            "error",
            "traceback",
        )
        if any(keyword in normalized for keyword in keywords):
            return "normal"

        return "ignore"

    def cleanup_old_files(self):
        logger.info("Cleanup old files button clicked.")
        days = self.view.get_retention_days()
        if self.view.ask_yes_no("确认操作", f"确定要清理 {days} 天前的所有结果文件吗？\n此操作不可撤销!"):
            try:
                logger.info(f"开始清理超过 {days} 天的旧文件...")
                self.view.update_log(f"开始清理 {days} 天前的旧文件...") # User message
                cleanup_result = self.runtime_service.cleanup_results(days)
                cleaned_count = cleanup_result.data["deleted_count"]
                if cleaned_count > 0:
                    logger.info(f"清理完成，删除了 {cleaned_count} 个目录。")
                    self.view.show_info("清理完成", f"已清理 {cleaned_count} 个旧结果目录")
                    self.view.update_log(f"清理完成，删除了 {cleaned_count} 个目录。") # User message
                else:
                    logger.info("清理完成: 没有需要清理的旧文件。")
                    self.view.show_info("清理完成", "没有需要清理的旧文件")
                    self.view.update_log("没有找到需要清理的旧文件。") # User message
            except Exception as e:
                logger.error(f"清理文件时出错 (days={days})", exc_info=True)
                self.view.show_error("清理失败", f"清理文件时出错: {e}")
                self.view.update_log("清理文件时出错，请查看日志文件。") # User message

    def open_results_folder(self):
        logger.info("Open results folder button clicked.")
        try:
            result = self.runtime_service.resolve_results_folder()
            results_dir = result.data["results_dir"]
            if result.success:
                logger.info(f"尝试打开结果文件夹: {results_dir}")
                self.view.update_log(f"尝试打开结果文件夹: {results_dir}") # User message
                webbrowser.open(f"file:///{results_dir}")
                self.view.update_log("结果文件夹已打开。") # User message
            else:
                logger.error(f"无法打开结果文件夹: 路径无效或不存在 '{results_dir}'")
                self.view.show_error("打开文件夹失败", f"结果文件夹路径无效或不存在: {results_dir}")
                self.view.update_log(f"无法打开无效的结果文件夹路径: {results_dir}") # User message
        except Exception as e:
            logger.error("无法打开结果文件夹", exc_info=True)
            self.view.show_error("打开文件夹失败", f"无法打开结果文件夹: {e}")
            self.view.update_log("无法打开结果文件夹，请查看日志文件。") # User message
    # 示例：添加一个新映射的处理方法
    def handle_add_irregular_mapping(self, original_name, corrected_name, notes):
        result = self.irregular_mapping_service.add_mapping(original_name, corrected_name, notes)
        if result.success:
            self.view.update_log(result.message)
            self.refresh_irregular_mappings_view()
        else:
            self.view.show_error("添加失败", result.message)

    # 处理更新不规则名称映射的方法
    def handle_update_irregular_mapping(self, mapping_id, original_name, corrected_name, notes):
        logger.info(f"更新不规则名称映射: ID={mapping_id}, 原始名={original_name}, 修正名={corrected_name}")
        result = self.irregular_mapping_service.update_mapping(mapping_id, original_name, corrected_name, notes)
        if result.success:
            self.view.update_log(result.message)
            self.refresh_irregular_mappings_view()
        else:
            self.view.show_error("更新失败", result.message)

    # 处理删除不规则名称映射的方法
    def handle_delete_irregular_mapping(self, mapping_id):
        logger.info(f"删除不规则名称映射: ID={mapping_id}")
        result = self.irregular_mapping_service.delete_mapping(mapping_id)
        if result.success:
            self.view.update_log(result.message)
            self.refresh_irregular_mappings_view()
        else:
            self.view.show_error("删除失败", result.message)

    # 示例：刷新GUI中映射列表的方法
    def refresh_irregular_mappings_view(self):
        result = self.irregular_mapping_service.list_mappings()
        self.view.load_irregular_mappings(result.data or [])
        
    # --- 模型配置管理相关方法 ---
    def refresh_model_config_view(self):
        """获取并显示所有模型配置数据"""
        result = self.model_config_service.get_snapshot()
        snapshot = result.data
        
        self.view.load_model_node_types(snapshot.node_types)
        self.view.load_node_indices(snapshot.node_indices)
        self.view.load_model_extensions(snapshot.extensions)
        logger.info(
            f"已刷新模型配置视图：{len(snapshot.node_types)}个节点类型, "
            f"{len(snapshot.node_indices)}个索引映射, {len(snapshot.extensions)}个扩展名"
        )
    
    def handle_add_model_node_type(self, node_type):
        """添加模型节点类型"""
        result = self.model_config_service.add_model_node_type(node_type)
        if result.success:
            self.refresh_model_config_view()
            self.view.show_info("成功", result.message)
            return True
        self.view.show_warning("警告", result.message)
        return False
    
    def handle_delete_model_node_type(self, node_type):
        """删除模型节点类型"""
        result = self.model_config_service.delete_model_node_type(node_type)
        if result.success:
            self.refresh_model_config_view()
            self.view.show_info("成功", result.message)
            return True
        self.view.show_warning("警告", result.message)
        return False
    
    def handle_add_node_model_index(self, node_type, index):
        """添加节点模型索引映射"""
        result = self.model_config_service.add_node_model_index(node_type, index)
        if result.success:
            self.refresh_model_config_view()
            self.view.show_info("成功", result.message)
            return True
        if result.message == "索引必须是整数":
            self.view.show_error("错误", result.message)
            return False
        self.view.show_warning("警告", result.message)
        return False
    
    def handle_delete_node_model_index(self, node_type, index=None):
        """删除节点模型索引映射(整个节点类型或特定索引)"""
        result = self.model_config_service.delete_node_model_index(node_type, index)
        if result.success:
            self.refresh_model_config_view()
            self.view.show_info("成功", result.message)
            return True
        if result.message == "索引必须是整数":
            self.view.show_error("错误", result.message)
            return False
        self.view.show_warning("警告", result.message)
        return False
    
    def handle_add_model_extension(self, extension):
        """添加模型文件扩展名"""
        result = self.model_config_service.add_model_extension(extension)
        if result.success:
            self.refresh_model_config_view()
            self.view.show_info("成功", result.message)
            return True
        self.view.show_warning("警告", result.message)
        return False
    
    def handle_delete_model_extension(self, extension):
        """删除模型文件扩展名"""
        result = self.model_config_service.delete_model_extension(extension)
        if result.success:
            self.refresh_model_config_view()
            self.view.show_info("成功", result.message)
            return True
        self.view.show_warning("警告", result.message)
        return False

    def refresh_plugin_repair_view(self):
        """刷新插件修复标签页的数据"""
        logger.debug("刷新插件修复标签页数据")
        try:
            result = self.plugin_repair_service.get_plugins_for_view()
            plugins_data = result.data or []
            if hasattr(self.view, 'display_repair_plugins'):
                self.view.display_repair_plugins(plugins_data)
            logger.info(f"已加载 {len(plugins_data)} 个支持修复的插件")
        except Exception as e:
            logger.error(f"刷新插件修复标签页时出错: {e}", exc_info=True)
    
    def browse_comfyui_path(self):
        """浏览ComfyUI安装路径"""
        logger.debug("浏览ComfyUI路径按钮点击")
        dir_path = filedialog.askdirectory(title="选择ComfyUI安装目录")
        if dir_path:
            logger.info(f"已选择ComfyUI路径: {dir_path}")
            self._loaded_comfyui_path = dir_path
            if hasattr(self.view, 'set_comfyui_path'):
                self.view.set_comfyui_path(dir_path)
            # 选择路径后自动检查
            self.check_plugin_status()
    
    def check_plugin_status(self):
        """检查插件状态"""
        logger.debug("检查插件状态按钮点击")
        comfyui_path = self.view.get_comfyui_path()
        if not comfyui_path:
            self.view.show_error("错误", "请先选择ComfyUI安装路径")
            return
        
        if not os.path.exists(comfyui_path):
            self.view.show_error("错误", f"路径不存在: {comfyui_path}")
            return
        
        # 检查是否是ComfyUI目录
        validation_result = self._validate_comfyui_dir(comfyui_path)
        if not validation_result.success:
            if not self.view.ask_yes_no("确认", f"目录 {comfyui_path} 不像是标准的ComfyUI安装目录。\n是否继续？"):
                return
        
        try:
            result = self.plugin_repair_service.check_plugin_status(comfyui_path)
            for plugin_status in result.data["plugin_statuses"]:
                self.view.update_plugin_status(plugin_status["name"], plugin_status["status"])
            
            if result.message:
                self.view.show_info("检查结果", result.message)
        except Exception as e:
            logger.error(f"检查插件状态时出错: {e}", exc_info=True)
            self.view.show_error("错误", f"检查插件状态时出错: {e}")
    
    def _validate_comfyui_dir(self, dir_path):
        """验证目录是否为ComfyUI安装目录"""
        return self.plugin_repair_service.validate_comfyui_dir(dir_path)
    
    def repair_selected_plugin(self):
        """修复选中的插件"""
        logger.debug("修复选中插件按钮点击")
        plugin_name = self.view.get_selected_plugin()
        if not plugin_name:
            self.view.show_error("错误", "请先选择要修复的插件")
            return
        
        comfyui_path = self.view.get_comfyui_path()
        if not comfyui_path:
            self.view.show_error("错误", "请先选择ComfyUI安装路径")
            return
        
        if not os.path.exists(comfyui_path):
            self.view.show_error("错误", f"ComfyUI路径 {comfyui_path} 不存在")
            return
        
        # 禁用修复按钮，防止重复点击
        self.view.repair_button.config(state=tk.DISABLED)
        
        # 更新状态
        self.view.set_repair_status("启动修复助手...", 0)
        
        try:
            result = self.plugin_repair_service.launch_repair_helper()
            if result.success:
                logger.info(f"已启动插件修复助手: {result.data['script_path']}")
                self.view.set_repair_status(result.message, 100)
            else:
                self.view.show_error("错误", result.message)
        except Exception as e:
            logger.error(f"启动插件修复助手时发生异常: {e}", exc_info=True)
            self.view.show_error("错误", f"启动修复助手时发生异常: {e}")
        finally:
            # 延迟一秒后重新启用修复按钮
            self.root.after(1000, lambda: self.view.repair_button.config(state=tk.NORMAL))

