from .operation_result import OperationResult


class DependencyInstallPlanner:
    ALLOWED_SAFE_CONCLUSIONS = {"safe", "safe_with_policy"}

    def build_execution_plan(self, packages, preflight_result, *, safe_only=False) -> OperationResult:
        rows_by_id = {item["id"]: item for item in (preflight_result or {}).get("rows", [])}
        executable_packages = []
        blocked_packages = []
        skipped_packages = []

        for package in packages or []:
            row = rows_by_id.get(package["id"], {})
            conclusion = row.get("conclusion", "warning")
            if conclusion == "blocked":
                blocked_packages.append(
                    {
                        "id": package["id"],
                        "title": package.get("title", package["id"]),
                        "reasons": list(row.get("reasons") or []),
                    }
                )
                continue

            if safe_only and conclusion not in self.ALLOWED_SAFE_CONCLUSIONS:
                skipped_packages.append(
                    {
                        "id": package["id"],
                        "title": package.get("title", package["id"]),
                        "conclusion": conclusion,
                    }
                )
                continue

            package_copy = dict(package)
            package_copy["dependency_strategy"] = row.get("strategy", "install")
            package_copy["dependency_conclusion"] = conclusion
            executable_packages.append(package_copy)

        if blocked_packages and not safe_only:
            return OperationResult(
                False,
                "依赖预检发现阻断项，请先处理或仅安装安全项。",
                {
                    "executable_packages": executable_packages,
                    "blocked_packages": blocked_packages,
                    "skipped_packages": skipped_packages,
                },
                code="dependency_execution_blocked",
            )

        if not executable_packages:
            return OperationResult(
                False,
                "当前没有可执行的安装项。",
                {
                    "executable_packages": [],
                    "blocked_packages": blocked_packages,
                    "skipped_packages": skipped_packages,
                },
                code="dependency_execution_empty",
            )

        return OperationResult(
            True,
            "Dependency execution plan prepared.",
            {
                "executable_packages": executable_packages,
                "blocked_packages": blocked_packages,
                "skipped_packages": skipped_packages,
            },
            code="dependency_execution_ready",
        )
