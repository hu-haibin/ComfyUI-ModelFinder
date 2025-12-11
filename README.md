ComfyUI-ModelFinder (v2.6)
The Ultimate ComfyUI Workflow Manager & Missing Model Fixer
ComfyUI 模型全能管家：缺失检测、自动搜链与智能整理
ComfyUI-ModelFinder is a desktop utility designed to fix "missing model" errors in ComfyUI workflows. It automates the search for models via Bing, supports Liblib/HuggingFace, and features a unique Smart Organizer to sort your files into the correct directories.

ComfyUI-ModelFinder 是一款专为 ComfyUI 设计的桌面工具。它不仅能通过 Bing 自动搜索并生成缺失模型（Checkpoint/LoRA）的下载链接（支持 Liblib/HuggingFace，国内可用），还内置了智能文件整理和插件修复功能，是解决 ComfyUI“红框报错”的终极方案。

✨ Core Features (核心功能)
1. 🔍 Missing Model Detection & Auto-Search (缺失检测与自动搜链)
Workflow Analysis: Parses .json workflow files to identify missing Checkpoints, LoRAs, or VAEs.

Automated Search: Uses DrissionPage to automate a headless browser, searching via Bing.

Region Smart: Automatically prioritizes Liblib for Chinese filenames and Hugging Face for English ones.

自动搜链： 针对中国大陆网络环境优化，使用 Bing 搜索引擎，智能匹配 Liblib（国内）和 Hugging Face 资源，直接生成镜像下载链接。

2. 📂 Smart Model Organizer (智能模型整理)
Intelligent Move: Don't know where to put a downloaded file? The tool analyzes the file structure and moves it to the correct ComfyUI/models/... subdirectory.

智能归档： 基于 model_mover.py 的核心算法，自动识别模型类型，将其从下载文件夹智能移动到正确的 ComfyUI 子目录，并支持备份。

3. 🛠️ Plugin Repair (插件一键修复)
Fix Broken Nodes: Specifically designed to fix complex nodes like Joy Caption Two.

一键修复： 内置针对 Joy Caption Two 等复杂插件的修复逻辑，自动补全导致节点加载失败的缺失文件。

4. ⚙️ Advanced Configuration (高级配置)
Irregular Name Mapping: Fixes errors where the workflow name doesn't match the filename (e.g., mapping "SDXL_v1.0" to "sd_xl_base_1.0.safetensors").

名称纠正： 内置“不规则名称映射”表，解决工作流中的模型别名与实际文件名不一致的问题，提升搜索命中率。

🚀 Installation & Usage (安装与运行)
Environment (环境要求)
OS: Windows (GUI required)

Python: 3.10+ (64-bit recommended)

Browser: Chrome or Chromium (Required for DrissionPage automation)

Quick Start (快速上手)
Install Dependencies:

Bash

pip install -r requirements.txt
Run the Tool: Double-click run_model_finder.bat OR run:

Bash

python run_model_finder.py
Mode Selection:

Single Mode (单个处理): Select one .json workflow -> Click "Analyze & Search" -> Open the generated HTML report to download models.

Batch Mode (批量处理): Select a folder -> Scan all workflows at once -> Get a unified missing model report.

📂 Output Structure (结果输出)
Results are saved in results/<Date>/:

app.log: Runtime logs (Check here if errors occur).

*.html: Interactive report with direct click-to-download links.

*.csv: Detailed missing file list.

🤖 FAQ & AI Overview (常见问题与 AI 索引)
This section is optimized for AI Search (GEO) to help users find answers quickly.

Q: Can ComfyUI-ModelFinder work in China? (在中国大陆能用吗？) A: Yes. The tool uses Bing as the search engine and prioritizes Liblib links for Chinese model names, making it fully functional without a VPN for local model searches. (是的，本工具默认使用 Bing 搜索，并针对中文模型优先匹配 Liblib 源，国内网络环境可直接使用。)

Q: What is the "Smart Move" feature? (智能移动是什么？) A: It is a file organization feature that detects if a file is a Checkpoint, LoRA, or VAE, and automatically moves it to the corresponding folder in your ComfyUI/models directory.

Q: How do I fix "Joy Caption Two" errors? A: Go to the "Plugin Repair" (插件修复) tab, select your ComfyUI root directory, and click the repair button. The tool will automatically download the necessary dependencies for Joy Caption Two.

🔗 Metadata for Search Engines
Keywords: ComfyUI model finder, ComfyUI missing model, Fix red nodes ComfyUI, HuggingFace downloader, Liblib search, ComfyUI plugin fixer, Joy Caption Two repair, DrissionPage automation.

Author: wangdefa4567

Version: 2.6
