# Adaptive Recursive Repair Agent (ARR)

An auditable and context-aware auto-repair system that combines static analysis (Ruff) and dynamic unit testing (Pytest) with LLM-powered code generation.

## Features

- **Ruff First Strategy**: Automatically fixes mechanical errors before LLM invocation
- **Active Issue Focus**: Provides LLM only with history related to currently occurring errors
- **Dual-History Management**: Maintains separate histories for LLM efficiency and user auditability
- **Full Audit Logging**: Preserves all attempts and results in TOON format
- **Infinite Loop Prevention**: Detects duplicate patches and signature cycles
- **Atomic File Operations**: Safe patch application with automatic backup and recovery

## Installation

```bash
pip install -e .
```

## Quick Start

```python
from pathlib import Path
from repair_agent import run_repair_session

# Run repair session on a test file
result = run_repair_session(
    target_file=Path("tests/test_example.py"),
    max_retries=5
)

print(f"Result: {result}")  # SUCCESS, MAX_RETRIES_EXCEEDED, or CYCLE_DETECTED
```

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `LLM_API_KEY` | API key for LLM service | Yes | - |
| `LLM_MODEL` | Model identifier (e.g., gpt-4, claude-3) | Yes | - |
| `REPAIR_MAX_RETRIES` | Maximum repair iterations | No | 5 |
| `REPAIR_LOG_LEVEL` | Logging verbosity (DEBUG,INFO,WARNING,ERROR) | No | INFO |
| `REPAIR_LOG_DIR` | Base directory for session logs | No | ./repair_logs |
| `REPAIR_ENABLE_RUFF` | Enable/disable Ruff auto-fix | No | true |
| `LLM_TIMEOUT` | LLM request timeout in seconds | No | 300 |

## Architecture

The system consists of the following modules:

- **StaticFixer**: Ruff-based auto-fix implementation
- **DebuggingContext**: Test execution and error collection
- **HistoryManager**: Dual-history tracking (ContextPruner & SessionRecorder)
- **CycleDetector**: Infinite loop prevention
- **PatchManager**: Safe patch application with backup
- **LLMGateway**: LLM communication interface
- **AgentOrchestrator**: Main pipeline controller

## Session Artifacts

Each repair session generates the following artifacts in `repair_logs/session_{timestamp}/`:

- `iter_{NN}_failure.toon` - Raw error log for iteration N
- `iter_{NN}_patch.toon` - LLM-proposed code patch for iteration N
- `iter_{NN}_context.toon` - Active context sent to LLM
- `full_session_summary.toon` - Complete session summary
- `session_metadata.json` - Session configuration and metrics

## TOON Format

All data exchange between modules uses TOON (Token-Oriented Object Notation) format for efficiency (~40% fewer tokens than JSON).

Example:
```toon
[3] {id, name, status}
1 | Alice | active
2 | Bob | inactive
3 | Charlie | active
```

## Development

Run tests:
```bash
pytest tests/
```

Run linting:
```bash
ruff check src/
black src/
```

## License

MIT
