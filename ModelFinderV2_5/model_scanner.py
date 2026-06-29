"""
模型扫描器模块 - 负责扫描本地模型文件并计算哈希值
支持异步扫描、进度追踪、可中断操作
"""
import os
import hashlib
import json
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Callable
from datetime import datetime
from logger_config import setup_logger
import logging

logger = setup_logger(logging.INFO)


class ModelScanner:
    """本地模型扫描器"""
    
    # 支持的模型文件扩展名
    MODEL_EXTENSIONS = {
        '.safetensors', '.ckpt', '.pt', '.pth', '.bin',
        '.onnx', '.pb', '.tflite', '.h5'
    }
    
    # 模型类型映射 (根据路径推断类型)
    MODEL_TYPE_MAPPING = {
        'checkpoints': 'Checkpoint',
        'loras': 'LoRA',
        'controlnet': 'ControlNet',
        'upscale_models': 'Upscaler',
        'vae': 'VAE',
        'embeddings': 'Embedding',
        'hypernetworks': 'Hypernetwork',
        'clip': 'CLIP',
        'clip_vision': 'CLIP Vision',
        'unet': 'UNet',
        'style_models': 'Style Model',
        'ipadapter': 'IP-Adapter',
    }
    
    def __init__(self, cache_file: str = None, performance_mode: str = 'balanced'):
        """
        初始化扫描器
        
        Args:
            cache_file: 缓存文件路径，用于存储扫描结果
            performance_mode: 性能模式 ('conservative', 'balanced', 'aggressive')
                - conservative: 最保守，最低CPU占用，适合后台运行
                - balanced: 平衡模式（默认），适合大多数情况
                - aggressive: 激进模式，最快速度，适合空闲时扫描
        """
        self.cache_file = cache_file or os.path.join(
            os.path.dirname(__file__), 'model_cache.json'
        )
        self.models: List[Dict] = []
        self.is_scanning = False
        self.should_stop = False
        self.scan_thread: Optional[threading.Thread] = None
        
        # 性能配置（根据模式设置）
        self.performance_mode = performance_mode
        self._configure_performance_settings()
        
        # 扫描进度信息
        self.progress = {
            'total_files': 0,
            'scanned_files': 0,
            'current_file': '',
            'percentage': 0,
            'status': 'idle',  # idle, scanning, completed, cancelled, error
            'start_time': None,
            'end_time': None,
            'errors': [],
            'performance_mode': performance_mode
        }
        
        # 加载缓存
        self.load_cache()
    
    def _configure_performance_settings(self):
        """根据性能模式配置参数"""
        if self.performance_mode == 'conservative':
            # 保守模式：最低CPU占用
            self.chunk_size = 4096  # 4KB 块
            self.sleep_interval = 5  # 每5个文件休眠一次
            self.sleep_duration = 0.05  # 休眠50毫秒
            self.save_interval = 20  # 每20个文件保存一次
            logger.info("性能模式：保守 - 最低CPU占用，适合后台运行")
        elif self.performance_mode == 'aggressive':
            # 激进模式：最快速度
            self.chunk_size = 16384  # 16KB 块
            self.sleep_interval = 20  # 每20个文件休眠一次
            self.sleep_duration = 0.005  # 休眠5毫秒
            self.save_interval = 100  # 每100个文件保存一次
            logger.info("性能模式：激进 - 最快速度，适合空闲时扫描")
        else:
            # 平衡模式（默认）
            self.chunk_size = 8192  # 8KB 块
            self.sleep_interval = 10  # 每10个文件休眠一次
            self.sleep_duration = 0.01  # 休眠10毫秒
            self.save_interval = 50  # 每50个文件保存一次
            logger.info("性能模式：平衡 - 速度与资源占用平衡")
    
    def load_cache(self):
        """从缓存文件加载已扫描的模型信息"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.models = data.get('models', [])
                    logger.info(f"从缓存加载了 {len(self.models)} 个模型记录")
        except Exception as e:
            logger.error(f"加载缓存失败: {e}")
            self.models = []
    
    def save_cache(self):
        """保存模型信息到缓存文件"""
        try:
            data = {
                'models': self.models,
                'last_updated': datetime.now().isoformat(),
                'total_count': len(self.models)
            }
            
            # 确保目录存在
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"缓存已保存，共 {len(self.models)} 个模型")
        except Exception as e:
            logger.error(f"保存缓存失败: {e}")
    
    def calculate_file_hash(self, file_path: str) -> Optional[str]:
        """
        计算文件的 SHA256 哈希值
        
        Args:
            file_path: 文件路径
        
        Returns:
            SHA256 哈希值，失败返回 None
        """
        try:
            sha256_hash = hashlib.sha256()
            file_size = os.path.getsize(file_path)
            
            with open(file_path, 'rb') as f:
                # 分块读取文件，避免大文件占用过多内存
                bytes_read = 0
                while True:
                    if self.should_stop:
                        return None
                    
                    chunk = f.read(self.chunk_size)
                    if not chunk:
                        break
                    sha256_hash.update(chunk)
                    bytes_read += len(chunk)
                    
                    # 对于超大文件（>1GB），额外休眠以避免长时间占用CPU
                    if file_size > 1024 * 1024 * 1024 and bytes_read % (self.chunk_size * 100) == 0:
                        time.sleep(0.001)
            
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"计算哈希值失败 {file_path}: {e}")
            return None
    
    def get_file_size_formatted(self, size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"
    
    def infer_model_type(self, file_path: str, models_root: str) -> str:
        """
        根据文件路径推断模型类型
        
        Args:
            file_path: 文件完整路径
            models_root: 模型根目录
        
        Returns:
            模型类型字符串
        """
        try:
            # 获取相对路径
            rel_path = os.path.relpath(file_path, models_root).lower()
            path_parts = Path(rel_path).parts
            
            # 尝试从路径中匹配模型类型
            for part in path_parts:
                for key, model_type in self.MODEL_TYPE_MAPPING.items():
                    if key in part:
                        return model_type
            
            return 'Unknown'
        except Exception as e:
            logger.error(f"推断模型类型失败: {e}")
            return 'Unknown'
    
    def scan_directory(self, root_path: str, progress_callback: Optional[Callable] = None):
        """
        扫描指定目录下的所有模型文件
        
        Args:
            root_path: 要扫描的根目录
            progress_callback: 进度回调函数
        """
        if not os.path.exists(root_path):
            raise ValueError(f"目录不存在: {root_path}")
        
        self.is_scanning = True
        self.should_stop = False
        self.progress['status'] = 'scanning'
        self.progress['start_time'] = datetime.now().isoformat()
        self.progress['errors'] = []
        
        logger.info(f"开始扫描目录: {root_path}")
        
        try:
            # 第一阶段：收集所有模型文件
            logger.info("阶段 1/2: 收集模型文件...")
            model_files = []
            
            for root, dirs, files in os.walk(root_path):
                if self.should_stop:
                    logger.info("扫描被用户取消")
                    self.progress['status'] = 'cancelled'
                    return
                
                # 过滤出模型文件
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in self.MODEL_EXTENSIONS:
                        file_path = os.path.join(root, file)
                        model_files.append(file_path)
            
            self.progress['total_files'] = len(model_files)
            logger.info(f"找到 {len(model_files)} 个模型文件")
            
            if len(model_files) == 0:
                logger.warning("未找到任何模型文件")
                self.progress['status'] = 'completed'
                self.progress['end_time'] = datetime.now().isoformat()
                return
            
            # 创建已有模型的哈希映射（用于快速查找）
            existing_models = {m['hash']: m for m in self.models if m.get('hash')}
            new_models = []
            
            # 第二阶段：处理每个文件
            logger.info("阶段 2/2: 分析模型文件...")
            
            for idx, file_path in enumerate(model_files, 1):
                if self.should_stop:
                    logger.info("扫描被用户取消")
                    self.progress['status'] = 'cancelled'
                    return
                
                try:
                    self.progress['scanned_files'] = idx
                    self.progress['current_file'] = os.path.basename(file_path)
                    self.progress['percentage'] = int((idx / len(model_files)) * 100)
                    
                    # 获取文件信息
                    file_stat = os.stat(file_path)
                    file_size = file_stat.st_size
                    modified_time = datetime.fromtimestamp(file_stat.st_mtime).isoformat()
                    
                    # 检查缓存中是否已有此文件（通过路径和修改时间判断）
                    cached_model = None
                    for model in self.models:
                        if model['path'] == file_path and model.get('modified_time') == modified_time:
                            cached_model = model
                            break
                    
                    if cached_model:
                        # 使用缓存的信息
                        logger.debug(f"使用缓存: {os.path.basename(file_path)}")
                        new_models.append(cached_model)
                    else:
                        # 计算哈希值
                        logger.debug(f"计算哈希 ({idx}/{len(model_files)}): {os.path.basename(file_path)}")
                        file_hash = self.calculate_file_hash(file_path)
                        
                        if file_hash is None:
                            if self.should_stop:
                                continue
                            error_msg = f"无法计算哈希: {file_path}"
                            logger.warning(error_msg)
                            self.progress['errors'].append(error_msg)
                            continue
                        
                        # 推断模型类型
                        model_type = self.infer_model_type(file_path, root_path)
                        
                        # 创建模型记录
                        model_info = {
                            'name': os.path.basename(file_path),
                            'path': file_path,
                            'hash': file_hash,
                            'size': file_size,
                            'size_formatted': self.get_file_size_formatted(file_size),
                            'type': model_type,
                            'extension': os.path.splitext(file_path)[1],
                            'modified_time': modified_time,
                            'scanned_time': datetime.now().isoformat(),
                            'relative_path': os.path.relpath(file_path, root_path)
                        }
                        
                        new_models.append(model_info)
                    
                    # 定期保存进度
                    if idx % self.save_interval == 0:
                        self.models = new_models
                        self.save_cache()
                        logger.debug(f"进度已保存: {idx}/{len(model_files)}")
                    
                    # 调用进度回调
                    if progress_callback:
                        progress_callback(self.progress.copy())
                    
                    # 定期休眠，避免 CPU 占用过高
                    if idx % self.sleep_interval == 0:
                        time.sleep(self.sleep_duration)
                
                except Exception as e:
                    error_msg = f"处理文件失败 {file_path}: {str(e)}"
                    logger.error(error_msg)
                    self.progress['errors'].append(error_msg)
            
            # 更新模型列表并保存
            self.models = new_models
            self.save_cache()
            
            self.progress['status'] = 'completed'
            self.progress['end_time'] = datetime.now().isoformat()
            
            logger.info(f"扫描完成！共找到 {len(self.models)} 个模型")
            logger.info(f"错误数量: {len(self.progress['errors'])}")
            
        except Exception as e:
            error_msg = f"扫描过程出错: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.progress['status'] = 'error'
            self.progress['errors'].append(error_msg)
            self.progress['end_time'] = datetime.now().isoformat()
        
        finally:
            self.is_scanning = False
    
    def start_scan(self, root_path: str, progress_callback: Optional[Callable] = None):
        """
        在后台线程中启动扫描
        
        Args:
            root_path: 要扫描的根目录
            progress_callback: 进度回调函数
        """
        if self.is_scanning:
            raise RuntimeError("扫描正在进行中，请等待完成或先取消当前扫描")
        
        self.scan_thread = threading.Thread(
            target=self.scan_directory,
            args=(root_path, progress_callback),
            daemon=True
        )
        self.scan_thread.start()
        logger.info("扫描线程已启动")
    
    def stop_scan(self):
        """停止正在进行的扫描"""
        if self.is_scanning:
            logger.info("请求停止扫描...")
            self.should_stop = True
            
            # 等待线程结束（最多等待 5 秒）
            if self.scan_thread and self.scan_thread.is_alive():
                self.scan_thread.join(timeout=5)
            
            self.is_scanning = False
            logger.info("扫描已停止")
    
    def get_progress(self) -> Dict:
        """获取当前扫描进度"""
        return self.progress.copy()
    
    def get_models(self, 
                   search_term: str = None,
                   model_type: str = None,
                   sort_by: str = 'name',
                   sort_order: str = 'asc',
                   limit: int = None,
                   offset: int = 0) -> Dict:
        """
        获取模型列表（支持搜索、筛选、排序、分页）
        
        Args:
            search_term: 搜索关键词
            model_type: 模型类型筛选
            sort_by: 排序字段 (name, size, type, modified_time)
            sort_order: 排序顺序 (asc, desc)
            limit: 返回数量限制
            offset: 偏移量（用于分页）
        
        Returns:
            包含模型列表和统计信息的字典
        """
        filtered_models = self.models.copy()
        
        # 搜索筛选
        if search_term:
            search_term = search_term.lower()
            filtered_models = [
                m for m in filtered_models
                if search_term in m['name'].lower() or search_term in m.get('relative_path', '').lower()
            ]
        
        # 类型筛选
        if model_type and model_type != 'All':
            filtered_models = [m for m in filtered_models if m['type'] == model_type]
        
        # 排序
        reverse = (sort_order == 'desc')
        if sort_by == 'name':
            filtered_models.sort(key=lambda x: x['name'].lower(), reverse=reverse)
        elif sort_by == 'size':
            filtered_models.sort(key=lambda x: x['size'], reverse=reverse)
        elif sort_by == 'type':
            filtered_models.sort(key=lambda x: x['type'], reverse=reverse)
        elif sort_by == 'modified_time':
            filtered_models.sort(key=lambda x: x.get('modified_time', ''), reverse=reverse)
        
        # 统计信息
        total_count = len(filtered_models)
        
        # 分页
        if limit:
            filtered_models = filtered_models[offset:offset + limit]
        
        # 统计各类型数量
        type_stats = {}
        for model in self.models:
            model_type = model['type']
            type_stats[model_type] = type_stats.get(model_type, 0) + 1
        
        return {
            'models': filtered_models,
            'total_count': total_count,
            'filtered_count': len(filtered_models),
            'type_stats': type_stats,
            'has_more': (offset + len(filtered_models)) < total_count
        }
    
    def get_model_by_hash(self, file_hash: str) -> Optional[Dict]:
        """根据哈希值获取模型信息"""
        for model in self.models:
            if model.get('hash') == file_hash:
                return model
        return None
    
    def get_statistics(self) -> Dict:
        """获取模型库统计信息"""
        if not self.models:
            return {
                'total_models': 0,
                'total_size': 0,
                'total_size_formatted': '0 B',
                'type_distribution': {},
                'extension_distribution': {}
            }
        
        total_size = sum(m['size'] for m in self.models)
        
        # 类型分布
        type_dist = {}
        for model in self.models:
            model_type = model['type']
            type_dist[model_type] = type_dist.get(model_type, 0) + 1
        
        # 扩展名分布
        ext_dist = {}
        for model in self.models:
            ext = model['extension']
            ext_dist[ext] = ext_dist.get(ext, 0) + 1
        
        return {
            'total_models': len(self.models),
            'total_size': total_size,
            'total_size_formatted': self.get_file_size_formatted(total_size),
            'type_distribution': type_dist,
            'extension_distribution': ext_dist
        }

