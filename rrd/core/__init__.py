"""
RRD Core - Reusable components for Recursive Repair Development

Extracted from aar/ prototype for building RRD implementation on Spec Kit.
"""

# TOON Utilities
from core.toon_utils import (
    ToonParser,
    ToonEncoder,
    ToonSerializer,
    encode_toon,
    parse_toon,
    dumps,
    dump,
    parse_toon_file,
    write_toon_file,
)

# History Management (Dual-History Architecture)
from core.history_manager import (
    ContextPruner,
    SessionRecorder,
    HistoryManager,
)

# Data Types
from core.data_types import (
    FailureSignature,
    FixReport,
    FailurePayload,
    PatchToon,
    ActiveContext,
    SessionSummary,
    CycleDetectionState,
    Config,
)

# Cycle Detection
from core.cycle_detector import CycleDetector

# Patch Management
from core.patch_manager import PatchManager

# Configuration
from core.config_loader import RRDConfig, load_rrd_config

__all__ = [
    # TOON
    "ToonParser",
    "ToonEncoder",
    "ToonSerializer",
    "encode_toon",
    "parse_toon",
    "dumps",
    "dump",
    "parse_toon_file",
    "write_toon_file",
    # History
    "ContextPruner",
    "SessionRecorder",
    "HistoryManager",
    # Data Types
    "FailureSignature",
    "FixReport",
    "FailurePayload",
    "PatchToon",
    "ActiveContext",
    "SessionSummary",
    "CycleDetectionState",
    "Config",
    # Cycle Detection
    "CycleDetector",
    # Patch Management
    "PatchManager",
    # Configuration
    "RRDConfig",
    "load_rrd_config",
]

__version__ = "1.0.0"
__author__ = "RRD Development Team"
__description__ = "Core components for Recursive Repair Development"
