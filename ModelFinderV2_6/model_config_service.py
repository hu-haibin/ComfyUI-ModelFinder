from dataclasses import dataclass

from .operation_result import OperationResult


@dataclass
class ModelConfigSnapshot:
    node_types: list
    node_indices: dict
    extensions: list


class ModelConfigService:
    def __init__(self, config_manager):
        self.config_manager = config_manager

    def get_snapshot(self):
        return ModelConfigSnapshot(
            node_types=self.config_manager.get_model_node_types(),
            node_indices=self.config_manager.get_node_model_indices(),
            extensions=self.config_manager.get_model_extensions(),
        )

    def add_model_node_type(self, node_type):
        normalized = (node_type or "").strip()
        if not normalized:
            return OperationResult(False, "节点类型不能为空")

        success = self.config_manager.add_model_node_type(normalized)
        if success:
            return OperationResult(True, f"已添加节点类型: {normalized}")
        return OperationResult(False, f"节点类型 '{normalized}' 已存在")

    def delete_model_node_type(self, node_type):
        success = self.config_manager.remove_model_node_type(node_type)
        if success:
            return OperationResult(True, f"已删除节点类型: {node_type}")
        return OperationResult(False, f"删除节点类型失败: {node_type}")

    def add_node_model_index(self, node_type, index):
        try:
            parsed_index = int(index)
        except ValueError:
            return OperationResult(False, "索引必须是整数")

        success = self.config_manager.add_node_model_index(node_type, [parsed_index])
        if success:
            return OperationResult(True, f"已添加节点索引映射: {node_type} -> {parsed_index}")
        return OperationResult(False, f"添加节点索引映射失败: {node_type} -> {parsed_index}")

    def delete_node_model_index(self, node_type, index=None):
        try:
            parsed_index = int(index) if index is not None else None
        except ValueError:
            return OperationResult(False, "索引必须是整数")

        success = self.config_manager.remove_node_model_index(node_type, parsed_index)
        if success:
            message = f"已删除节点索引映射: {node_type}"
            if parsed_index is not None:
                message += f" -> {parsed_index}"
            return OperationResult(True, message)
        return OperationResult(False, "删除节点索引映射失败")

    def add_model_extension(self, extension):
        normalized = (extension or "").strip()
        if not normalized:
            return OperationResult(False, "扩展名不能为空")

        if not normalized.startswith("."):
            normalized = "." + normalized

        success = self.config_manager.add_model_extension(normalized)
        if success:
            return OperationResult(True, f"已添加模型扩展名: {normalized}")
        return OperationResult(False, f"模型扩展名 '{normalized}' 已存在")

    def delete_model_extension(self, extension):
        success = self.config_manager.remove_model_extension(extension)
        if success:
            return OperationResult(True, f"已删除模型扩展名: {extension}")
        return OperationResult(False, f"删除模型扩展名失败: {extension}")
