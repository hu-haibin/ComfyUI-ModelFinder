import os
import json
import logging
from typing import List, Dict, Any, Union

logger = logging.getLogger(__name__)

class ModelConfigManager:
    """
    管理模型配置文件，提供CRUD操作功能。
    支持对model_node_types、node_model_indices和model_extensions的读取和修改。
    """
    CONFIG_FILENAME = "model_config.json"

    def __init__(self):
        self._config_path = self._get_config_path()
        self._config = self._load_config()
        logger.info(f"模型配置管理器初始化，配置文件路径: {self._config_path}")
        logger.info(f"已加载 {len(self.get_model_node_types())} 个节点类型, " 
                   f"{len(self.get_node_model_indices())} 个节点索引映射, "
                   f"{len(self.get_model_extensions())} 个模型扩展名")

    def _get_config_path(self) -> str:
        """确定配置文件的绝对路径。"""
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), self.CONFIG_FILENAME)

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件，如果不存在则创建默认配置。"""
        if not os.path.exists(self._config_path):
            logger.warning(f"配置文件不存在: {self._config_path}，将创建默认配置")
            self._create_default_config()
        
        try:
            with open(self._config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            # 验证配置文件结构
            self._validate_config(config)
            return config
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}", exc_info=True)
            return self._create_default_config()

    def _save_config(self) -> bool:
        """保存配置到文件。"""
        try:
            # 创建备份
            if os.path.exists(self._config_path):
                backup_path = f"{self._config_path}.bak"
                try:
                    with open(self._config_path, 'r', encoding='utf-8') as src, \
                            open(backup_path, 'w', encoding='utf-8') as dst:
                        dst.write(src.read())
                except Exception as e:
                    logger.warning(f"创建配置文件备份失败: {e}")
            
            # 写入新配置
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, ensure_ascii=False, indent=4)
            logger.info(f"配置已保存到: {self._config_path}")
            return True
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}", exc_info=True)
            return False

    def _validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置文件结构。"""
        required_keys = ['model_node_types', 'node_model_indices', 'model_extensions']
        for key in required_keys:
            if key not in config:
                raise ValueError(f"配置文件缺少必要的键: {key}")
        
        # 验证类型
        if not isinstance(config['model_node_types'], list):
            raise TypeError("model_node_types 必须是列表类型")
        if not isinstance(config['node_model_indices'], dict):
            raise TypeError("node_model_indices 必须是字典类型")
        if not isinstance(config['model_extensions'], list):
            raise TypeError("model_extensions 必须是列表类型")
            
        # 验证node_model_indices的每个值是否为列表
        for node_type, indices in config['node_model_indices'].items():
            if isinstance(indices, int):
                # 自动修复：将单个整数转换为列表
                config['node_model_indices'][node_type] = [indices]
                logger.warning(f"已修复节点索引格式: {node_type} -> [{indices}]")
            elif not isinstance(indices, list):
                raise TypeError(f"节点 {node_type} 的索引映射必须是整数列表")
        
        return True

    def _create_default_config(self) -> Dict[str, Any]:
        """创建默认配置文件。"""
        default_config = {
            "model_node_types": [
                "CheckpointLoader", "VAELoader", "ModelLoader", "LoraLoader"
            ],
            "node_model_indices": {
                "default": [0]
            },
            "model_extensions": [
                ".safetensors", ".pth", ".ckpt", ".pt", ".bin"
            ]
        }
        
        try:
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=4)
            logger.info(f"已创建默认配置文件: {self._config_path}")
        except Exception as e:
            logger.error(f"创建默认配置文件失败: {e}", exc_info=True)
        
        return default_config

    # ---------- CRUD 操作: 获取配置 ----------
    
    def get_model_node_types(self) -> List[str]:
        """获取所有支持的模型节点类型。"""
        return self._config.get('model_node_types', [])
    
    def get_node_model_indices(self) -> Dict[str, List[int]]:
        """获取节点模型索引映射。"""
        return self._config.get('node_model_indices', {"default": [0]})
    
    def get_model_extensions(self) -> List[str]:
        """获取所有支持的模型文件扩展名。"""
        return self._config.get('model_extensions', [])
    
    def get_full_config(self) -> Dict[str, Any]:
        """获取完整配置。"""
        return self._config.copy()
    
    # ---------- CRUD 操作: 添加配置项 ----------
    
    def add_model_node_type(self, node_type: str) -> bool:
        """添加一个模型节点类型。"""
        if not node_type or not isinstance(node_type, str):
            logger.error(f"无效的节点类型: {node_type}")
            return False
        
        if node_type in self._config['model_node_types']:
            logger.warning(f"节点类型已存在: {node_type}")
            return True
        
        self._config['model_node_types'].append(node_type)
        logger.info(f"已添加节点类型: {node_type}")
        return self._save_config()
    
    def add_node_model_index(self, node_type: str, indices: Union[List[int], int]) -> bool:
        """为指定节点类型添加模型索引映射。
        
        Args:
            node_type: 节点类型名称
            indices: 可以是单个整数或整数列表
        """
        if not node_type or not isinstance(node_type, str):
            logger.error(f"无效的节点类型: {node_type}")
            return False
        
        # 检查并标准化索引参数
        if isinstance(indices, int):
            indices = [indices]  # 将单个整数转换为列表
        elif not isinstance(indices, (list, tuple)):
            logger.error(f"无效的索引格式: {indices}, 必须是整数或整数列表")
            return False
        
        # 检查列表中的每个元素是否为整数
        if not all(isinstance(idx, int) for idx in indices):
            logger.error(f"索引列表中包含非整数值: {indices}")
            return False
        
        if node_type in self._config['node_model_indices']:
            logger.warning(f"节点索引映射已存在: {node_type}, 将更新")
        
        self._config['node_model_indices'][node_type] = indices
        logger.info(f"已添加/更新节点索引映射: {node_type} -> {indices}")
        return self._save_config()
    
    def add_model_extension(self, extension: str) -> bool:
        """添加一个模型文件扩展名。"""
        if not extension or not isinstance(extension, str):
            logger.error(f"无效的文件扩展名: {extension}")
            return False
        
        # 确保扩展名以点开头
        if not extension.startswith('.'):
            extension = f".{extension}"
        
        if extension in self._config['model_extensions']:
            logger.warning(f"文件扩展名已存在: {extension}")
            return True
        
        self._config['model_extensions'].append(extension)
        logger.info(f"已添加文件扩展名: {extension}")
        return self._save_config()
    
    # ---------- CRUD 操作: 删除配置项 ----------
    
    def remove_model_node_type(self, node_type: str) -> bool:
        """删除一个模型节点类型。"""
        if not node_type or not isinstance(node_type, str):
            logger.error(f"无效的节点类型: {node_type}")
            return False
        
        if node_type not in self._config['model_node_types']:
            logger.warning(f"节点类型不存在: {node_type}")
            return True
        
        self._config['model_node_types'].remove(node_type)
        logger.info(f"已删除节点类型: {node_type}")
        return self._save_config()
    
    def remove_node_model_index(self, node_type: str) -> bool:
        """删除指定节点类型的模型索引映射。"""
        if not node_type or not isinstance(node_type, str):
            logger.error(f"无效的节点类型: {node_type}")
            return False
        
        if node_type not in self._config['node_model_indices']:
            logger.warning(f"节点索引映射不存在: {node_type}")
            return True
        
        if node_type == "default":
            logger.error("不能删除默认节点索引映射")
            return False
        
        del self._config['node_model_indices'][node_type]
        logger.info(f"已删除节点索引映射: {node_type}")
        return self._save_config()
    
    def remove_model_extension(self, extension: str) -> bool:
        """删除一个模型文件扩展名。"""
        if not extension or not isinstance(extension, str):
            logger.error(f"无效的文件扩展名: {extension}")
            return False
        
        # 确保扩展名以点开头
        if not extension.startswith('.'):
            extension = f".{extension}"
        
        if extension not in self._config['model_extensions']:
            logger.warning(f"文件扩展名不存在: {extension}")
            return True
        
        self._config['model_extensions'].remove(extension)
        logger.info(f"已删除文件扩展名: {extension}")
        return self._save_config()
    
    # ---------- CRUD 操作: 更新配置项 ----------
    
    def update_model_node_types(self, node_types: List[str]) -> bool:
        """更新所有模型节点类型。"""
        if not isinstance(node_types, list):
            logger.error(f"无效的节点类型列表: {node_types}")
            return False
        
        self._config['model_node_types'] = node_types
        logger.info(f"已更新所有节点类型，共 {len(node_types)} 个")
        return self._save_config()
    
    def update_node_model_indices(self, indices_map: Dict[str, List[int]]) -> bool:
        """更新所有节点模型索引映射。"""
        if not isinstance(indices_map, dict):
            logger.error(f"无效的节点索引映射字典: {indices_map}")
            return False
        
        # 确保包含默认映射
        if "default" not in indices_map:
            indices_map["default"] = self._config['node_model_indices'].get("default", [0])
            logger.warning("保留默认节点索引映射")
        
        self._config['node_model_indices'] = indices_map
        logger.info(f"已更新所有节点索引映射，共 {len(indices_map)} 个")
        return self._save_config()
    
    def update_model_extensions(self, extensions: List[str]) -> bool:
        """更新所有模型文件扩展名。"""
        if not isinstance(extensions, list):
            logger.error(f"无效的文件扩展名列表: {extensions}")
            return False
        
        # 确保所有扩展名都以点开头
        normalized_extensions = []
        for ext in extensions:
            if not ext.startswith('.'):
                normalized_extensions.append(f".{ext}")
            else:
                normalized_extensions.append(ext)
        
        self._config['model_extensions'] = normalized_extensions
        logger.info(f"已更新所有文件扩展名，共 {len(normalized_extensions)} 个")
        return self._save_config()
    
    # ---------- 特殊功能 ----------
    
    def reset_to_default(self) -> bool:
        """重置为默认配置。"""
        self._config = self._create_default_config()
        logger.info("已重置为默认配置")
        return True
    
    def reload_config(self) -> bool:
        """重新加载配置文件。"""
        try:
            self._config = self._load_config()
            logger.info("已重新加载配置文件")
            return True
        except Exception as e:
            logger.error(f"重新加载配置文件失败: {e}", exc_info=True)
            return False 