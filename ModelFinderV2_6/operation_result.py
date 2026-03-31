from dataclasses import dataclass
from typing import Any


@dataclass
class OperationResult:
    success: bool
    message: str = ""
    data: Any = None
