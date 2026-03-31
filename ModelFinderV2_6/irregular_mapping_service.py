from .operation_result import OperationResult


class IrregularMappingService:
    def __init__(self, irregular_names_model):
        self.irregular_names_model = irregular_names_model

    def list_mappings(self):
        mappings = self.irregular_names_model.get_all_mappings()
        return OperationResult(True, "\u4e0d\u89c4\u5219\u540d\u79f0\u6620\u5c04\u5df2\u52a0\u8f7d", mappings, code="mappings_loaded")

    def add_mapping(self, original_name, corrected_name, notes):
        original_name = (original_name or "").strip()
        corrected_name = (corrected_name or "").strip()
        if not original_name or not corrected_name:
            return OperationResult(
                False,
                "\u539f\u59cb\u540d\u79f0\u548c\u4fee\u6b63\u540d\u79f0\u4e0d\u80fd\u4e3a\u7a7a",
                code="invalid_mapping",
            )

        if self.irregular_names_model.add_mapping(original_name, corrected_name, notes):
            return OperationResult(True, "\u6210\u529f\u6dfb\u52a0\u4e0d\u89c4\u5219\u540d\u79f0\u6620\u5c04", code="mapping_added")
        return OperationResult(
            False,
            "\u65e0\u6cd5\u6dfb\u52a0\u4e0d\u89c4\u5219\u540d\u79f0\u6620\u5c04\uff0c\u8bf7\u68c0\u67e5\u8f93\u5165\u6216\u65e5\u5fd7",
            code="mapping_add_failed",
        )

    def update_mapping(self, mapping_id, original_name, corrected_name, notes):
        original_name = (original_name or "").strip()
        corrected_name = (corrected_name or "").strip()
        if not mapping_id:
            return OperationResult(False, "\u7f3a\u5c11\u6620\u5c04ID", code="missing_mapping_id")
        if not original_name or not corrected_name:
            return OperationResult(
                False,
                "\u539f\u59cb\u540d\u79f0\u548c\u4fee\u6b63\u540d\u79f0\u4e0d\u80fd\u4e3a\u7a7a",
                code="invalid_mapping",
            )

        if self.irregular_names_model.update_mapping(mapping_id, original_name, corrected_name, notes):
            return OperationResult(True, "\u6210\u529f\u66f4\u65b0\u4e0d\u89c4\u5219\u540d\u79f0\u6620\u5c04", code="mapping_updated")
        return OperationResult(
            False,
            "\u65e0\u6cd5\u66f4\u65b0\u4e0d\u89c4\u5219\u540d\u79f0\u6620\u5c04\uff0c\u8bf7\u68c0\u67e5\u8f93\u5165\u6216\u65e5\u5fd7",
            code="mapping_update_failed",
        )

    def delete_mapping(self, mapping_id):
        if not mapping_id:
            return OperationResult(False, "\u7f3a\u5c11\u6620\u5c04ID", code="missing_mapping_id")

        if self.irregular_names_model.delete_mapping(mapping_id):
            return OperationResult(True, "\u6210\u529f\u5220\u9664\u4e0d\u89c4\u5219\u540d\u79f0\u6620\u5c04", code="mapping_deleted")
        return OperationResult(
            False,
            "\u65e0\u6cd5\u5220\u9664\u4e0d\u89c4\u5219\u540d\u79f0\u6620\u5c04\uff0c\u8bf7\u68c0\u67e5\u8f93\u5165\u6216\u65e5\u5fd7",
            code="mapping_delete_failed",
        )
