from .operation_result import OperationResult


class IrregularMappingService:
    def __init__(self, irregular_names_model):
        self.irregular_names_model = irregular_names_model

    def list_mappings(self):
        return self.irregular_names_model.get_all_mappings()

    def add_mapping(self, original_name, corrected_name, notes):
        if self.irregular_names_model.add_mapping(original_name, corrected_name, notes):
            return OperationResult(True, "成功添加不规则名称映射。")
        return OperationResult(False, "无法添加不规则名称映射，请检查输入或日志。")

    def update_mapping(self, mapping_id, original_name, corrected_name, notes):
        if self.irregular_names_model.update_mapping(mapping_id, original_name, corrected_name, notes):
            return OperationResult(True, "成功更新不规则名称映射。")
        return OperationResult(False, "无法更新不规则名称映射，请检查输入或日志。")

    def delete_mapping(self, mapping_id):
        if self.irregular_names_model.delete_mapping(mapping_id):
            return OperationResult(True, "成功删除不规则名称映射。")
        return OperationResult(False, "无法删除不规则名称映射，请检查输入或日志。")
