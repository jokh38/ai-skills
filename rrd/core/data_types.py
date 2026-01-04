"""Data type definitions for the repair agent"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, FrozenSet


@dataclass
class FailureSignature:
    file_path: str
    function_name: str
    error_type: str

    def __str__(self) -> str:
        return f"{self.file_path}::{self.function_name}::{self.error_type}"

    def __hash__(self) -> int:
        return hash((self.file_path, self.function_name, self.error_type))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FailureSignature):
            return False
        return (
            self.file_path == other.file_path
            and self.function_name == other.function_name
            and self.error_type == other.error_type
        )


@dataclass
class FixReport:
    target_path: str
    fixes_applied: List[str]
    summary: str
    success: bool


@dataclass
class FailurePayload:
    failures: List[FailureSignature]
    traceback_snippets: Dict[str, str]
    context: Dict[str, Any]


@dataclass
class PatchToon:
    file_path: str
    line_range: Tuple[int, int]
    old_code: str
    new_code: str

    def __hash__(self) -> int:
        return hash((self.file_path, self.line_range, self.old_code, self.new_code))


@dataclass
class ActiveContext:
    active_history: List[Dict[str, Any]]
    current_failures: List[FailureSignature]
    iteration: int
    current_file: Optional[str] = None
    history: List[FailureSignature] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionSummary:
    session_id: str
    timestamp: str
    total_iterations: int
    status: str
    success_rate: float
    phases_completed: List[str] = field(default_factory=list)
    failures: List[FailureSignature] = field(default_factory=list)
    workspace: str = ""


@dataclass
class CycleDetectionState:
    patch_hash_history: List[int] = field(default_factory=list)
    signature_history: List[FrozenSet[str]] = field(default_factory=list)
    last_patch_hash: Optional[int] = None
    last_patch: Optional[PatchToon] = None

    def reset(self) -> None:
        self.patch_hash_history.clear()
        self.signature_history.clear()
        self.last_patch_hash = None
        self.last_patch = None


class Config:
    max_retries: int = 5
    ruff_enabled: bool = True
    ruff_rules: str = "E,F,W"
    log_level: str = "INFO"
    cycle_window: int = 4
    toon_delimiter: str = "|"
    atomic_write_enabled: bool = True
    backup_before_patch: bool = True
    llm_timeout_seconds: int = 300
    max_toon_retries: int = 3
    enable_key_folding: bool = False

    @classmethod
    def from_env(cls) -> "Config":
        import os

        config = cls()
        if "REPAIR_MAX_RETRIES" in os.environ:
            config.max_retries = int(os.environ["REPAIR_MAX_RETRIES"])
        if "REPAIR_LOG_LEVEL" in os.environ:
            config.log_level = os.environ["REPAIR_LOG_LEVEL"]
        if "REPAIR_ENABLE_RUFF" in os.environ:
            config.ruff_enabled = os.environ["REPAIR_ENABLE_RUFF"].lower() == "true"
        if "LLM_TIMEOUT" in os.environ:
            config.llm_timeout_seconds = int(os.environ["LLM_TIMEOUT"])
        return config
