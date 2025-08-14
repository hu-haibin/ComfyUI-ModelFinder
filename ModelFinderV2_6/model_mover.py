import os
import shutil
import logging
import json
from typing import List, Dict, Any, Union, Tuple

logger = logging.getLogger(__name__)

class ModelMover:
    """
    ComfyUI模型文件移动器。
    提供模型文件的移动、复制和组织功能。
    """
    
    def __init__(self):
        self.comfyui_models_root = None
        self.backup_dir = None
        self.model_extensions = [".safetensors", ".ckpt", ".pt", ".pth", ".bin"]
        self.model_type_detector = None
        logger.info("ModelMover已初始化")
    
    def set_paths(self, comfyui_models_root: str, backup_dir: str = None) -> bool:
        """
        设置ComfyUI模型目录和备份目录路径
        
        Args:
            comfyui_models_root: ComfyUI模型根目录，通常是ComfyUI/models
            backup_dir: 备份目录路径，如果不提供则创建在models_root同级的backup目录
        
        Returns:
            设置是否成功
        """
        if not os.path.exists(comfyui_models_root):
            logger.error(f"ComfyUI模型目录不存在: {comfyui_models_root}")
            return False
        
        self.comfyui_models_root = os.path.abspath(comfyui_models_root)
        
        if backup_dir:
            self.backup_dir = os.path.abspath(backup_dir)
        else:
            # 在models目录同级创建backup目录
            parent_dir = os.path.dirname(self.comfyui_models_root)
            self.backup_dir = os.path.join(parent_dir, "backup")
        
        # 确保备份目录存在
        if not os.path.exists(self.backup_dir):
            try:
                os.makedirs(self.backup_dir)
                logger.info(f"创建备份目录: {self.backup_dir}")
            except Exception as e:
                logger.error(f"创建备份目录失败: {e}")
                return False
        
        # 初始化模型类型检测器
        try:
            from .model_type_detector import ModelTypeDetector
            self.model_type_detector = ModelTypeDetector()
            # 学习当前的ComfyUI目录结构
            self.model_type_detector.learn_from_comfyui_structure(self.comfyui_models_root)
            logger.info("已初始化模型类型检测器")
        except ImportError:
            logger.warning("模型类型检测器不可用，智能移动功能将不可用")
            self.model_type_detector = None
        
        logger.info(f"设置ComfyUI模型目录: {self.comfyui_models_root}")
        logger.info(f"设置备份目录: {self.backup_dir}")
        return True
    
    def get_model_subdirectories(self) -> List[str]:
        """
        获取模型目录下的所有子目录
        
        Returns:
            子目录列表 (相对于comfyui_models_root的路径)
        """
        if not self.comfyui_models_root or not os.path.exists(self.comfyui_models_root):
            logger.error("未设置有效的ComfyUI模型目录")
            return []
        
        subdirs = []
        for root, dirs, _ in os.walk(self.comfyui_models_root):
            rel_path = os.path.relpath(root, self.comfyui_models_root)
            if rel_path != ".":
                subdirs.append(rel_path)
        
        return sorted(subdirs)
    
    def scan_model_files(self, subdir: str = None) -> List[Dict[str, Any]]:
        """
        扫描模型文件
        
        Args:
            subdir: 子目录路径，不提供则扫描根目录
            
        Returns:
            模型文件信息列表
        """
        if not self.comfyui_models_root or not os.path.exists(self.comfyui_models_root):
            logger.error("未设置有效的ComfyUI模型目录")
            return []
        
        scan_dir = self.comfyui_models_root
        if subdir:
            scan_dir = os.path.join(self.comfyui_models_root, subdir)
            if not os.path.exists(scan_dir):
                logger.error(f"子目录不存在: {scan_dir}")
                return []
        
        model_files = []
        for root, _, files in os.walk(scan_dir):
            rel_dir = os.path.relpath(root, self.comfyui_models_root)
            for file in files:
                _, ext = os.path.splitext(file)
                if ext.lower() in self.model_extensions:
                    file_path = os.path.join(root, file)
                    file_size = os.path.getsize(file_path)
                    model_info = {
                        "name": file,
                        "path": file_path,
                        "rel_path": os.path.join(rel_dir, file) if rel_dir != "." else file,
                        "size": file_size,
                        "size_mb": round(file_size / (1024 * 1024), 2),
                        "directory": rel_dir if rel_dir != "." else "",
                        "extension": ext.lower()
                    }
                    
                    # 如果模型类型检测器可用，尝试检测模型类型
                    if self.model_type_detector:
                        model_type, confidence = self.model_type_detector.detect_model_type(file_path)
                        model_info["detected_type"] = model_type
                        model_info["type_confidence"] = confidence
                    
                    model_files.append(model_info)
        
        return sorted(model_files, key=lambda x: x["rel_path"])
    
    def move_model_file(self, source_path: str, target_dir: str, create_backup: bool = True) -> Tuple[bool, str]:
        """
        移动模型文件到指定目录
        
        Args:
            source_path: 源文件路径 (相对于comfyui_models_root或绝对路径)
            target_dir: 目标目录 (相对于comfyui_models_root或绝对路径)
            create_backup: 是否创建备份
            
        Returns:
            (成功与否, 错误信息或成功信息)
        """
        if not self.comfyui_models_root:
            return False, "未设置ComfyUI模型目录"
        
        # 解析源文件路径
        if not os.path.isabs(source_path):
            source_path = os.path.join(self.comfyui_models_root, source_path)
        
        if not os.path.exists(source_path):
            return False, f"源文件不存在: {source_path}"
        
        # 解析目标目录路径
        if not os.path.isabs(target_dir):
            target_dir = os.path.join(self.comfyui_models_root, target_dir)
        
        # 确保目标目录存在
        if not os.path.exists(target_dir):
            try:
                os.makedirs(target_dir)
                logger.info(f"创建目标目录: {target_dir}")
            except Exception as e:
                return False, f"创建目标目录失败: {e}"
        
        # 获取文件名并构建目标路径
        file_name = os.path.basename(source_path)
        target_path = os.path.join(target_dir, file_name)
        
        # 检查目标文件是否已存在
        if os.path.exists(target_path):
            return False, f"目标文件已存在: {target_path}"
        
        # 创建备份
        if create_backup and self.backup_dir:
            backup_file = os.path.join(self.backup_dir, file_name)
            try:
                shutil.copy2(source_path, backup_file)
                logger.info(f"已创建备份: {backup_file}")
            except Exception as e:
                logger.warning(f"创建备份失败: {e}")
                # 继续执行，即使备份失败
        
        # 移动文件
        try:
            shutil.move(source_path, target_path)
            logger.info(f"已移动文件: {source_path} -> {target_path}")
            rel_target = os.path.relpath(target_path, self.comfyui_models_root)
            return True, f"已成功移动文件到: {rel_target}"
        except Exception as e:
            logger.error(f"移动文件失败: {e}")
            return False, f"移动文件失败: {e}"
    
    def copy_model_file(self, source_path: str, target_dir: str) -> Tuple[bool, str]:
        """
        复制模型文件到指定目录
        
        Args:
            source_path: 源文件路径 (相对于comfyui_models_root或绝对路径)
            target_dir: 目标目录 (相对于comfyui_models_root或绝对路径)
            
        Returns:
            (成功与否, 错误信息或成功信息)
        """
        if not self.comfyui_models_root:
            return False, "未设置ComfyUI模型目录"
        
        # 解析源文件路径
        if not os.path.isabs(source_path):
            source_path = os.path.join(self.comfyui_models_root, source_path)
        
        if not os.path.exists(source_path):
            return False, f"源文件不存在: {source_path}"
        
        # 解析目标目录路径
        if not os.path.isabs(target_dir):
            target_dir = os.path.join(self.comfyui_models_root, target_dir)
        
        # 确保目标目录存在
        if not os.path.exists(target_dir):
            try:
                os.makedirs(target_dir)
                logger.info(f"创建目标目录: {target_dir}")
            except Exception as e:
                return False, f"创建目标目录失败: {e}"
        
        # 获取文件名并构建目标路径
        file_name = os.path.basename(source_path)
        target_path = os.path.join(target_dir, file_name)
        
        # 检查目标文件是否已存在
        if os.path.exists(target_path):
            return False, f"目标文件已存在: {target_path}"
        
        # 复制文件
        try:
            shutil.copy2(source_path, target_path)
            logger.info(f"已复制文件: {source_path} -> {target_path}")
            rel_target = os.path.relpath(target_path, self.comfyui_models_root)
            return True, f"已成功复制文件到: {rel_target}"
        except Exception as e:
            logger.error(f"复制文件失败: {e}")
            return False, f"复制文件失败: {e}"
    
    def create_directory(self, dir_path: str) -> Tuple[bool, str]:
        """
        在模型目录下创建新目录
        
        Args:
            dir_path: 目录路径 (相对于comfyui_models_root)
            
        Returns:
            (成功与否, 错误信息或成功信息)
        """
        if not self.comfyui_models_root:
            return False, "未设置ComfyUI模型目录"
        
        full_path = os.path.join(self.comfyui_models_root, dir_path)
        
        if os.path.exists(full_path):
            return False, f"目录已存在: {dir_path}"
        
        try:
            os.makedirs(full_path)
            logger.info(f"已创建目录: {full_path}")
            return True, f"已成功创建目录: {dir_path}"
        except Exception as e:
            logger.error(f"创建目录失败: {e}")
            return False, f"创建目录失败: {e}"
    
    def delete_empty_directories(self) -> Tuple[int, List[str]]:
        """
        删除所有空目录
        
        Returns:
            (删除的目录数量, 删除的目录列表)
        """
        if not self.comfyui_models_root:
            return 0, []
        
        deleted_dirs = []
        
        # 从下往上遍历目录树，先删除深层目录
        for root, dirs, files in os.walk(self.comfyui_models_root, topdown=False):
            if root == self.comfyui_models_root:
                continue  # 不删除根目录
            
            # 检查目录是否为空 (没有文件且没有子目录)
            if not files and not dirs:
                rel_path = os.path.relpath(root, self.comfyui_models_root)
                try:
                    os.rmdir(root)
                    logger.info(f"已删除空目录: {root}")
                    deleted_dirs.append(rel_path)
                except Exception as e:
                    logger.error(f"删除空目录失败: {root}, 错误: {e}")
        
        return len(deleted_dirs), deleted_dirs
    
    def get_model_stats(self) -> Dict[str, Any]:
        """
        获取模型统计信息
        
        Returns:
            统计信息字典
        """
        if not self.comfyui_models_root:
            return {"error": "未设置ComfyUI模型目录"}
        
        all_files = self.scan_model_files()
        total_size = sum(f["size"] for f in all_files)
        
        # 按目录统计
        dir_stats = {}
        for file in all_files:
            dir_name = file["directory"] or "根目录"
            if dir_name not in dir_stats:
                dir_stats[dir_name] = {"count": 0, "size": 0}
            dir_stats[dir_name]["count"] += 1
            dir_stats[dir_name]["size"] += file["size"]
        
        # 按扩展名统计
        ext_stats = {}
        for file in all_files:
            ext = file["extension"]
            if ext not in ext_stats:
                ext_stats[ext] = {"count": 0, "size": 0}
            ext_stats[ext]["count"] += 1
            ext_stats[ext]["size"] += file["size"]
        
        return {
            "total_files": len(all_files),
            "total_size": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "total_size_gb": round(total_size / (1024 * 1024 * 1024), 2),
            "directories": len(dir_stats),
            "dir_stats": dir_stats,
            "ext_stats": ext_stats
        }
    
    # ---- 智能移动功能 ----
    
    def detect_model_type(self, file_path: str) -> Tuple[str, float]:
        """
        检测模型文件的类型
        
        Args:
            file_path: 模型文件路径
            
        Returns:
            (模型类型, 置信度)，如果检测器不可用则返回("unknown", 0.0)
        """
        if not self.model_type_detector:
            return "unknown", 0.0
        
        return self.model_type_detector.detect_model_type(file_path)
    
    def get_recommended_directories(self, file_path: str) -> List[Dict[str, Any]]:
        """
        获取文件的推荐目标目录
        
        Args:
            file_path: 模型文件路径
            
        Returns:
            推荐目录列表，每个元素为字典:
            {
                'directory': 目录路径,
                'confidence': 置信度,
                'reason': 推荐理由,
                'needs_creation': 是否需要创建目录
            }
        """
        if not self.model_type_detector or not self.comfyui_models_root:
            return []
        
        # 确保文件路径存在
        full_path = file_path
        if not os.path.isabs(file_path):
            full_path = os.path.join(self.comfyui_models_root, file_path)
        
        if not os.path.exists(full_path):
            logger.warning(f"获取推荐目录失败：文件不存在: {file_path}")
            return []
        
        # 使用检测器获取推荐
        recommendations = self.model_type_detector.recommend_model_placement(full_path, self.comfyui_models_root)
        
        return recommendations
    
    def smart_move(self, source_path: str, target_dir: str = None, create_backup: bool = True) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """
        智能移动模型文件，如果不提供目标目录则返回推荐目录
        
        Args:
            source_path: 源文件路径
            target_dir: 目标目录，为None则只返回推荐而不执行移动
            create_backup: 是否创建备份
            
        Returns:
            (成功与否, 消息, 推荐目录列表)
        """
        # 确保源文件路径正确
        full_source_path = source_path
        if not os.path.isabs(source_path):
            full_source_path = os.path.join(self.comfyui_models_root, source_path)
        
        if not os.path.exists(full_source_path):
            return False, f"源文件不存在: {source_path}", []
        
        # 获取推荐目录
        recommendations = self.get_recommended_directories(full_source_path)
        
        # 如果未提供目标目录，则返回推荐
        if target_dir is None:
            return True, "获取推荐目录成功", recommendations
        
        # 如果提供了目标目录，则执行移动
        success, message = self.move_model_file(full_source_path, target_dir, create_backup)
        
        return success, message, recommendations
    
    def batch_smart_move(self, source_files: List[str], create_backup: bool = True) -> List[Dict[str, Any]]:
        """
        批量智能移动模型文件，只返回推荐结果，不执行移动
        
        Args:
            source_files: 源文件路径列表
            create_backup: 是否创建备份
            
        Returns:
            批量推荐结果，每个元素为字典:
            {
                'file_path': 文件路径,
                'file_name': 文件名,
                'detected_type': 检测到的模型类型,
                'confidence': 类型检测置信度,
                'recommendations': 推荐目录列表
            }
        """
        results = []
        
        for source_path in source_files:
            # 确保源文件路径正确
            full_source_path = source_path
            if not os.path.isabs(source_path):
                full_source_path = os.path.join(self.comfyui_models_root, source_path)
            
            if not os.path.exists(full_source_path):
                results.append({
                    'file_path': source_path,
                    'file_name': os.path.basename(source_path),
                    'error': f"源文件不存在: {source_path}",
                    'recommendations': []
                })
                continue
            
            # 检测模型类型
            model_type, confidence = self.detect_model_type(full_source_path)
            
            # 获取推荐目录
            recommendations = self.get_recommended_directories(full_source_path)
            
            results.append({
                'file_path': source_path,
                'file_name': os.path.basename(source_path),
                'detected_type': model_type,
                'confidence': confidence,
                'recommendations': recommendations
            })
        
        return results
    
    def execute_batch_move(self, batch_moves: List[Dict[str, str]], create_backup: bool = True) -> List[Dict[str, Any]]:
        """
        执行批量移动
        
        Args:
            batch_moves: 批量移动配置列表，每个元素为字典: {'source': 源文件路径, 'target': 目标目录}
            create_backup: 是否创建备份
            
        Returns:
            移动结果列表，每个元素为字典:
            {
                'source': 源文件路径,
                'target': 目标目录,
                'success': 成功与否,
                'message': 结果消息
            }
        """
        results = []
        
        for move_item in batch_moves:
            source_path = move_item.get('source')
            target_dir = move_item.get('target')
            
            if not source_path or not target_dir:
                results.append({
                    'source': source_path,
                    'target': target_dir,
                    'success': False,
                    'message': "源文件路径或目标目录未提供"
                })
                continue
            
            # 执行移动
            success, message = self.move_model_file(source_path, target_dir, create_backup)
            
            results.append({
                'source': source_path,
                'target': target_dir,
                'success': success,
                'message': message
            })
        
        return results 