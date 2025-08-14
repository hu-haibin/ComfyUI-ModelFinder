"""
工具函数模块 (Utility Function Module)
包含辅助功能：依赖检查、浏览器检测、HTML生成等 (Contains helper functions: dependency check, browser detection, HTML generation, etc.)
"""

import os
import sys
import subprocess
import traceback
from urllib.parse import urlparse, urljoin
import csv
# Ensure pandas is imported if check_dependencies doesn't handle it early enough
try:
    import pandas as pd
except ImportError:
    print("错误：缺少 pandas 库。请先运行依赖检查或手动安装 `pip install pandas`。")
    # Optionally, you could call check_dependencies() here or exit
    # check_dependencies()
    # sys.exit(1)


def check_dependencies():
    """检查并安装缺失依赖 (Check and install missing dependencies)"""
    required_packages = {"pandas": "pandas", "DrissionPage": "DrissionPage", "ttkbootstrap": "ttkbootstrap"}
    missing_packages = []

    for package, pip_name in required_packages.items():
        try:
            __import__(package)
            print(f"✓ {package} 已安装 (is installed)")
        except ImportError:
            print(f"✗ 缺少 {package} (is missing)")
            missing_packages.append(pip_name)

    if missing_packages:
        print("\n安装缺失依赖... (Installing missing dependencies...)")
        try:
            # 尝试使用国内镜像源安装 (Try installing using domestic mirror source)
            cmd = [sys.executable, "-m", "pip", "install",
                   "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"]
            cmd.extend(missing_packages)
            subprocess.check_call(cmd)
            print("依赖安装成功! (Dependencies installed successfully!)")

            # 需要重启脚本以使导入生效 (Need to restart the script for imports to take effect)
            print("重启程序以应用更改... (Restarting the program to apply changes...)")
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as e:
            print(f"安装依赖出错 (Error installing dependencies): {e}")
            # 尝试使用备用源 (Try using alternative source)
            try:
                print("尝试备用镜像... (Trying alternative mirror...)")
                cmd = [sys.executable, "-m", "pip", "install",
                       "-i", "https://mirrors.aliyun.com/pypi/simple/"]
                cmd.extend(missing_packages)
                subprocess.check_call(cmd)
                print("依赖安装成功! (Dependencies installed successfully!)")

                # 需要重启脚本以使导入生效 (Need to restart the script for imports to take effect)
                print("重启程序以应用更改... (Restarting the program to apply changes...)")
                os.execv(sys.executable, [sys.executable] + sys.argv)
            except Exception as e2:
                print(f"安装依赖出错 (Error installing dependencies): {e2}")
                print("请手动安装以下包 (Please manually install the following packages):")
                for pkg in missing_packages:
                    print(f"pip install {pkg}")
                input("按Enter键退出... (Press Enter to exit...)")
                sys.exit(1)

def find_chrome_path():
    """查找Chrome浏览器路径 (Find Chrome browser path)"""
    # 可能的Chrome安装路径 (Possible Chrome installation paths)
    possible_paths = [
        # Windows 标准路径 (Windows standard paths)
        os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), 'Google', 'Chrome', 'Application', 'chrome.exe'),
        os.path.join(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'), 'Google', 'Chrome', 'Application', 'chrome.exe'),
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
        # 其他可能的Windows路径 (Other possible Windows paths)
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    ]

    # 检查这些路径 (Check these paths)
    for path in possible_paths:
        if os.path.exists(path):
            print(f"找到Chrome浏览器 (Found Chrome browser): {path}")
            return path

    # 从注册表获取Chrome路径(仅Windows) (Get Chrome path from registry (Windows only))
    if sys.platform.startswith('win'):
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe") as key:
                chrome_path = winreg.QueryValue(key, None)
                if os.path.exists(chrome_path):
                    print(f"从注册表找到Chrome浏览器 (Found Chrome browser from registry): {chrome_path}")
                    return chrome_path
        except Exception as e:
            print(f"检查注册表时出错 (Error checking registry): {e}")

    print("警告: 未找到Chrome浏览器。请安装Chrome。 (Warning: Chrome browser not found. Please install Chrome.)")
    return None

def get_mirror_link(original_url):
    """获取Hugging Face的镜像链接 (Get Hugging Face mirror link)"""
    if not original_url or 'huggingface.co' not in original_url:
        return ''

    try:
        # 解析URL以确保正确的格式转换 (Parse URL to ensure correct format conversion)
        parsed_url = urlparse(original_url)
        path = parsed_url.path

        # 确保路径格式正确（移除/resolve/并替换为对应路径）(Ensure correct path format (remove /resolve/ and replace with corresponding path))
        if '/resolve/' in path:
            path = path.replace('/resolve/', '/blob/') # Temporarily use /blob/ for joining

        # 构建正确的镜像链接 (Build the correct mirror link)
        mirror_base_url = "https://hf-mirror.com"
        mirror_url = urljoin(mirror_base_url, path)

        # 将blob替换回resolve用于下载 (Replace blob back with resolve for downloading)
        if '/blob/' in mirror_url:
            mirror_url = mirror_url.replace('/blob/', '/resolve/')

        return mirror_url
    except Exception as e:
        print(f"构建镜像链接时出错 (Error building mirror link): {e}")
        return ''

def create_html_view(csv_file):
    """创建改进的HTML视图，包含表头筛选、批量复制和统一字体 (Create improved HTML view with header filtering, batch copy, and unified font)

    参数 (Args):
        csv_file: CSV文件路径，可能是单个工作流的结果或汇总文件 (CSV file path, could be result of a single workflow or a summary file)

    返回 (Returns):
        生成的HTML文件路径，失败则返回None (Path to the generated HTML file, or None on failure)
    """
    # Ensure pandas is available before proceeding
    if 'pd' not in globals():
         print("错误: pandas 库未加载。无法创建 HTML 视图。")
         return None

    try:
        # 添加调试信息 (Add debug info)
        print(f"正在为 {csv_file} 创建HTML视图 (Creating HTML view for {csv_file})")

        # 读取CSV文件并尝试不同的编码 (Read CSV file and try different encodings)
        df = None
        encodings_to_try = ['utf-8', 'utf-8-sig', 'gbk', 'gb18030']
        for enc in encodings_to_try:
            try:
                df = pd.read_csv(csv_file, encoding=enc)
                print(f"使用 {enc} 成功读取CSV，列名 (Successfully read CSV using {enc}, columns): {df.columns.tolist()}")
                break # Stop trying once successful
            except UnicodeDecodeError:
                print(f"尝试 {enc} 编码失败 (Failed trying {enc} encoding)")
            except Exception as e:
                print(f"读取CSV文件时发生其他错误 (Other error reading CSV file): {e}")
                # Don't break here, maybe another encoding works

        if df is None:
            print(f"读取CSV文件失败，尝试了 {encodings_to_try} (Failed to read CSV file after trying {encodings_to_try})")
            return None

        # 确定核心列 (Determine core columns)
        # Find the actual column name for mirror links, case-insensitive check
        mirror_link_col = None
        for col in df.columns:
            if col.lower() == '镜像链接' or col.lower() == 'hf镜像':
                 mirror_link_col = col
                 break

        if not mirror_link_col:
            print("警告: CSV文件中未找到 '镜像链接' 或 'hf镜像' 列。批量复制功能将不可用。(Warning: '镜像链接' or 'hf镜像' column not found in CSV. Batch copy feature will be unavailable.)")
            # Continue without batch copy feature if column is missing

        # 生成HTML文件名 (Generate HTML filename)
        html_file = os.path.splitext(csv_file)[0] + '.html'

        # --- HTML Head and Styles ---
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>模型下载链接 (Model Download Links)</title>
            <style>
                body { font-family: "Microsoft YaHei", Arial, sans-serif; margin: 20px; }
                table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; word-wrap: break-word; } /* Added word-wrap */
                th {
                    background-color: #f2f2f2;
                    position: sticky;
                    top: 0; /* Stick to the top */
                    z-index: 5; /* Ensure header is above table content */
                    cursor: pointer;
                    user-select: none;
                }
                th:hover { background-color: #e0e0e0; }
                th .filter-icon { margin-left: 5px; font-size: 12px; color: #666; }
                tr:nth-child(even) { background-color: #f9f9f9; }
                a { text-decoration: none; color: #0066cc; } /* Default link color */
                a:hover { text-decoration: underline; }
                .status-processed { color: green; font-weight: bold; }
                .status-notfound { color: red; }
                .status-error { color: orange; }
                .file-name { font-weight: bold; }
                /* Adjusted link column style */
                .link-col { max-width: 150px; text-align: center; font-size: 14px; }
                .link-col a { display: inline-block; padding: 2px 6px; border-radius: 3px; }
                .hf-link a { background-color: #ffe0cc; color: #ff6000; } /* HuggingFace */
                .mirror-link a { background-color: #cce0ff; color: #0066ff; } /* HF Mirror */
                .liblib-link a { background-color: #ccffcc; color: #00aa00; } /* LibLib */
                .no-link { color: #999; text-align: center; font-size: 14px; } /* Style for '×暂无' */

                .summary { margin-top: 20px; padding: 10px; background-color: #f8f8f8; border-radius: 5px; }
                .section-title { font-size: 1.2em; margin-top: 30px; margin-bottom: 10px; font-weight: bold; }
                .controls-box { margin-bottom: 20px; padding: 10px; background: #f0f0f0; border-radius: 5px; display: flex; align-items: center; gap: 15px; flex-wrap: wrap; }
                #filterInput { padding: 5px; border: 1px solid #ccc; border-radius: 3px; }
                #copyButton {
                    padding: 5px 10px;
                    background-color: #4CAF50; /* Green */
                    color: white;
                    border: none;
                    border-radius: 3px;
                    cursor: pointer;
                    font-size: 14px;
                    transition: background-color 0.3s ease;
                }
                #copyButton:hover { background-color: #45a049; }
                #copyButton:disabled { background-color: #cccccc; cursor: not-allowed; }
                #copyMessage { margin-left: 10px; color: green; font-weight: bold; }

                .usage-guide {
                    margin-bottom: 15px; padding: 10px; background: #f8fff8;
                    border-left: 4px solid #00aa00; border-radius: 3px; font-size: 14px;
                }
                .usage-guide ul { margin: 5px 0 0 20px; padding: 0; }

                /* Dropdown styles */
                .dropdown-content {
                    display: none; position: absolute; background-color: white;
                    min-width: 160px; box-shadow: 0px 8px 16px 0px rgba(0,0,0,0.2);
                    z-index: 10; padding: 5px; border-radius: 3px;
                    max-height: 300px; overflow-y: auto; border: 1px solid #ccc;
                }
                .dropdown-content.show { display: block; }
                .dropdown-item { padding: 5px; cursor: pointer; display: flex; align-items: center; font-size: 14px; }
                .dropdown-item:hover { background-color: #f1f1f1; }
                .dropdown-item input[type='checkbox'] { margin-right: 8px; }
                .dropdown-search { width: 100%; box-sizing: border-box; padding: 5px; margin-bottom: 5px; border: 1px solid #ccc; border-radius: 3px; }
                .filter-buttons { display: flex; justify-content: space-between; margin-top: 5px; padding-top: 5px; border-top: 1px solid #eee; }
                .filter-apply, .filter-clear { padding: 3px 8px; cursor: pointer; background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 3px; font-size: 12px; }
                .filter-apply:hover, .filter-clear:hover { background-color: #e0e0e0; }
            </style>
        </head>
        <body>
            <h1>模型下载链接 (Model Download Links)</h1>
        """

        # --- File Info and Usage Guide ---
        file_basename = os.path.basename(csv_file)
        html_content += f"""
            <p>源文件 (Source File): {file_basename}</p>
            <p>生成时间 (Generated Time): {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

            <div class="usage-guide">
                <p><strong>使用说明 (Instructions):</strong></p>
                <ul>
                    <li>点击表格标题可以<strong>排序</strong>列内容 (Click table headers to <strong>sort</strong> columns)</li>
                    <li>点击表格标题右侧的筛选图标 <span class="filter-icon">▼</span> 可以<strong>筛选</strong>列内容 (Click filter icon <span class="filter-icon">▼</span> next to headers to <strong>filter</strong> columns)</li>
                    <li>表格中 <span style="color: #0066cc;">✓点此跳转</span> 表示有链接可点击，<span class="no-link">×暂无</span> 表示无链接 (✓Link indicates a clickable link, ×NoLink means no link)</li>
                    <li><span class="hf-link" style="padding: 0 3px; border-radius: 3px;">✓HF</span> - 跳转到 HuggingFace 模型页面 (Go to HuggingFace model page)</li>
                    <li><span class="mirror-link" style="padding: 0 3px; border-radius: 3px;">✓镜像</span> - 跳转到 HF镜像 下载页面 (Go to HF Mirror download page)</li>
                    <li><span class="liblib-link" style="padding: 0 3px; border-radius: 3px;">✓LibLib</span> - 跳转到 LibLib 模型页面 (Go to LibLib model page)</li>
                    <li>使用 "批量复制镜像链接" 按钮复制当前可见的 HF 镜像链接到剪贴板，可粘贴到下载工具。(Use "Batch Copy Mirror Links" button to copy visible HF Mirror links to clipboard for download tools.)</li>
                </ul>
            </div>
        """

        # --- Controls: Filter and Batch Copy Button ---
        # Only show controls if it's a model list (has '文件名' column)
        if '文件名' in df.columns:
            html_content += """
            <div class="controls-box">
                <div>
                    <label for="filterInput">筛选模型名称 (Filter Model Name): </label>
                    <input type="text" id="filterInput" onkeyup="filterTable()" placeholder="输入关键词... (Enter keywords...)">
                </div>
            """
            # Add Batch Copy button only if mirror link column exists
            if mirror_link_col:
                 html_content += """
                 <div>
                     <button id="copyButton" onclick="batchCopyMirrorLinks()">批量复制镜像链接 (Batch Copy Mirror Links)</button>
                     <span id="copyMessage"></span>
                 </div>
                 """
            html_content += "</div>" # Close controls-box

        # --- Table Generation ---
        html_content += '<table id="modelTable">\n<thead>\n<tr>\n' # Use thead for sticky header

        # Generate Table Headers
        display_columns = []
        col_name_map = {} # To store original column names for data access
        mirror_link_col_index = -1 # Track index for JS

        # Define preferred column order (can be adjusted)
        preferred_order = ['序号', '文件名', '节点ID', '节点类型', '下载链接', '镜像链接', 'hf镜像', '搜索链接', '状态', 'CSV文件', '工作流文件', '缺失数量']
        available_cols_ordered = [col for col in preferred_order if col in df.columns or col.lower() in [c.lower() for c in df.columns]]
        # Add any remaining columns not in preferred order
        remaining_cols = [col for col in df.columns if col not in available_cols_ordered and col.lower() not in [c.lower() for c in available_cols_ordered]]
        final_column_order = available_cols_ordered + remaining_cols

        col_index_counter = 0
        for col in final_column_order:
             # Find the actual case-sensitive column name from df.columns
             actual_col = next((c for c in df.columns if c.lower() == col.lower()), None)
             if not actual_col: continue # Skip if somehow column doesn't exist

             display_columns.append(actual_col)
             col_name_map[col_index_counter] = actual_col # Map index to actual name

             # Display Name Mapping
             display_name = actual_col
             if actual_col.lower() == '下载链接': display_name = 'HuggingFace'
             elif actual_col.lower() == '镜像链接' or actual_col.lower() == 'hf镜像':
                 display_name = 'HF镜像 (Mirror)'
                 mirror_link_col_index = col_index_counter # Store the index
             elif actual_col.lower() == '搜索链接': display_name = 'LibLib'

             # Add header cell with sorting and filtering
             html_content += f'<th onclick="sortTable({col_index_counter})">{display_name}<span class="filter-icon" onclick="event.stopPropagation(); showFilter(event, {col_index_counter})">▼</span></th>\n'
             col_index_counter += 1

        html_content += "</tr>\n</thead>\n<tbody>\n" # Close thead, open tbody

        # Generate Table Rows
        row_count = 0
        for index, row in df.iterrows():
            row_count += 1
            html_content += "<tr>\n"

            for i in range(len(display_columns)):
                actual_col_name = display_columns[i] # Get the correct column name
                value = row.get(actual_col_name, '')
                if pd.isna(value):
                    value = ''

                # --- Cell Formatting ---
                if actual_col_name == '状态':
                    status_class = "status-notfound" # Default
                    if isinstance(value, str):
                        if '已处理' in value or 'Found' in value: status_class = "status-processed"
                        elif '错误' in value or 'Error' in value: status_class = "status-error"
                    html_content += f'<td class="{status_class}">{value}</td>\n'

                elif actual_col_name in ['文件名', 'CSV文件', '工作流文件']:
                    html_content += f'<td class="file-name">{value}</td>\n'

                elif actual_col_name.lower() in ['下载链接', '镜像链接', 'hf镜像', '搜索链接']:
                    link_text = "✓" # Default symbol
                    link_class = "link-col"
                    tooltip = ""
                    target_url = str(value).strip() if value else ""

                    if target_url:
                        if actual_col_name.lower() == '下载链接':
                             if 'huggingface' in target_url:
                                 link_class += " hf-link"
                                 link_text = "✓ HF"
                                 tooltip = "跳转到HuggingFace模型页面 (Go to HuggingFace)"
                             elif 'liblib' in target_url: # Handle cases where liblib link might be in '下载链接'
                                 link_class += " liblib-link"
                                 link_text = "✓ LibLib"
                                 tooltip = "跳转到LibLib模型页面 (Go to LibLib)"
                             else: # Generic link
                                 tooltip = "跳转到下载页面 (Go to download page)"
                                 link_text = "✓ Link"

                        elif actual_col_name.lower() == '镜像链接' or actual_col_name.lower() == 'hf镜像':
                             link_class += " mirror-link"
                             link_text = "✓ 镜像 (Mirror)"
                             tooltip = "跳转到HF镜像下载页面 (Go to HF Mirror)"

                        elif actual_col_name.lower() == '搜索链接':
                             link_class += " liblib-link"
                             link_text = "✓ LibLib"
                             tooltip = "跳转到LibLib模型页面 (Go to LibLib)"

                        html_content += f'<td class="{link_class}"><a href="{target_url}" target="_blank" title="{tooltip}">{link_text}</a></td>\n'
                    else:
                        # No link
                        html_content += '<td class="no-link">× 暂无 (None)</td>\n'
                else:
                    # Other columns
                    html_content += f'<td>{value}</td>\n'

            html_content += "</tr>\n"

        # --- Table End and Summary ---
        html_content += "</tbody>\n</table>\n" # Close tbody and table

        html_content += f"""
            <div class="summary">
                <p>总记录数 (Total Records): {row_count}</p>
            </div>
        """

        # --- Filter Dropdown Element ---
        html_content += """
            <div id="filterDropdown" class="dropdown-content">
                <input type="text" class="dropdown-search" placeholder="搜索筛选项... (Search filter options...)" id="filterSearchInput" onkeyup="filterDropdownItems()">
                <div id="dropdown-items"></div>
                <div class="filter-buttons">
                    <button class="filter-apply" onclick="applyFilter()">应用 (Apply)</button>
                    <button class="filter-clear" onclick="clearFilter()">清除 (Clear)</button>
                </div>
            </div>
        """

        # --- JavaScript Section ---
        # IMPORTANT: Use regular triple quotes """, not f""" for the script block
        # to avoid Python interpreting JS curly braces.
        html_content += f"""
            <script>
            // Pass Python variable to JS before the main script block
            var mirrorLinkColumnIndex = {mirror_link_col_index};
            </script>
        """
        # Now add the main script block as a regular string
        html_content += """
            <script>
            // Global variables for filtering and table access
            var currentFilterColumn = -1;
            var currentFilterValues = {}; // Stores active filters: {colIndex: [value1, value2]}
            var modelTable = document.getElementById("modelTable");
            var tableHeaders = modelTable.querySelectorAll("thead th"); // Target thead headers
            var tableBody = modelTable.querySelector("tbody"); // Target tbody for rows
            // mirrorLinkColumnIndex is already defined in the previous script tag

            // --- Batch Copy Function ---
            function batchCopyMirrorLinks() {
                if (mirrorLinkColumnIndex < 0) {
                    alert("错误：未找到镜像链接列，无法复制。(Error: Mirror link column not found, cannot copy.)");
                    return;
                }

                var links = [];
                var rows = tableBody.getElementsByTagName("tr");
                var copyButton = document.getElementById("copyButton");
                var copyMessage = document.getElementById("copyMessage");

                copyButton.disabled = true; // Disable button during copy
                copyMessage.textContent = "正在复制... (Copying...)";

                for (var i = 0; i < rows.length; i++) {
                    // Check if row is visible (not display: none)
                    if (rows[i].style.display !== "none") {
                        var cells = rows[i].getElementsByTagName("td");
                        if (cells.length > mirrorLinkColumnIndex) {
                            var cell = cells[mirrorLinkColumnIndex];
                            var linkElement = cell.querySelector("a"); // Find the link within the cell
                            if (linkElement && linkElement.href) {
                                links.push(linkElement.href);
                            }
                        }
                    }
                }

                if (links.length > 0) {
                    var linksText = links.join("\\n"); // Join with newlines for Thunder
                    navigator.clipboard.writeText(linksText).then(function() {
                        copyMessage.textContent = `✓ 已复制 ${links.length} 条链接! (Copied ${links.length} links!)`;
                        copyButton.textContent = "复制成功 (Copied!)";
                        setTimeout(() => { // Reset message and button after a delay
                            copyMessage.textContent = "";
                            copyButton.textContent = "批量复制镜像链接 (Batch Copy Mirror Links)";
                            copyButton.disabled = false;
                        }, 3000); // Reset after 3 seconds
                    }, function(err) {
                        copyMessage.textContent = "复制失败! (Copy failed!)";
                        console.error('Async: Could not copy text: ', err);
                        alert("复制失败，请检查浏览器权限或手动复制。(Copy failed. Check browser permissions or copy manually.)");
                        copyButton.disabled = false; // Re-enable button on failure
                        copyButton.textContent = "批量复制镜像链接 (Batch Copy Mirror Links)";
                    });
                } else {
                    copyMessage.textContent = "没有可见的镜像链接可复制。(No visible mirror links to copy.)";
                     setTimeout(() => {
                         copyMessage.textContent = "";
                         copyButton.disabled = false;
                         copyButton.textContent = "批量复制镜像链接 (Batch Copy Mirror Links)";
                     }, 3000);
                }
            }

            // --- Sorting Function ---
            function sortTable(n) {
                var switching, i, x, y, shouldSwitch, dir, switchcount = 0;
                switching = true;
                dir = "asc"; // Default sort direction

                // Get current sort direction from header icon if available
                var currentIcon = tableHeaders[n].querySelector(".filter-icon").textContent;
                if (currentIcon === "▲") {
                    dir = "desc"; // If already ascending, switch to descending
                }

                while (switching) {
                    switching = false;
                    var rows = tableBody.getElementsByTagName("tr"); // Use tbody rows

                    for (i = 0; i < (rows.length - 1); i++) {
                        shouldSwitch = false;
                        x = rows[i].getElementsByTagName("TD")[n];
                        y = rows[i + 1].getElementsByTagName("TD")[n];

                        var xText = x.textContent || x.innerText;
                        var yText = y.textContent || y.innerText;

                        // Handle link columns ('✓' vs '×')
                        var xIsLink = x.querySelector("a") !== null;
                        var yIsLink = y.querySelector("a") !== null;

                        if (x.classList.contains('link-col') || x.classList.contains('no-link')) {
                             if (dir == "asc") { // Links first
                                 shouldSwitch = !xIsLink && yIsLink;
                             } else { // No links first
                                 shouldSwitch = xIsLink && !yIsLink;
                             }
                             // If both are links or both not links, sort by text (e.g., "✓ HF" vs "✓ Mirror")
                             if (xIsLink === yIsLink) {
                                 if (dir == "asc") {
                                     shouldSwitch = xText.toLowerCase() > yText.toLowerCase();
                                 } else {
                                     shouldSwitch = xText.toLowerCase() < yText.toLowerCase();
                                 }
                             }
                        } else {
                            // Attempt numeric sort first
                            var xNum = parseFloat(xText.replace(/,/g, '')); // Handle commas in numbers
                            var yNum = parseFloat(yText.replace(/,/g, ''));

                            if (!isNaN(xNum) && !isNaN(yNum)) {
                                if (dir == "asc") {
                                    shouldSwitch = xNum > yNum;
                                } else {
                                    shouldSwitch = xNum < yNum;
                                }
                            } else {
                                // Fallback to string comparison
                                if (dir == "asc") {
                                    shouldSwitch = xText.toLowerCase() > yText.toLowerCase();
                                } else {
                                    shouldSwitch = xText.toLowerCase() < yText.toLowerCase();
                                }
                            }
                        }


                        if (shouldSwitch) {
                            rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
                            switching = true;
                            switchcount++;
                            break; // Break after a switch and restart loop
                        }
                    }
                }

                // Update header icons
                for (var k = 0; k < tableHeaders.length; k++) {
                    var icon = tableHeaders[k].querySelector(".filter-icon");
                    // Reset non-active sort/filter icons, keep active filter icons
                     if (!icon.textContent || icon.textContent === "▲" || icon.textContent === "▼") {
                         // Check if filter is active for this column (k) and if it's not filtering everything out
                         var isFullyFiltered = currentFilterValues[k] && currentFilterValues[k].length === 0; // No values selected means filter is active but shows nothing
                         var isPartiallyFiltered = currentFilterValues[k] && currentFilterValues[k].length > 0 && (tableBody.rows.length > 0 ? currentFilterValues[k].length < new Set(Array.from(tableBody.rows).map(r => r.cells[k].textContent.trim())).size : false);

                         if (k !== n && (isFullyFiltered || isPartiallyFiltered)) {
                             // If it's not the column being sorted AND it has an active filter, keep the filter icon
                             icon.textContent = "🔍";
                         } else if (k !==n) {
                             // Otherwise, reset to default arrow if it's not the sorted column
                             icon.textContent = "▼";
                         }
                     } else if (k !== n && icon.textContent === "🔍") {
                         // Keep filter icon if it's already there and not the column being sorted
                          icon.textContent = "🔍";
                     } else if (k !== n) {
                        // Default reset for non-sorted, non-filtered columns
                        icon.textContent = "▼";
                     }
                }
                 // Set the current sort icon for the column that was just sorted (n)
                 tableHeaders[n].querySelector(".filter-icon").textContent = (dir === "asc") ? "▲" : "▼";
            }


            // --- Global Text Filter Function ---
            function filterTable() {
                var input, filter, tr, td, i, j, txtValue, found;
                input = document.getElementById("filterInput");
                filter = input ? input.value.toUpperCase() : ""; // Handle case where input might not exist
                tr = tableBody.getElementsByTagName("tr");

                for (i = 0; i < tr.length; i++) {
                    // First check column filters
                    if (!passesColumnFilters(tr[i])) {
                        tr[i].style.display = "none";
                        continue;
                    }

                    // Then check global text filter (if input exists)
                    if (filter === "") {
                        tr[i].style.display = ""; // Show if no global filter and passes column filters
                        continue;
                    }

                    td = tr[i].getElementsByTagName("td");
                    found = false;
                    for (j = 0; j < td.length; j++) {
                        txtValue = td[j].textContent || td[j].innerText;
                        if (txtValue.toUpperCase().indexOf(filter) > -1) {
                            found = true;
                            break;
                        }
                    }
                    tr[i].style.display = found ? "" : "none";
                }
            }

            // --- Column Filter Dropdown Functions ---
            function showFilter(event, colIndex) {
                var dropdown = document.getElementById("filterDropdown");
                currentFilterColumn = colIndex; // Set the column being filtered

                // Position dropdown below the icon
                var icon = event.target; // Should be the span icon
                var th = icon.closest('th'); // Get the parent th
                var rect = th.getBoundingClientRect(); // Use th for positioning base
                var iconRect = icon.getBoundingClientRect(); // Use icon for fine-tuning

                dropdown.style.left = rect.left + window.scrollX + "px";
                // Position below the icon itself, not the whole header cell bottom
                dropdown.style.top = iconRect.bottom + window.scrollY + 5 + "px";
                dropdown.style.minWidth = Math.max(180, rect.width) + "px"; // Base width on header cell

                populateDropdown(colIndex); // Fill with options
                dropdown.classList.add("show");
                document.getElementById('filterSearchInput').value = ''; // Clear search
                filterDropdownItems(); // Show all items initially

                // Close dropdown if clicked outside
                 // Use setTimeout to defer adding the listener slightly
                setTimeout(() => {
                    window.onclick = function(closeEvent) {
                        // Close if click is outside dropdown AND outside the filter icon that opened it
                        if (!dropdown.contains(closeEvent.target) && !icon.contains(closeEvent.target)) {
                            dropdown.classList.remove("show");
                            window.onclick = null; // Remove listener after closing
                        }
                    }
                }, 0);
            }

            function populateDropdown(colIndex) {
                var rows = tableBody.getElementsByTagName("tr");
                var uniqueValues = new Set();

                // Collect unique values from the column
                for (var i = 0; i < rows.length; i++) {
                    // Only consider rows currently potentially visible (respects global filter, but not column filters yet)
                    // This prevents options disappearing entirely if globally filtered out.
                    // We will rely on passesColumnFilters later.
                    // if (rows[i].style.display !== "none") { // Optimization: only check visible rows? Might hide options. Let's check all.
                        if (rows[i].cells.length > colIndex) {
                            var cell = rows[i].cells[colIndex];
                            var value = (cell.textContent || cell.innerText).trim();
                            uniqueValues.add(value);
                        }
                    // }
                }

                var sortedValues = Array.from(uniqueValues).sort();
                var dropdownItemsDiv = document.getElementById("dropdown-items");
                dropdownItemsDiv.innerHTML = ""; // Clear previous items

                // Add "Select All"
                var allItem = document.createElement("div");
                allItem.className = "dropdown-item";
                allItem.innerHTML = '<input type="checkbox" id="select-all" onchange="toggleAll(this.checked)"> <label for="select-all">全选 (Select All)</label>';
                dropdownItemsDiv.appendChild(allItem);
                dropdownItemsDiv.appendChild(document.createElement("hr")); // Separator

                // Add items for each unique value
                var activeFilters = currentFilterValues[colIndex] || null; // Get active filters for this column

                sortedValues.forEach(function(value, index) {
                    var item = document.createElement("div");
                    item.className = "dropdown-item";
                    var checkboxId = "filter-item-" + index;
                    // Check if this value should be checked (either no filter active, or this value is in the active filter list)
                    var isChecked = !activeFilters || activeFilters.includes(value);

                    item.innerHTML = `<input type="checkbox" id="${checkboxId}" value="${value}" ${isChecked ? "checked" : ""}> <label for="${checkboxId}">${value || '(Blank)'}</label>`; // Handle blank values
                    dropdownItemsDiv.appendChild(item);
                });

                updateSelectAllCheckbox(); // Set initial state of "Select All"
            }

            function filterDropdownItems() {
                var input = document.getElementById("filterSearchInput");
                var filter = input.value.toUpperCase();
                var items = document.querySelectorAll("#dropdown-items .dropdown-item:not(:first-child)"); // Exclude "Select All"

                items.forEach(function(item) {
                    var label = item.querySelector("label");
                    var text = label ? (label.textContent || label.innerText) : "";
                    item.style.display = text.toUpperCase().indexOf(filter) > -1 ? "" : "none";
                });
                 updateSelectAllCheckbox(); // Update select all based on visible items
            }

            function applyFilter() {
                var selectedValues = [];
                var checkboxes = document.querySelectorAll("#dropdown-items .dropdown-item:not(:first-child) input[type='checkbox']");
                var allPossibleValuesInDropdown = []; // All values currently in the dropdown (before filtering)

                 // Re-populate the unique values set to get ALL possible values for this column
                 var allRows = tableBody.getElementsByTagName("tr");
                 var allUniqueValuesSet = new Set();
                 for (var i = 0; i < allRows.length; i++) {
                     if (allRows[i].cells.length > currentFilterColumn) {
                         allUniqueValuesSet.add((allRows[i].cells[currentFilterColumn].textContent || allRows[i].cells[currentFilterColumn].innerText).trim());
                     }
                 }
                 allPossibleValuesInDropdown = Array.from(allUniqueValuesSet);


                checkboxes.forEach(function(checkbox) {
                    // allPossibleValuesInDropdown.push(checkbox.value); // Collect all values represented by checkboxes
                    if (checkbox.checked) {
                        selectedValues.push(checkbox.value);
                    }
                });

                var filterIcon = tableHeaders[currentFilterColumn].querySelector(".filter-icon");

                // Update filter state
                // Check if the number of selected values equals the total number of unique values for that column
                if (selectedValues.length === allPossibleValuesInDropdown.length || selectedValues.length === 0) {
                    // If all unique values are selected, or none are selected, treat as no filter active for this column
                    delete currentFilterValues[currentFilterColumn];
                    // Reset icon only if it wasn't a sort icon (▲ or ▼)
                    if (filterIcon.textContent === "🔍") {
                       // Check if it's also the sort column, if so, restore sort icon, otherwise default
                       var currentSortIcon = tableHeaders[currentFilterColumn].matches('[aria-sort]') ? (tableHeaders[currentFilterColumn].getAttribute('aria-sort') === 'ascending' ? '▲' : '▼') : '▼'; // A bit complex, maybe simplify
                       filterIcon.textContent = "▼"; // Simplified: just reset to default arrow when filter cleared
                    }
                } else {
                    // Otherwise, apply the filter with the selected values
                    currentFilterValues[currentFilterColumn] = selectedValues;
                    filterIcon.textContent = "🔍"; // Set filter indicator
                }


                document.getElementById("filterDropdown").classList.remove("show");
                filterTable(); // Re-apply filters to the main table
            }

            function clearFilter() {
                 // Clear filter for the current column
                 if (currentFilterColumn in currentFilterValues) {
                     delete currentFilterValues[currentFilterColumn];
                 }

                 // Reset header icon (only if it's the filter icon)
                 var filterIcon = tableHeaders[currentFilterColumn].querySelector(".filter-icon");
                 if (filterIcon.textContent === "🔍") {
                    filterIcon.textContent = "▼"; // Reset to default
                 }


                 // Check all checkboxes in the dropdown (even hidden ones by search)
                 var checkboxes = document.querySelectorAll("#dropdown-items .dropdown-item input[type='checkbox']");
                 checkboxes.forEach(function(checkbox) { checkbox.checked = true; });

                 document.getElementById("filterDropdown").classList.remove("show");
                 filterTable(); // Re-apply filters
            }

            function toggleAll(checked) {
                var checkboxes = document.querySelectorAll("#dropdown-items .dropdown-item:not(:first-child) input[type='checkbox']");
                checkboxes.forEach(function(checkbox) {
                    // Only toggle visible checkboxes (respecting dropdown search)
                    if (checkbox.closest('.dropdown-item').style.display !== "none") {
                        checkbox.checked = checked;
                    }
                });
            }

            function updateSelectAllCheckbox() {
                 var allCheckbox = document.getElementById("select-all");
                 if (!allCheckbox) return; // Should exist, but safety check

                 var checkboxes = document.querySelectorAll("#dropdown-items .dropdown-item:not(:first-child) input[type='checkbox']");
                 var allVisibleChecked = true;
                 var noneVisibleChecked = true;
                 var anyVisible = false;

                 checkboxes.forEach(function(checkbox) {
                     // Only consider checkboxes that are currently visible in the dropdown
                     if (checkbox.closest('.dropdown-item').style.display !== "none") {
                         anyVisible = true;
                         if (checkbox.checked) {
                             noneVisibleChecked = false;
                         } else {
                             allVisibleChecked = false;
                         }
                     }
                 });

                 if (!anyVisible) { // Handle case where search filters out everything
                     allCheckbox.checked = false;
                     allCheckbox.indeterminate = false;
                 } else {
                     allCheckbox.checked = allVisibleChecked;
                     // Indeterminate if some visible items are checked, but not all visible items are checked
                     allCheckbox.indeterminate = !allVisibleChecked && !noneVisibleChecked;
                 }
            }

            // Check if a row passes all active column filters
            function passesColumnFilters(row) {
                var cells = row.getElementsByTagName("td");
                for (var colIdx in currentFilterValues) {
                    // Ensure colIdx is a valid index for the row's cells
                    if (cells.length > colIdx) {
                        var cellValue = (cells[colIdx].textContent || cells[colIdx].innerText).trim();
                        var allowedValues = currentFilterValues[colIdx]; // This is the array of selected values for this column's filter

                        // If there's an active filter for this column (allowedValues exists)
                        // AND the current cell's value is NOT in the list of allowed values...
                        if (allowedValues && !allowedValues.includes(cellValue)) {
                            return false; // ...then this row fails the filter
                        }
                    }
                }
                return true; // Passes all active filters (or no filters are active)
            }

            // Initial setup: Apply any default filters if needed (usually none)
            // filterTable(); // Call once on load if you have default filters

            </script>
        """

        # --- HTML End ---
        html_content += """
        </body>
        </html>
        """

        # Write HTML file
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"HTML视图已生成: {html_file} (HTML view generated: {html_file})")
        return html_file

    except pd.errors.EmptyDataError:
        print(f"错误: CSV文件 '{csv_file}' 为空或格式不正确。(Error: CSV file '{csv_file}' is empty or malformed.)")
        return None
    except KeyError as e:
        print(f"创建HTML视图时出错: 缺少列 {e} (Error creating HTML view: Missing column {e})")
        traceback.print_exc()
        return None
    except Exception as e:
        print(f"创建HTML视图时发生意外错误 (Unexpected error creating HTML view): {e}")
        traceback.print_exc()
        return None

# Example usage (optional, for testing):
# if __name__ == '__main__':
#     # Create a dummy CSV for testing
#     dummy_data = {
#         '文件名': ['model_a.safetensors', 'model_b.ckpt', 'lora_c.pt', 'model_d_missing.safetensors'],
#         '下载链接': ['https://huggingface.co/repo/model_a', 'https://huggingface.co/repo/model_b', '', ''],
#         '镜像链接': ['https://hf-mirror.com/repo/resolve/main/model_a.safetensors', 'https://hf-mirror.com/repo/resolve/main/model_b.ckpt', '', ''],
#         '搜索链接': ['https://www.liblib.ai/modelinfo/123', 'https://www.liblib.ai/modelinfo/456', 'https://www.liblib.ai/modelinfo/789', ''],
#         '状态': ['已处理', '已处理', '已处理', '未找到']
#     }
#     dummy_csv_file = 'dummy_models.csv'
#     try:
#         # Ensure pandas is imported for the dummy data creation
#         import pandas as pd
#         df_dummy = pd.DataFrame(dummy_data)
#         df_dummy.to_csv(dummy_csv_file, index=False, encoding='utf-8')
#         print(f"创建了测试文件 (Created test file): {dummy_csv_file}")
#
#         # Test the HTML creation
#         html_output = create_html_view(dummy_csv_file)
#         if html_output:
#             print(f"测试HTML文件已生成 (Test HTML file generated): {html_output}")
#             # Optional: Automatically open the HTML file
#             # import webbrowser
#             # webbrowser.open(f'file://{os.path.abspath(html_output)}')
#         else:
#             print("测试HTML文件生成失败 (Test HTML file generation failed)")
#
#     except ImportError:
#         print("无法运行测试，缺少 pandas 库。(Cannot run test, pandas library missing.)")
#     except Exception as test_e:
#         print(f"运行测试时出错 (Error running test): {test_e}")
#     finally:
#         # Clean up dummy file
#         # if os.path.exists(dummy_csv_file):
#         #     os.remove(dummy_csv_file)
#         pass # Keep dummy file for inspection if needed
