# ModelFinder V2.6

ModelFinder是一个用于ComfyUI的模型管理工具，可以帮助您检测缺失模型、自动搜索下载链接，并提供智能的模型管理功能。
需要安装python，需要安装chrome


## 主要功能

### 1. 模型查找
- 分析ComfyUI工作流JSON文件，检测缺失的模型文件
- 自动搜索模型下载链接（支持Hugging Face和LibLib）
- 生成包含下载链接的HTML报告
- 批量处理多个工作流文件

### 2. 文件管理
- 提供直观的界面浏览和管理ComfyUI模型目录
- 支持模型文件的移动、复制和组织
- 创建和管理模型目录结构

### 3. 模型记录
- 维护模型信息数据库，包括名称、路径、类型、标签等
- 搜索和过滤模型记录
- 导入/导出模型记录

> [!IMPORTANT]
> ## 🚀 寻找更强大的 ComfyUI 管理工具？试试 ModelFinder Launcher！
>
> **ComfyUI-ModelFinder** 是开源的命令行/桌面模型查找工具。如果你希望获得 **更完整的 ComfyUI 管理体验**，我们推荐升级到 **[ModelFinder Launcher（官方发版仓）](https://github.com/hu-haibin/wonderful-launcher-comfyui)**——一款功能全面的 ComfyUI 一站式启动器：
>
> - ✅ **内置模型匹配引擎**（1000+ 模型目录，自动匹配 HuggingFace / ModelScope / Civitai）
> - ✅ **一键部署 ComfyUI**（选版本 / GPU / 预装插件，全程可视化）
> - ✅ **AI 智能诊断**（启动失败自动分析日志、生成修复方案）
> - ✅ **多实例管理 / PyTorch 版本切换 / 插件管理 / 批量出图**
> - ✅ **Windows Fluent Design 现代 UI，深色/浅色主题**
>
> 👉 **[立即下载 ModelFinder Launcher（免费）](https://github.com/hu-haibin/wonderful-launcher-comfyui/releases/latest)**
>
> ![ModelFinder Launcher 主界面](https://raw.githubusercontent.com/hu-haibin/wonderful-launcher-comfyui/main/assets/screenshots/2.0.15-home.png)

## 使用指南

### 设置

1. 打开软件，切换到"智能移动"选项卡
2. 设置ComfyUI模型根目录（通常是ComfyUI/models）
3. 设置备份目录（可选，默认在models目录同级创建backup文件夹）
4. 点击"应用路径设置"保存设置

### 使用模型类型识别和智能移动

单个文件处理:
1. 从左侧目录树选择一个目录
2. 从右侧文件列表选择一个模型文件
3. 点击"智能移动"按钮或右键选择"智能移动"
4. 在弹出的对话框中选择推荐的目标目录
5. 确认移动操作

批量处理下载文件:
1. 在"下载文件处理"区域设置下载文件夹
2. 点击"刷新"扫描下载的模型文件
3. 选择要处理的文件（或全部处理）
4. 点击"批量智能移动"按钮
5. 在弹出的对话框中为每个文件选择推荐的目标目录
6. 点击"执行批量移动"完成操作

重做模型管理

## 开发者信息

- 版本: 2.6
- 作者: wangdefa4567 
