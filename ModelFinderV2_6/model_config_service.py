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
        snapshot = ModelConfigSnapshot(
            node_types=self.config_manager.get_model_node_types(),
            node_indices=self.config_manager.get_node_model_indices(),
            extensions=self.config_manager.get_model_extensions(),
        )
        return OperationResult(True, "\u6a21\u578b\u914d\u7f6e\u5df2\u52a0\u8f7d", snapshot, code="snapshot_loaded")

    def add_model_node_type(self, node_type):
        normalized = (node_type or "").strip()
        if not normalized:
            return OperationResult(
                False,
                "\u8282\u70b9\u7c7b\u578b\u4e0d\u80fd\u4e3a\u7a7a",
                code="invalid_node_type",
            )

        success = self.config_manager.add_model_node_type(normalized)
        if success:
            return OperationResult(
                True,
                f"\u5df2\u6dfb\u52a0\u8282\u70b9\u7c7b\u578b: {normalized}",
                code="node_type_added",
            )
        return OperationResult(
            False,
            f"\u8282\u70b9\u7c7b\u578b '{normalized}' \u5df2\u5b58\u5728",
            code="node_type_exists",
        )

    def delete_model_node_type(self, node_type):
        success = self.config_manager.remove_model_node_type(node_type)
        if success:
            return OperationResult(
                True,
                f"\u5df2\u5220\u9664\u8282\u70b9\u7c7b\u578b: {node_type}",
                code="node_type_deleted",
            )
        return OperationResult(
            False,
            f"\u5220\u9664\u8282\u70b9\u7c7b\u578b\u5931\u8d25: {node_type}",
            code="node_type_delete_failed",
        )

    def add_node_model_index(self, node_type, index):
        try:
            parsed_index = int(index)
        except ValueError:
            return OperationResult(False, "\u7d22\u5f15\u5fc5\u987b\u662f\u6574\u6570", code="invalid_index")

        success = self.config_manager.add_node_model_index(node_type, [parsed_index])
        if success:
            return OperationResult(
                True,
                f"\u5df2\u6dfb\u52a0\u8282\u70b9\u7d22\u5f15\u6620\u5c04: {node_type} -> {parsed_index}",
                code="node_index_added",
            )
        return OperationResult(
            False,
            f"\u6dfb\u52a0\u8282\u70b9\u7d22\u5f15\u6620\u5c04\u5931\u8d25: {node_type} -> {parsed_index}",
            code="node_index_add_failed",
        )

    def delete_node_model_index(self, node_type, index=None):
        try:
            parsed_index = int(index) if index is not None else None
        except ValueError:
            return OperationResult(False, "\u7d22\u5f15\u5fc5\u987b\u662f\u6574\u6570", code="invalid_index")

        success = self.config_manager.remove_node_model_index(node_type, parsed_index)
        if success:
            message = f"\u5df2\u5220\u9664\u8282\u70b9\u7d22\u5f15\u6620\u5c04: {node_type}"
            if parsed_index is not None:
                message += f" -> {parsed_index}"
            return OperationResult(True, message, code="node_index_deleted")
        return OperationResult(
            False,
            "\u5220\u9664\u8282\u70b9\u7d22\u5f15\u6620\u5c04\u5931\u8d25",
            code="node_index_delete_failed",
        )

    def add_model_extension(self, extension):
        normalized = (extension or "").strip()
        if not normalized:
            return OperationResult(False, "\u6269\u5c55\u540d\u4e0d\u80fd\u4e3a\u7a7a", code="invalid_extension")

        if not normalized.startswith("."):
            normalized = "." + normalized

        success = self.config_manager.add_model_extension(normalized)
        if success:
            return OperationResult(
                True,
                f"\u5df2\u6dfb\u52a0\u6a21\u578b\u6269\u5c55\u540d: {normalized}",
                code="extension_added",
            )
        return OperationResult(
            False,
            f"\u6a21\u578b\u6269\u5c55\u540d '{normalized}' \u5df2\u5b58\u5728",
            code="extension_exists",
        )

    def delete_model_extension(self, extension):
        success = self.config_manager.remove_model_extension(extension)
        if success:
            return OperationResult(
                True,
                f"\u5df2\u5220\u9664\u6a21\u578b\u6269\u5c55\u540d: {extension}",
                code="extension_deleted",
            )
        return OperationResult(
            False,
            f"\u5220\u9664\u6a21\u578b\u6269\u5c55\u540d\u5931\u8d25: {extension}",
            code="extension_delete_failed",
        )
