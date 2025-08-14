import os
import json
import logging
import time
from typing import List, Dict, Any, Optional, Union

logger = logging.getLogger(__name__)

class ModelRegistry:
    """
    模型记录管理器。
    提供模型信息的记录、查询、更新和删除功能。
    """
    
    def __init__(self):
        self.registry_file = None
        self.models = {}  # 模型记录字典，键为模型ID
        self.next_id = 1  # 下一个可用ID
        logger.info("ModelRegistry已初始化")
    
    def set_registry_file(self, file_path: str) -> bool:
        """
        设置记录文件路径并加载数据
        
        Args:
            file_path: 记录文件的路径
            
        Returns:
            设置是否成功
        """
        try:
            self.registry_file = file_path
            # 如果文件存在，加载数据
            if os.path.exists(file_path):
                self.load()
            else:
                # 确保目录存在
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                # 创建空记录
                self.models = {}
                self.next_id = 1
                # 保存到文件
                self.save()
            
            logger.info(f"设置记录文件: {file_path}")
            return True
        except Exception as e:
            logger.error(f"设置记录文件失败: {e}")
            return False
    
    def load(self) -> bool:
        """
        从文件加载模型记录
        
        Returns:
            加载是否成功
        """
        if not self.registry_file or not os.path.exists(self.registry_file):
            logger.error("记录文件不存在")
            return False
        
        try:
            with open(self.registry_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.models = data.get('models', {})
                self.next_id = data.get('next_id', 1)
            
            # 转换ID为字符串，确保一致性
            models_copy = {}
            for k, v in self.models.items():
                models_copy[str(k)] = v
            self.models = models_copy
            
            logger.info(f"已从 {self.registry_file} 加载 {len(self.models)} 条模型记录")
            return True
        except Exception as e:
            logger.error(f"加载记录失败: {e}")
            return False
    
    def save(self) -> bool:
        """
        保存模型记录到文件
        
        Returns:
            保存是否成功
        """
        if not self.registry_file:
            logger.error("未设置记录文件路径")
            return False
        
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.registry_file), exist_ok=True)
            
            # 保存数据
            data = {
                'models': self.models,
                'next_id': self.next_id,
                'last_updated': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            with open(self.registry_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"已保存 {len(self.models)} 条模型记录到 {self.registry_file}")
            return True
        except Exception as e:
            logger.error(f"保存记录失败: {e}")
            return False
    
    def add_model(self, model_data: Dict[str, Any]) -> Optional[str]:
        """
        添加模型记录
        
        Args:
            model_data: 模型信息字典，必须包含 'name' 和 'path' 字段
            
        Returns:
            成功添加返回模型ID，失败返回None
        """
        if not model_data.get('name') or not model_data.get('path'):
            logger.error("添加模型记录失败: 缺少必要字段(name或path)")
            return None
        
        # 生成模型ID
        model_id = str(self.next_id)
        self.next_id += 1
        
        # 添加时间戳
        model_data['added_time'] = time.strftime('%Y-%m-%d %H:%M:%S')
        model_data['updated_time'] = model_data['added_time']
        
        # 保存记录
        self.models[model_id] = model_data
        self.save()
        
        logger.info(f"已添加模型记录: ID={model_id}, 名称={model_data['name']}")
        return model_id
    
    def get_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定ID的模型记录
        
        Args:
            model_id: 模型ID
            
        Returns:
            模型记录字典，不存在返回None
        """
        model_id = str(model_id)  # 确保ID为字符串
        if model_id not in self.models:
            logger.warning(f"获取模型记录失败: ID={model_id} 不存在")
            return None
        
        return self.models[model_id]
    
    def update_model(self, model_id: str, model_data: Dict[str, Any]) -> bool:
        """
        更新模型记录
        
        Args:
            model_id: 模型ID
            model_data: 更新的模型信息
            
        Returns:
            更新是否成功
        """
        model_id = str(model_id)  # 确保ID为字符串
        if model_id not in self.models:
            logger.warning(f"更新模型记录失败: ID={model_id} 不存在")
            return False
        
        # 保留原始添加时间
        if 'added_time' in self.models[model_id]:
            model_data['added_time'] = self.models[model_id]['added_time']
        
        # 更新时间戳
        model_data['updated_time'] = time.strftime('%Y-%m-%d %H:%M:%S')
        
        # 更新记录
        self.models[model_id] = model_data
        self.save()
        
        logger.info(f"已更新模型记录: ID={model_id}, 名称={model_data.get('name', '未知')}")
        return True
    
    def delete_model(self, model_id: str) -> bool:
        """
        删除模型记录
        
        Args:
            model_id: 模型ID
            
        Returns:
            删除是否成功
        """
        model_id = str(model_id)  # 确保ID为字符串
        if model_id not in self.models:
            logger.warning(f"删除模型记录失败: ID={model_id} 不存在")
            return False
        
        # 获取模型名称用于日志
        model_name = self.models[model_id].get('name', '未知')
        
        # 删除记录
        del self.models[model_id]
        self.save()
        
        logger.info(f"已删除模型记录: ID={model_id}, 名称={model_name}")
        return True
    
    def get_all_models(self) -> List[Dict[str, Any]]:
        """
        获取所有模型记录
        
        Returns:
            模型记录列表，每个元素包含模型信息和ID
        """
        result = []
        for model_id, model_data in self.models.items():
            model_copy = model_data.copy()
            model_copy['id'] = model_id
            result.append(model_copy)
        
        return sorted(result, key=lambda x: x.get('name', ''))
    
    def search_models(self, query: str = None, tags: List[str] = None, model_type: str = None) -> List[Dict[str, Any]]:
        """
        搜索模型记录
        
        Args:
            query: 搜索关键词，匹配名称和描述
            tags: 标签列表，模型必须包含所有指定标签
            model_type: 模型类型
            
        Returns:
            匹配的模型记录列表
        """
        results = []
        
        for model_id, model_data in self.models.items():
            # 检查是否匹配所有条件
            match = True
            
            # 检查关键词
            if query and query.lower() not in model_data.get('name', '').lower() and query.lower() not in model_data.get('description', '').lower():
                match = False
            
            # 检查标签
            if tags and not all(tag in model_data.get('tags', []) for tag in tags):
                match = False
            
            # 检查类型
            if model_type and model_type != model_data.get('type', ''):
                match = False
            
            if match:
                model_copy = model_data.copy()
                model_copy['id'] = model_id
                results.append(model_copy)
        
        return sorted(results, key=lambda x: x.get('name', ''))
    
    def get_all_tags(self) -> List[str]:
        """
        获取所有已使用的标签
        
        Returns:
            标签列表
        """
        tags = set()
        for model_data in self.models.values():
            if 'tags' in model_data and isinstance(model_data['tags'], list):
                tags.update(model_data['tags'])
        
        return sorted(list(tags))
    
    def get_all_types(self) -> List[str]:
        """
        获取所有已使用的模型类型
        
        Returns:
            模型类型列表
        """
        types = set()
        for model_data in self.models.values():
            if 'type' in model_data and model_data['type']:
                types.add(model_data['type'])
        
        return sorted(list(types))
    
    def add_tag_to_model(self, model_id: str, tag: str) -> bool:
        """
        为模型添加标签
        
        Args:
            model_id: 模型ID
            tag: 标签
            
        Returns:
            操作是否成功
        """
        model_id = str(model_id)  # 确保ID为字符串
        if model_id not in self.models:
            logger.warning(f"为模型添加标签失败: ID={model_id} 不存在")
            return False
        
        # 获取当前标签列表
        model_data = self.models[model_id]
        if 'tags' not in model_data or not isinstance(model_data['tags'], list):
            model_data['tags'] = []
        
        # 检查标签是否已存在
        if tag in model_data['tags']:
            return True  # 已存在，视为成功
        
        # 添加标签
        model_data['tags'].append(tag)
        model_data['updated_time'] = time.strftime('%Y-%m-%d %H:%M:%S')
        self.save()
        
        logger.info(f"为模型添加标签: ID={model_id}, 标签={tag}")
        return True
    
    def remove_tag_from_model(self, model_id: str, tag: str) -> bool:
        """
        从模型移除标签
        
        Args:
            model_id: 模型ID
            tag: 标签
            
        Returns:
            操作是否成功
        """
        model_id = str(model_id)  # 确保ID为字符串
        if model_id not in self.models:
            logger.warning(f"从模型移除标签失败: ID={model_id} 不存在")
            return False
        
        # 获取当前标签列表
        model_data = self.models[model_id]
        if 'tags' not in model_data or not isinstance(model_data['tags'], list) or tag not in model_data['tags']:
            return True  # 标签不存在，视为成功
        
        # 移除标签
        model_data['tags'].remove(tag)
        model_data['updated_time'] = time.strftime('%Y-%m-%d %H:%M:%S')
        self.save()
        
        logger.info(f"从模型移除标签: ID={model_id}, 标签={tag}")
        return True
    
    def export_registry(self, file_path: str) -> bool:
        """
        导出模型记录到文件
        
        Args:
            file_path: 导出文件路径
            
        Returns:
            导出是否成功
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 准备导出数据
            export_data = {
                'models': self.models,
                'exported_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                'count': len(self.models)
            }
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"已导出 {len(self.models)} 条模型记录到 {file_path}")
            return True
        except Exception as e:
            logger.error(f"导出记录失败: {e}")
            return False
    
    def import_registry(self, file_path: str, merge: bool = True) -> bool:
        """
        从文件导入模型记录
        
        Args:
            file_path: 导入文件路径
            merge: 是否合并记录，True为合并，False为替换
            
        Returns:
            导入是否成功
        """
        if not os.path.exists(file_path):
            logger.error(f"导入记录失败: 文件不存在 {file_path}")
            return False
        
        try:
            # 读取导入文件
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            imported_models = import_data.get('models', {})
            if not imported_models:
                logger.warning(f"导入记录失败: 文件中没有模型记录 {file_path}")
                return False
            
            # 处理导入
            if merge:
                # 合并记录
                max_id = max([int(id) for id in self.models.keys()]) if self.models else 0
                next_id = max_id + 1
                
                for _, model_data in imported_models.items():
                    # 生成新ID
                    model_id = str(next_id)
                    next_id += 1
                    
                    # 更新时间戳
                    model_data['imported_time'] = time.strftime('%Y-%m-%d %H:%M:%S')
                    if 'updated_time' not in model_data:
                        model_data['updated_time'] = model_data['imported_time']
                    
                    # 添加到记录
                    self.models[model_id] = model_data
                
                self.next_id = next_id
            else:
                # 替换记录
                self.models = imported_models
                self.next_id = import_data.get('next_id', len(imported_models) + 1)
            
            # 保存到文件
            self.save()
            
            logger.info(f"已导入 {len(imported_models)} 条模型记录，模式: {'合并' if merge else '替换'}")
            return True
        except Exception as e:
            logger.error(f"导入记录失败: {e}")
            return False 