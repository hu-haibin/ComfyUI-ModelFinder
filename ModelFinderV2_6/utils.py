"""
工具函数模块 (Utility Function Module)
包含辅助功能：依赖检查、浏览器检测、HTML生成等 (Contains helper functions: dependency check, browser detection, HTML generation, etc.)
"""

import os
import sys
import subprocess
import traceback
import json
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
    """Create a high-performance HTML report with client-side pagination."""
    if 'pd' not in globals():
        print("Error: pandas is not available. Cannot create HTML view.")
        return None

    # Canonical CSV column names (unicode escapes to avoid terminal encoding issues)
    col_seq = '\u5e8f\u53f7'
    col_file = '\u6587\u4ef6\u540d'
    col_node_id = '\u8282\u70b9ID'
    col_node_type = '\u8282\u70b9\u7c7b\u578b'
    col_download = '\u4e0b\u8f7d\u94fe\u63a5'
    col_mirror = '\u955c\u50cf\u94fe\u63a5'
    col_hf_mirror = 'hf\u955c\u50cf'
    col_search = '\u641c\u7d22\u94fe\u63a5'
    col_status = '\u72b6\u6001'
    col_csv = 'CSV\u6587\u4ef6'
    col_workflow = '\u5de5\u4f5c\u6d41\u6587\u4ef6'
    col_missing_count = '\u7f3a\u5931\u6570\u91cf'

    try:
        print(f"Creating HTML view for {csv_file}")

        df = None
        encodings_to_try = ['utf-8', 'utf-8-sig', 'gbk', 'gb18030']
        for enc in encodings_to_try:
            try:
                df = pd.read_csv(csv_file, encoding=enc)
                print(f"CSV loaded with {enc}; columns: {df.columns.tolist()}")
                break
            except UnicodeDecodeError:
                print(f"Encoding {enc} failed")
            except Exception as e:
                print(f"CSV read error with {enc}: {e}")

        if df is None:
            print(f"Failed to read CSV with encodings: {encodings_to_try}")
            return None

        for col in df.columns:
            df[col] = df[col].fillna('').astype(str)

        mirror_link_col = None
        for col in df.columns:
            if col.lower() in (col_mirror.lower(), col_hf_mirror.lower()):
                mirror_link_col = col
                break

        preferred_order = [
            col_seq, col_file, col_node_id, col_node_type,
            col_download, col_mirror, col_hf_mirror, col_search, col_status,
            col_csv, col_workflow, col_missing_count,
        ]

        available_cols_ordered = [
            col for col in preferred_order
            if col in df.columns or col.lower() in [c.lower() for c in df.columns]
        ]
        remaining_cols = [
            col for col in df.columns
            if col not in available_cols_ordered and col.lower() not in [c.lower() for c in available_cols_ordered]
        ]

        final_column_order = []
        for col in available_cols_ordered + remaining_cols:
            actual_col = next((c for c in df.columns if c.lower() == col.lower()), None)
            if actual_col and actual_col not in final_column_order:
                final_column_order.append(actual_col)

        column_meta = []
        for col in final_column_order:
            display_name = col
            if col.lower() == col_download.lower():
                display_name = 'HuggingFace'
            elif col.lower() in (col_mirror.lower(), col_hf_mirror.lower()):
                display_name = 'HF Mirror'
            elif col.lower() == col_search.lower():
                display_name = 'LibLib'
            column_meta.append({'key': col, 'label': display_name})

        df_display = df[final_column_order].copy() if final_column_order else df.copy()
        records = df_display.to_dict(orient='records')

        records_json = json.dumps(records, ensure_ascii=False).replace('</', r'<\/')
        columns_json = json.dumps(column_meta, ensure_ascii=False).replace('</', r'<\/')
        mirror_key_json = json.dumps(mirror_link_col if mirror_link_col else '', ensure_ascii=False)

        html_file = os.path.splitext(csv_file)[0] + '.html'
        source_file = os.path.basename(csv_file)
        generated_time = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        show_copy_js = 'true' if mirror_link_col else 'false'

        html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Model Download Links</title>
    <style>
        body { font-family: "Microsoft YaHei", Arial, sans-serif; margin: 20px; background: #fafafa; }
        h1 { margin-bottom: 8px; }
        .meta { color: #555; margin-bottom: 8px; font-size: 13px; }
        .controls {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            align-items: center;
            margin: 12px 0;
            padding: 10px;
            background: #fff;
            border: 1px solid #ddd;
            border-radius: 6px;
        }
        .controls input[type="text"], .controls select {
            padding: 6px 8px;
            border: 1px solid #ccc;
            border-radius: 4px;
            min-width: 180px;
        }
        .controls button {
            padding: 6px 10px;
            border: 1px solid #ccc;
            border-radius: 4px;
            background: #fff;
            cursor: pointer;
        }
        .controls button.primary { background: #14833b; color: #fff; border-color: #14833b; }
        .controls button:disabled { background: #eee; color: #888; cursor: not-allowed; }

        .summary {
            margin-bottom: 10px;
            padding: 8px 10px;
            background: #fff;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 13px;
        }

        table {
            border-collapse: collapse;
            width: 100%;
            background: #fff;
            border: 1px solid #ddd;
            table-layout: fixed;
        }
        thead th {
            position: sticky;
            top: 0;
            z-index: 2;
            background: #f3f3f3;
            cursor: pointer;
            user-select: none;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
            word-break: break-all;
            vertical-align: top;
            font-size: 13px;
        }
        tbody tr:nth-child(even) { background: #fcfcfc; }

        .file-name { font-weight: 600; }
        .status-processed { color: #108a00; font-weight: 600; }
        .status-notfound { color: #c33; }
        .status-error { color: #d08400; }

        .link-col { text-align: center; }
        .link-col a { display: inline-block; text-decoration: none; padding: 2px 6px; border-radius: 4px; font-weight: 600; }
        .hf-link a { background: #ffe4d1; color: #d95f00; }
        .mirror-link a { background: #d9e8ff; color: #0a57d1; }
        .liblib-link a { background: #daf8dc; color: #167a1d; }
        .no-link { color: #888; text-align: center; }

        .pagination {
            margin-top: 10px;
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }
        .pagination .page-info { color: #444; font-size: 13px; }
    </style>
</head>
<body>
    <h1>Model Download Links</h1>
    <div class="meta">Source: __MF_SOURCE_FILE__</div>
    <div class="meta">Generated: __MF_GENERATED_TIME__</div>

    <div class="controls">
        <label>Filter:</label>
        <input id="filterInput" type="text" placeholder="Type keywords...">

        <label>Rows/Page:</label>
        <select id="pageSizeSelect">
            <option value="20">20</option>
            <option value="50" selected>50</option>
            <option value="100">100</option>
            <option value="200">200</option>
        </select>

        <button id="copyButton" class="primary" onclick="batchCopyMirrorLinks()">Copy Mirror Links</button>
        <span id="copyMessage"></span>
    </div>

    <div class="summary" id="summaryBar"></div>

    <table>
        <thead id="tableHead"></thead>
        <tbody id="tableBody"></tbody>
    </table>

    <div class="pagination">
        <button id="prevBtn" onclick="prevPage()">Prev</button>
        <button id="nextBtn" onclick="nextPage()">Next</button>
        <span class="page-info" id="pageInfo"></span>
    </div>

    <script>
        const allRows = __MF_DATA_ROWS__;
        const columns = __MF_COLUMNS__;
        const mirrorLinkKey = __MF_MIRROR_KEY__;
        const showCopyButton = __MF_SHOW_COPY__;

        const COL_STATUS = __COL_STATUS__;
        const COL_FILE = __COL_FILE__;
        const COL_CSV = __COL_CSV__;
        const COL_WORKFLOW = __COL_WORKFLOW__;
        const COL_DOWNLOAD = __COL_DOWNLOAD__;
        const COL_MIRROR = __COL_MIRROR__;
        const COL_HF_MIRROR = __COL_HF_MIRROR__;
        const COL_SEARCH = __COL_SEARCH__;

        const STATUS_PROCESSED = __STATUS_PROCESSED__;

        let filteredRows = allRows.slice();
        let currentPage = 1;
        let pageSize = 50;
        let sortKey = '';
        let sortDir = 'asc';

        function escapeHtml(value) {
            return String(value)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }

        function isLinkColumn(key) {
            const lk = key.toLowerCase();
            return key === COL_DOWNLOAD || key === COL_SEARCH || lk === COL_MIRROR.toLowerCase() || lk === COL_HF_MIRROR.toLowerCase();
        }

        function getStatusClass(statusText) {
            const s = (statusText || '').toString();
            if (s.includes(STATUS_PROCESSED) || s.includes('Found')) return 'status-processed';
            if (s.includes('\u9519\u8bef') || s.includes('Error')) return 'status-error';
            return 'status-notfound';
        }

        function compareValues(a, b) {
            const av = (a || '').toString();
            const bv = (b || '').toString();
            const an = parseFloat(av.replace(/,/g, ''));
            const bn = parseFloat(bv.replace(/,/g, ''));
            const bothNumber = !Number.isNaN(an) && !Number.isNaN(bn);
            if (bothNumber) return an - bn;
            return av.localeCompare(bv, 'zh-CN', { sensitivity: 'base' });
        }

        function applyFilters(resetPage) {
            const keyword = (document.getElementById('filterInput').value || '').trim().toLowerCase();
            filteredRows = allRows.filter((row) => {
                if (!keyword) return true;
                for (const meta of columns) {
                    const value = (row[meta.key] || '').toString().toLowerCase();
                    if (value.includes(keyword)) return true;
                }
                return false;
            });

            if (sortKey) {
                filteredRows.sort((ra, rb) => {
                    const cmp = compareValues(ra[sortKey], rb[sortKey]);
                    return sortDir === 'asc' ? cmp : -cmp;
                });
            }

            if (resetPage) currentPage = 1;
            renderTable();
        }

        function toggleSort(colKey) {
            if (sortKey === colKey) {
                sortDir = sortDir === 'asc' ? 'desc' : 'asc';
            } else {
                sortKey = colKey;
                sortDir = 'asc';
            }
            applyFilters(false);
        }

        function renderHeader() {
            const head = document.getElementById('tableHead');
            let html = '<tr>';
            for (const meta of columns) {
                let arrow = '';
                if (sortKey === meta.key) arrow = sortDir === 'asc' ? ' ?' : ' ?';
                html += '<th onclick="toggleSort('' + meta.key.replace(/'/g, "\'") + '')">' + escapeHtml(meta.label) + arrow + '</th>';
            }
            html += '</tr>';
            head.innerHTML = html;
        }

        function renderCell(row, key) {
            const value = (row[key] || '').toString().trim();

            if (key === COL_STATUS) {
                return '<td class="' + getStatusClass(value) + '">' + escapeHtml(value) + '</td>';
            }

            if (key === COL_FILE || key === COL_CSV || key === COL_WORKFLOW) {
                return '<td class="file-name">' + escapeHtml(value) + '</td>';
            }

            if (isLinkColumn(key)) {
                if (!value) return '<td class="no-link">N/A</td>';

                const lk = key.toLowerCase();
                let cls = 'link-col';
                let text = 'Link';

                if (key === COL_DOWNLOAD) {
                    cls += ' hf-link';
                    text = 'HF';
                } else if (lk === COL_MIRROR.toLowerCase() || lk === COL_HF_MIRROR.toLowerCase()) {
                    cls += ' mirror-link';
                    text = 'Mirror';
                } else if (key === COL_SEARCH) {
                    cls += ' liblib-link';
                    text = 'LibLib';
                }

                return '<td class="' + cls + '"><a target="_blank" href="' + escapeHtml(value) + '">' + text + '</a></td>';
            }

            return '<td>' + escapeHtml(value) + '</td>';
        }

        function renderTableBody() {
            const tbody = document.getElementById('tableBody');
            const total = filteredRows.length;
            const totalPages = Math.max(1, Math.ceil(total / pageSize));
            if (currentPage > totalPages) currentPage = totalPages;

            const start = (currentPage - 1) * pageSize;
            const end = Math.min(total, start + pageSize);
            const pageRows = filteredRows.slice(start, end);

            let html = '';
            for (const row of pageRows) {
                html += '<tr>';
                for (const meta of columns) {
                    html += renderCell(row, meta.key);
                }
                html += '</tr>';
            }
            tbody.innerHTML = html;
        }

        function renderPagination() {
            const total = filteredRows.length;
            const totalPages = Math.max(1, Math.ceil(total / pageSize));
            if (currentPage > totalPages) currentPage = totalPages;

            document.getElementById('pageInfo').textContent = 'Page ' + currentPage + ' / ' + totalPages + ', rows: ' + total;
            document.getElementById('prevBtn').disabled = currentPage <= 1;
            document.getElementById('nextBtn').disabled = currentPage >= totalPages;
        }

        function renderSummary() {
            const total = allRows.length;
            const visible = filteredRows.length;
            document.getElementById('summaryBar').textContent = 'Total rows: ' + total + ', after filter: ' + visible;
        }

        function renderTable() {
            renderHeader();
            renderTableBody();
            renderPagination();
            renderSummary();
        }

        function prevPage() {
            if (currentPage > 1) {
                currentPage -= 1;
                renderTable();
            }
        }

        function nextPage() {
            const totalPages = Math.max(1, Math.ceil(filteredRows.length / pageSize));
            if (currentPage < totalPages) {
                currentPage += 1;
                renderTable();
            }
        }

        function batchCopyMirrorLinks() {
            const copyButton = document.getElementById('copyButton');
            const copyMessage = document.getElementById('copyMessage');

            if (!mirrorLinkKey) {
                copyMessage.textContent = 'Mirror column not found';
                return;
            }

            const links = [];
            for (const row of filteredRows) {
                const v = (row[mirrorLinkKey] || '').toString().trim();
                if (v) links.push(v);
            }

            if (links.length === 0) {
                copyMessage.textContent = 'No mirror links in filtered rows';
                return;
            }

            copyButton.disabled = true;
            navigator.clipboard.writeText(links.join('\n')).then(() => {
                copyMessage.textContent = 'Copied ' + links.length + ' mirror links';
                setTimeout(() => {
                    copyMessage.textContent = '';
                    copyButton.disabled = false;
                }, 2500);
            }).catch((err) => {
                console.error(err);
                copyMessage.textContent = 'Copy failed. Check browser permissions';
                copyButton.disabled = false;
            });
        }

        document.addEventListener('DOMContentLoaded', () => {
            const pageSizeSelect = document.getElementById('pageSizeSelect');
            const filterInput = document.getElementById('filterInput');
            const copyButton = document.getElementById('copyButton');

            if (!showCopyButton) {
                copyButton.style.display = 'none';
            }

            pageSizeSelect.addEventListener('change', () => {
                const val = parseInt(pageSizeSelect.value, 10);
                pageSize = Number.isFinite(val) && val > 0 ? val : 50;
                applyFilters(true);
            });

            filterInput.addEventListener('input', () => applyFilters(true));
            renderTable();
        });
    </script>
</body>
</html>
"""

        html_content = (
            html_template
            .replace('__MF_SOURCE_FILE__', source_file)
            .replace('__MF_GENERATED_TIME__', generated_time)
            .replace('__MF_DATA_ROWS__', records_json)
            .replace('__MF_COLUMNS__', columns_json)
            .replace('__MF_MIRROR_KEY__', mirror_key_json)
            .replace('__MF_SHOW_COPY__', show_copy_js)
            .replace('__COL_STATUS__', json.dumps(col_status, ensure_ascii=False))
            .replace('__COL_FILE__', json.dumps(col_file, ensure_ascii=False))
            .replace('__COL_CSV__', json.dumps(col_csv, ensure_ascii=False))
            .replace('__COL_WORKFLOW__', json.dumps(col_workflow, ensure_ascii=False))
            .replace('__COL_DOWNLOAD__', json.dumps(col_download, ensure_ascii=False))
            .replace('__COL_MIRROR__', json.dumps(col_mirror, ensure_ascii=False))
            .replace('__COL_HF_MIRROR__', json.dumps(col_hf_mirror, ensure_ascii=False))
            .replace('__COL_SEARCH__', json.dumps(col_search, ensure_ascii=False))
            .replace('__STATUS_PROCESSED__', json.dumps('\u5df2\u5904\u7406', ensure_ascii=False))
        )

        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"HTML view generated: {html_file}")
        return html_file

    except pd.errors.EmptyDataError:
        print(f"Error: CSV file '{csv_file}' is empty or malformed")
        return None
    except KeyError as e:
        print(f"Error creating HTML view: missing column {e}")
        traceback.print_exc()
        return None
    except Exception as e:
        print(f"Unexpected error creating HTML view: {e}")
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
