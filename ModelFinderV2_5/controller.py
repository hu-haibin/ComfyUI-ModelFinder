# model_finder/controller.py
import os
import sys
import json
import random
import threading
import webbrowser
import traceback
import glob
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import logging # Import logging
from .irregular_names_model import IrregularNamesModel

# Import other parts of the application
from .settings_model import SettingsModel
from .view import AppView
from .utils import check_dependencies, find_chrome_path, get_mirror_link, create_html_view
from .analysis_model import AnalysisModel
from .file_manager import cleanup_old_results, get_output_path, get_results_folder
from .plugin_repair import PluginRepairModel  # 导入插件修复模型
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
        # 初始化analysis_model时传递controller自身作为参数
        self.analysis_model = AnalysisModel(controller=self)
        # 初始化plugin_repair_model
        self.plugin_repair_model = PluginRepairModel()

        self.html_file_path = None
        self.batch_summary_file_path = None

        self.auto_open_html = tk.BooleanVar()
        self.random_theme = tk.BooleanVar()
        self._loaded_theme = "cosmo"
        self._loaded_chrome_path = ""
        self._loaded_retention_days = 30

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
        self.show_welcome_message()   # Then show welcome message
        logger.debug("Controller initialize sequence finished.")

    # --- Getters for View Initialization/Update ---
    def get_loaded_theme_preference(self): return self._loaded_theme
    def get_loaded_chrome_path(self): return self._loaded_chrome_path
    def get_loaded_retention_days(self): return self._loaded_retention_days
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
            missing_files = self.analysis_model.find_missing_models(workflow_file)

            if not missing_files:
                 self.root.after(0, logger.info, "分析完成: 没有发现缺失文件。")
                 self.root.after(0, self.view.update_log, "分析完成: 没有发现缺失文件。") # User message
                 self.root.after(0, self.update_status, "分析完成: 没有缺失文件")
                 self.root.after(0, self.view.show_info, "完成", "没有发现缺失文件")
                 return

            self.root.after(0, logger.info, f"发现 {len(missing_files)} 个缺失文件。正在创建CSV...")
            self.root.after(0, self.view.update_log, f"发现 {len(missing_files)} 个缺失文件。正在创建CSV...") # User message
            output_basename = os.path.basename(workflow_file)
            csv_file = self.analysis_model.create_csv_file(missing_files, output_basename)

            if not csv_file:
                 self.root.after(0, logger.error, "创建CSV文件失败。")
                 self.root.after(0, self.view.update_log, "创建CSV文件失败。") # User message
                 self.root.after(0, self.update_status, "分析完成，但创建CSV失败")
                 self.root.after(0, self.view.show_error, "错误", "创建CSV文件失败")
                 return

            self.root.after(0, logger.info, f"CSV文件已创建: {csv_file}")
            self.root.after(0, self.view.update_log, f"CSV文件已创建: {os.path.basename(csv_file)}") # User message (short path)
            self.root.after(0, self.update_status, "分析完成，准备搜索链接...")

            # Start search
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
                html_result = self.analysis_model.search_model_links(csv_file, progress_callback=update_progress_callback)

                if isinstance(html_result, str) and os.path.exists(html_result):
                    self.html_file_path = html_result
                    logger.info(f"搜索成功！HTML结果: {html_result}")
                    self.root.after(0, self.view.update_log, f"搜索完成！HTML结果: {os.path.basename(html_result)}") # User message
                    self.root.after(0, self.update_status, "搜索完成")
                    self.root.after(0, self.view.set_progress, 100, "100%")
                    self.root.after(0, self.view.enable_view_result_button, True)

                    if self.auto_open_html.get():
                        self.root.after(0, logger.info,"自动打开HTML结果...")
                        self.root.after(0, self.view.update_log,"自动打开HTML结果...") # User message
                        self.root.after(100, lambda: webbrowser.open(f"file:///{self.html_file_path}"))

                    self.root.after(0, self.view.show_info, "完成", "搜索完成，可以查看HTML结果")

                elif html_result == True:
                     logger.info("搜索完成: 无需搜索，模型已处理或存在。")
                     self.root.after(0, self.view.update_log,"无需搜索，所有模型均已处理或存在。") # User message
                     self.root.after(0, self.update_status,"无需搜索")
                     self.root.after(0, self.view.set_progress, 100, "100%")

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

            processed_summary_csv = None
            all_missing_summary_csv = None

            try:
                self.root.after(0, self.view.update_log, f"开始批量处理目录: {directory}") # User message
                processed_summary_csv = self.analysis_model.batch_process_workflows(directory, file_pattern, progress_callback=update_batch_progress)

                # Find the "汇总缺失文件.csv"
                try:
                     output_dir = get_results_folder()
                     if output_dir and os.path.isdir(output_dir):
                         date_folders = sorted([d for d in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, d))], reverse=True)
                         if date_folders:
                              latest_date_dir = os.path.join(output_dir, date_folders[0])
                              potential_summary = os.path.join(latest_date_dir, "汇总缺失文件.csv")
                              if os.path.exists(potential_summary):
                                  all_missing_summary_csv = potential_summary
                                  self.batch_summary_file_path = all_missing_summary_csv
                                  self.root.after(0, logger.info, f"找到汇总缺失文件: {all_missing_summary_csv}")
                                  self.root.after(0, self.view.update_log, f"找到汇总缺失文件: {os.path.basename(all_missing_summary_csv)}") # User message
                              else: logger.warning(f"汇总缺失文件.csv not found in {latest_date_dir}")
                         else: logger.warning(f"No date folders found in results directory: {output_dir}")
                     else: logger.warning(f"Results directory not valid: {output_dir}")
                except Exception as e:
                     logger.error("查找汇总缺失文件时出错", exc_info=True)
                     self.root.after(0, self.view.update_log, "查找汇总缺失文件时出错，请查看日志。") # User message

                # --- Process results ---
                if processed_summary_csv == True:
                     logger.info("Batch process complete: No missing files found.")
                     self.root.after(0, self.view.update_log,"批量处理完成，所有工作流均未发现缺失文件。") # User message
                     self.root.after(0, self.update_status,"批量处理完成: 无缺失")
                     self.root.after(0, self.view.set_batch_progress, 100, "100%")
                     self.root.after(0, self.view.show_info, "完成", "批量处理完成，未发现缺失文件。")

                elif isinstance(processed_summary_csv, str) and os.path.exists(processed_summary_csv):
                    logger.info(f"批量处理完成，结果摘要: {processed_summary_csv}")
                    self.root.after(0, self.view.update_log,f"批量处理完成，结果摘要: {os.path.basename(processed_summary_csv)}") # User message
                    self.root.after(0, self.update_status,"批量处理完成，准备搜索...")
                    self.root.after(0, self.view.set_batch_progress, 100, "100%")

                    # Update Treeview
                    try:
                        import pandas as pd # Local import might be slightly cleaner for threads
                        df_summary = pd.read_csv(processed_summary_csv, encoding='utf-8-sig')
                        self.root.after(0, self.view.clear_batch_results)
                        for _, row in df_summary.iterrows():
                             self.root.after(0, self.view.add_batch_result,
                                             row.get('工作流文件', ''), row.get('缺失数量', '0'), "已分析")
                    except Exception as e:
                         logger.error(f"读取批量结果CSV时出错: {processed_summary_csv}", exc_info=True)
                         self.root.after(0, self.view.update_log, f"读取批量结果CSV时出错: {os.path.basename(processed_summary_csv)}") # User message

                    # --- Search based on summary ---
                    if all_missing_summary_csv:
                         self.root.after(0, self.update_status,"开始搜索汇总链接...")
                         self.root.after(0, self.view.set_batch_progress, 0, "0%") # Reset for search

                         update_search_progress = lambda current, total: \
                              self.root.after(0, self.view.set_batch_progress, int((current / total) * 100), f"{int((current / total) * 100)}%") if total > 0 else None

                         logger.info(f"Starting summary search for: {all_missing_summary_csv}")
                         html_result = self.analysis_model.search_model_links(all_missing_summary_csv, progress_callback=update_search_progress)

                         if isinstance(html_result, str) and os.path.exists(html_result):
                              self.batch_summary_file_path = html_result # Store HTML path
                              logger.info(f"汇总搜索成功！HTML结果: {html_result}")
                              self.root.after(0, self.view.update_log,f"汇总搜索完成！HTML结果: {os.path.basename(html_result)}") # User message
                              self.root.after(0, self.update_status,"批量搜索完成")
                              self.root.after(0, self.view.set_batch_progress, 100, "100%")
                              if self.auto_open_html.get():
                                   self.root.after(0, logger.info,"自动打开HTML结果...")
                                   self.root.after(0, self.view.update_log,"自动打开HTML结果...") # User message
                                   self.root.after(100, lambda: webbrowser.open(f"file:///{html_result}"))
                              self.root.after(0, self.view.show_info, "完成", "批量处理和搜索完成")
                         else:
                              logger.warning(f"汇总搜索完成，但未能生成HTML结果 for {all_missing_summary_csv}")
                              self.root.after(0, self.view.update_log,"汇总搜索完成，但未能生成HTML结果。") # User message
                              self.root.after(0, self.update_status,"汇总搜索未生成HTML")
                              self.root.after(0, self.view.show_info, "完成", "批量搜索完成，但未生成HTML。")
                    else:
                         logger.warning("未找到'汇总缺失文件.csv'，无法执行搜索。")
                         self.root.after(0, self.view.update_log,"未找到'汇总缺失文件.csv'，无法执行搜索。") # User message
                         self.root.after(0, self.update_status,"批量处理完成，未找到汇总文件")
                         self.root.after(0, self.view.show_warning, "警告", "未找到汇总缺失文件，无法进行链接搜索。")
                else:
                     logger.error(f"批量处理失败或未生成预期的结果文件. Result: {processed_summary_csv}")
                     self.root.after(0, self.view.update_log,"批量处理失败或未生成预期的结果文件。") # User message
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
        path_to_open = self.batch_summary_file_path
        logger.info(f"Attempting to view batch result: {path_to_open}")
        if path_to_open and os.path.exists(path_to_open):
             if path_to_open.lower().endswith(".csv"):
                  logger.info(f"CSV file found, attempting to generate HTML view for: {path_to_open}")
                  self.root.after(0, self.view.update_log, f"尝试为 {os.path.basename(path_to_open)} 生成HTML视图...") # User message
                  try:
                      html_file = create_html_view(path_to_open) # Util function
                      if html_file and os.path.exists(html_file):
                           logger.info(f"HTML view generated: {html_file}, opening...")
                           webbrowser.open(f"file:///{html_file}")
                           return
                      else:
                           logger.error(f"无法生成或找到HTML视图 for {path_to_open}")
                           self.root.after(0, self.view.update_log, "无法生成或找到HTML视图。") # User message
                           self.root.after(0, self.view.show_error, "错误", "无法生成HTML视图。")
                           return
                  except Exception as e:
                       logger.error(f"生成HTML视图时出错: {path_to_open}", exc_info=True)
                       self.root.after(0, self.view.update_log, f"生成HTML视图时出错: {e}") # User message
                       self.root.after(0, self.view.show_error, "错误", f"生成HTML视图时出错: {e}")
                       return
             elif path_to_open.lower().endswith(".html"):
                  logger.info(f"HTML file found, opening: {path_to_open}")
                  webbrowser.open(f"file:///{path_to_open}")
                  return
             else:
                  logger.error(f"Cannot view batch result: Unknown file type: {path_to_open}")
                  self.view.show_error("错误", f"未知的文件类型: {os.path.basename(path_to_open)}")
        else:
             logger.warning("View batch HTML failed: Path not valid or not set.")
             self.view.show_error("错误", "未找到可查看的结果文件。请先运行批量处理。")

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
            retention_days_from_view = self.view.get_retention_days()
            logger.debug(f"Value from view for retention_days: {retention_days_from_view}")

            settings_to_save = {
                'auto_open_html': self.auto_open_html.get(),
                'chrome_path': self.view.get_chrome_path(),
                'random_theme': self.random_theme.get(),
                
                'theme': self.view.get_selected_theme(), # Saves the theme currently selected in the view's combobox.
                'retention_days': retention_days_from_view
            }
            logger.debug(f"Data to be saved: {settings_to_save}")

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
        self._loaded_retention_days = loaded_settings.get('retention_days', 30)
        logger.debug(f"Loaded settings values: AutoOpen={self.auto_open_html.get()}, RandomTheme={self.random_theme.get()}, Theme={self._loaded_theme}, Chrome='{self._loaded_chrome_path}', Days={self._loaded_retention_days}")

        if not self._loaded_chrome_path:
            found_chrome = find_chrome_path()
            if found_chrome:
                self._loaded_chrome_path = found_chrome
                logger.info(f"自动检测到Chrome路径: {found_chrome}")
                self.view.update_log(f"自动检测到Chrome路径: {found_chrome}") # User message

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

    def cleanup_old_files(self):
        logger.info("Cleanup old files button clicked.")
        days = self.view.get_retention_days()
        if self.view.ask_yes_no("确认操作", f"确定要清理 {days} 天前的所有结果文件吗？\n此操作不可撤销!"):
            try:
                logger.info(f"开始清理超过 {days} 天的旧文件...")
                self.view.update_log(f"开始清理 {days} 天前的旧文件...") # User message
                cleaned_count = cleanup_old_results(days_to_keep=days) # Service call
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
            results_dir = get_results_folder() # Service call
            if results_dir and os.path.isdir(results_dir):
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
        if self.irregular_names_model.add_mapping(original_name, corrected_name, notes):
            self.view.update_log("成功添加不规则名称映射。")
            self.refresh_irregular_mappings_view() # 一个新的方法，用于更新GUI中的列表
        else:
            self.view.show_error("添加失败", "无法添加不规则名称映射，请检查输入或日志。")

    # 处理更新不规则名称映射的方法
    def handle_update_irregular_mapping(self, mapping_id, original_name, corrected_name, notes):
        logger.info(f"更新不规则名称映射: ID={mapping_id}, 原始名={original_name}, 修正名={corrected_name}")
        if self.irregular_names_model.update_mapping(mapping_id, original_name, corrected_name, notes):
            self.view.update_log("成功更新不规则名称映射。")
            self.refresh_irregular_mappings_view()
        else:
            self.view.show_error("更新失败", "无法更新不规则名称映射，请检查输入或日志。")

    # 处理删除不规则名称映射的方法
    def handle_delete_irregular_mapping(self, mapping_id):
        logger.info(f"删除不规则名称映射: ID={mapping_id}")
        if self.irregular_names_model.delete_mapping(mapping_id):
            self.view.update_log("成功删除不规则名称映射。")
            self.refresh_irregular_mappings_view()
        else:
            self.view.show_error("删除失败", "无法删除不规则名称映射，请检查输入或日志。")

    # 示例：刷新GUI中映射列表的方法
    def refresh_irregular_mappings_view(self):
        # 获取并显示所有不规则映射
        mappings = self.irregular_names_model.get_all_mappings()
        self.view.load_irregular_mappings(mappings)
        
    # --- 模型配置管理相关方法 ---
    def refresh_model_config_view(self):
        """获取并显示所有模型配置数据"""
        node_types = self.analysis_model.config_manager.get_model_node_types()
        node_indices = self.analysis_model.config_manager.get_node_model_indices()
        extensions = self.analysis_model.config_manager.get_model_extensions()
        
        self.view.load_model_node_types(node_types)
        self.view.load_node_indices(node_indices)
        self.view.load_model_extensions(extensions)
        logger.info(f"已刷新模型配置视图：{len(node_types)}个节点类型, {len(node_indices)}个索引映射, {len(extensions)}个扩展名")
    
    def handle_add_model_node_type(self, node_type):
        """添加模型节点类型"""
        if not node_type.strip():
            self.view.show_warning("警告", "节点类型不能为空")
            return False
            
        success = self.analysis_model.config_manager.add_model_node_type(node_type)
        if success:
            self.refresh_model_config_view()
            self.view.show_info("成功", f"已添加节点类型: {node_type}")
            return True
        else:
            self.view.show_warning("警告", f"节点类型 '{node_type}' 已存在")
            return False
    
    def handle_delete_model_node_type(self, node_type):
        """删除模型节点类型"""
        success = self.analysis_model.config_manager.remove_model_node_type(node_type)
        if success:
            self.refresh_model_config_view()
            self.view.show_info("成功", f"已删除节点类型: {node_type}")
            return True
        else:
            self.view.show_warning("警告", f"删除节点类型失败: {node_type}")
            return False
    
    def handle_add_node_model_index(self, node_type, index):
        """添加节点模型索引映射"""
        try:
            index = int(index)
            # 将单个索引值转换为列表，然后传递给config_manager
            indices = [index]
            success = self.analysis_model.config_manager.add_node_model_index(node_type, indices)
            if success:
                self.refresh_model_config_view()
                self.view.show_info("成功", f"已添加节点索引映射: {node_type} -> {index}")
                return True
            else:
                self.view.show_warning("警告", f"添加节点索引映射失败: {node_type} -> {index}")
                return False
        except ValueError:
            self.view.show_error("错误", "索引必须是整数")
            return False
    
    def handle_delete_node_model_index(self, node_type, index=None):
        """删除节点模型索引映射(整个节点类型或特定索引)"""
        try:
            if index is not None:
                index = int(index)
                success = self.analysis_model.config_manager.remove_node_model_index(node_type, index)
            else:
                success = self.analysis_model.config_manager.remove_node_model_index_type(node_type)
            
            if success:
                self.refresh_model_config_view()
                msg = f"已删除节点索引映射: {node_type}"
                if index is not None:
                    msg += f" -> {index}"
                self.view.show_info("成功", msg)
                return True
            else:
                self.view.show_warning("警告", f"删除节点索引映射失败")
                return False
        except ValueError:
            self.view.show_error("错误", "索引必须是整数")
            return False
    
    def handle_add_model_extension(self, extension):
        """添加模型文件扩展名"""
        if not extension.strip():
            self.view.show_warning("警告", "扩展名不能为空")
            return False
            
        # 确保扩展名格式正确
        if not extension.startswith('.'):
            extension = '.' + extension
            
        success = self.analysis_model.config_manager.add_model_extension(extension)
        if success:
            self.refresh_model_config_view()
            self.view.show_info("成功", f"已添加模型扩展名: {extension}")
            return True
        else:
            self.view.show_warning("警告", f"模型扩展名 '{extension}' 已存在")
            return False
    
    def handle_delete_model_extension(self, extension):
        """删除模型文件扩展名"""
        success = self.analysis_model.config_manager.remove_model_extension(extension)
        if success:
            self.refresh_model_config_view()
            self.view.show_info("成功", f"已删除模型扩展名: {extension}")
            return True
        else:
            self.view.show_warning("警告", f"删除模型扩展名失败: {extension}")
            return False

    def handle_scan_downloads_folder(self, folder_path=None):
        """扫描下载文件夹中的模型文件"""
        # 如果未提供路径，使用视图中的路径
        if not folder_path:
            folder_path = self.view.get_downloads_folder_path()
        
        if not folder_path or not os.path.exists(folder_path):
            self.view.show_warning("路径错误", "下载文件夹路径无效")
            return False
        
        # 扫描文件夹中的模型文件
        file_paths = []
        for root, _, files in os.walk(folder_path):
            for file in files:
                _, ext = os.path.splitext(file)
                if ext.lower() in self.model_mover.model_extensions:
                    file_paths.append(os.path.join(root, file))
        
        if not file_paths:
            self.view.show_info("无模型文件", "下载文件夹中未找到模型文件")
            self.view.update_log("下载文件夹中未找到模型文件")
            return False
        
        # 加载找到的文件到视图
        self.view.load_download_files(file_paths)
        self.view.update_log(f"在下载文件夹中找到 {len(file_paths)} 个模型文件")
        
        return True

    def refresh_plugin_repair_view(self):
        """刷新插件修复标签页的数据"""
        logger.debug("刷新插件修复标签页数据")
        try:
            plugins = self.plugin_repair_model.get_all_plugins()
            plugins_data = [{"name": plugin.name, 
                            "description": plugin.description,
                            "status": "未检测"} 
                           for plugin in plugins]
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
        if not self._validate_comfyui_dir(comfyui_path):
            if not self.view.ask_yes_no("确认", f"目录 {comfyui_path} 不像是标准的ComfyUI安装目录。\n是否继续？"):
                return
        
        try:
            # 获取需要修复的插件
            need_repair = self.plugin_repair_model.check_plugin_status(comfyui_path)
            
            # 更新UI中的插件状态
            plugins = self.plugin_repair_model.get_all_plugins()
            for plugin in plugins:
                if plugin.name in need_repair:
                    self.view.update_plugin_status(plugin.name, "需要修复")
                else:
                    self.view.update_plugin_status(plugin.name, "已安装正确")
            
            if not need_repair:
                self.view.show_info("检查结果", "所有支持的插件都已正确安装。")
        except Exception as e:
            logger.error(f"检查插件状态时出错: {e}", exc_info=True)
            self.view.show_error("错误", f"检查插件状态时出错: {e}")
    
    def _validate_comfyui_dir(self, dir_path):
        """验证目录是否为ComfyUI安装目录"""
        # 检查一些ComfyUI典型的文件/目录是否存在
        expected_items = ["main.py", "web", "comfy", "models"]
        found_count = 0
        for item in expected_items:
            if os.path.exists(os.path.join(dir_path, item)):
                found_count += 1
        
        # 如果找到一半以上的预期项，就认为是ComfyUI目录
        return found_count >= len(expected_items) // 2
    
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
            # 直接运行download_helper_joy_caption_two.py脚本
            script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                     "download_helper_joy_caption_two.py")
            
            # 在新进程中运行脚本
            if sys.platform.startswith('win'):
                # Windows下使用subprocess.Popen打开新窗口
                subprocess.Popen([sys.executable, script_path], 
                               creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                # Linux/Mac下直接运行脚本
                subprocess.Popen([sys.executable, script_path])
                
            logger.info(f"已启动插件修复助手: {script_path}")
            self.view.set_repair_status("已启动修复助手，请在新窗口中操作", 100)
            
        except Exception as e:
            logger.error(f"启动插件修复助手时发生异常: {e}", exc_info=True)
            self.view.show_error("错误", f"启动修复助手时发生异常: {e}")
        finally:
            # 延迟一秒后重新启用修复按钮
            self.root.after(1000, lambda: self.view.repair_button.config(state=tk.NORMAL))