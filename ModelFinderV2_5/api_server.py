from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import sys
import traceback
import webbrowser
import logging
from datetime import datetime

# 确保当前目录在Python路径中，解决导入问题
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 导入日志配置
from logger_config import setup_logger
# 设置日志记录系统
logger = setup_logger(logging.DEBUG)  # 设置为调试级别以获取详细日志

# 现在导入模块应该不会有问题
from analysis_model import AnalysisModel, ComfyUIWorkflowAnalyzer
from model_config_manager import ModelConfigManager
from irregular_names_model import IrregularNamesModel
from model_registry import ModelRegistry
from model_mover import ModelMover
from model_scanner import ModelScanner
from utils import get_mirror_link, create_html_view, find_chrome_path
from file_manager import get_output_path

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 初始化各种管理器
model_config = ModelConfigManager()
irregular_names = IrregularNamesModel()
model_registry = ModelRegistry()
model_scanner = ModelScanner()

@app.route('/api/analyze', methods=['POST'])
def analyze_workflow():
    try:
        data = request.json
        workflow_path = data.get('workflow_path')
        
        logger.info(f"收到分析请求: 工作流={workflow_path}")
        
        if not workflow_path or not os.path.exists(workflow_path):
            logger.error(f"分析失败: 工作流文件不存在: {workflow_path}")
            return jsonify({"error": f"工作流文件不存在: {workflow_path}"}), 400
        
        # 使用分析器分析工作流
        logger.info(f"开始分析工作流: {os.path.basename(workflow_path)}")
        analyzer = ComfyUIWorkflowAnalyzer(
            workflow_path=workflow_path,
            model_config=model_config,
            irregular_names=irregular_names
        )
        
        result = analyzer.analyze()
        missing_count = len(result.get("missing_models", []))
        used_count = len(result.get("used_models", []))
        logger.info(f"工作流分析完成: 使用了 {used_count} 个模型，其中 {missing_count} 个缺失")
        
        html_path = analyzer.generate_html_report()
        logger.info(f"HTML报告已生成: {html_path}")
        
        return jsonify({
            "missing_models": result.get("missing_models", []),
            "used_models": result.get("used_models", []),
            "html_path": html_path
        })
    except Exception as e:
        logger.error(f"分析工作流时出错: {str(e)}", exc_info=True)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/batch_process', methods=['POST'])
def batch_process():
    try:
        data = request.json
        directory_path = data.get('directory_path')
        file_pattern = data.get('file_pattern', '*.json')
        auto_open_html = data.get('auto_open_html', True)
        
        logger.info(f"收到批量处理请求: 目录={directory_path}, 文件模式={file_pattern}, 自动打开HTML={auto_open_html}")
        
        if not directory_path or not os.path.exists(directory_path):
            logger.error(f"批量处理失败: 目录不存在: {directory_path}")
            return jsonify({"error": f"目录不存在: {directory_path}"}), 400
        
        # 这里实现批量处理逻辑
        results = []
        summary_html = os.path.join(os.path.dirname(__file__), "results", "summary.html")
        
        # 遍历目录中的文件
        import glob
        workflow_files = glob.glob(os.path.join(directory_path, file_pattern))
        logger.info(f"找到 {len(workflow_files)} 个匹配的工作流文件")
        
        for i, workflow_file in enumerate(workflow_files, 1):
            logger.info(f"正在处理工作流 ({i}/{len(workflow_files)}): {os.path.basename(workflow_file)}")
            
            analyzer = ComfyUIWorkflowAnalyzer(
                workflow_path=workflow_file,
                model_config=model_config,
                irregular_names=irregular_names
            )
            
            result = analyzer.analyze()
            missing_count = len(result.get("missing_models", []))
            logger.info(f"工作流 {os.path.basename(workflow_file)} 分析完成: {missing_count} 个缺失模型")
            
            html_path = analyzer.generate_html_report()
            logger.debug(f"生成HTML报告: {html_path}")
            
            file_name = os.path.basename(workflow_file)
            results.append({
                "file_name": file_name,
                "missing_count": missing_count,
                "status": "处理完成",
                "html_path": html_path
            })
        
        # 生成汇总HTML报告
        # TODO: 实现汇总报告生成
        logger.info(f"批量处理完成，共处理 {len(results)} 个文件")
        
        if auto_open_html and os.path.exists(summary_html):
            logger.info(f"自动打开汇总HTML: {summary_html}")
            webbrowser.open(f"file://{summary_html}")
        
        return jsonify({
            "results": results,
            "summary_html": summary_html
        })
    except Exception as e:
        logger.error(f"批量处理出错: {str(e)}", exc_info=True)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/view_html', methods=['POST'])
def view_html():
    try:
        data = request.json
        html_path = data.get('html_path', '')
        
        logger.info(f"收到查看HTML请求: {html_path if html_path else '未指定路径'}")
        
        if not html_path:
            # 尝试打开最新的结果
            logger.debug("未指定HTML路径，尝试查找最新的HTML结果")
            result_dir = os.path.join(os.path.dirname(__file__), "results")
            if os.path.exists(result_dir):
                html_files = sorted(
                    [os.path.join(result_dir, f) for f in os.listdir(result_dir) if f.endswith('.html')],
                    key=os.path.getmtime,
                    reverse=True
                )
                if html_files:
                    html_path = html_files[0]
                    logger.info(f"找到最新的HTML文件: {html_path}")
                else:
                    logger.warning(f"在结果目录中没有找到HTML文件: {result_dir}")
        
        if html_path and os.path.exists(html_path):
            logger.info(f"打开HTML文件: {html_path}")
            webbrowser.open(f"file://{html_path}")
            return jsonify({"status": "success"})
        else:
            logger.error(f"HTML文件不存在: {html_path}")
            return jsonify({"error": "HTML文件不存在"}), 404
    except Exception as e:
        logger.error(f"查看HTML时出错: {str(e)}", exc_info=True)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/irregular_mappings', methods=['GET'])
def get_irregular_mappings():
    try:
        mappings = irregular_names.get_all_mappings()
        return jsonify({"mappings": mappings})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/irregular_mappings', methods=['POST'])
def add_irregular_mapping():
    try:
        data = request.json
        original_name = data.get('original_name')
        corrected_name = data.get('corrected_name')
        notes = data.get('notes')
        
        if not original_name or not corrected_name:
            return jsonify({"error": "原始名称和修正名称不能为空"}), 400
        
        mapping_id = irregular_names.add_mapping(original_name, corrected_name, notes)
        return jsonify({"id": mapping_id, "original_name": original_name, "corrected_name": corrected_name, "notes": notes})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/model_config', methods=['GET'])
def get_model_config():
    try:
        config = model_config.get_config()
        return jsonify(config)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/model_config/node_types', methods=['PUT'])
def update_node_types():
    try:
        data = request.json
        node_types = data.get('node_types', [])
        model_config.update_node_types(node_types)
        return jsonify({"status": "success"})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/model_directories', methods=['GET'])
def get_model_directories():
    try:
        # 这里应该从配置或模型注册表中获取目录
        directories = ["checkpoints", "loras", "controlnet", "upscalers"]
        return jsonify({"directories": directories})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/model_files', methods=['POST'])
def get_model_files():
    try:
        data = request.json
        directory = data.get('directory')
        search_term = data.get('search_term')
        
        # 示例：返回目录中的文件列表
        files = []
        # TODO: 实现真实文件列表获取逻辑
        
        return jsonify({"files": files})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ==================== 模型库管理 API ====================

@app.route('/api/models/scan_local', methods=['POST'])
def scan_local_models():
    """启动本地模型扫描"""
    global model_scanner  # 必须在函数开头声明
    
    try:
        data = request.json
        root_path = data.get('root_path')
        performance_mode = data.get('performance_mode', 'balanced')
        
        if not root_path:
            return jsonify({"error": "未指定模型根目录"}), 400
        
        if not os.path.exists(root_path):
            return jsonify({"error": f"目录不存在: {root_path}"}), 400
        
        if model_scanner.is_scanning:
            return jsonify({"error": "扫描正在进行中"}), 409
        
        # 如果性能模式改变，重新初始化扫描器
        if model_scanner.performance_mode != performance_mode:
            logger.info(f"切换性能模式: {model_scanner.performance_mode} -> {performance_mode}")
            model_scanner = ModelScanner(performance_mode=performance_mode)
        
        logger.info(f"开始扫描本地模型目录: {root_path} (性能模式: {performance_mode})")
        
        # 在后台线程启动扫描
        model_scanner.start_scan(root_path)
        
        return jsonify({
            "status": "started",
            "message": "模型扫描已启动",
            "performance_mode": performance_mode
        })
    except Exception as e:
        logger.error(f"启动扫描失败: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/models/scan_status', methods=['GET'])
def get_scan_status():
    """获取扫描进度状态"""
    try:
        progress = model_scanner.get_progress()
        return jsonify(progress)
    except Exception as e:
        logger.error(f"获取扫描状态失败: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/models/scan_cancel', methods=['POST'])
def cancel_scan():
    """取消正在进行的扫描"""
    try:
        if not model_scanner.is_scanning:
            return jsonify({"error": "当前没有进行中的扫描"}), 400
        
        logger.info("用户请求取消扫描")
        model_scanner.stop_scan()
        
        return jsonify({
            "status": "cancelled",
            "message": "扫描已取消"
        })
    except Exception as e:
        logger.error(f"取消扫描失败: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/models/get_local', methods=['POST'])
def get_local_models():
    """获取本地模型列表（支持搜索、筛选、排序、分页）"""
    try:
        data = request.json or {}
        
        search_term = data.get('search_term')
        model_type = data.get('model_type')
        sort_by = data.get('sort_by', 'name')
        sort_order = data.get('sort_order', 'asc')
        limit = data.get('limit')
        offset = data.get('offset', 0)
        
        result = model_scanner.get_models(
            search_term=search_term,
            model_type=model_type,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            offset=offset
        )
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"获取模型列表失败: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/models/statistics', methods=['GET'])
def get_model_statistics():
    """获取模型库统计信息"""
    try:
        stats = model_scanner.get_statistics()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"获取统计信息失败: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/models/search_by_hash', methods=['POST'])
def search_model_by_hash():
    """根据哈希值查找模型"""
    try:
        data = request.json
        file_hash = data.get('hash')
        
        if not file_hash:
            return jsonify({"error": "未提供哈希值"}), 400
        
        model = model_scanner.get_model_by_hash(file_hash)
        
        if model:
            return jsonify({"found": True, "model": model})
        else:
            return jsonify({"found": False, "model": None})
    except Exception as e:
        logger.error(f"哈希查找失败: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/models/verify_file', methods=['POST'])
def verify_model_file():
    """验证模型文件是否存在"""
    try:
        data = request.json
        file_path = data.get('file_path')
        
        if not file_path:
            return jsonify({"error": "未提供文件路径"}), 400
        
        exists = os.path.exists(file_path)
        
        result = {
            "exists": exists,
            "path": file_path
        }
        
        if exists:
            file_stat = os.stat(file_path)
            result["size"] = file_stat.st_size
            result["modified_time"] = datetime.fromtimestamp(file_stat.st_mtime).isoformat()
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"验证文件失败: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# 更多API端点...

if __name__ == '__main__':
    logger.info("正在启动ModelFinder后端API服务器... (Starting ModelFinder backend API server)")
    # 确保results目录存在
    results_dir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(results_dir, exist_ok=True)
    logger.debug(f"结果目录确认存在: {results_dir}")
    
    # 如需请求超时控制，建议在生产部署（如 waitress/gunicorn/nginx）层配置
    logger.info("提示：开发服务器不支持 request_timeout，如需超时请用生产服务器配置")
    
    # 启动服务器
    logger.info("API服务器启动在 0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)