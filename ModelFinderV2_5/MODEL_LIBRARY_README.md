# 模型库管理功能说明

## 功能概述

模型库管理是 ModelFinder V3 的核心功能之一，用于扫描、管理和查询本地 ComfyUI 模型文件。

## 主要特性

### 1. 智能扫描
- **后台扫描**：使用独立线程进行扫描，不会阻塞主程序
- **批量处理**：每 50 个文件保存一次进度，避免数据丢失
- **性能优化**：
  - 分块读取文件（8KB/块），避免大文件占用过多内存
  - 每处理 10 个文件休眠 0.01 秒，降低 CPU 占用
  - 使用缓存机制，已扫描的文件（基于路径和修改时间）不重复计算哈希
- **实时进度**：前端每 500ms 轮询一次进度，实时显示扫描状态

### 2. 文件识别
支持的文件格式：
- `.safetensors`、`.ckpt`、`.pt`、`.pth`、`.bin`
- `.onnx`、`.pb`、`.tflite`、`.h5`

### 3. 智能分类
根据文件路径自动识别模型类型：
- Checkpoint、LoRA、ControlNet、VAE、Upscaler
- Embedding、Hypernetwork、CLIP、IP-Adapter 等

### 4. 哈希计算
- 为每个模型文件计算 SHA256 哈希值
- 用于模型去重、工作流依赖匹配、文件完整性验证

### 5. 高级查询
- 搜索、筛选、排序、分页

## API 接口

### 启动扫描
```
POST /api/models/scan_local
Body: {"root_path": "C:/ComfyUI/models"}
```

### 获取扫描进度
```
GET /api/models/scan_status
```

### 取消扫描
```
POST /api/models/scan_cancel
```

### 获取模型列表
```
POST /api/models/get_local
Body: {
  "search_term": "sd",
  "model_type": "Checkpoint",
  "sort_by": "name",
  "sort_order": "asc",
  "limit": 50,
  "offset": 0
}
```

### 获取统计信息
```
GET /api/models/statistics
```

## 使用方法

1. 启动后端服务：`python api_server.py`
2. 启动前端应用：`flutter run -d windows`
3. 在"模型库"页面选择目录并开始扫描
4. 等待扫描完成后即可搜索和查看模型

## 性能优化

### 避免系统死机的设计
- ✅ 后台线程：不阻塞主线程和 UI
- ✅ 分块读取：避免大文件一次性加载到内存
- ✅ 定期休眠：降低 CPU 占用率
- ✅ 进度保存：每 50 个文件保存一次
- ✅ 可中断：用户随时可以取消扫描

## 数据存储

扫描结果保存在：`ModelFinderV2_5/model_cache.json`

