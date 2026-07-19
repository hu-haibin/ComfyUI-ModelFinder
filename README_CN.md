🌐 [English](README.md) | **简体中文**

<div align="center">

# 你要找的是当前维护的 ComfyUI 启动器吗？

### 如果你的目标是运行工作流、修缺失模型，或者安装 Windows 桌面应用，请先下载 Wonderful Launcher。

[**下载 Wonderful Launcher**](https://github.com/hu-haibin/wonderful-launcher-comfyui/releases/latest) · [**Wonderful Launcher 发版仓**](https://github.com/hu-haibin/wonderful-launcher-comfyui) · [**官网**](https://wonderfullauncher.com/) · [**文档**](https://wonderfullauncher.com/docs)

</div>

---

> [!IMPORTANT]
> 如果你是因为 ComfyUI 工作流缺模型才来到这里，当前维护路径是 **Wonderful Launcher**。这个仓库是旧版独立 Python 工具，主要留给明确需要旧实现的人。

## 应该使用哪个仓库？

| 你的情况 | 推荐路径 |
|----------|----------|
| 想用 Windows 桌面应用启动 ComfyUI、看启动日志、匹配缺失模型、下载可用模型 | 使用 [Wonderful Launcher](https://github.com/hu-haibin/wonderful-launcher-comfyui/releases/latest) |
| 需要打包好的安装程序 | 去 [Wonderful Launcher 发版仓](https://github.com/hu-haibin/wonderful-launcher-comfyui) 下载 |
| 想查看或修改早期独立 Python 模型查找代码 | 使用当前仓库 |
| 熟悉 Python、Chrome 自动化和手动目录配置 | 当前仓库仍然可以作为旧工具使用 |

---

## 当前仓库：ComfyUI-ModelFinder

ComfyUI-ModelFinder 是一个旧版开源 Python/Tkinter 工具，用来查找 ComfyUI 工作流缺失模型。它可以帮你：

- 扫描 ComfyUI 工作流 JSON，提取引用到的模型名称
- 对比本地 ComfyUI `models` 目录，找出可能缺失的模型
- 通过浏览器搜索缺失模型文件
- 生成本地结果报告
- 把下载好的模型移动或整理到 ComfyUI 模型目录

它适合愿意自己维护 Python 环境、Chrome 环境和本地 ComfyUI 目录的人。

## 重要限制

- 它不是当前的 Wonderful Launcher 桌面应用。
- 它不提供 Windows 安装包。
- 它需要 Python 和 Chrome。
- 搜索依赖浏览器自动化和公开搜索页面，结果可能不完整，也可能有噪音。
- 它不走 Wonderful Launcher 当前维护的云端模型目录和下载流程。
- 如果你的目标只是“让这个工作流跑起来”，Wonderful Launcher 是更干净的路径。

---

## 运行旧版 Python 工具

### 环境要求

- Windows
- 命令行可以直接运行 `python`
- Google Chrome
- `requirements.txt` 中的 Python 依赖

### 安装依赖

```powershell
python -m pip install -r requirements.txt
```

也可以运行：

```powershell
.\install_requirements.bat
```

### 启动

```powershell
python run_model_finder.py
```

也可以运行：

```powershell
.\run_model_finder.bat
```

启动后，在界面里选择你的 ComfyUI 路径和模型目录。

---

## 命名说明

- **ComfyUI-ModelFinder**：当前仓库；早期独立 Python 模型查找工具。
- **Wonderful Launcher**：当前维护的 ComfyUI Windows 桌面启动器；包含启动、日志、修复、模型匹配和下载等流程。
- **发版仓**：<https://github.com/hu-haibin/wonderful-launcher-comfyui>

普通用户应该把发版仓当作下载页。当前仓库主要留给明确需要旧版 Python 实现的人。

## 常见问题

<details>
<summary><b>我要下载 release repo 里的 Source code.zip 吗？</b></summary>

不要。如果你想安装 Windows 启动器，请在最新版 GitHub Release 中下载 `WonderfulLauncher-Setup-v...exe`。

</details>

<details>
<summary><b>这个仓库是不是不维护了？</b></summary>

它会保留为开源旧工具。新的 ComfyUI 启动、修复、模型匹配和下载体验，主要在 Wonderful Launcher 中维护。

</details>

<details>
<summary><b>它现在还能查找缺失模型吗？</b></summary>

它仍然可以扫描工作流并帮助搜索模型名，但属于偏手动的本地工具。如果希望流程更顺，建议使用 Wonderful Launcher。

</details>
