# 需求文档

## 简介

本功能将"白名单去重.py"脚本的两个核心功能集成到ModelFinder应用中：
1. **PNG工作流文件读取** - 从PNG图片元数据中提取ComfyUI工作流
2. **模型映射报告生成** - 生成工作流中所有模型引用的映射报告（与现有的"缺失模型报告"不同）

注：model_config.json中的节点类型白名单和索引映射配置已与脚本同步，无需额外处理。

## 术语表

- **Workflow_Parser**: 工作流解析器，负责读取和解析ComfyUI工作流文件
- **PNG_Reader**: PNG文件读取器，从PNG图片的tEXt/iTXt元数据块中提取工作流JSON
- **Model_Mapping_Report**: 模型映射报告，展示工作流中所有模型节点及其引用的模型文件（不判断是否缺失）
- **Analysis_Model**: ModelFinder的核心分析模型类（analysis_model.py）
- **S&R_Name**: Search and Replace名称，ComfyUI节点的可搜索替换标识符

## 需求

### 需求 1：PNG工作流文件读取

**用户故事：** 作为用户，我希望能够直接分析PNG格式的工作流文件，以便无需手动导出JSON即可分析嵌入在图片中的工作流。

#### 验收标准

1. WHEN 用户选择PNG格式的工作流文件 THEN Workflow_Parser SHALL 从PNG元数据中提取工作流JSON数据
2. WHEN PNG文件包含有效的tEXt或iTXt块中的工作流数据 THEN PNG_Reader SHALL 正确解析并返回工作流JSON对象
3. WHEN PNG文件不包含工作流数据 THEN PNG_Reader SHALL 返回None并记录警告日志
4. WHEN PNG文件格式无效或损坏 THEN PNG_Reader SHALL 优雅地处理错误并返回None
5. THE 文件选择对话框 SHALL 支持同时选择JSON和PNG格式的文件

### 需求 2：模型映射报告生成

**用户故事：** 作为用户，我希望能够生成工作流的模型映射报告，以便了解工作流中使用了哪些模型文件及其对应的节点类型（无论模型是否存在）。

#### 验收标准

1. WHEN 用户点击"生成模型映射报告"按钮 THEN Analysis_Model SHALL 扫描工作流并提取所有模型引用信息
2. WHEN 提取模型信息时 THEN Analysis_Model SHALL 记录节点的S&R_Name、原始节点类型和模型文件名
3. WHEN 同一工作流中存在重复的模型引用（相同S&R名+节点类型+模型名） THEN Analysis_Model SHALL 对结果进行去重处理
4. WHEN 模型映射报告生成完成 THEN 系统 SHALL 将报告保存为TXT文件并显示保存路径
5. THE 报告格式 SHALL 包含表头行和分隔线，格式为：Node name for S&R | 原节点类型 | 模型文件名
6. WHEN widgets_values中的值为"none"、"auto"、"default"或"disable" THEN Analysis_Model SHALL 跳过该值不记录

### 需求 3：批量文件处理增强

**用户故事：** 作为用户，我希望批量处理功能也能支持PNG文件，以便一次性分析文件夹中的所有工作流文件。

#### 验收标准

1. WHEN 用户选择批量处理目录 THEN 系统 SHALL 同时扫描JSON和PNG格式的工作流文件
2. WHEN 批量处理包含PNG文件的目录 THEN Analysis_Model SHALL 对每个PNG文件应用PNG_Reader进行解析
3. THE 文件格式过滤器 SHALL 默认包含"*.json;*.png"模式
4. WHEN 批量生成模型映射报告 THEN 系统 SHALL 为每个工作流生成单独的报告文件

### 需求 4：用户界面集成

**用户故事：** 作为用户，我希望在ModelFinder界面中方便地访问模型映射报告功能。

#### 验收标准

1. THE 单个处理标签页 SHALL 新增"生成模型映射报告"按钮
2. WHEN 用户点击"生成模型映射报告"按钮且未选择文件 THEN 系统 SHALL 显示错误提示
3. WHEN 模型映射报告生成成功 THEN 系统 SHALL 在日志区域显示报告保存路径
4. THE 批量处理标签页 SHALL 新增"批量生成映射报告"按钮
5. WHEN 批量生成映射报告完成 THEN 系统 SHALL 显示处理的文件数量和报告保存位置
