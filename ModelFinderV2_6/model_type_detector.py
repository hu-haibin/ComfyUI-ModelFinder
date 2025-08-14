"""
模型类型检测器
负责识别模型类型并推荐正确的目标目录
"""

import os
import re
import json
import logging
from typing import Dict, List, Tuple, Optional, Any

logger = logging.getLogger(__name__)

class ModelTypeDetector:
    """
    模型类型检测器
    根据文件名、扩展名和可能的文件特征识别模型类型，并推荐合适的目标目录
    """
    
    # 常见模型类型与目录映射关系
    DEFAULT_TYPE_MAPPINGS = {
        "checkpoint": ["checkpoints"],
        "lora": ["loras"],
        "controlnet": ["controlnet"],
        "vae": ["vae"],
        "embedding": ["embeddings"],
        "upscaler": ["upscale_models"],
        "clip": ["clip"],
        "ipadapter": ["ipadapter"],
        "style_model": ["style_models"],
        "instantid": ["instantid"],
        "hypernetwork": ["hypernetworks"],
        "inpaint": ["inpaint"],
        "t2i_adapter": ["t2i_adapter"],
        "lycoris": ["lycoris"],
        "unet": ["unet"],
        "diffusers": ["diffusers"],
        "tokenizer": ["tokenizers"],
        "wildcard": ["wildcards"],
        "motion_module": ["motion_modules"],
        "clip_vision": ["clip_vision"],
        "gligen": ["gligen"],
        "presets": ["presets"],
        "photomaker": ["photomaker"],
        "unclip": ["unclip"],
        "pose": ["pose"],
        "lcm": ["lcm"],
        "videofusion": ["videofusion"],
        "misc": ["misc", "other"]
    }
    
    # 文件名关键词匹配规则
    DEFAULT_FILENAME_PATTERNS = {
        r"lora|loha|locon|lokr|locon|dylora": "lora",
        r"controlnet|control_|cnet_": "controlnet",
        r"vae|variational": "vae",
        r"embed|textual_inversion|embedding": "embedding",
        r"upscale|upscaler|esrgan": "upscaler",
        r"clip_|clip-|openclip": "clip",
        r"ip-adapter|ip_adapter|ipadapter": "ipadapter",
        r"style_model|style-model": "style_model",
        r"instant-id|instantid": "instantid",
        r"hypernetwork|hypernet": "hypernetwork",
        r"inpaint": "inpaint",
        r"t2i-adapter|t2i_adapter": "t2i_adapter",
        r"lycoris|loky|lora-lycoris|lyco": "lycoris",
        r"unet": "unet",
        r"diffusers": "diffusers",
        r"tokenizer": "tokenizer",
        r"wildcard": "wildcard",
        r"motion-module|motion_module|mm|animatediff": "motion_module",
        r"clip_vision|clip-vision": "clip_vision",
        r"gligen": "gligen",
        r"preset|setting": "presets",
        r"photomaker": "photomaker",
        r"unclip": "unclip",
        r"pose|mlsd|hed|openpose|dw-pose": "pose",
        r"lcm": "lcm",
        r"videofusion": "videofusion",
        r"sd_|sd-|stable-diffusion|checkpoint|safetensor": "checkpoint"
    }
    
    # 扩展名与模型类型关联
    DEFAULT_EXTENSION_MAPPINGS = {
        ".safetensors": ["checkpoint", "lora", "controlnet", "vae"],
        ".ckpt": ["checkpoint"],
        ".pt": ["clip", "embedding", "upscaler"],
        ".pth": ["clip", "embedding", "upscaler"],
        ".bin": ["clip", "embedding", "tokenizer"],
        ".json": ["config", "presets"],
        ".yaml": ["config", "presets"],
        ".onnx": ["onnx_model"]
    }
    
    def __init__(self, config_file: str = None):
        """
        初始化模型类型检测器
        
        Args:
            config_file: 配置文件路径，为None则使用默认配置
        """
        self.type_mappings = self.DEFAULT_TYPE_MAPPINGS.copy()
        self.filename_patterns = self.DEFAULT_FILENAME_PATTERNS.copy()
        self.extension_mappings = self.DEFAULT_EXTENSION_MAPPINGS.copy()
        self.comfyui_folder_structure = {}
        
        if config_file and os.path.exists(config_file):
            self.load_config(config_file)
            
        logger.info("ModelTypeDetector已初始化")
    
    def load_config(self, config_file: str) -> bool:
        """
        从配置文件加载规则
        
        Args:
            config_file: 配置文件路径
            
        Returns:
            加载是否成功
        """
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            # 加载模型类型与目录映射
            if 'type_mappings' in config and isinstance(config['type_mappings'], dict):
                custom_mappings = config['type_mappings']
                for model_type, directories in custom_mappings.items():
                    if isinstance(directories, list) and directories:
                        self.type_mappings[model_type] = directories
            
            # 加载文件名匹配规则
            if 'filename_patterns' in config and isinstance(config['filename_patterns'], dict):
                custom_patterns = config['filename_patterns']
                for pattern, model_type in custom_patterns.items():
                    if pattern and model_type:
                        self.filename_patterns[pattern] = model_type
            
            # 加载扩展名映射
            if 'extension_mappings' in config and isinstance(config['extension_mappings'], dict):
                custom_ext_mappings = config['extension_mappings']
                for ext, types in custom_ext_mappings.items():
                    if ext.startswith('.') and isinstance(types, list) and types:
                        self.extension_mappings[ext] = types
                        
            logger.info(f"已从配置文件加载模型检测规则: {config_file}")
            return True
        except Exception as e:
            logger.error(f"加载模型检测配置失败: {e}")
            return False
    
    def learn_from_comfyui_structure(self, comfyui_models_path: str) -> bool:
        """
        学习ComfyUI的目录结构，用于更准确地推荐目标目录
        
        Args:
            comfyui_models_path: ComfyUI模型目录路径
            
        Returns:
            学习是否成功
        """
        if not os.path.exists(comfyui_models_path) or not os.path.isdir(comfyui_models_path):
            logger.error(f"ComfyUI模型目录不存在或不是目录: {comfyui_models_path}")
            return False
            
        try:
            # 扫描目录结构
            for root, dirs, files in os.walk(comfyui_models_path):
                rel_path = os.path.relpath(root, comfyui_models_path)
                if rel_path == '.':
                    continue  # 跳过根目录
                    
                # 统计不同扩展名的文件数量
                ext_counts = {}
                for file in files:
                    _, ext = os.path.splitext(file)
                    ext = ext.lower()
                    if ext:
                        ext_counts[ext] = ext_counts.get(ext, 0) + 1
                
                # 存储目录信息
                self.comfyui_folder_structure[rel_path] = {
                    'file_count': len(files),
                    'extension_counts': ext_counts,
                    'subdirs': dirs
                }
                
                # 根据目录中的文件扩展名推断可能的模型类型
                possible_types = set()
                for ext, counts in ext_counts.items():
                    if ext in self.extension_mappings:
                        possible_types.update(self.extension_mappings[ext])
                
                if possible_types:
                    self.comfyui_folder_structure[rel_path]['possible_types'] = list(possible_types)
            
            # 更新类型映射，将目录名与可能的类型关联
            for folder, info in self.comfyui_folder_structure.items():
                if 'possible_types' in info:
                    for model_type in info['possible_types']:
                        if model_type in self.type_mappings:
                            if folder not in self.type_mappings[model_type]:
                                self.type_mappings[model_type].append(folder)
            
            logger.info(f"已学习ComfyUI目录结构，识别了 {len(self.comfyui_folder_structure)} 个目录")
            return True
        except Exception as e:
            logger.error(f"学习ComfyUI目录结构失败: {e}")
            return False
    
    def detect_model_type(self, file_path: str) -> Tuple[str, float]:
        """
        检测模型文件的类型
        
        Args:
            file_path: 模型文件路径
            
        Returns:
            (模型类型, 置信度)，置信度为0-1之间的浮点数
        """
        if not os.path.exists(file_path):
            logger.warning(f"检测模型类型失败：文件不存在: {file_path}")
            return "unknown", 0.0
            
        # 获取文件名和扩展名
        file_name = os.path.basename(file_path)
        base_name, ext = os.path.splitext(file_name.lower())
        ext = ext.lower()
        
        # 初始化候选类型和置信度
        candidates = {}
        
        # 1. 首先通过文件名匹配规则检测
        for pattern, model_type in self.filename_patterns.items():
            if re.search(pattern, base_name, re.IGNORECASE):
                candidates[model_type] = candidates.get(model_type, 0) + 0.5
                
        # 2. 通过扩展名检测
        if ext in self.extension_mappings:
            possible_types = self.extension_mappings[ext]
            for t in possible_types:
                candidates[t] = candidates.get(t, 0) + 0.3
        
        # 3. 对于某些特殊文件，尝试通过内容识别
        # 例如：检查前几个字节或查看JSON内容等
        # TODO: 实现更复杂的文件内容分析
        
        # 如果没有找到任何匹配项
        if not candidates:
            # 根据扩展名进行基本分类
            if ext == '.safetensors':
                candidates["checkpoint"] = 0.3
            elif ext == '.ckpt':
                candidates["checkpoint"] = 0.4
            elif ext in ['.pt', '.pth']:
                candidates["embedding"] = 0.3
            elif ext == '.bin':
                candidates["clip"] = 0.3
            else:
                candidates["misc"] = 0.2
        
        # 选择置信度最高的类型
        if candidates:
            best_type = max(candidates.items(), key=lambda x: x[1])
            return best_type[0], min(best_type[1], 1.0)  # 确保置信度不超过1.0
        
        return "unknown", 0.0
    
    def recommend_target_directory(self, file_path: str, model_type: str = None, min_confidence: float = 0.3) -> List[Dict[str, Any]]:
        """
        推荐模型文件的目标目录
        
        Args:
            file_path: 模型文件路径
            model_type: 模型类型，如果为None则自动检测
            min_confidence: 最小置信度，低于此值的推荐将被过滤
            
        Returns:
            推荐目录列表，每个元素为字典:
            {
                'directory': 目录路径,
                'confidence': 置信度,
                'reason': 推荐理由
            }
        """
        # 如果未提供类型，则自动检测
        if model_type is None:
            model_type, confidence = self.detect_model_type(file_path)
        else:
            confidence = 0.8  # 用户指定的类型给予较高置信度
        
        recommendations = []
        
        # 1. 根据类型映射推荐目录
        if model_type in self.type_mappings:
            for dir_path in self.type_mappings[model_type]:
                recommendations.append({
                    'directory': dir_path,
                    'confidence': confidence,
                    'reason': f"基于模型类型 '{model_type}' 的标准映射"
                })
        
        # 2. 如果ComfyUI目录结构已学习，根据现有结构推荐
        if self.comfyui_folder_structure:
            file_name = os.path.basename(file_path)
            _, ext = os.path.splitext(file_name.lower())
            ext = ext.lower()
            
            # 寻找包含相似扩展名文件的目录
            for folder, info in self.comfyui_folder_structure.items():
                if ext in info.get('extension_counts', {}):
                    # 如果目录中有相同扩展名的文件，增加推荐可能性
                    conf = min(0.7, 0.3 + (info['extension_counts'][ext] / max(info['file_count'], 1)) * 0.4)
                    
                    # 如果目录名包含模型类型，增加置信度
                    if model_type != "unknown" and (model_type in folder.lower() or any(t in folder.lower() for t in self.type_mappings.get(model_type, []))):
                        conf += 0.2
                    
                    if conf >= min_confidence:
                        recommendations.append({
                            'directory': folder,
                            'confidence': conf,
                            'reason': f"基于现有目录结构，该目录包含 {info['extension_counts'][ext]} 个相同扩展名的文件"
                        })
        
        # 3. 如果没有足够的推荐，添加通用推荐
        if not recommendations or all(r['confidence'] < 0.5 for r in recommendations):
            _, ext = os.path.splitext(file_path.lower())
            
            if ext == '.safetensors':
                recommendations.append({
                    'directory': 'checkpoints',
                    'confidence': 0.4,
                    'reason': "通用推荐：safetensors文件通常为模型权重"
                })
            elif ext == '.ckpt':
                recommendations.append({
                    'directory': 'checkpoints',
                    'confidence': 0.5,
                    'reason': "通用推荐：ckpt文件通常为完整模型"
                })
            elif ext in ['.pt', '.pth']:
                recommendations.append({
                    'directory': 'embeddings',
                    'confidence': 0.4,
                    'reason': "通用推荐：pt/pth文件可能为词嵌入或小型模型"
                })
            elif ext == '.bin':
                recommendations.append({
                    'directory': 'clip',
                    'confidence': 0.4,
                    'reason': "通用推荐：bin文件可能为CLIP模型"
                })
        
        # 按置信度排序，过滤低置信度项
        recommendations = [r for r in recommendations if r['confidence'] >= min_confidence]
        recommendations.sort(key=lambda x: x['confidence'], reverse=True)
        
        # 去除重复的目录
        unique_dirs = set()
        filtered_recommendations = []
        for rec in recommendations:
            if rec['directory'] not in unique_dirs:
                unique_dirs.add(rec['directory'])
                filtered_recommendations.append(rec)
        
        return filtered_recommendations
    
    def recommend_model_placement(self, file_path: str, target_root: str) -> List[Dict[str, Any]]:
        """
        推荐模型文件的放置位置，返回完整的目标路径
        
        Args:
            file_path: 模型文件路径
            target_root: 目标根目录(ComfyUI模型目录)
            
        Returns:
            推荐目标列表，每个元素为字典:
            {
                'directory': 相对目录路径,
                'full_path': 完整目标路径,
                'confidence': 置信度,
                'reason': 推荐理由,
                'needs_creation': 是否需要创建目录
            }
        """
        recommendations = self.recommend_target_directory(file_path)
        result = []
        
        for rec in recommendations:
            rel_dir = rec['directory']
            full_path = os.path.join(target_root, rel_dir)
            needs_creation = not os.path.exists(full_path)
            
            result.append({
                'directory': rel_dir,
                'full_path': full_path,
                'confidence': rec['confidence'],
                'reason': rec['reason'],
                'needs_creation': needs_creation
            })
        
        return result
    
    def get_model_directory_stats(self, comfyui_models_path: str) -> Dict[str, Any]:
        """
        获取模型目录统计信息
        
        Args:
            comfyui_models_path: ComfyUI模型目录路径
            
        Returns:
            目录统计信息
        """
        if not os.path.exists(comfyui_models_path) or not os.path.isdir(comfyui_models_path):
            logger.error(f"ComfyUI模型目录不存在或不是目录: {comfyui_models_path}")
            return {"error": "模型目录无效"}
            
        try:
            stats = {
                "total_directories": 0,
                "directories": {},
                "extensions": {},
                "model_types": {}
            }
            
            # 扫描目录结构
            for root, dirs, files in os.walk(comfyui_models_path):
                rel_path = os.path.relpath(root, comfyui_models_path)
                if rel_path == '.':
                    continue  # 跳过根目录
                    
                stats["total_directories"] += 1
                
                # 统计目录中的文件
                file_count = len(files)
                stats["directories"][rel_path] = {
                    "file_count": file_count,
                    "extensions": {}
                }
                
                # 统计扩展名
                for file in files:
                    _, ext = os.path.splitext(file)
                    ext = ext.lower()
                    if ext:
                        stats["directories"][rel_path]["extensions"][ext] = stats["directories"][rel_path]["extensions"].get(ext, 0) + 1
                        stats["extensions"][ext] = stats["extensions"].get(ext, 0) + 1
                
                # 推断目录可能的模型类型
                dir_name = os.path.basename(root).lower()
                for model_type, dirs in self.type_mappings.items():
                    if any(dir_name == d.lower() or dir_name in d.lower() for d in dirs):
                        stats["directories"][rel_path]["possible_type"] = model_type
                        stats["model_types"][model_type] = stats["model_types"].get(model_type, 0) + 1
                        break
            
            return stats
        except Exception as e:
            logger.error(f"获取模型目录统计信息失败: {e}")
            return {"error": str(e)} 