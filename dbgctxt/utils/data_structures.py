from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ExecutionResult:
    exit_code: int
    total_tests: int
    failed_tests: int
    report_path: Path


@dataclass
class FailureData:
    test_id: str
    source_file: str
    line_number: int
    error_type: str
    error_message: str
    traceback: str
    signature: str


@dataclass
class RichContext:
    failure: FailureData
    related_code: str
    ast_scope: str
    static_errors: List[str]
    deduplication_note: str
    error_class: str
    stack_trace: List[Dict[str, Any]] = field(default_factory=list)
    locals_snapshot: Optional[Dict[str, Any]] = None
    related_symbols: List[Dict[str, str]] = field(default_factory=list)
    import_chain: List[Dict[str, Any]] = field(default_factory=list)
    search_paths: List[Dict[str, Any]] = field(default_factory=list)
    expected_vs_actual: Optional[Dict[str, Any]] = None
    call_context: Optional[Dict[str, Any]] = None
    test_context: Optional[Dict[str, Any]] = None
    missing_resources: List[Dict[str, str]] = field(default_factory=list)
    config_state: Optional[Dict[str, Any]] = None
    missing_vars: List[str] = field(default_factory=list)
    rule_info: Optional[Dict[str, Any]] = None
    suggested_fix: Optional[Dict[str, str]] = None


@dataclass
class StaticMap:
    structure_map: Dict[Path, List[Any]]
    quality_map: Dict[Path, List[Any]]


@dataclass
class FixPayload:
    timestamp: str
    status: str
    message: str
    total_failures: int
    contexts: List[RichContext] = field(default_factory=list)
    root_cause_analysis: Optional[List[Dict[str, Any]]] = None
    fix_suggestions: List[Dict[str, Any]] = field(default_factory=list)
    dead_code_analysis: Optional[Dict[str, Any]] = None


@dataclass
class RootCauseCorrelation:
    failure_id: str
    primary_cause: str
    confidence: float
    secondary_causes: List[Dict[str, float]] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)


@dataclass
class FixSuggestion:
    failure_id: str
    priority: int
    action: str
    effort: str
    confidence: str
    code_diff: Optional[str] = None
    evidence: List[str] = field(default_factory=list)


@dataclass
class DeadCodeAnalysis:
    function_name: str
    file: str
    line: int
    safe_to_remove: bool
    confidence: int
    checks: Dict[str, bool]
    removal_steps: List[str] = field(default_factory=list)
