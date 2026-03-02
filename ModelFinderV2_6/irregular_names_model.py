# ModelFinderV2_5/irregular_names_model.py
import os
import json
import logging
import uuid # 用于生成唯一的ID，方便编辑和删除
import re

logger = logging.getLogger(__name__)

class IrregularNamesModel:
    """
    处理不规则模型名称与规范名称之间的映射。
    数据将存储在同目录下的 irregular_names_map.json 文件中。
    """
    MAPPINGS_FILENAME = "irregular_names_map.json"

    def __init__(self):
        self._mappings_path = self._get_mappings_path()
        self.mappings = self._load_mappings() # 将映射加载到内存中
        logger.info(f"不规则名称映射文件路径: {self._mappings_path}")
        logger.info(f"加载了 {len(self.mappings)} 条名称映射")
        # 日志记录所有加载的映射以便验证
        for mapping in self.mappings:
            logger.debug(f"加载映射: '{mapping.get('original_name')}' -> '{mapping.get('corrected_name')}'")

    def _get_mappings_path(self):
        """确定映射文件的绝对路径。"""
        return os.path.join(os.path.dirname(__file__), self.MAPPINGS_FILENAME)

    def _load_mappings(self):
        """
        从JSON文件加载映射。
        如果文件不存在或无效，则返回一个空列表。
        每个映射条目将包含一个唯一的 'id'。
        """
        if not os.path.exists(self._mappings_path):
            logger.warning(f"映射文件 {self._mappings_path} 未找到。将创建一个新的空映射列表。")
            return []
        try:
            with open(self._mappings_path, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
                # 确保每个条目都有一个ID，用于未来的编辑/删除操作
                # 如果旧数据没有ID，可以考虑在这里添加，但这可能会改变现有文件结构
                # 为简单起见，我们假设新添加的条目会有ID
                # 或者，可以在加载时为没有ID的条目动态分配（但不保存回文件，除非有更改）
                return loaded_data
        except json.JSONDecodeError:
            logger.error(f"解析JSON文件 {self._mappings_path} 出错。将返回空映射列表。", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"读取映射文件 {self._mappings_path} 时出错。将返回空映射列表。", exc_info=True)
            return []

    def _save_mappings(self):
        """
        将当前内存中的所有映射保存到JSON文件。
        返回 True 表示成功, False 表示失败。
        """
        logger.debug(f"尝试保存 {len(self.mappings)} 条映射到 {self._mappings_path}")
        try:
            with open(self._mappings_path, 'w', encoding='utf-8') as f:
                json.dump(self.mappings, f, ensure_ascii=False, indent=2)
            logger.info(f"映射已成功保存到 {self._mappings_path}")
            return True
        except Exception as e:
            logger.error(f"写入映射文件 {self._mappings_path} 时出错。", exc_info=True)
            return False

    def get_all_mappings(self):
        """
        返回内存中所有映射的列表副本。
        """
        return list(self.mappings) # 返回副本以防止外部直接修改

    def add_mapping(self, original_name, corrected_name, notes=""):
        """
        添加一个新的名称映射。
        original_name: 不规则的原始名称。
        corrected_name: 修正后的规范名称。
        notes: 可选的备注信息。
        返回 True 表示成功添加并保存, False 表示失败或已存在（基于original_name）。
        """
        if not original_name or not corrected_name:
            logger.warning("添加映射失败：原始名称和修正后名称不能为空。")
            return False

        # 检查原始名称是否已存在，避免重复（您可以根据需要调整此逻辑）
        for mapping in self.mappings:
            if mapping.get('original_name') == original_name:
                logger.warning(f"添加映射失败：原始名称 '{original_name}' 已存在映射。")
                return False # 或者根据需要允许重复，或者更新现有条目

        new_mapping = {
            "id": str(uuid.uuid4()), # 为每个映射生成一个唯一ID
            "original_name": original_name,
            "corrected_name": corrected_name,
            "notes": notes
        }
        self.mappings.append(new_mapping)
        logger.info(f"已添加新映射: ID={new_mapping['id']}, 原名='{original_name}', 修正名='{corrected_name}'")
        return self._save_mappings()

    def update_mapping(self, mapping_id, new_original_name, new_corrected_name, new_notes=""):
        """
        根据映射的唯一ID更新一个已存在的映射。
        mapping_id: 要更新的映射的唯一ID。
        new_original_name: 新的原始名称。
        new_corrected_name: 新的修正后名称。
        new_notes: 新的备注。
        返回 True 表示成功更新并保存, False 表示未找到该ID或更新失败。
        """
        if not new_original_name or not new_corrected_name:
            logger.warning("更新映射失败：原始名称和修正后名称不能为空。")
            return False

        for i, mapping in enumerate(self.mappings):
            if mapping.get('id') == mapping_id:
                # 检查更新后的original_name是否与除了当前条目之外的其他条目冲突
                for other_idx, other_mapping in enumerate(self.mappings):
                    if i != other_idx and other_mapping.get('original_name') == new_original_name:
                        logger.warning(f"更新映射失败：新的原始名称 '{new_original_name}' 与ID为 {other_mapping.get('id')} 的条目冲突。")
                        return False

                self.mappings[i]['original_name'] = new_original_name
                self.mappings[i]['corrected_name'] = new_corrected_name
                self.mappings[i]['notes'] = new_notes
                logger.info(f"已更新映射: ID='{mapping_id}', 新原名='{new_original_name}', 新修正名='{new_corrected_name}'")
                return self._save_mappings()
        logger.warning(f"更新映射失败：未找到ID为 '{mapping_id}' 的映射。")
        return False

    def delete_mapping(self, mapping_id):
        """
        根据映射的唯一ID删除一个映射。
        mapping_id: 要删除的映射的唯一ID。
        返回 True 表示成功删除并保存, False 表示未找到该ID或删除失败。
        """
        original_length = len(self.mappings)
        self.mappings = [m for m in self.mappings if m.get('id') != mapping_id]
        if len(self.mappings) < original_length:
            logger.info(f"已删除映射: ID='{mapping_id}'")
            return self._save_mappings()
        else:
            logger.warning(f"删除映射失败：未找到ID为 '{mapping_id}' 的映射。")
            return False

    def _normalize_string(self, text):
        """
        标准化字符串，移除多余空格，统一大小写等。
        """
        if not text or not isinstance(text, str):
            return ""
        # 移除前后空格
        normalized = text.strip()
        # 将多个空格替换为单个空格
        normalized = re.sub(r'\s+', ' ', normalized)
        # 可选：转换为小写进行不区分大小写的比较
        # normalized = normalized.lower()
        return normalized

    def get_corrected_name(self, name_to_check):
        """
        根据提供的原始名称查找对应的修正后名称。
        如果找到匹配的 'original_name'，则返回其 'corrected_name'。
        否则，返回原始的 'name_to_check'。
        """
        if not name_to_check:
            return name_to_check # 或者返回 None，取决于您的偏好
        
        # 记录查询
        logger.debug(f"查询名称映射 (RAW): '{name_to_check}'")
        
        # 标准化输入字符串
        normalized_input = self._normalize_string(name_to_check)
        logger.debug(f"规范化后的查询名称: '{normalized_input}'")
        
        # 精确匹配优先
        for mapping in self.mappings:
            original = mapping.get('original_name', '')
            if original == name_to_check:
                corrected = mapping.get('corrected_name')
                logger.info(f"精确匹配 '{name_to_check}' -> '{corrected}'")
                return corrected
        
        # 标准化匹配（可能处理空格差异等）
        for mapping in self.mappings:
            original = mapping.get('original_name', '')
            normalized_original = self._normalize_string(original)
            
            # 调试每一次比较
            logger.debug(f"比较: 输入='{normalized_input}' vs 映射='{normalized_original}' (原始='{original}')")
            
            if normalized_original == normalized_input:
                corrected = mapping.get('corrected_name')
                logger.info(f"标准化匹配 '{normalized_input}' -> '{corrected}' (原始输入='{name_to_check}', 原始映射='{original}')")
                return corrected
            
        # 不区分大小写匹配
        for mapping in self.mappings:
            original = mapping.get('original_name', '')
            if original.lower() == name_to_check.lower():
                corrected = mapping.get('corrected_name')
                logger.info(f"不区分大小写匹配 '{name_to_check}' -> '{corrected}'")
                return corrected

        logger.debug(f"未找到 '{name_to_check}' 的映射，将使用原始名称。")
        return name_to_check

    def find_mapping_by_id(self, mapping_id):
        """
        根据ID查找映射条目。
        返回找到的映射字典，否则返回None。
        """
        for mapping in self.mappings:
            if mapping.get('id') == mapping_id:
                return mapping
        return None
        
    def dump_all_mappings_debug(self):
        """
        输出所有当前加载的映射到日志，用于诊断目的。
        """
        logger.info(f"当前加载的映射总数: {len(self.mappings)}")
        for i, mapping in enumerate(self.mappings):
            original = mapping.get('original_name', '[空]')
            corrected = mapping.get('corrected_name', '[空]')
            mapping_id = mapping.get('id', '[无ID]')
            logger.info(f"映射 #{i+1}: ID={mapping_id}, 原名='{original}', 修正名='{corrected}'")
        return len(self.mappings)