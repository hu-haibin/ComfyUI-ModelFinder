#!/usr/bin/env python3
"""
ModelFinder API 包装器 - 概念验证
将现有功能暴露为API，无需修改原有代码
"""

from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import json
import asyncio
import uvicorn
from typing import List
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

# 导入现有的业务逻辑（无需修改！）
try:
    from ModelFinderV2_5.analysis_model import AnalysisModel
    from ModelFinderV2_5.irregular_names_model import IrregularNamesModel
    from ModelFinderV2_5.model_config_manager import ModelConfigManager
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保在项目根目录下运行此脚本")
    sys.exit(1)

app = FastAPI(title="ModelFinder API", version="3.0")

# 启用CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 提供静态文件服务
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# 创建业务逻辑实例（使用现有代码）
analysis_model = AnalysisModel()
irregular_names_model = IrregularNamesModel()
config_manager = ModelConfigManager()

# WebSocket连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

# API路由 - 包装现有功能
@app.get("/vue")
async def vue_app():
    """返回Vue应用界面"""
    try:
        with open("frontend/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    except FileNotFoundError:
        return HTMLResponse("<h1>Vue界面文件未找到</h1><p>请确保 frontend/index.html 存在</p>")

@app.get("/")
async def root():
    """返回简单的测试页面"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>ModelFinder API Test</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            button { padding: 10px 20px; margin: 10px; cursor: pointer; }
            #result { background: #f0f0f0; padding: 20px; margin-top: 20px; }
            .file-drop { 
                border: 2px dashed #ccc; 
                padding: 40px; 
                text-align: center; 
                margin: 20px 0;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔍 ModelFinder API 测试</h1>
            
            <div class="file-drop" id="dropZone">
                拖拽 JSON 工作流文件到这里，或点击选择文件
                <input type="file" id="fileInput" accept=".json" style="display: none;">
            </div>
            
            <button onclick="testIrregularNames()">测试不规则名称映射</button>
            <button onclick="testModelConfig()">测试模型配置</button>
            <button onclick="analyzeFile()">分析工作流</button>
            
            <div id="result"></div>
        </div>

        <script>
            const resultDiv = document.getElementById('result');
            const dropZone = document.getElementById('dropZone');
            const fileInput = document.getElementById('fileInput');
            let selectedFile = null;

            // 文件拖拽处理
            dropZone.addEventListener('click', () => fileInput.click());
            dropZone.addEventListener('dragover', (e) => {
                e.preventDefault();
                dropZone.style.backgroundColor = '#e6f7ff';
            });
            dropZone.addEventListener('dragleave', () => {
                dropZone.style.backgroundColor = '';
            });
            dropZone.addEventListener('drop', (e) => {
                e.preventDefault();
                dropZone.style.backgroundColor = '';
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    selectedFile = files[0];
                    dropZone.innerHTML = `已选择: ${selectedFile.name}`;
                }
            });
            fileInput.addEventListener('change', (e) => {
                if (e.target.files.length > 0) {
                    selectedFile = e.target.files[0];
                    dropZone.innerHTML = `已选择: ${selectedFile.name}`;
                }
            });

            async function testIrregularNames() {
                try {
                    const response = await fetch('/api/irregular-names');
                    const data = await response.json();
                    resultDiv.innerHTML = `
                        <h3>不规则名称映射 (${data.data ? data.data.length : 0} 条)</h3>
                        <pre>${JSON.stringify(data.data ? data.data.slice(0, 3) : [], null, 2)}...</pre>
                    `;
                } catch (error) {
                    resultDiv.innerHTML = `<p style="color: red;">错误: ${error}</p>`;
                }
            }

            async function testModelConfig() {
                try {
                    const response = await fetch('/api/model-config');
                    const data = await response.json();
                    resultDiv.innerHTML = `
                        <h3>模型配置</h3>
                        <p>节点类型: ${data.node_types.length} 个</p>
                        <p>扩展名: ${data.extensions.length} 个</p>
                        <pre>${JSON.stringify(data, null, 2).substring(0, 500)}...</pre>
                    `;
                } catch (error) {
                    resultDiv.innerHTML = `<p style="color: red;">错误: ${error}</p>`;
                }
            }

            async function analyzeFile() {
                if (!selectedFile) {
                    alert('请先选择一个JSON文件');
                    return;
                }

                const formData = new FormData();
                formData.append('file', selectedFile);

                try {
                    resultDiv.innerHTML = '<p>正在分析...</p>';
                    const response = await fetch('/api/analyze', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await response.json();
                    
                    resultDiv.innerHTML = `
                        <h3>分析结果</h3>
                        <p>状态: ${data.status}</p>
                        <p>发现的模型: ${data.models ? data.models.length : 0} 个</p>
                        <pre>${JSON.stringify(data, null, 2).substring(0, 1000)}...</pre>
                    `;
                } catch (error) {
                    resultDiv.innerHTML = `<p style="color: red;">分析错误: ${error}</p>`;
                }
            }
        </script>
    </body>
    </html>
    """)

@app.get("/api/irregular-names")
async def get_irregular_names():
    """获取不规则名称映射 - 直接使用现有代码"""
    try:
        mappings = irregular_names_model.get_all_mappings()
        return {"status": "success", "data": mappings, "count": len(mappings)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/model-config") 
async def get_model_config():
    """获取模型配置 - 直接使用现有代码"""
    try:
        return {
            "status": "success",
            "node_types": config_manager.get_model_node_types(),
            "extensions": config_manager.get_model_extensions(),
            "indices": config_manager.get_node_model_indices()
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/analyze")
async def analyze_workflow(file: UploadFile = File(...)):
    """分析工作流文件 - 使用现有分析逻辑"""
    try:
        # 读取文件内容
        content = await file.read()
        workflow_data = json.loads(content)
        
        # 广播开始分析
        await manager.broadcast({
            "type": "analysis_start",
            "filename": file.filename
        })
        
        # 使用现有的分析逻辑 - 创建临时JSON文件
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as temp_file:
            json.dump(workflow_data, temp_file, ensure_ascii=False, indent=2)
            temp_path = temp_file.name
        
        try:
            # 调用现有的分析方法
            missing_models = analysis_model.find_missing_models(temp_path)
            
            # 为每个模型生成搜索和下载链接
            enriched_models = []
            for model in missing_models:
                # 处理模型名称用于搜索
                file_path = model.get('file_path', '')
                node_type = model.get('node_type', '')
                
                # 使用分析模型的内部方法生成搜索信息
                try:
                    processed_names = analysis_model._process_name_for_search(file_path)
                    base_url, site_query = analysis_model._get_search_url(
                        processed_names['mapped'],
                        processed_names['final_search_term'],
                        node_type
                    )
                    
                    # 生成搜索链接
                    query_param = site_query.replace(' ', '+').replace('"', '%22')
                    search_link = f"https://www.bing.com/search?q={query_param}"
                    
                    # 生成Civitai链接 (如果适用)
                    download_link = None
                    if "civitai.com" in site_query.lower():
                        download_link = f"https://civitai.com/search/models?query={processed_names['final_search_term'].replace(' ', '%20')}"
                    
                except Exception as e:
                    search_link = f"https://www.bing.com/search?q={file_path.replace(' ', '+')}"
                    download_link = None
                
                enriched_model = {
                    'filename': file_path,
                    'name': file_path,
                    'node_type': node_type,
                    'node_id': model.get('node_id', ''),
                    'status': 'missing',
                    'search_link': search_link,
                    'download_link': download_link
                }
                enriched_models.append(enriched_model)
            
            model_list = enriched_models
            model_count = len(enriched_models)
            
        finally:
            # 清理临时文件
            import os
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        
        # 广播分析完成
        await manager.broadcast({
            "type": "analysis_complete", 
            "models": model_list,
            "count": model_count
        })
        
        return {
            "status": "success",
            "filename": file.filename,
            "models": model_list,
            "count": model_count,
            "message": f"成功分析，发现 {model_count} 个模型引用"
        }
        
    except json.JSONDecodeError:
        return {"status": "error", "message": "无效的JSON文件格式"}
    except Exception as e:
        return {"status": "error", "message": f"分析失败: {str(e)}"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket连接，用于实时通信"""
    await manager.connect(websocket)
    try:
        while True:
            # 保持连接
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    print("🚀 启动 ModelFinder API 服务...")
    print("📱 测试页面: http://localhost:8000")
    print("📚 API文档: http://localhost:8000/docs")
    print("\n💡 这个API包装了你现有的所有业务逻辑，无需修改原代码！")
    
    uvicorn.run(
        "api_wrapper:app",
        host="127.0.0.1", 
        port=8000,
        reload=True,  # 热重载！
        log_level="info"
    )
