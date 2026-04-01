# model_finder/view.py
import tkinter as tk
from tkinter import messagebox, filedialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import os
import logging # Import logging

logger = logging.getLogger(__name__) # Get logger for this module

class AppView:
    def __init__(self, root):
        self.root = root
        self.controller = None # Set later by set_controller

        self.notebook = None
        self.tab_workflow = None
        self.tab_settings = None
        self.tab_irregular_names = None # 新增：不规则名称标签页的引用
        self.tab_model_config = None # 新增：模型配置标签页的引用

        self.tab_plugin_repair = None # 插件修复标签页的引用
        self.tab_comfyui_launch = None # ComfyUI 启动标签页的引用

        self.tab_missing_installer = None

        self.workflow_path_var = tk.StringVar()
        self.workflow_dir_var = tk.StringVar()
        self.workflow_mode_var = tk.StringVar(value="single")
        self.file_pattern_var = tk.StringVar(value="*.json;*")
        self.chrome_path_var = tk.StringVar()
        self.comfyui_python_path_var = tk.StringVar()
        self.theme_var = tk.StringVar()
        self.retention_days_var = tk.IntVar(value=30) # Keep default for initial display

        self.log_text = None
        self.progress_bar = None
        self.progress_label = None
        self.batch_progress_bar = None
        self.batch_progress_label = None
        self.result_tree = None
        self.view_result_button = None
        self.workflow_start_button = None
        self.theme_dropdown = None
        self.status_label = None # Reference for status bar label
        self.workflow_single_input_frame = None
        self.workflow_batch_input_frame = None
        self.workflow_single_content_frame = None
        self.workflow_batch_content_frame = None
        self._single_view_result_enabled = False
        # References for checkbuttons needed in _update_initial_settings
        self.auto_open_html_check = None
        self.auto_open_check = None # Checkbutton in batch tab
        self.random_theme_check = None
        
        # --- 不规则名称映射相关的UI元素引用 ---
        self.irregular_original_name_entry = None
        self.irregular_corrected_name_entry = None
        self.irregular_notes_entry = None
        self.selected_mapping_id = tk.StringVar() # 用于存储当前选中行的ID
        self.add_mapping_button = None
        self.update_mapping_button = None
        self.delete_mapping_button = None
        self.clear_fields_button = None
        self.irregular_mappings_tree = None
        # -------------------------------------



        # --- 插件修复相关的UI元素引用 ---
        self.comfyui_path_var = tk.StringVar()
        self.repair_progress_var = tk.IntVar()
        self.repair_status_var = tk.StringVar()
        self.repair_plugins_tree = None
        self.repair_button = None
        # -------------------------------------
        self.comfyui_launch_status_var = tk.StringVar(value="未启动")
        self.comfyui_launch_pid_var = tk.StringVar(value="")
        self.comfyui_launch_command_var = tk.StringVar(value="")
        self.comfyui_launch_auto_scroll_var = tk.BooleanVar(value=True)
        self.comfyui_launch_log_text = None
        self.comfyui_launch_start_button = None
        self.comfyui_launch_stop_button = None

        self.missing_installer_comfyui_status_var = tk.StringVar(value="未启动")
        self.missing_installer_manager_status_var = tk.StringVar(value="未启动")
        self.missing_installer_queue_progress_var = tk.StringVar(value="")
        self.missing_installer_quick_path_var = tk.StringVar(value="")
        self.missing_installer_summary_vars = {
            "total_workflows": tk.StringVar(value="0"),
            "total_node_types": tk.StringVar(value="0"),
            "missing_count": tk.StringVar(value="0"),
            "installable_count": tk.StringVar(value="0"),
            "manual_count": tk.StringVar(value="0"),
        }
        self.missing_installer_preflight_summary_vars = {
            "safe": tk.StringVar(value="0"),
            "safe_with_policy": tk.StringVar(value="0"),
            "warning": tk.StringVar(value="0"),
            "blocked": tk.StringVar(value="0"),
        }
        self.missing_installer_step_buttons = []
        self.missing_installer_step_frames = {}
        self.missing_installer_selected_paths_listbox = None
        self.missing_installer_package_tree = None
        self.missing_installer_preflight_tree = None
        self.missing_installer_install_tree = None
        self.missing_installer_manual_listbox = None
        self.missing_installer_log_text = None
        self.missing_installer_start_button = None
        self.missing_installer_preflight_install_button = None
        self.missing_installer_preflight_safe_button = None
        self.missing_installer_restart_button = None

        self._set_icon()
        self._create_main_widgets() # self.notebook 在这里创建
        self._setup_tabs()          # 所有标签页在这里添加和设置
        if self.notebook and not self.tab_missing_installer:
            self.tab_missing_installer = ttk.Frame(self.notebook, padding="10")
            self.notebook.add(self.tab_missing_installer, text="缺失节点安装")
            self._create_missing_installer_tab()
        logger.debug("AppView initialized.")

    def set_controller(self, controller):
        """Sets the controller reference and updates initial settings from controller."""
        logger.debug("Setting controller reference in View.")
        self.controller = controller
        if self.controller:
            self._update_initial_settings()
            # Link status bar label to controller's variable
            if self.status_label:
                self.status_label.config(textvariable=self.controller.status_var)
            else:
                logger.warning("Status label widget not found during set_controller.")
            # 加载不规则名称映射列表到UI
            self.controller.refresh_irregular_mappings_view() # <--- 在controller设置后刷新

    def _set_icon(self):
        """设置应用程序的图标。"""
        try:
            # 修正路径，假设 Modelfinder.ico 在项目根目录的上一级
            # 或者更可靠的是，将其作为包内资源，并使用相对路径
            # 例如，可以改成从当前文件所在目录拼出 assets/Modelfinder.ico
            # base_dir = os.path.dirname(__file__) # 当前文件(view.py)所在目录
            # icon_path = os.path.join(base_dir, "assets", "Modelfinder.ico")
            # 为简单起见，我们先假设它在项目根目录
            project_root = os.path.dirname(os.path.dirname(__file__)) # 获取项目根目录 (ModelFinder_V2)
            icon_path = os.path.join(project_root, "Modelfinder.ico")

            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
                logger.info(f"Application icon set from: {icon_path}")
            else:
                 logger.warning(f"Icon file not found at {icon_path}")
        except Exception as e:
             logger.error(f"加载图标时出错: {e}", exc_info=True)

    def _create_main_widgets(self):
        """创建应用的主框架、Notebook和状态栏等。"""
        # Notebook - 确保在这里创建
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10,0)) # Notebook 顶部 pady

        # Status bar: Create label, textvariable linked in set_controller
        # 确保状态栏在Notebook之后，但在root的底部
        self.status_label = ttk.Label(self.root, text="初始化...", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, padx=0, pady=0)


    def _setup_tabs(self):
        """创建并配置所有的标签页，并将它们添加到Notebook中。"""
        if not self.notebook:
            logger.error("Notebook not initialized before _setup_tabs call.")
            return
        logger.debug("Setting up tabs.")

        # 单个处理标签页
        self.tab_workflow = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.tab_workflow, text="工作流")
        self._setup_workflow_tab(self.tab_workflow)

        # === 新增：创建不规则名称映射标签页 ===
        self.tab_irregular_names = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.tab_irregular_names, text="不规则名称映射")
        self._create_irregular_names_tab_content(self.tab_irregular_names) # 调用新方法创建内容
        
        # === 创建模型配置标签页 ===
        self.tab_model_config = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.tab_model_config, text="模型配置")
        self._create_model_config_tab()
        


        # === 创建插件修复标签页 ===
        self.tab_plugin_repair = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.tab_plugin_repair, text="插件修复")
        self._create_plugin_repair_tab()

        # === 创建 ComfyUI 启动标签页 ===
        self.tab_comfyui_launch = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.tab_comfyui_launch, text="启动 ComfyUI")
        self._create_comfyui_launch_tab()

        # 设置标签页
        self.tab_settings = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.tab_settings, text="设置")
        self._setup_settings_tab(self.tab_settings)


    def _setup_single_tab(self, tab_frame):
        """设置"单个处理"标签页的内容。"""
        main_frame = ttk.Frame(tab_frame, padding="10") # 统一使用padding
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="工作流文件:").grid(row=1, column=0, sticky="w", padx=(0,5), pady=5)
        ttk.Entry(main_frame, textvariable=self.workflow_path_var, width=60).grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        ttk.Button(main_frame, text="浏览...", command=lambda: self.controller.browse_workflow() if self.controller else None).grid(row=1, column=2, padx=5, pady=5)

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=3, sticky="w", pady=10)
        ttk.Button(button_frame, text="一键分析并搜索", style="success.TButton", command=lambda: self.controller.analyze_and_search() if self.controller else None).pack(side=tk.LEFT, padx=(0, 5))
        self.view_result_button = ttk.Button(button_frame, text="查看结果", command=lambda: self.controller.view_result() if self.controller else None, state=tk.DISABLED)
        self.view_result_button.pack(side=tk.LEFT)

        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=5)
        ttk.Label(progress_frame, text="进度:").pack(side=tk.LEFT, padx=(0, 5))
        self.progress_bar = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.progress_label = ttk.Label(progress_frame, text="0%")
        self.progress_label.pack(side=tk.LEFT, padx=5)

        ttk.Separator(main_frame, orient="horizontal").grid(row=4, column=0, columnspan=3, sticky="ew", pady=10)
        ttk.Label(main_frame, text="处理日志:").grid(row=5, column=0, columnspan=3, sticky="w", pady=(0, 5))
        log_frame = ttk.Frame(main_frame)
        log_frame.grid(row=6, column=0, columnspan=3, sticky="nsew", pady=(0, 5))

        self.log_text = tk.Text(log_frame, height=15, wrap=tk.WORD, relief="solid", borderwidth=1)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set, state=tk.DISABLED) # 初始为只读

        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(6, weight=1)


    def _setup_batch_tab(self, tab_frame):
        """设置"批量处理"标签页的内容。"""
        main_frame = ttk.Frame(tab_frame, padding="10") # 统一使用padding
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="工作流目录:").grid(row=1, column=0, sticky="w", padx=(0,5), pady=5)
        ttk.Entry(main_frame, textvariable=self.workflow_dir_var, width=60).grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        ttk.Button(main_frame, text="浏览...", command=lambda: self.controller.browse_workflow_dir() if self.controller else None).grid(row=1, column=2, padx=5, pady=5)

        ttk.Label(main_frame, text="文件格式:").grid(row=2, column=0, sticky="w", padx=(0,5), pady=5)
        ttk.Entry(main_frame, textvariable=self.file_pattern_var, width=20).grid(row=2, column=1, sticky="w", padx=5, pady=5)

        options_frame = ttk.Frame(main_frame)
        options_frame.grid(row=3, column=0, columnspan=3, sticky="w", pady=5)
        self.auto_open_check = ttk.Checkbutton(options_frame, text="自动打开结果") # 变量在_update_initial_settings中设置
        self.auto_open_check.pack(side=tk.LEFT)

        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=4, column=0, columnspan=3, sticky="w", pady=10)
        ttk.Button(buttons_frame, text="开始处理并搜索", style="success.TButton",
                   command=lambda: self.controller.batch_process() if self.controller else None).pack(side=tk.LEFT)

        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=5, column=0, columnspan=3, sticky="ew", pady=5)
        ttk.Label(progress_frame, text="进度:").pack(side=tk.LEFT, padx=(0, 5))
        self.batch_progress_bar = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.batch_progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.batch_progress_label = ttk.Label(progress_frame, text="0%")
        self.batch_progress_label.pack(side=tk.LEFT, padx=5)

        ttk.Label(main_frame, text="处理结果:").grid(row=6, column=0, columnspan=3, sticky="w", pady=(10, 5))
        result_frame = ttk.Frame(main_frame)
        result_frame.grid(row=7, column=0, columnspan=3, sticky="nsew", pady=(0, 5))
        columns = ("文件名", "缺失数量", "状态")
        self.result_tree = ttk.Treeview(result_frame, columns=columns, show="headings", height=10)
        for col_idx, col_name in enumerate(columns):
            self.result_tree.heading(col_name, text=col_name)
            width = 150 if col_idx < 2 else 100 # 状态列窄一些
            self.result_tree.column(col_name, width=width, anchor="w")
        self.result_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_tree.config(yscrollcommand=scrollbar.set)

        self.view_batch_html_button = ttk.Button(main_frame, text="查看汇总HTML结果", command=lambda: self.controller.view_batch_html() if self.controller else None)
        self.view_batch_html_button.grid(row=8, column=0, columnspan=3, sticky="w", pady=10)

        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(7, weight=1)


    def _setup_workflow_tab(self, tab_frame):
        """设置统一的工作流标签页内容。"""
        main_frame = ttk.Frame(tab_frame, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        mode_frame = ttk.LabelFrame(main_frame, text="处理模式", padding=10)
        mode_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Radiobutton(
            mode_frame,
            text="单文件",
            variable=self.workflow_mode_var,
            value="single",
            command=self._update_workflow_mode_ui,
        ).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(
            mode_frame,
            text="目录",
            variable=self.workflow_mode_var,
            value="batch",
            command=self._update_workflow_mode_ui,
        ).pack(side=tk.LEFT)

        input_frame = ttk.LabelFrame(main_frame, text="工作流输入", padding=10)
        input_frame.pack(fill=tk.X, pady=(0, 10))

        self.workflow_single_input_frame = ttk.Frame(input_frame)
        ttk.Label(self.workflow_single_input_frame, text="工作流文件:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(self.workflow_single_input_frame, textvariable=self.workflow_path_var, width=60).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=5
        )
        ttk.Button(
            self.workflow_single_input_frame,
            text="浏览...",
            command=lambda: self.controller.browse_workflow_input() if self.controller else None,
        ).pack(side=tk.LEFT, padx=(5, 0))

        self.workflow_batch_input_frame = ttk.Frame(input_frame)
        dir_row = ttk.Frame(self.workflow_batch_input_frame)
        dir_row.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(dir_row, text="工作流目录:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(dir_row, textvariable=self.workflow_dir_var, width=60).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=5
        )
        ttk.Button(
            dir_row,
            text="浏览...",
            command=lambda: self.controller.browse_workflow_input() if self.controller else None,
        ).pack(side=tk.LEFT, padx=(5, 0))

        pattern_row = ttk.Frame(self.workflow_batch_input_frame)
        pattern_row.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(pattern_row, text="文件格式:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(pattern_row, textvariable=self.file_pattern_var, width=20).pack(side=tk.LEFT, padx=5)

        options_row = ttk.Frame(self.workflow_batch_input_frame)
        options_row.pack(fill=tk.X)
        self.auto_open_check = ttk.Checkbutton(options_row, text="自动打开结果")
        self.auto_open_check.pack(side=tk.LEFT)

        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=(0, 10))
        self.workflow_start_button = ttk.Button(
            action_frame,
            text="开始分析并搜索",
            style="success.TButton",
            command=lambda: self.controller.start_workflow_processing() if self.controller else None,
        )
        self.workflow_start_button.pack(side=tk.LEFT, padx=(0, 5))
        self.view_result_button = ttk.Button(
            action_frame,
            text="查看结果",
            command=lambda: self.controller.view_workflow_result() if self.controller else None,
            state=tk.DISABLED,
        )
        self.view_result_button.pack(side=tk.LEFT)

        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)

        self.workflow_single_content_frame = ttk.Frame(content_frame)
        progress_frame = ttk.Frame(self.workflow_single_content_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(progress_frame, text="进度:").pack(side=tk.LEFT, padx=(0, 5))
        self.progress_bar = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.progress_label = ttk.Label(progress_frame, text="0%")
        self.progress_label.pack(side=tk.LEFT, padx=5)

        ttk.Separator(self.workflow_single_content_frame, orient="horizontal").pack(fill=tk.X, pady=(0, 10))
        ttk.Label(self.workflow_single_content_frame, text="处理日志:").pack(anchor="w", pady=(0, 5))
        log_frame = ttk.Frame(self.workflow_single_content_frame)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_frame, height=15, wrap=tk.WORD, relief="solid", borderwidth=1)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set, state=tk.DISABLED)

        self.workflow_batch_content_frame = ttk.Frame(content_frame)
        batch_progress_frame = ttk.Frame(self.workflow_batch_content_frame)
        batch_progress_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(batch_progress_frame, text="进度:").pack(side=tk.LEFT, padx=(0, 5))
        self.batch_progress_bar = ttk.Progressbar(
            batch_progress_frame, orient=tk.HORIZONTAL, length=100, mode='determinate'
        )
        self.batch_progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.batch_progress_label = ttk.Label(batch_progress_frame, text="0%")
        self.batch_progress_label.pack(side=tk.LEFT, padx=5)

        ttk.Label(self.workflow_batch_content_frame, text="处理结果:").pack(anchor="w", pady=(0, 5))
        result_frame = ttk.Frame(self.workflow_batch_content_frame)
        result_frame.pack(fill=tk.BOTH, expand=True)
        columns = ("文件名", "缺失数量", "状态")
        self.result_tree = ttk.Treeview(result_frame, columns=columns, show="headings", height=10)
        for col_idx, col_name in enumerate(columns):
            self.result_tree.heading(col_name, text=col_name)
            width = 150 if col_idx < 2 else 100
            self.result_tree.column(col_name, width=width, anchor="w")
        self.result_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        batch_scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_tree.yview)
        batch_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_tree.config(yscrollcommand=batch_scrollbar.set)

        self._update_workflow_mode_ui()

    def _update_workflow_mode_ui(self):
        """根据当前模式切换工作流标签页的显示内容。"""
        mode = self.get_workflow_mode()

        if self.workflow_single_input_frame:
            self.workflow_single_input_frame.pack_forget()
        if self.workflow_batch_input_frame:
            self.workflow_batch_input_frame.pack_forget()
        if self.workflow_single_content_frame:
            self.workflow_single_content_frame.pack_forget()
        if self.workflow_batch_content_frame:
            self.workflow_batch_content_frame.pack_forget()

        if mode == "batch":
            if self.workflow_batch_input_frame:
                self.workflow_batch_input_frame.pack(fill=tk.X)
            if self.workflow_batch_content_frame:
                self.workflow_batch_content_frame.pack(fill=tk.BOTH, expand=True)
        else:
            if self.workflow_single_input_frame:
                self.workflow_single_input_frame.pack(fill=tk.X)
            if self.workflow_single_content_frame:
                self.workflow_single_content_frame.pack(fill=tk.BOTH, expand=True)

        if self.workflow_start_button:
            button_text = "开始处理并搜索" if mode == "batch" else "开始分析并搜索"
            self.workflow_start_button.config(text=button_text)

        if self.view_result_button:
            button_state = tk.NORMAL if mode == "batch" or self._single_view_result_enabled else tk.DISABLED
            self.view_result_button.config(text="查看结果", state=button_state)

    def _setup_settings_tab(self, tab_frame):
        """设置"设置"标签页的内容。"""
        main_frame = ttk.Frame(tab_frame, padding="10") # 统一使用padding
        main_frame.pack(fill="both", expand=True)

        app_frame = ttk.LabelFrame(main_frame, text="应用设置")
        app_frame.pack(fill="x", pady=5, padx=5) # 加点边距

        auto_html_frame = ttk.Frame(app_frame)
        auto_html_frame.pack(fill="x", padx=10, pady=5) # 内部也加点边距
        self.auto_open_html_check = ttk.Checkbutton(auto_html_frame, text="搜索完成后自动打开HTML结果") # 变量在_update_initial_settings中设置
        self.auto_open_html_check.pack(side="left")

        chrome_frame = ttk.Frame(app_frame)
        chrome_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(chrome_frame, text="Chrome路径:").pack(side="left", padx=(0,5))
        ttk.Entry(chrome_frame, textvariable=self.chrome_path_var, width=50).pack(side="left", fill="x", expand=True)
        ttk.Button(chrome_frame, text="浏览", command=lambda: self.controller.browse_chrome() if self.controller else None).pack(side="left", padx=5)

        theme_frame = ttk.LabelFrame(main_frame, text="界面主题")
        theme_frame.pack(fill="x", pady=5, padx=5)

        theme_select_frame = ttk.Frame(theme_frame)
        theme_select_frame.pack(fill="x", padx=10, pady=5)
        theme_names = ttk.Style().theme_names() # 获取所有可用主题
        ttk.Label(theme_select_frame, text="选择主题:").pack(side="left", padx=(0,5))
        self.theme_dropdown = ttk.Combobox(theme_select_frame, textvariable=self.theme_var, values=theme_names, state="readonly", width=15)
        self.theme_dropdown.pack(side="left")
        ttk.Button(theme_select_frame, text="应用主题", command=lambda: self.controller.apply_theme() if self.controller else None).pack(side="left", padx=5)

        random_theme_frame = ttk.Frame(theme_frame) # ttk.Frame
        random_theme_frame.pack(fill="x", padx=10, pady=5)
        self.random_theme_check = ttk.Checkbutton(random_theme_frame, text="启动时使用随机主题") # 变量在_update_initial_settings中设置
        self.random_theme_check.pack(side="left")

        file_frame = ttk.LabelFrame(main_frame, text="文件管理")
        file_frame.pack(fill="x", pady=5, padx=5)
        ttk.Label(file_frame, text="所有结果文件保存在results文件夹中，按日期组织。").pack(anchor="w", padx=10, pady=2)

        retention_frame = ttk.Frame(file_frame)
        retention_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(retention_frame, text="保留文件天数:").pack(side="left", padx=(0,5))
        ttk.Spinbox(retention_frame, from_=1, to=365, width=5, textvariable=self.retention_days_var).pack(side="left")

        btn_frame = ttk.Frame(file_frame)
        btn_frame.pack(fill="x", padx=10, pady=5)
        ttk.Button(btn_frame, text="清理旧文件", command=lambda: self.controller.cleanup_old_files() if self.controller else None).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="打开结果文件夹", command=lambda: self.controller.open_results_folder() if self.controller else None).pack(side="left", padx=5)

        save_frame = ttk.Frame(main_frame) # 移到main_frame的底部
        save_frame.pack(fill="x", pady=10, padx=5, side="bottom", anchor="e") # 靠右
        ttk.Button(save_frame, text="保存设置", style="primary.TButton", command=lambda: self.controller.save_settings() if self.controller else None).pack(side="right")


    def _create_irregular_names_tab_content(self, parent_tab):
        """在指定的父标签页中创建不规则名称映射管理的UI元素。"""
        logger.debug(f"Creating irregular names tab content in {parent_tab}.")
        # --- 输入表单 ---
        form_frame = ttk.Labelframe(parent_tab, text="添加/编辑映射")
        form_frame.pack(fill="x", padx=5, pady=5, side="top")

        ttk.Label(form_frame, text="原始名称:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.irregular_original_name_entry = ttk.Entry(form_frame, width=50)
        self.irregular_original_name_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(form_frame, text="修正后名称:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.irregular_corrected_name_entry = ttk.Entry(form_frame, width=50)
        self.irregular_corrected_name_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(form_frame, text="备注:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.irregular_notes_entry = ttk.Entry(form_frame, width=50)
        self.irregular_notes_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        form_frame.columnconfigure(1, weight=1) # 使输入框列可拉伸

        # --- 操作按钮 ---
        buttons_frame = ttk.Frame(parent_tab)
        buttons_frame.pack(fill="x", padx=5, pady=(5,10), side="top")

        self.add_mapping_button = ttk.Button(buttons_frame, text="添加新映射", style="success.TButton", command=self._on_add_mapping)
        self.add_mapping_button.pack(side="left", padx=5)

        self.update_mapping_button = ttk.Button(buttons_frame, text="更新选中映射", style="info.TButton", command=self._on_update_mapping, state=tk.DISABLED)
        self.update_mapping_button.pack(side="left", padx=5)

        self.delete_mapping_button = ttk.Button(buttons_frame, text="删除选中映射", style="danger.TButton", command=self._on_delete_mapping, state=tk.DISABLED)
        self.delete_mapping_button.pack(side="left", padx=5)

        self.clear_fields_button = ttk.Button(buttons_frame, text="清空输入框", style="secondary.TButton", command=self._clear_irregular_name_fields)
        self.clear_fields_button.pack(side="left", padx=5)

        # --- 映射列表 Treeview ---
        list_frame = ttk.Labelframe(parent_tab, text="当前映射列表")
        list_frame.pack(fill="both", expand=True, padx=5, pady=5, side="top")

        columns = ("id", "original_name", "corrected_name", "notes")
        self.irregular_mappings_tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")

        self.irregular_mappings_tree.heading("id", text="ID")
        self.irregular_mappings_tree.heading("original_name", text="原始名称")
        self.irregular_mappings_tree.heading("corrected_name", text="修正后名称")
        self.irregular_mappings_tree.heading("notes", text="备注")

        self.irregular_mappings_tree.column("id", width=60, anchor="w", stretch=tk.NO)
        self.irregular_mappings_tree.column("original_name", width=250, anchor="w")
        self.irregular_mappings_tree.column("corrected_name", width=250, anchor="w")
        self.irregular_mappings_tree.column("notes", width=200, anchor="w")

        scrollbar_y = ttk.Scrollbar(list_frame, orient="vertical", command=self.irregular_mappings_tree.yview)
        scrollbar_x = ttk.Scrollbar(list_frame, orient="horizontal", command=self.irregular_mappings_tree.xview)
        self.irregular_mappings_tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        scrollbar_y.pack(side="right", fill="y")
        scrollbar_x.pack(side="bottom", fill="x")
        self.irregular_mappings_tree.pack(side="left", fill="both", expand=True)

        self.irregular_mappings_tree.bind("<<TreeviewSelect>>", self._on_tree_select)

    def _clear_irregular_name_fields(self, clear_id=True):
        """清空不规则名称映射表单的输入字段。"""
        if self.irregular_original_name_entry: self.irregular_original_name_entry.delete(0, tk.END)
        if self.irregular_corrected_name_entry: self.irregular_corrected_name_entry.delete(0, tk.END)
        if self.irregular_notes_entry: self.irregular_notes_entry.delete(0, tk.END)
        if clear_id:
            self.selected_mapping_id.set("")
        if self.update_mapping_button: self.update_mapping_button.config(state=tk.DISABLED)
        if self.delete_mapping_button: self.delete_mapping_button.config(state=tk.DISABLED)
        if self.irregular_mappings_tree and self.irregular_mappings_tree.selection():
            self.irregular_mappings_tree.selection_remove(self.irregular_mappings_tree.selection())

    def _on_tree_select(self, event):
        """当Treeview中的条目被选中时，用其数据填充表单字段。"""
        if not self.irregular_mappings_tree: return
        selected_items = self.irregular_mappings_tree.selection()
        if not selected_items:
            self._clear_irregular_name_fields()
            return

        selected_item = selected_items[0]
        values = self.irregular_mappings_tree.item(selected_item, "values")

        if values and len(values) == 4:
            mapping_id, original_name, corrected_name, notes = values
            self.selected_mapping_id.set(mapping_id)

            if self.irregular_original_name_entry:
                self.irregular_original_name_entry.delete(0, tk.END)
                self.irregular_original_name_entry.insert(0, original_name)
            if self.irregular_corrected_name_entry:
                self.irregular_corrected_name_entry.delete(0, tk.END)
                self.irregular_corrected_name_entry.insert(0, corrected_name)
            if self.irregular_notes_entry:
                self.irregular_notes_entry.delete(0, tk.END)
                self.irregular_notes_entry.insert(0, notes)

            if self.update_mapping_button: self.update_mapping_button.config(state=tk.NORMAL)
            if self.delete_mapping_button: self.delete_mapping_button.config(state=tk.NORMAL)
        else:
            logger.warning(f"Could not retrieve values or incorrect number of values from Treeview item: {values}")
            self._clear_irregular_name_fields()

    def _on_add_mapping(self):
        """处理"添加新映射"按钮点击事件。"""
        if not self.controller or not self.irregular_original_name_entry: return
        original_name = self.irregular_original_name_entry.get().strip()
        corrected_name = self.irregular_corrected_name_entry.get().strip()
        notes = self.irregular_notes_entry.get().strip()

        if not original_name or not corrected_name:
            self.show_error("输入错误", "原始名称和修正后名称不能为空！")
            return
        self.controller.handle_add_irregular_mapping(original_name, corrected_name, notes)
        self._clear_irregular_name_fields(clear_id=True)

    def _on_update_mapping(self):
        """处理"更新选中映射"按钮点击事件。"""
        if not self.controller or not self.irregular_original_name_entry: return
        mapping_id = self.selected_mapping_id.get()
        if not mapping_id:
            self.show_error("操作错误", "请先从列表中选择一个映射进行更新。")
            return
        original_name = self.irregular_original_name_entry.get().strip()
        corrected_name = self.irregular_corrected_name_entry.get().strip()
        notes = self.irregular_notes_entry.get().strip()
        if not original_name or not corrected_name:
            self.show_error("输入错误", "原始名称和修正后名称不能为空！")
            return
        self.controller.handle_update_irregular_mapping(mapping_id, original_name, corrected_name, notes)
        self._clear_irregular_name_fields(clear_id=True)

    def _on_delete_mapping(self):
        """处理"删除选中映射"按钮点击事件。"""
        if not self.controller: return
        mapping_id = self.selected_mapping_id.get()
        if not mapping_id:
            self.show_error("操作错误", "请先从列表中选择一个映射进行删除。")
            return
        if self.ask_yes_no("确认删除", f"确定要删除ID为 '{mapping_id}' 的映射吗？此操作不可撤销。"):
            self.controller.handle_delete_irregular_mapping(mapping_id)
            self._clear_irregular_name_fields(clear_id=True)

    def display_irregular_mappings(self, mappings):
        """用从Controller获取的映射数据更新Treeview。"""
        if not self.irregular_mappings_tree:
            logger.warning("irregular_mappings_tree is not initialized in display_irregular_mappings.")
            return
        for item in self.irregular_mappings_tree.get_children():
            self.irregular_mappings_tree.delete(item)
        for mapping in mappings:
            self.irregular_mappings_tree.insert("", tk.END, values=(
                mapping.get("id", ""),
                mapping.get("original_name", ""),
                mapping.get("corrected_name", ""),
                mapping.get("notes", "")
            ))
        if not mappings:
            self._clear_irregular_name_fields(clear_id=True)

    def _update_initial_settings(self):
        """Update widgets based on controller state after controller is set."""
        logger.debug("View updating initial settings from controller.")
        if self.controller:
            # Link checkbuttons to controller variables now that controller exists
            if self.auto_open_html_check and hasattr(self.controller, 'auto_open_html'):
                 self.auto_open_html_check.config(variable=self.controller.auto_open_html)
            if self.auto_open_check and hasattr(self.controller, 'auto_open_html'): # Link batch tab checkbutton too
                 self.auto_open_check.config(variable=self.controller.auto_open_html)
            if self.random_theme_check and hasattr(self.controller, 'random_theme'):
                 self.random_theme_check.config(variable=self.controller.random_theme)

            # Get initial values from controller getters
            theme = self.controller.get_loaded_theme_preference()
            chrome = self.controller.get_loaded_chrome_path()
            comfyui = self.controller.get_loaded_comfyui_path()
            comfyui_python = self.controller.get_loaded_comfyui_python_path()
            days = self.controller.get_loaded_retention_days()
            logger.debug(
                f"Applying initial settings to view: Theme={theme}, Chrome='{chrome}', "
                f"ComfyUI='{comfyui}', ComfyUIPython='{comfyui_python}', Days={days}"
            )

            # Apply values to view widgets
            if theme and self.theme_dropdown: self.set_selected_theme(theme)
            self.set_chrome_path(chrome) # Assuming set_chrome_path updates the var
            self.set_comfyui_path(comfyui)
            self.set_comfyui_python_path(comfyui_python)
            if self.retention_days_var : self.retention_days_var.set(days) # Directly set IntVar
        else:
             logger.warning("Controller not set in view during _update_initial_settings.")


    def update_log(self, message, clear_first=False):
        """更新日志文本区域的内容。"""
        if hasattr(self, 'log_text') and self.log_text:
            try:
                self.log_text.config(state=tk.NORMAL)
                if clear_first:
                    self.log_text.delete('1.0', tk.END)
                self.log_text.insert(tk.END, message + "\n")
                self.log_text.see(tk.END)
                self.log_text.config(state=tk.DISABLED)
            except tk.TclError as e:
                logger.error(f"Error updating log_text: {e}. Widget might be destroyed.")
        else:
            logger.info(f"View Log (widget not available): {message}")

    def clear_log(self):
        """清空日志区域。"""
        self.update_log("", clear_first=True)


    def show_error(self, title, message):
        logger.error(f"Showing error dialog: {title} - {message}")
        messagebox.showerror(title, message, parent=self.root) # Explicitly set parent

    def show_info(self, title, message):
        logger.info(f"Showing info dialog: {title} - {message}")
        messagebox.showinfo(title, message, parent=self.root)

    def show_warning(self, title, message):
        logger.warning(f"Showing warning dialog: {title} - {message}")
        messagebox.showwarning(title, message, parent=self.root)

    def ask_yes_no(self, title, message):
        logger.info(f"Showing yes/no dialog: {title} - {message}")
        return messagebox.askyesno(title, message, parent=self.root)

    # --- Getter/Setter for UI elements if needed by Controller ---
    def get_workflow_path(self): return self.workflow_path_var.get().strip()
    def set_workflow_path(self, path): self.workflow_path_var.set(path)

    def get_workflow_dir(self): return self.workflow_dir_var.get().strip()
    def set_workflow_dir(self, path): self.workflow_dir_var.set(path)

    def get_workflow_mode(self): return self.workflow_mode_var.get().strip() or "single"
    def set_workflow_mode(self, mode):
        self.workflow_mode_var.set(mode if mode in {"single", "batch"} else "single")
        self._update_workflow_mode_ui()

    def get_file_pattern(self): return self.file_pattern_var.get().strip()
    # No setter for file_pattern_var as it's usually just read

    def get_chrome_path(self): return self.chrome_path_var.get().strip()
    def set_chrome_path(self, path): self.chrome_path_var.set(path)

    def get_selected_theme(self): return self.theme_var.get()
    def set_selected_theme(self, theme_name):
        logger.debug(f"View setting theme dropdown/var to: {theme_name}")
        self.theme_var.set(theme_name)
        # if self.theme_dropdown: self.theme_dropdown.set(theme_name) # Combobox updates via textvariable

    def get_retention_days(self):
        try:
            return self.retention_days_var.get()
        except tk.TclError: # Handle case where var might not be perfectly set yet
            logger.warning("Could not get retention_days_var, returning default 30.")
            return 30
    # No explicit set_retention_days(self, days) as it's handled by _update_initial_settings via var

    def enable_view_result_button(self, enable=True):
        self._single_view_result_enabled = bool(enable)
        if self.view_result_button and self.get_workflow_mode() == "single":
            self.view_result_button.config(state=tk.NORMAL if enable else tk.DISABLED)

    def set_progress(self, value, text):
        if self.progress_bar: self.progress_bar['value'] = value
        if self.progress_label: self.progress_label.config(text=text)
        if self.root.winfo_exists(): self.root.update_idletasks()

    def set_batch_progress(self, value, text):
        if self.batch_progress_bar: self.batch_progress_bar['value'] = value
        if self.batch_progress_label: self.batch_progress_label.config(text=text)
        if self.root.winfo_exists(): self.root.update_idletasks()

    def clear_batch_results(self):
        if self.result_tree:
            for item in self.result_tree.get_children():
                self.result_tree.delete(item)

    def add_batch_result(self, workflow_file, missing_count, status): # Changed from file_name
        if self.result_tree:
            self.result_tree.insert("", tk.END, values=(os.path.basename(workflow_file), missing_count, status))

    # Added from your original file, seems useful
    def update_batch_result_status(self, file_name, new_status):
         if self.result_tree:
             for item in self.result_tree.get_children():
                 values = self.result_tree.item(item, 'values')
                 if len(values) > 0 and values[0] == file_name: # Assuming file_name is the first value
                     # Make sure to update all values if the tuple length is fixed
                     current_values = list(self.result_tree.item(item, 'values'))
                     current_values[2] = new_status # Update status at index 2
                     self.result_tree.item(item, values=tuple(current_values))
                     break

    def set_window_title(self, title):
        self.root.title(title)

    def _create_model_config_tab(self):
        """创建模型配置标签页内容"""
        logger.debug(f"Creating model config tab content in {self.tab_model_config}.")
        
        # 创建顶层框架，包含三个部分：节点类型、节点索引和模型扩展名
        config_frame = ttk.Frame(self.tab_model_config, padding=10)
        config_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建左侧框架 - 节点类型
        node_types_frame = ttk.LabelFrame(config_frame, text="模型节点类型", padding=10)
        node_types_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # 创建节点类型树形视图
        self.model_node_types_tree = ttk.Treeview(node_types_frame, columns=("node_type",), show="headings", height=15)
        self.model_node_types_tree.heading("node_type", text="节点类型")
        self.model_node_types_tree.column("node_type", width=200)
        self.model_node_types_tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 添加滚动条
        scroll_y = ttk.Scrollbar(node_types_frame, orient=tk.VERTICAL, command=self.model_node_types_tree.yview)
        self.model_node_types_tree.configure(yscrollcommand=scroll_y.set)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 添加节点类型的输入框和按钮
        input_frame = ttk.Frame(node_types_frame)
        input_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        ttk.Label(input_frame, text="节点类型:").pack(side=tk.LEFT)
        self.node_type_entry = ttk.Entry(input_frame)
        self.node_type_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        ttk.Button(input_frame, text="添加", command=self._add_node_type).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(input_frame, text="删除", command=self._delete_node_type).pack(side=tk.LEFT)
        
        # 创建中间框架 - 节点索引
        node_indices_frame = ttk.LabelFrame(config_frame, text="节点模型索引映射", padding=10)
        node_indices_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        # 创建节点索引树形视图
        self.node_indices_tree = ttk.Treeview(node_indices_frame, columns=("node_type", "index"), show="headings", height=15)
        self.node_indices_tree.heading("node_type", text="节点类型")
        self.node_indices_tree.heading("index", text="索引")
        self.node_indices_tree.column("node_type", width=150)
        self.node_indices_tree.column("index", width=50)
        self.node_indices_tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 添加滚动条
        scroll_y2 = ttk.Scrollbar(node_indices_frame, orient=tk.VERTICAL, command=self.node_indices_tree.yview)
        self.node_indices_tree.configure(yscrollcommand=scroll_y2.set)
        scroll_y2.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 添加节点索引的输入框和按钮
        input_frame2 = ttk.Frame(node_indices_frame)
        input_frame2.pack(side=tk.BOTTOM, fill=tk.X)
        
        ttk.Label(input_frame2, text="节点类型:").pack(side=tk.LEFT)
        self.node_index_type_entry = ttk.Entry(input_frame2, width=15)
        self.node_index_type_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(input_frame2, text="索引:").pack(side=tk.LEFT)
        self.node_index_entry = ttk.Entry(input_frame2, width=5)
        self.node_index_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(input_frame2, text="添加", command=self._add_node_index).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(input_frame2, text="删除", command=self._delete_node_index).pack(side=tk.LEFT)
        
        # 创建右侧框架 - 模型扩展名
        extensions_frame = ttk.LabelFrame(config_frame, text="模型文件扩展名", padding=10)
        extensions_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # 创建模型扩展名列表框
        self.model_extensions_list = tk.Listbox(extensions_frame, height=15)
        self.model_extensions_list.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 添加滚动条
        scroll_y3 = ttk.Scrollbar(extensions_frame, orient=tk.VERTICAL, command=self.model_extensions_list.yview)
        self.model_extensions_list.configure(yscrollcommand=scroll_y3.set)
        scroll_y3.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 添加扩展名的输入框和按钮
        input_frame3 = ttk.Frame(extensions_frame)
        input_frame3.pack(side=tk.BOTTOM, fill=tk.X)
        
        ttk.Label(input_frame3, text="扩展名:").pack(side=tk.LEFT)
        self.extension_entry = ttk.Entry(input_frame3)
        self.extension_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        ttk.Button(input_frame3, text="添加", command=self._add_extension).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(input_frame3, text="删除", command=self._delete_extension).pack(side=tk.LEFT)
        
    # 添加这些辅助方法来处理UI事件
    def _add_node_type(self):
        """添加节点类型"""
        node_type = self.node_type_entry.get().strip()
        if node_type and self.controller:
            self.controller.handle_add_model_node_type(node_type)
            self.node_type_entry.delete(0, tk.END)  # 清空输入框

    def _delete_node_type(self):
        """删除节点类型"""
        selection = self.model_node_types_tree.selection()
        if selection and self.controller:
            item_id = selection[0]
            node_type = self.model_node_types_tree.item(item_id, "values")[0]
            self.controller.handle_delete_model_node_type(node_type)

    def _add_node_index(self):
        """添加节点索引映射"""
        node_type = self.node_index_type_entry.get().strip()
        index = self.node_index_entry.get().strip()
        if node_type and index and self.controller:
            self.controller.handle_add_node_model_index(node_type, index)
            self.node_index_entry.delete(0, tk.END)  # 只清空索引输入框

    def _delete_node_index(self):
        """删除节点索引映射"""
        selection = self.node_indices_tree.selection()
        if selection and self.controller:
            item_id = selection[0]
            values = self.node_indices_tree.item(item_id, "values")
            node_type = values[0]
            index = values[1]
            self.controller.handle_delete_node_model_index(node_type, index)

    def _add_extension(self):
        """添加模型扩展名"""
        extension = self.extension_entry.get().strip()
        if extension and self.controller:
            self.controller.handle_add_model_extension(extension)
            self.extension_entry.delete(0, tk.END)  # 清空输入框

    def _delete_extension(self):
        """删除模型扩展名"""
        selection = self.model_extensions_list.curselection()
        if selection and self.controller:
            index = selection[0]
            extension = self.model_extensions_list.get(index)
            self.controller.handle_delete_model_extension(extension)
            
    # 数据加载方法
    def load_model_node_types(self, node_types):
        """加载模型节点类型到树形视图"""
        self.model_node_types_tree.delete(*self.model_node_types_tree.get_children())
        for node_type in sorted(node_types):
            self.model_node_types_tree.insert("", "end", values=(node_type,))

    def load_node_indices(self, node_indices):
        """加载节点索引映射到树形视图"""
        self.node_indices_tree.delete(*self.node_indices_tree.get_children())
        # 首先按节点类型排序
        sorted_items = []
        for node_type, indices in node_indices.items():
            # 检查indices是否为列表类型，如果是单个整数则转换为列表
            if isinstance(indices, int):
                indices = [indices]  # 将单个整数转换为列表
            elif not isinstance(indices, (list, tuple)):
                logger.warning(f"节点索引格式无效: {node_type} -> {indices}")
                continue
                
            for index in indices:
                sorted_items.append((node_type, index))
                
        sorted_items.sort(key=lambda x: x[0])  # 按节点类型字符串排序
        
        for node_type, index in sorted_items:
            self.node_indices_tree.insert("", "end", values=(node_type, index))

    def load_model_extensions(self, extensions):
        """加载模型扩展名到列表框"""
        self.model_extensions_list.delete(0, tk.END)
        for ext in sorted(extensions):
            self.model_extensions_list.insert(tk.END, ext)
            
    # 重命名display_irregular_mappings为load_irregular_mappings以保持命名一致性
    def load_irregular_mappings(self, mappings):
        """用从Controller获取的映射数据更新Treeview。"""
        if not self.irregular_mappings_tree:
            logger.warning("irregular_mappings_tree is not initialized in load_irregular_mappings.")
            return
        for item in self.irregular_mappings_tree.get_children():
            self.irregular_mappings_tree.delete(item)
        for mapping in mappings:
            self.irregular_mappings_tree.insert("", tk.END, values=(
                mapping.get("id", ""),
                mapping.get("original_name", ""),
                mapping.get("corrected_name", ""),
                mapping.get("notes", "")
            ))
        if not mappings:
            self._clear_irregular_name_fields(clear_id=True)
    # Legacy model mover / model registry UI has been isolated from AppView.
    # The active notebook only exposes fully supported production tabs.

    def _create_comfyui_launch_tab(self):
        """创建 ComfyUI 启动标签页的内容"""
        logger.debug("Creating ComfyUI launch tab.")

        main_frame = ttk.Frame(self.tab_comfyui_launch, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(header_frame, text="ComfyUI 启动", font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT)
        ttk.Label(
            header_frame,
            textvariable=self.comfyui_launch_status_var,
            bootstyle="info",
            font=("Segoe UI", 10, "bold"),
        ).pack(side=tk.RIGHT)

        path_frame = ttk.Frame(main_frame)
        path_frame.pack(fill=tk.X, pady=(0, 8))

        comfyui_row = ttk.Frame(path_frame)
        comfyui_row.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(comfyui_row, text="ComfyUI", width=10).pack(side=tk.LEFT)
        ttk.Entry(comfyui_row, textvariable=self.comfyui_path_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8)
        )
        ttk.Button(
            comfyui_row,
            text="浏览",
            width=8,
            command=lambda: self.controller.browse_comfyui_launch_path() if self.controller else None,
        ).pack(side=tk.LEFT)

        python_row = ttk.Frame(path_frame)
        python_row.pack(fill=tk.X)
        ttk.Label(python_row, text="Python", width=10).pack(side=tk.LEFT)
        ttk.Entry(python_row, textvariable=self.comfyui_python_path_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8)
        )
        ttk.Button(
            python_row,
            text="浏览",
            width=8,
            command=lambda: self.controller.browse_comfyui_python_path() if self.controller else None,
        ).pack(side=tk.LEFT)

        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=(0, 8))
        self.comfyui_launch_start_button = ttk.Button(
            action_frame,
            text="启动 ComfyUI",
            style="success.TButton",
            command=lambda: self.controller.start_comfyui() if self.controller else None,
        )
        self.comfyui_launch_start_button.pack(side=tk.LEFT, padx=(0, 6))
        self.comfyui_launch_stop_button = ttk.Button(
            action_frame,
            text="停止",
            style="danger.TButton",
            command=lambda: self.controller.stop_comfyui() if self.controller else None,
            state=tk.DISABLED,
        )
        self.comfyui_launch_stop_button.pack(side=tk.LEFT, padx=(0, 12))
        ttk.Button(
            action_frame,
            text="保存配置",
            command=lambda: self.controller.save_comfyui_launch_settings() if self.controller else None,
        ).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(
            action_frame,
            text="校验路径",
            command=lambda: self.controller.validate_comfyui_launch_paths() if self.controller else None,
        ).pack(side=tk.LEFT)

        runtime_frame = ttk.Frame(main_frame)
        runtime_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(runtime_frame, text="PID", width=10, bootstyle="secondary").grid(row=0, column=0, sticky="w")
        ttk.Label(runtime_frame, textvariable=self.comfyui_launch_pid_var).grid(row=0, column=1, sticky="w")
        ttk.Label(runtime_frame, text="命令", width=10, bootstyle="secondary").grid(row=1, column=0, sticky="nw", pady=(4, 0))
        ttk.Label(
            runtime_frame,
            textvariable=self.comfyui_launch_command_var,
            justify=tk.LEFT,
            wraplength=720,
            foreground="#667085",
        ).grid(row=1, column=1, sticky="w", pady=(4, 0))
        runtime_frame.columnconfigure(1, weight=1)

        log_frame = ttk.Frame(main_frame)
        log_frame.pack(fill=tk.BOTH, expand=True)

        log_actions = ttk.Frame(log_frame)
        log_actions.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(log_actions, text="启动日志", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=(0, 12))
        ttk.Button(
            log_actions,
            text="清空日志",
            command=lambda: self.controller.clear_comfyui_launch_log() if self.controller else None,
        ).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(
            log_actions,
            text="自动滚动",
            variable=self.comfyui_launch_auto_scroll_var,
        ).pack(side=tk.LEFT)

        log_content_frame = ttk.Frame(log_frame)
        log_content_frame.pack(fill=tk.BOTH, expand=True)
        self.comfyui_launch_log_text = tk.Text(
            log_content_frame,
            height=15,
            wrap=tk.WORD,
            relief="solid",
            borderwidth=1,
        )
        self.comfyui_launch_log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(log_content_frame, orient=tk.VERTICAL, command=self.comfyui_launch_log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.comfyui_launch_log_text.config(yscrollcommand=scrollbar.set, state=tk.DISABLED)

    def _create_missing_installer_tab(self):
        logger.debug("Creating missing installer tab.")

        main_frame = ttk.Frame(self.tab_missing_installer, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(header_frame, text="缺失节点安装", font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT)

        status_frame = ttk.Frame(header_frame)
        status_frame.pack(side=tk.RIGHT)
        ttk.Label(status_frame, text="ComfyUI", bootstyle="secondary").pack(side=tk.LEFT, padx=(0, 4))
        ttk.Label(status_frame, textvariable=self.missing_installer_comfyui_status_var, bootstyle="info").pack(side=tk.LEFT, padx=(0, 12))
        ttk.Label(status_frame, text="Manager", bootstyle="secondary").pack(side=tk.LEFT, padx=(0, 4))
        ttk.Label(status_frame, textvariable=self.missing_installer_manager_status_var, bootstyle="info").pack(side=tk.LEFT, padx=(0, 12))
        self.missing_installer_start_button = ttk.Button(
            status_frame,
            text="启动 ComfyUI",
            bootstyle="success",
            command=lambda: self.controller.start_comfyui_for_missing_installer() if self.controller else None,
        )
        self.missing_installer_start_button.pack(side=tk.LEFT)

        steps_frame = ttk.Frame(main_frame)
        steps_frame.pack(fill=tk.X, pady=(0, 10))
        self.missing_installer_step_buttons = []
        for index, title in enumerate(["上传工作流", "分析缺失节点", "选择插件", "预检依赖", "下载安装"]):
            button = ttk.Button(
                steps_frame,
                text=f"{index + 1}. {title}",
                bootstyle="secondary",
                state=tk.DISABLED,
                command=lambda value=index: self.controller.go_to_missing_installer_step(value) if self.controller else None,
            )
            button.pack(side=tk.LEFT, padx=(0, 6))
            self.missing_installer_step_buttons.append(button)

        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)

        upload_frame = ttk.Frame(content_frame)
        analysis_frame = ttk.Frame(content_frame)
        select_frame = ttk.Frame(content_frame)
        preflight_frame = ttk.Frame(content_frame)
        install_frame = ttk.Frame(content_frame)
        self.missing_installer_step_frames = {
            0: upload_frame,
            1: analysis_frame,
            2: select_frame,
            3: preflight_frame,
            4: install_frame,
        }

        quick_input_frame = ttk.Frame(upload_frame)
        quick_input_frame.pack(fill=tk.X, pady=(0, 8))
        quick_path_entry = ttk.Entry(
            quick_input_frame,
            textvariable=self.missing_installer_quick_path_var,
        )
        quick_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        quick_path_entry.bind(
            "<Return>",
            lambda event: self.controller.add_missing_installer_quick_path(auto_analyze=True) if self.controller else None,
        )
        ttk.Button(
            quick_input_frame,
            text="添加路径",
            command=lambda: self.controller.add_missing_installer_quick_path() if self.controller else None,
        ).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(
            quick_input_frame,
            text="粘贴",
            command=lambda: self.controller.paste_missing_installer_path() if self.controller else None,
        ).pack(side=tk.LEFT)

        ttk.Label(
            upload_frame,
            text="支持粘贴工作流文件或目录路径，单个输入回车可直接分析。",
            bootstyle="secondary",
        ).pack(anchor="w", pady=(0, 8))

        upload_actions = ttk.Frame(upload_frame)
        upload_actions.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(
            upload_actions,
            text="选择文件",
            command=lambda: self.controller.browse_missing_installer_workflow_files() if self.controller else None,
        ).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(
            upload_actions,
            text="选择文件夹",
            command=lambda: self.controller.browse_missing_installer_workflow_folder() if self.controller else None,
        ).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(
            upload_actions,
            text="清空",
            command=lambda: self.controller.clear_missing_installer_workflow_inputs() if self.controller else None,
        ).pack(side=tk.LEFT, padx=(0, 12))
        ttk.Button(
            upload_actions,
            text="分析缺失节点",
            bootstyle="primary",
            command=lambda: self.controller.analyze_missing_installer_workflows() if self.controller else None,
        ).pack(side=tk.LEFT)

        self.missing_installer_selected_paths_listbox = tk.Listbox(upload_frame, height=6, activestyle="none")
        self.missing_installer_selected_paths_listbox.pack(fill=tk.BOTH, expand=True)
        self.missing_installer_selected_paths_listbox.bind(
            "<Return>",
            lambda event: self.controller.analyze_missing_installer_workflows() if self.controller else None,
        )

        summary_grid = ttk.Frame(analysis_frame)
        summary_grid.pack(fill=tk.X, pady=(0, 8))
        summary_items = [
            ("工作流", "total_workflows"),
            ("节点类型", "total_node_types"),
            ("缺失节点", "missing_count"),
            ("可安装", "installable_count"),
            ("人工处理", "manual_count"),
        ]
        for column, (label, key) in enumerate(summary_items):
            item_frame = ttk.Frame(summary_grid, padding=8)
            item_frame.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 6, 0))
            summary_grid.columnconfigure(column, weight=1)
            ttk.Label(item_frame, text=label, bootstyle="secondary").pack(anchor="w")
            ttk.Label(item_frame, textvariable=self.missing_installer_summary_vars[key], font=("Segoe UI", 16, "bold")).pack(anchor="w")

        ttk.Button(
            analysis_frame,
            text="继续选择插件",
            bootstyle="primary",
            command=lambda: self.controller.advance_missing_installer_to_selection() if self.controller else None,
        ).pack(anchor="w")

        select_actions = ttk.Frame(select_frame)
        select_actions.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(select_actions, text="双击插件包可切换勾选", bootstyle="secondary").pack(side=tk.LEFT)
        ttk.Button(
            select_actions,
            text="直接安装",
            bootstyle="primary",
            command=lambda: self.controller.start_missing_installer_installation(ignore_preflight=True) if self.controller else None,
        ).pack(side=tk.RIGHT)
        ttk.Button(
            select_actions,
            text="预检依赖",
            bootstyle="secondary",
            command=lambda: self.controller.run_missing_installer_dependency_preflight() if self.controller else None,
        ).pack(side=tk.RIGHT, padx=(0, 6))

        self.missing_installer_package_tree = ttk.Treeview(
            select_frame,
            columns=("selected", "title", "missing_count", "state", "status"),
            show="headings",
            height=8,
        )
        self.missing_installer_package_tree.heading("selected", text="选择")
        self.missing_installer_package_tree.heading("title", text="插件包")
        self.missing_installer_package_tree.heading("missing_count", text="覆盖节点")
        self.missing_installer_package_tree.heading("state", text="当前状态")
        self.missing_installer_package_tree.heading("status", text="安装状态")
        self.missing_installer_package_tree.column("selected", width=60, anchor="center")
        self.missing_installer_package_tree.column("title", width=280)
        self.missing_installer_package_tree.column("missing_count", width=90, anchor="center")
        self.missing_installer_package_tree.column("state", width=100, anchor="center")
        self.missing_installer_package_tree.column("status", width=120, anchor="center")
        self.missing_installer_package_tree.pack(fill=tk.BOTH, expand=True)
        self.missing_installer_package_tree.bind(
            "<Double-1>",
            lambda event: self.controller.toggle_missing_installer_package_selection() if self.controller else None,
        )

        manual_frame = ttk.Frame(select_frame)
        manual_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        ttk.Label(manual_frame, text="需人工处理", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 4))
        self.missing_installer_manual_listbox = tk.Listbox(manual_frame, height=5, activestyle="none")
        self.missing_installer_manual_listbox.pack(fill=tk.BOTH, expand=True)

        preflight_summary_grid = ttk.Frame(preflight_frame)
        preflight_summary_grid.pack(fill=tk.X, pady=(0, 8))
        preflight_summary_items = [
            ("安全", "safe"),
            ("需策略安装", "safe_with_policy"),
            ("警告", "warning"),
            ("阻断", "blocked"),
        ]
        for column, (label, key) in enumerate(preflight_summary_items):
            item_frame = ttk.Frame(preflight_summary_grid, padding=8)
            item_frame.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 6, 0))
            preflight_summary_grid.columnconfigure(column, weight=1)
            ttk.Label(item_frame, text=label, bootstyle="secondary").pack(anchor="w")
            ttk.Label(
                item_frame,
                textvariable=self.missing_installer_preflight_summary_vars[key],
                font=("Segoe UI", 16, "bold"),
            ).pack(anchor="w")

        preflight_actions = ttk.Frame(preflight_frame)
        preflight_actions.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(
            preflight_actions,
            text="系统会先按 aki 规则评估风险，再决定是否允许继续安装。",
            bootstyle="secondary",
        ).pack(side=tk.LEFT)
        self.missing_installer_preflight_safe_button = ttk.Button(
            preflight_actions,
            text="仅安装安全项",
            bootstyle="secondary",
            command=lambda: self.controller.start_missing_installer_installation(safe_only=True) if self.controller else None,
        )
        self.missing_installer_preflight_safe_button.pack(side=tk.RIGHT, padx=(6, 0))
        self.missing_installer_preflight_install_button = ttk.Button(
            preflight_actions,
            text="开始安装",
            bootstyle="primary",
            command=lambda: self.controller.start_missing_installer_installation() if self.controller else None,
        )
        self.missing_installer_preflight_install_button.pack(side=tk.RIGHT)

        self.missing_installer_preflight_tree = ttk.Treeview(
            preflight_frame,
            columns=("title", "source", "strategy", "risk", "conclusion"),
            show="headings",
            height=8,
        )
        self.missing_installer_preflight_tree.heading("title", text="依赖或插件")
        self.missing_installer_preflight_tree.heading("source", text="来源插件")
        self.missing_installer_preflight_tree.heading("strategy", text="推荐策略")
        self.missing_installer_preflight_tree.heading("risk", text="风险等级")
        self.missing_installer_preflight_tree.heading("conclusion", text="当前结论")
        self.missing_installer_preflight_tree.column("title", width=250)
        self.missing_installer_preflight_tree.column("source", width=220)
        self.missing_installer_preflight_tree.column("strategy", width=140, anchor="center")
        self.missing_installer_preflight_tree.column("risk", width=90, anchor="center")
        self.missing_installer_preflight_tree.column("conclusion", width=160, anchor="center")
        self.missing_installer_preflight_tree.pack(fill=tk.BOTH, expand=True)

        install_actions = ttk.Frame(install_frame)
        install_actions.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(install_actions, textvariable=self.missing_installer_queue_progress_var, bootstyle="secondary").pack(side=tk.LEFT)
        self.missing_installer_restart_button = ttk.Button(
            install_actions,
            text="一键重启并复检",
            bootstyle="warning",
            command=lambda: self.controller.restart_comfyui_and_recheck_missing_nodes() if self.controller else None,
        )
        self.missing_installer_restart_button.pack(side=tk.RIGHT)
        self.missing_installer_restart_button.pack_forget()

        self.missing_installer_install_tree = ttk.Treeview(
            install_frame,
            columns=("title", "status", "missing_count"),
            show="headings",
            height=10,
        )
        self.missing_installer_install_tree.heading("title", text="插件包")
        self.missing_installer_install_tree.heading("status", text="状态")
        self.missing_installer_install_tree.heading("missing_count", text="覆盖节点")
        self.missing_installer_install_tree.column("title", width=320)
        self.missing_installer_install_tree.column("status", width=140, anchor="center")
        self.missing_installer_install_tree.column("missing_count", width=100, anchor="center")
        self.missing_installer_install_tree.pack(fill=tk.BOTH, expand=True)

        log_frame = ttk.Frame(main_frame)
        log_frame.pack(fill=tk.BOTH, expand=False, pady=(10, 0))
        log_actions = ttk.Frame(log_frame)
        log_actions.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(log_actions, text="任务日志", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=(0, 12))
        ttk.Button(
            log_actions,
            text="清空日志",
            command=lambda: self.controller.clear_missing_installer_log() if self.controller else None,
        ).pack(side=tk.LEFT)
        self.missing_installer_log_text = tk.Text(log_frame, height=8, wrap=tk.WORD, relief="solid", borderwidth=1)
        self.missing_installer_log_text.pack(fill=tk.BOTH, expand=True)
        self.missing_installer_log_text.config(state=tk.DISABLED)

        self.show_missing_installer_step(0)

    def _create_plugin_repair_tab(self):
        """创建插件修复标签页的内容"""
        logger.debug("创建插件修复标签页")
        
        main_frame = ttk.Frame(self.tab_plugin_repair, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 顶部说明
        ttk.Label(main_frame, text="插件修复工具", font=("Helvetica", 14, "bold")).pack(pady=5)
        ttk.Label(main_frame, text="用于修复因文件缺失导致的插件错误").pack(pady=5)
        
        # ComfyUI路径选择框架
        path_frame = ttk.Frame(main_frame)
        path_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(path_frame, text="ComfyUI路径:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(path_frame, textvariable=self.comfyui_path_var, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(path_frame, text="浏览...", command=lambda: self.controller.browse_comfyui_path() if self.controller else None).pack(side=tk.LEFT, padx=5)
        
        # 支持的插件信息
        info_frame = ttk.LabelFrame(main_frame, text="支持修复的插件")
        info_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # 简化的插件信息显示
        self.repair_plugins_tree = ttk.Treeview(info_frame, columns=("name", "description"), show="headings", selectmode="browse")
        self.repair_plugins_tree.heading("name", text="插件名称")
        self.repair_plugins_tree.heading("description", text="描述")
        self.repair_plugins_tree.column("name", width=150)
        self.repair_plugins_tree.column("description", width=450)
        
        # 添加固定的Joy Caption Two插件
        self.repair_plugins_tree.insert("", tk.END, values=("Joy Caption Two", "高质量图像描述插件"))
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(info_frame, orient=tk.VERTICAL, command=self.repair_plugins_tree.yview)
        self.repair_plugins_tree.configure(yscrollcommand=scrollbar.set)
        
        # 放置Treeview和滚动条
        self.repair_plugins_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 说明信息
        label = ttk.Label(main_frame, text='点击"修复选中的插件"按钮后，将打开插件修复助手窗口，按照提示操作即可', wraplength=600, justify=tk.LEFT)
        label.pack(pady=10)
        
        # 修复按钮和进度条框架
        repair_controls_frame = ttk.Frame(main_frame)
        repair_controls_frame.pack(fill=tk.X, pady=10)
        
        self.repair_button = ttk.Button(repair_controls_frame, 
                                        text="修复选中的插件", 
                                        command=lambda: self.controller.repair_selected_plugin() if self.controller else None)
        self.repair_button.pack(side=tk.LEFT, padx=5)
        
        repair_progress = ttk.Progressbar(repair_controls_frame, variable=self.repair_progress_var, maximum=100)
        repair_progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        status_label = ttk.Label(repair_controls_frame, textvariable=self.repair_status_var)
        status_label.pack(side=tk.LEFT, padx=5)
    
    def set_repair_status(self, message, progress):
        """更新修复状态信息和进度条"""
        self.repair_status_var.set(message)
        self.repair_progress_var.set(progress)
    
    def get_comfyui_path(self):
        """获取ComfyUI路径"""
        return self.comfyui_path_var.get()
    
    def set_comfyui_path(self, path):
        """设置ComfyUI路径"""
        self.comfyui_path_var.set(path)

    def get_comfyui_python_path(self):
        """获取 ComfyUI 启动使用的 Python 路径"""
        return self.comfyui_python_path_var.get().strip()

    def set_comfyui_python_path(self, path):
        """设置 ComfyUI 启动使用的 Python 路径"""
        self.comfyui_python_path_var.set(path)

    def append_comfyui_launch_log(self, message):
        if not self.comfyui_launch_log_text:
            logger.info(f"ComfyUI Launch Log (widget not available): {message}")
            return

        try:
            self.comfyui_launch_log_text.config(state=tk.NORMAL)
            self.comfyui_launch_log_text.insert(tk.END, f"{message}\n")
            if self.comfyui_launch_auto_scroll_var.get():
                self.comfyui_launch_log_text.see(tk.END)
            self.comfyui_launch_log_text.config(state=tk.DISABLED)
        except tk.TclError as exc:
            logger.error(f"Error updating comfyui_launch_log_text: {exc}.")

    def clear_comfyui_launch_log(self):
        if not self.comfyui_launch_log_text:
            return

        try:
            self.comfyui_launch_log_text.config(state=tk.NORMAL)
            self.comfyui_launch_log_text.delete("1.0", tk.END)
            self.comfyui_launch_log_text.config(state=tk.DISABLED)
        except tk.TclError as exc:
            logger.error(f"Error clearing comfyui_launch_log_text: {exc}.")

    def set_comfyui_launch_status(self, status):
        self.comfyui_launch_status_var.set(status)

    def set_comfyui_launch_details(self, *, pid="", command=""):
        self.comfyui_launch_pid_var.set("" if pid in (None, "") else str(pid))
        self.comfyui_launch_command_var.set(command or "")

    def set_comfyui_launch_button_states(self, *, start_enabled, stop_enabled):
        if self.comfyui_launch_start_button:
            self.comfyui_launch_start_button.config(state=tk.NORMAL if start_enabled else tk.DISABLED)
        if self.comfyui_launch_stop_button:
            self.comfyui_launch_stop_button.config(state=tk.NORMAL if stop_enabled else tk.DISABLED)

    def set_missing_installer_runtime_status(self, *, comfyui_status, manager_status, start_enabled):
        self.missing_installer_comfyui_status_var.set(comfyui_status)
        self.missing_installer_manager_status_var.set(manager_status)
        if self.missing_installer_start_button:
            self.missing_installer_start_button.config(state=tk.NORMAL if start_enabled else tk.DISABLED)

    def set_missing_installer_steps(self, *, current_step, completed_steps):
        completed_steps = set(completed_steps or [])
        for index, button in enumerate(self.missing_installer_step_buttons):
            if index == current_step:
                button.config(bootstyle="primary", state=tk.DISABLED)
            elif index in completed_steps:
                button.config(bootstyle="outline-secondary", state=tk.NORMAL)
            else:
                button.config(bootstyle="secondary", state=tk.DISABLED)

    def show_missing_installer_step(self, step_index):
        for index, frame in self.missing_installer_step_frames.items():
            frame.pack_forget()
            if index == step_index:
                frame.pack(fill=tk.BOTH, expand=True)

    def set_missing_installer_selected_paths(self, paths):
        if not self.missing_installer_selected_paths_listbox:
            return
        self.missing_installer_selected_paths_listbox.delete(0, tk.END)
        for path in paths or []:
            self.missing_installer_selected_paths_listbox.insert(tk.END, path)
        if len(paths or []) == 1:
            self.missing_installer_quick_path_var.set((paths or [""])[0])
        elif not paths:
            self.missing_installer_quick_path_var.set("")

    def get_missing_installer_quick_path(self):
        return self.missing_installer_quick_path_var.get().strip()

    def set_missing_installer_quick_path(self, path):
        self.missing_installer_quick_path_var.set((path or "").strip())

    def set_missing_installer_analysis_summary(self, summary):
        summary = summary or {}
        for key, var in self.missing_installer_summary_vars.items():
            var.set(str(summary.get(key, 0)))

    def load_missing_installer_packages(self, packages):
        if not self.missing_installer_package_tree:
            return
        for item in self.missing_installer_package_tree.get_children():
            self.missing_installer_package_tree.delete(item)

        for package in packages or []:
            self.missing_installer_package_tree.insert(
                "",
                tk.END,
                iid=package["id"],
                values=(
                    "√" if package.get("selected", True) else "",
                    package.get("title", ""),
                    package.get("missing_count", 0),
                    package.get("state", ""),
                    package.get("status", ""),
                ),
            )

    def set_missing_installer_preflight_summary(self, summary):
        summary = summary or {}
        for key, var in self.missing_installer_preflight_summary_vars.items():
            var.set(str(summary.get(key, 0)))

    def load_missing_installer_preflight_rows(self, rows):
        if not self.missing_installer_preflight_tree:
            return
        for item in self.missing_installer_preflight_tree.get_children():
            self.missing_installer_preflight_tree.delete(item)

        for row in rows or []:
            self.missing_installer_preflight_tree.insert(
                "",
                tk.END,
                iid=row["id"],
                values=(
                    row.get("title", ""),
                    ", ".join(row.get("source_plugins") or []),
                    row.get("strategy", ""),
                    row.get("risk_level", ""),
                    row.get("conclusion_label", ""),
                ),
            )

    def set_missing_installer_preflight_actions(self, *, can_install, safe_only_enabled, blocked_count):
        if self.missing_installer_preflight_install_button:
            self.missing_installer_preflight_install_button.config(
                state=tk.DISABLED if blocked_count else (tk.NORMAL if can_install else tk.DISABLED)
            )
        if self.missing_installer_preflight_safe_button:
            self.missing_installer_preflight_safe_button.config(
                state=tk.NORMAL if safe_only_enabled else tk.DISABLED
            )

    def get_selected_missing_installer_package_id(self):
        if not self.missing_installer_package_tree:
            return None
        selected = self.missing_installer_package_tree.selection()
        if selected:
            return selected[0]
        focus = self.missing_installer_package_tree.focus()
        return focus or None

    def load_missing_installer_manual_items(self, items):
        if not self.missing_installer_manual_listbox:
            return
        self.missing_installer_manual_listbox.delete(0, tk.END)
        for item in items or []:
            self.missing_installer_manual_listbox.insert(
                tk.END,
                f"{item.get('node_type', '')} - {item.get('reason', '')}",
            )

    def load_missing_installer_install_rows(self, packages):
        if not self.missing_installer_install_tree:
            return
        for item in self.missing_installer_install_tree.get_children():
            self.missing_installer_install_tree.delete(item)

        for package in packages or []:
            self.missing_installer_install_tree.insert(
                "",
                tk.END,
                iid=package["id"],
                values=(
                    package.get("title", ""),
                    package.get("status", ""),
                    package.get("missing_count", 0),
                ),
            )

    def append_missing_installer_log(self, message):
        if not self.missing_installer_log_text:
            logger.info(f"Missing installer log (widget not available): {message}")
            return
        try:
            self.missing_installer_log_text.config(state=tk.NORMAL)
            self.missing_installer_log_text.insert(tk.END, f"{message}\n")
            self.missing_installer_log_text.see(tk.END)
            self.missing_installer_log_text.config(state=tk.DISABLED)
        except tk.TclError as exc:
            logger.error(f"Error updating missing_installer_log_text: {exc}.")

    def clear_missing_installer_log(self):
        if not self.missing_installer_log_text:
            return
        try:
            self.missing_installer_log_text.config(state=tk.NORMAL)
            self.missing_installer_log_text.delete("1.0", tk.END)
            self.missing_installer_log_text.config(state=tk.DISABLED)
        except tk.TclError as exc:
            logger.error(f"Error clearing missing_installer_log_text: {exc}.")

    def set_missing_installer_queue_progress(self, message):
        self.missing_installer_queue_progress_var.set(message or "")

    def set_missing_installer_restart_button_visible(self, visible):
        if not self.missing_installer_restart_button:
            return
        if visible:
            self.missing_installer_restart_button.pack(side=tk.RIGHT)
        else:
            self.missing_installer_restart_button.pack_forget()
    
    def get_selected_plugin(self):
        """获取当前选中的插件名称"""
        selected = self.repair_plugins_tree.selection()
        if not selected:
            return None
        return self.repair_plugins_tree.item(selected[0], "values")[0]
    
    def display_repair_plugins(self, plugins_data):
        """显示插件列表"""
        # 清空现有项
        for item in self.repair_plugins_tree.get_children():
            self.repair_plugins_tree.delete(item)
        
        # 添加新项
        for plugin in plugins_data:
            self.repair_plugins_tree.insert("", tk.END, values=(
                plugin.get("name", ""),
                plugin.get("description", ""),
                plugin.get("status", "未检测")
            ))
    
    def update_plugin_status(self, plugin_name, status):
        """更新指定插件的状态"""
        for item in self.repair_plugins_tree.get_children():
            if self.repair_plugins_tree.item(item, "values")[0] == plugin_name:
                values = list(self.repair_plugins_tree.item(item, "values"))
                values[2] = status
                self.repair_plugins_tree.item(item, values=values)
                break

    # ... 原有代码 ...
