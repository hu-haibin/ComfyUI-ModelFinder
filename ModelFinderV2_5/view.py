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
        self.tab_single = None
        self.tab_batch = None
        self.tab_settings = None
        self.tab_irregular_names = None # 新增：不规则名称标签页的引用
        self.tab_model_config = None # 新增：模型配置标签页的引用

        self.tab_plugin_repair = None # 插件修复标签页的引用

        self.workflow_path_var = tk.StringVar()
        self.workflow_dir_var = tk.StringVar()
        self.file_pattern_var = tk.StringVar(value="*.json;*")
        self.chrome_path_var = tk.StringVar()
        self.theme_var = tk.StringVar()
        self.retention_days_var = tk.IntVar(value=30) # Keep default for initial display

        self.log_text = None
        self.progress_bar = None
        self.progress_label = None
        self.batch_progress_bar = None
        self.batch_progress_label = None
        self.result_tree = None
        self.view_result_button = None
        self.view_batch_html_button = None
        self.theme_dropdown = None
        self.status_label = None # Reference for status bar label
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

        self._set_icon()
        self._create_main_widgets() # self.notebook 在这里创建
        self._setup_tabs()          # 所有标签页在这里添加和设置
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
            # 或者更可靠的是，将其放在 ModelFinderV2_5 包内，并使用相对路径
            # 例如，如果 icon 在 ModelFinderV2_5/assets/Modelfinder.ico
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
        self.tab_single = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.tab_single, text="单个处理")
        self._setup_single_tab(self.tab_single)

        # 批量处理标签页
        self.tab_batch = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.tab_batch, text="批量处理")
        self._setup_batch_tab(self.tab_batch)

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
            days = self.controller.get_loaded_retention_days()
            logger.debug(f"Applying initial settings to view: Theme={theme}, Chrome='{chrome}', Days={days}")

            # Apply values to view widgets
            if theme and self.theme_dropdown: self.set_selected_theme(theme)
            self.set_chrome_path(chrome) # Assuming set_chrome_path updates the var
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
        if self.view_result_button:
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


    def _on_file_search(self, event):
        """当搜索框内容更改时过滤文件列表"""
        try:
            search_text = self.file_search_var.get().lower()
            
            # 如果搜索文本为空，显示所有项目
            if not search_text:
                for item_id in self.model_files_tree.get_children():
                    self.model_files_tree.item(item_id, tags=())  # 移除所有标签
                return
            
            # 搜索和过滤
            for item_id in self.model_files_tree.get_children():
                values = self.model_files_tree.item(item_id, "values")
                if not values or len(values) < 3:
                    continue
                
                name = str(values[0]).lower()
                directory = str(values[2]).lower()
                
                if search_text in name or search_text in directory:
                    # 匹配项添加高亮标签
                    self.model_files_tree.item(item_id, tags=("match",))
                    self.model_files_tree.tag_configure("match", background="#e6f3ff")
                else:
                    # 不匹配项添加隐藏标签
                    self.model_files_tree.item(item_id, tags=("hidden",))
                    self.model_files_tree.tag_configure("hidden", background="#f0f0f0")
        except Exception as e:
            logger.error(f"搜索过滤出错: {e}")

    def _clear_file_search(self):
        """清除搜索框并重置文件列表"""
        self.file_search_var.set("")
        # 触发搜索事件以重置列表
        self._on_file_search(None)

    def _show_file_context_menu(self, event):
        """显示文件右键菜单"""
        # 确保点击了某个项目
        item = self.model_files_tree.identify_row(event.y)
        if item:
            # 选中被点击的项目
            self.model_files_tree.selection_set(item)
            # 保存选中的文件信息
            self._on_model_file_select(None)
            # 在点击位置显示右键菜单
            self.file_context_menu.post(event.x_root, event.y_root)

    def _show_move_dialog(self):
        """显示移动文件对话框"""
        try:
            if not self.controller or not self.selected_model_file:
                self.show_warning("未选择文件", "请先选择要移动的模型文件")
                return
            
            # 创建对话框
            dialog = tk.Toplevel(self.root)
            dialog.title("移动文件")
            dialog.geometry("400x500")
            dialog.transient(self.root)
            dialog.grab_set()
            
            # 文件信息
            info_frame = ttk.Frame(dialog, padding=10)
            info_frame.pack(fill=tk.X)
            
            file_name = os.path.basename(self.selected_model_file)
            ttk.Label(info_frame, text=f"选中文件: {file_name}", wraplength=380).pack(fill=tk.X)
            
            # 目标目录选择
            dir_frame = ttk.LabelFrame(dialog, text="选择目标目录", padding=10)
            dir_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # 创建目录列表框
            dir_listbox = tk.Listbox(dir_frame)
            dir_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            # 添加滚动条
            dir_scroll = ttk.Scrollbar(dir_frame, orient=tk.VERTICAL, command=dir_listbox.yview)
            dir_listbox.configure(yscrollcommand=dir_scroll.set)
            dir_scroll.pack(side=tk.RIGHT, fill=tk.Y)
            
            # 填充目录列表
            if self.controller and self.controller.model_mover.comfyui_models_root:
                directories = self.controller.model_mover.get_model_subdirectories()
                for directory in directories:
                    dir_listbox.insert(tk.END, directory)
            
            # 创建新目录输入框
            new_dir_frame = ttk.Frame(dialog, padding=10)
            new_dir_frame.pack(fill=tk.X)
            
            ttk.Label(new_dir_frame, text="新目录名:").pack(side=tk.LEFT)
            new_dir_entry = ttk.Entry(new_dir_frame)
            new_dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            
            ttk.Button(new_dir_frame, text="创建", 
                      command=lambda: self._create_dir_in_dialog(new_dir_entry, dir_listbox)).pack(side=tk.LEFT, padx=(0, 5))
            
            # 备份选项
            backup_var = tk.BooleanVar(value=True)
            ttk.Checkbutton(dialog, text="创建备份", variable=backup_var).pack(padx=10, pady=5, anchor=tk.W)
            
            # 操作按钮
            btn_frame = ttk.Frame(dialog, padding=10)
            btn_frame.pack(fill=tk.X)
            
            ttk.Button(btn_frame, text="移动", style="primary.TButton",
                      command=lambda: self._move_file_from_dialog(dir_listbox, backup_var.get(), dialog)).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="取消", 
                      command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        except Exception as e:
            logger.error(f"显示移动对话框出错: {e}")
            if 'dialog' in locals():
                try:
                    dialog.destroy()
                except:
                    pass

    def _show_copy_dialog(self):
        """显示复制文件对话框"""
        try:
            if not self.controller or not self.selected_model_file:
                self.show_warning("未选择文件", "请先选择要复制的模型文件")
                return
            
            # 创建对话框
            dialog = tk.Toplevel(self.root)
            dialog.title("复制文件")
            dialog.geometry("400x500")
            dialog.transient(self.root)
            dialog.grab_set()
            
            # 文件信息
            info_frame = ttk.Frame(dialog, padding=10)
            info_frame.pack(fill=tk.X)
            
            file_name = os.path.basename(self.selected_model_file)
            ttk.Label(info_frame, text=f"选中文件: {file_name}", wraplength=380).pack(fill=tk.X)
            
            # 目标目录选择
            dir_frame = ttk.LabelFrame(dialog, text="选择目标目录", padding=10)
            dir_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # 创建目录列表框
            dir_listbox = tk.Listbox(dir_frame)
            dir_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            # 添加滚动条
            dir_scroll = ttk.Scrollbar(dir_frame, orient=tk.VERTICAL, command=dir_listbox.yview)
            dir_listbox.configure(yscrollcommand=dir_scroll.set)
            dir_scroll.pack(side=tk.RIGHT, fill=tk.Y)
            
            # 填充目录列表
            if self.controller and self.controller.model_mover.comfyui_models_root:
                directories = self.controller.model_mover.get_model_subdirectories()
                for directory in directories:
                    dir_listbox.insert(tk.END, directory)
            
            # 创建新目录输入框
            new_dir_frame = ttk.Frame(dialog, padding=10)
            new_dir_frame.pack(fill=tk.X)
            
            ttk.Label(new_dir_frame, text="新目录名:").pack(side=tk.LEFT)
            new_dir_entry = ttk.Entry(new_dir_frame)
            new_dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            
            ttk.Button(new_dir_frame, text="创建", 
                      command=lambda: self._create_dir_in_dialog(new_dir_entry, dir_listbox)).pack(side=tk.LEFT)
            
            # 操作按钮
            btn_frame = ttk.Frame(dialog, padding=10)
            btn_frame.pack(fill=tk.X)
            
            ttk.Button(btn_frame, text="复制", style="primary.TButton",
                      command=lambda: self._copy_file_from_dialog(dir_listbox, dialog)).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="取消", 
                      command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        except Exception as e:
            logger.error(f"显示复制对话框出错: {e}")
            if 'dialog' in locals():
                try:
                    dialog.destroy()
                except:
                    pass

    def _create_dir_in_dialog(self, entry_widget, listbox_widget):
        """在对话框中创建新目录"""
        try:
            if not self.controller:
                return
            
            dir_name = entry_widget.get().strip()
            if not dir_name:
                self.show_warning("错误", "请输入目录名称")
                return
            
            success, message = self.controller.model_mover.create_directory(dir_name)
            if success:
                # 刷新目录列表
                listbox_widget.delete(0, tk.END)
                directories = self.controller.model_mover.get_model_subdirectories()
                for directory in directories:
                    listbox_widget.insert(tk.END, directory)
                
                # 选中新创建的目录
                for i, directory in enumerate(directories):
                    if directory == dir_name:
                        listbox_widget.selection_set(i)
                        listbox_widget.see(i)
                        break
                
                # 清空输入框
                entry_widget.delete(0, tk.END)
            else:
                self.show_error("创建失败", message)
        except Exception as e:
            logger.error(f"在对话框中创建目录出错: {e}")

    def _move_file_from_dialog(self, listbox_widget, create_backup, dialog):
        """从对话框中执行移动文件操作"""
        try:
            if not self.controller or not self.selected_model_file:
                dialog.destroy()
                return
            
            selected_indices = listbox_widget.curselection()
            if not selected_indices:
                self.show_warning("未选择目标目录", "请选择要移动到的目标目录")
                return
            
            target_dir = listbox_widget.get(selected_indices[0])
            success = self.controller.handle_move_model_file(self.selected_model_file, target_dir, create_backup)
            
            if success:
                dialog.destroy()
                # 刷新文件列表
                if self.controller:
                    self.controller.scan_model_files()
        except Exception as e:
            logger.error(f"从对话框移动文件出错: {e}")
            if 'dialog' in locals():
                try:
                    dialog.destroy()
                except:
                    pass

    def _copy_file_from_dialog(self, listbox_widget, dialog):
        """从对话框中执行复制文件操作"""
        try:
            if not self.controller or not self.selected_model_file:
                dialog.destroy()
                return
            
            selected_indices = listbox_widget.curselection()
            if not selected_indices:
                self.show_warning("未选择目标目录", "请选择要复制到的目标目录")
                return
            
            target_dir = listbox_widget.get(selected_indices[0])
            success = self.controller.handle_copy_model_file(self.selected_model_file, target_dir)
            
            if success:
                dialog.destroy()
                # 刷新文件列表
                if self.controller:
                    self.controller.scan_model_files()
        except Exception as e:
            logger.error(f"从对话框复制文件出错: {e}")
            if 'dialog' in locals():
                try:
                    dialog.destroy()
                except:
                    pass

    def _on_model_file_double_click(self, event):
        """双击模型文件时显示移动对话框"""
        self._show_move_dialog()


    def _add_selected_file_to_registry(self):
        """将选中的文件添加到模型记录"""
        if not self.controller or not self.selected_model_file:
            self.show_warning("未选择文件", "请先选择要添加到记录的模型文件")
            return
        
        # 获取文件完整路径
        file_path = self.selected_model_file
        if not os.path.isabs(file_path) and self.controller.model_mover.comfyui_models_root:
            file_path = os.path.join(self.controller.model_mover.comfyui_models_root, file_path)
        
        # 添加到记录
        selected_type = None
        # 可以在这里添加一个对话框让用户选择类型
        
        self.controller.handle_add_model_registry_from_file(file_path, selected_type)
        
        # 切换到记录视图
        self._switch_model_view("registry")

    def _on_registry_model_select(self, event):
        """当选择模型记录时，显示详情"""
        if not self.registry_tree:
            return
        
        selected_items = self.registry_tree.selection()
        if not selected_items:
            self.selected_registry_model = None
            self._clear_registry_form()
            return
        
        item_id = selected_items[0]
        values = self.registry_tree.item(item_id, "values")
        if values and len(values) >= 2:
            model_id = values[0]
            
            # 从controller获取完整模型数据
            if self.controller:
                model_data = self.controller.model_registry.get_model(model_id)
                if model_data:
                    self.selected_registry_model = model_id
                    
                    # 填充表单
                    self.registry_name_var.set(model_data.get('name', ''))
                    self.registry_path_var.set(model_data.get('path', ''))
                    self.registry_model_type_var.set(model_data.get('type', ''))
                    self.registry_desc_var.set(model_data.get('description', ''))
                    
                    # 标签列表转为逗号分隔字符串
                    tags = model_data.get('tags', [])
                    if isinstance(tags, list):
                        self.registry_tags_var.set(','.join(tags))
                    else:
                        self.registry_tags_var.set('')
                    
                    # 大小
                    size_mb = model_data.get('size_mb', 0)
                    self.registry_size_var.set(f"{size_mb} MB")
                    
                    # 添加时间
                    self.registry_added_time_var.set(model_data.get('added_time', ''))
                    
                    return
        
        # 如果没有找到数据或出错，清空表单
        self.selected_registry_model = None
        self._clear_registry_form()

    def _clear_registry_form(self):
        """清空模型记录表单"""
        self.registry_name_var.set('')
        self.registry_path_var.set('')
        self.registry_model_type_var.set('')
        self.registry_desc_var.set('')
        self.registry_tags_var.set('')
        self.registry_size_var.set('')
        self.registry_added_time_var.set('')

    def _new_model_registry(self):
        """创建新的模型记录"""
        self.selected_registry_model = None
        self._clear_registry_form()

    def _save_model_registry(self):
        """保存模型记录"""
        if not self.controller:
            return
        
        # 获取表单数据
        model_data = {
            'name': self.registry_name_var.get().strip(),
            'path': self.registry_path_var.get().strip(),
            'type': self.registry_model_type_var.get().strip(),
            'description': self.registry_desc_var.get().strip(),
            'tags': [tag.strip() for tag in self.registry_tags_var.get().split(',') if tag.strip()]
        }
        
        # 检查必填项
        if not model_data['name'] or not model_data['path']:
            self.show_warning("保存失败", "模型名称和路径不能为空")
            return
        
        if not os.path.exists(model_data['path']):
            if not self.ask_yes_no("路径不存在", f"模型文件路径不存在：\n{model_data['path']}\n\n是否仍要保存记录？"):
                return
        
        # 如果有模型ID，则更新，否则添加新记录
        if self.selected_registry_model:
            self.controller.handle_update_model_registry(self.selected_registry_model, model_data)
        else:
            # 如果是新记录，要获取文件大小信息
            if os.path.exists(model_data['path']):
                file_size = os.path.getsize(model_data['path'])
                model_data['size'] = file_size
                model_data['size_mb'] = round(file_size / (1024 * 1024), 2)
            
            model_id = self.controller.handle_add_model_registry(model_data)
            if model_id:
                self.selected_registry_model = model_id

    def _delete_model_registry(self):
        """删除模型记录"""
        if not self.controller or not self.selected_registry_model:
            self.show_warning("删除失败", "请先选择要删除的模型记录")
            return
        
        self.controller.handle_delete_model_registry(self.selected_registry_model)
        self.selected_registry_model = None
        self._clear_registry_form()

    def _browse_registry_model_path(self):
        """浏览选择模型文件路径"""
        file_path = filedialog.askopenfilename(
            title="选择模型文件",
            filetypes=[
                ("模型文件", "*.safetensors;*.ckpt;*.pt;*.pth;*.bin"),
                ("所有文件", "*.*")
            ]
        )
        if file_path:
            self.registry_path_var.set(file_path)

    def _locate_model_file(self):
        """定位模型文件"""
        if not self.controller or not self.selected_registry_model:
            self.show_warning("定位失败", "请先选择要定位的模型记录")
            return
        
        model_data = self.controller.model_registry.get_model(self.selected_registry_model)
        if not model_data:
            self.show_warning("定位失败", "无法获取模型数据")
            return
        
        file_path = model_data.get('path', '')
        if not file_path or not os.path.exists(file_path):
            self.show_warning("定位失败", f"文件不存在:\n{file_path}")
            return
        
        # 打开文件所在的文件夹
        folder_path = os.path.dirname(file_path)
        os.startfile(folder_path)

    def _show_batch_operations(self):
        """显示批量操作对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("批量操作")
        dialog.geometry("500x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 创建操作选项框架
        op_frame = ttk.LabelFrame(dialog, text="批量操作选项", padding=10)
        op_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 待实现的批量操作...
        ttk.Label(op_frame, text="批量操作功能正在开发中...").pack(pady=20)
        
        # 关闭按钮
        ttk.Button(dialog, text="关闭", command=dialog.destroy).pack(pady=10)

    # --- 模型记录相关方法 ---

    def load_model_registry_results(self, models):
        """加载模型记录搜索结果"""
        # 清空当前记录
        if self.registry_tree:
            for item in self.registry_tree.get_children():
                self.registry_tree.delete(item)
        
        # 添加搜索结果
        for model in models:
            # 标签列表转为字符串
            tags_str = ','.join(model.get('tags', []))
            
            self.registry_tree.insert("", "end", values=(
                model.get('id', ''),
                model.get('name', ''),
                model.get('type', ''),
                model.get('size_mb', ''),
                tags_str
            ))

    def _on_directory_select(self, event):
        """当选择目录时，加载该目录下的模型文件"""
        if not self.model_dirs_listbox or not self.controller:
            return
        
        selected_indices = self.model_dirs_listbox.curselection()
        if not selected_indices:
            return
        
        selected_dir = self.model_dirs_listbox.get(selected_indices[0])
        self.controller.scan_model_files(selected_dir)
        
        # 重置搜索框
        if hasattr(self, 'file_search_var'):
            self.file_search_var.set("")
            self._on_file_search(None)
        
        # 重置排序
        if hasattr(self, 'model_files_sort_column') and hasattr(self, 'model_files_sort_reverse'):
            self.model_files_sort_column = "name"
            self.model_files_sort_reverse = False
            # 更新表头显示
            original_titles = {"name": "文件名", "size": "大小(MB)", "directory": "目录"}
            for col in ["name", "size", "directory"]:
                self.model_files_tree.heading(col, text=original_titles[col])

    def _on_model_file_select(self, event):
        """当选择模型文件时，保存选中的文件信息"""
        if not self.model_files_tree:
            return
        
        selected_items = self.model_files_tree.selection()
        if not selected_items:
            self.selected_model_file = None
            return
        
        item_id = selected_items[0]
        values = self.model_files_tree.item(item_id, "values")
        if values and len(values) >= 3:
            file_name, file_size, directory = values
            if directory:
                file_path = os.path.join(directory, file_name)
            else:
                file_path = file_name
            
            self.selected_model_file = file_path
            logger.debug(f"Selected model file: {self.selected_model_file}")
        else:
            self.selected_model_file = None

    def _move_selected_file(self):
        """处理移动选中文件的操作"""
        if not self.controller or not self.selected_model_file:
            self.show_warning("未选择文件", "请先选择要移动的模型文件")
            return
        
        selected_indices = self.model_dirs_listbox.curselection()
        if not selected_indices:
            self.show_warning("未选择目标目录", "请先选择要移动到的目标目录")
            return
        
        target_dir = self.model_dirs_listbox.get(selected_indices[0])
        self.controller.handle_move_model_file(self.selected_model_file, target_dir)

    def _copy_selected_file(self):
        """处理复制选中文件的操作"""
        if not self.controller or not self.selected_model_file:
            self.show_warning("未选择文件", "请先选择要复制的模型文件")
            return
        
        selected_indices = self.model_dirs_listbox.curselection()
        if not selected_indices:
            self.show_warning("未选择目标目录", "请先选择要复制到的目标目录")
            return
        
        target_dir = self.model_dirs_listbox.get(selected_indices[0])
        self.controller.handle_copy_model_file(self.selected_model_file, target_dir)

    # --- 模型管理相关的数据加载方法 ---




    def _sort_model_files(self, column):
        """根据列排序模型文件列表"""
        try:
            # 如果点击同一列，切换升序/降序
            if self.model_files_sort_column == column:
                self.model_files_sort_reverse = not self.model_files_sort_reverse
            else:
                # 如果点击不同列，设置新的排序列并默认升序
                self.model_files_sort_column = column
                self.model_files_sort_reverse = False
            
            # 获取所有项目
            items = []
            for item_id in self.model_files_tree.get_children():
                values = self.model_files_tree.item(item_id, "values")
                if not values or len(values) < 3:
                    continue
                items.append((item_id, values))
            
            # 排序
            col_idx = {"name": 0, "size": 1, "directory": 2}[column]
            
            # 安全排序
            def get_sort_key(values, idx):
                if idx == 1:  # 大小列
                    try:
                        return float(values[idx])
                    except (ValueError, TypeError):
                        return 0
                else:
                    return str(values[idx])
            
            items.sort(key=lambda x: get_sort_key(x[1], col_idx), reverse=self.model_files_sort_reverse)
            
            # 重新排列
            for idx, (item_id, _) in enumerate(items):
                self.model_files_tree.move(item_id, "", idx)
            
            # 更新标题显示排序方向
            for col in ["name", "size", "directory"]:
                if col == column:
                    direction = " ↓" if self.model_files_sort_reverse else " ↑"
                    self.model_files_tree.heading(col, text=f"{col.title()}{direction}")
                else:
                    # 恢复原标题
                    original_titles = {"name": "文件名", "size": "大小(MB)", "directory": "目录"}
                    self.model_files_tree.heading(col, text=original_titles[col])
        except Exception as e:
            logger.error(f"排序文件列表出错: {e}")

    def set_downloads_folder_path(self, path):
        """设置下载文件夹路径"""
        if hasattr(self, 'downloads_folder_entry'):
            self.downloads_folder_entry.delete(0, tk.END)
            self.downloads_folder_entry.insert(0, path)
    
    def get_downloads_folder_path(self):
        """获取下载文件夹路径"""
        if hasattr(self, 'downloads_folder_entry'):
            return self.downloads_folder_entry.get()
        return ""
    
    def load_download_files(self, file_paths):
        """加载下载文件夹中的模型文件到列表"""
        if hasattr(self, 'download_files_tree'):
            # 清空现有项
            self.download_files_tree.delete(*self.download_files_tree.get_children())
            
            # 添加新文件
            for file_path in file_paths:
                file_name = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)
                file_size_mb = round(file_size / (1024 * 1024), 2)
                
                self.download_files_tree.insert("", "end", values=(file_name, file_size_mb, file_path))
    
    def show_directory_recommendations(self, file_path, recommendations):
        """显示目录推荐对话框"""
        # 创建对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("目录推荐")
        dialog.geometry("600x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 添加文件信息
        file_frame = ttk.LabelFrame(dialog, text="文件信息")
        file_frame.pack(fill=tk.X, padx=10, pady=5)
        
        file_name = os.path.basename(file_path)
        ttk.Label(file_frame, text=f"文件名: {file_name}").pack(anchor=tk.W, padx=5, pady=2)
        
        # 推荐列表
        rec_frame = ttk.LabelFrame(dialog, text="推荐目录")
        rec_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 创建Treeview显示推荐
        columns = ("directory", "confidence", "reason", "needs_creation")
        tree = ttk.Treeview(rec_frame, columns=columns, show="headings")
        tree.heading("directory", text="目录")
        tree.heading("confidence", text="置信度")
        tree.heading("reason", text="推荐理由")
        tree.heading("needs_creation", text="需要创建")
        
        tree.column("directory", width=150)
        tree.column("confidence", width=80)
        tree.column("reason", width=250)
        tree.column("needs_creation", width=80)
        
        tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(rec_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 填充推荐数据
        for rec in recommendations:
            needs_creation = "是" if rec.get('needs_creation', False) else "否"
            confidence = f"{rec.get('confidence', 0) * 100:.1f}%"
            tree.insert("", "end", values=(rec.get('directory', ''), confidence, rec.get('reason', ''), needs_creation))
        
        # 添加按钮区域
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 选择并移动按钮
        def on_select_move():
            selected_item = tree.selection()
            if not selected_item:
                messagebox.showwarning("未选择", "请选择一个推荐目录")
                return
                
            directory = tree.item(selected_item[0], "values")[0]
            
            # 确认对话框
            if messagebox.askyesno("确认移动", f"确定要将文件移动到目录 '{directory}' 吗？"):
                dialog.destroy()
                # 执行移动
                if self.controller:
                    self.controller.handle_smart_move(file_path, directory, create_backup=True)
        
        ttk.Button(button_frame, text="选择并移动", command=on_select_move).pack(side=tk.LEFT, padx=5)
        
        # 关闭按钮
        ttk.Button(button_frame, text="关闭", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
    

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

