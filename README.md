<div align="center">

# ComfyUI-ModelFinder

### 🔍 ComfyUI 模型全能管家：缺失检测、自动搜链与智能整理

**The Ultimate ComfyUI Missing Model Fixer & Organizer**

[![GitHub Stars](https://img.shields.io/github/stars/hu-haibin/ComfyUI-ModelFinder?style=for-the-badge&logo=github)](https://github.com/hu-haibin/ComfyUI-ModelFinder)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/github/license/hu-haibin/ComfyUI-ModelFinder?style=for-the-badge)](LICENSE)
[![Version](https://img.shields.io/badge/版本-v2.6-brightgreen?style=for-the-badge)](https://github.com/hu-haibin/ComfyUI-ModelFinder)

</div>

---

> [!IMPORTANT]
> ## 🚀 寻找更强大的 ComfyUI 管理工具？试试 ModelFinder Launcher！
>
> **ComfyUI-ModelFinder** 是开源的命令行/桌面模型查找工具。如果你希望获得 **更完整的 ComfyUI 管理体验**，我们推荐升级到 **[ModelFinder Launcher](https://github.com/hu-haibin/ModelFinder-Releases)**——一款功能全面的 ComfyUI 一站式启动器：
>
> - ✅ **内置模型匹配引擎**（1000+ 模型目录，自动匹配 HuggingFace / ModelScope / Civitai）
> - ✅ **一键部署 ComfyUI**（选版本 / GPU / 预装插件，全程可视化）
> - ✅ **AI 智能诊断**（启动失败自动分析日志、生成修复方案）
> - ✅ **多实例管理 / PyTorch 版本切换 / 插件管理 / 批量出图**
> - ✅ **Windows Fluent Design 现代 UI，深色/浅色主题**
>
> 👉 **[立即下载 ModelFinder Launcher（免费）](https://github.com/hu-haibin/ModelFinder-Releases/releases/latest)**

---

## ✨ 本项目介绍

ComfyUI-ModelFinder 是一款 **开源的 Python 桌面工具**，专为解决 ComfyUI 工作流中的"缺失模型"报错而设计。

它可以：
1. **解析工作流 JSON 文件**，自动识别缺失的 Checkpoint / LoRA / VAE
2. **通过 Bing 自动搜索**模型下载链接（优先匹配 Liblib / HuggingFace）
3. **智能整理**已下载的模型文件到正确的 ComfyUI 子目录
4. **一键修复**特定插件（如 Joy Caption Two）的依赖问题

> 💡 本工具使用 Bing 搜索引擎，**国内网络可直接使用**，无需 VPN。

---

## 🎯 核心功能

### 🔍 缺失模型检测 & 自动搜链

- **工作流解析**：解析 `.json` 工作流文件，识别缺失的模型文件
- **自动搜索**：通过 DrissionPage 驱动浏览器，使用 Bing 搜索模型
- **智能区分语种**：中文模型名优先匹配 Liblib（国内源），英文名优先匹配 HuggingFace
- **生成下载报告**：输出 HTML 交互式报告（可点击直接下载）和 CSV 清单

### 📂 智能模型整理

- **自动分类**：检测文件是 Checkpoint / LoRA / VAE，自动移动到对应的 `ComfyUI/models/` 子目录
- **支持备份**：移动前可选择备份原文件

### 🛠️ 插件一键修复

- **Joy Caption Two 修复**：自动补全导致节点加载失败的缺失依赖文件
- **可扩展**：修复逻辑模块化，便于添加更多插件支持

### ⚙️ 高级配置

- **不规则名称映射**：内置映射表，解决工作流模型别名与实际文件名不一致的问题（如 `SDXL_v1.0` → `sd_xl_base_1.0.safetensors`）
- **提升搜索命中率**：自动纠正常见命名差异

---

## 📦 安装与运行

### 环境要求

| 项目 | 要求 |
|------|------|
| **操作系统** | Windows |
| **Python** | 3.10+（64-bit 推荐） |
| **浏览器** | Chrome 或 Chromium（DrissionPage 自动化依赖） |

### 快速上手

**1. 安装依赖**

```bash
pip install -r requirements.txt
```

**2. 运行工具**

双击 `run_model_finder.bat`，或通过命令行：

```bash
python run_model_finder.py
```

**3. 选择模式**

| 模式 | 说明 |
|------|------|
| **单个处理** | 选择一个 `.json` 工作流 → 点击「分析 & 搜索」→ 查看 HTML 报告下载模型 |
| **批量处理** | 选择一个文件夹 → 扫描所有工作流 → 生成统一的缺失模型报告 |

---

## 📂 结果输出

运行结果保存在 `results/<日期>/` 目录：

| 文件 | 说明 |
|------|------|
| `app.log` | 运行日志（出错时优先查看） |
| `*.html` | 交互式报告，包含可点击的下载链接 |
| `*.csv` | 详细的缺失模型清单 |

---

## ❓ 常见问题

<details>
<summary><b>Q: 在中国大陆能用吗？</b></summary>

**可以。** 本工具默认使用 Bing 搜索引擎，并针对中文模型名优先匹配 Liblib 源，国内网络环境可直接使用，无需 VPN。

</details>

<details>
<summary><b>Q: "智能移动"是什么？</b></summary>

智能移动功能会自动检测文件是 Checkpoint、LoRA 还是 VAE，并将其移动到 ComfyUI/models 目录下对应的子文件夹中。

</details>

<details>
<summary><b>Q: 如何修复 Joy Caption Two 节点错误？</b></summary>

进入「插件修复」标签页，选择 ComfyUI 根目录，点击修复按钮即可。工具会自动下载 Joy Caption Two 所需的依赖文件。

</details>

<details>
<summary><b>Q: 和 ModelFinder Launcher 有什么区别？</b></summary>

| | ComfyUI-ModelFinder（本项目） | ModelFinder Launcher |
|---|---|---|
| **开源** | ✅ 开源 | ❌ 闭源 |
| **技术** | Python + DrissionPage | .NET + Avalonia UI |
| **模型搜索** | Bing 搜索 + 网页爬取 | 内置 1000+ 模型目录 + Civitai/HuggingFace API |
| **ComfyUI 管理** | ❌ | ✅ 部署 / 启动 / 包管理 / 插件管理 |
| **AI 诊断** | ❌ | ✅ 日志分析 + 自动修复 |
| **批量出图** | ❌ | ✅ 通过 API 自动化出图 |
| **适合人群** | 想要轻量、开源方案 | 想要一站式管理体验 |

👉 **[下载 ModelFinder Launcher](https://github.com/hu-haibin/ModelFinder-Releases/releases/latest)**

</details>

---

## 🔗 相关链接

- 🚀 **[ModelFinder Launcher](https://github.com/hu-haibin/ModelFinder-Releases)** — 一站式 ComfyUI 管理启动器（推荐）
- 🐛 **[Issues](https://github.com/hu-haibin/ComfyUI-ModelFinder/issues)** — Bug 反馈 / 功能建议
- ⭐ **觉得有用？给个 Star！**

---

## 📄 许可

本项目为开源软件，遵循仓库内的许可协议。

---

<div align="center">

**ComfyUI-ModelFinder** — 解决 ComfyUI "模型缺失红框报错"的开源方案

想要更完整的体验？试试 👉 **[ModelFinder Launcher](https://github.com/hu-haibin/ModelFinder-Releases)**

</div>
