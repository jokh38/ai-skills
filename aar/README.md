# ARR - Adaptive Recursive Repair Agent

An auditable, context-aware auto-repair system for Python code that combines static analysis (Ruff) and dynamic unit testing (Pytest) with LLM-powered reasoning.

## Overview

ARR automatically repairs failing Python tests through an intelligent feedback loop:

1. **Static Analysis**: Ruff auto-fix eliminates mechanical errors (lint, imports)
2. **Dynamic Testing**: Pytest identifies remaining failures
3. **LLM Reasoning**: AI generates targeted fixes based on error context
4. **Cycle Prevention**: Detects and prevents infinite loops
5. **Full Audit**: Complete traceability of all repair attempts

### Key Features

- **Strict TOON I/O**: All data exchange uses Token-Oriented Object Notation (~40% fewer tokens than JSON)
- **Dual-History Management**: Pruned context for LLM efficiency, full audit trail for transparency
- **Active Issue Focus**: Only unresolved errors are sent to LLM, reducing token usage
- **Safe Operations**: Atomic file writes, backup creation, and cycle detection

## Quick Start

### Installation

```bash
cd ARR/

# Install dependencies
pip install -r src/requirements.txt

# Install package in development mode
pip install -e src/
```

### Environment Setup

```bash
# Required
export LLM_API_KEY="your-api-key"
export LLM_MODEL="gpt-4"  # or claude-3, etc.

# Optional
export REPAIR_MAX_RETRIES=5
export REPAIR_LOG_LEVEL=INFO
export REPAIR_LOG_DIR=./repair_logs
export REPAIR_ENABLE_RUFF=true
```

### Usage

```bash
# Run repair on a test file
python arr.py repair sample_project/tests/test_math.py

# With custom options
python arr.py repair sample_project/tests/test_math.py --max-retries 10 --log-level DEBUG

# List all repair sessions
python arr.py list

# Show status of latest session
python arr.py status
```

After installation via `pip install -e src/`, you can also use:
```bash
arr repair tests/test_example.py
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            EXECUTION LOOP                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   [Start] ──► [Static Fixer (Ruff)] ──► [Test Runner (Pytest)]             │
│                        ▲                        │                           │
│                        │                        ├──► Pass ──► [FINISH]      │
│                        │                        │                           │
│                        │                        └──► Fail                   │
│                        │                               │                    │
│                        │                               ▼                    │
│   [Apply Patch] ◄── [LLM Gateway] ◄── [Payload Builder]                    │
│                                              ▲                              │
│                                              │                              │
│                              ┌───────────────┴───────────────┐              │
│                              │      HISTORY LOGIC            │              │
│                              │                               │              │
│                              │  [Debugging Context Engine]   │              │
│                              │            │                  │              │
│                              │            ▼                  │              │
│                              │    [History Manager]          │              │
│                              │      /          \             │              │
│                              │     /            \            │              │
│                              │ [Archive]    [Filter]         │              │
│                              │     │            │            │              │
│                              │     ▼            ▼            │              │
│                              │ [Session    [Context         │              │
│                              │  Recorder]   Pruner]          │              │
│                              │     │            │            │              │
│                              │     ▼            └────────────┼──► To LLM   │
│                              │ [Log Files]                   │              │
│                              └───────────────────────────────┘              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Core Modules

- **`static_fixer`**: Pre-LLM mechanical error elimination using Ruff
- **`debugging_context`**: Test execution and TOON-formatted error collection
- **`history_manager`**: Dual-history tracking (ContextPruner for LLM, SessionRecorder for audit)
- **`cycle_detector`**: Infinite loop prevention (duplicate patches, signature cycles)
- **`patch_manager`**: Safe patch application with atomic writes and backups
- **`agent_orchestrator`**: Main pipeline controller (includes LLMAdapter using tools/LLM_api/llm_client.py)

## Session Artifacts

Each repair session creates a timestamped directory with complete audit trail:

```
repair_logs/
└── session_20251231_143052/
    ├── session_metadata.json      # Session configuration and metrics
    ├── iter_01_failure.toon      # Test failures in TOON format
    ├── iter_01_patch.toon        # LLM-proposed code patch
    ├── iter_01_context.toon      # Active context sent to LLM
    ├── iter_02_failure.toon
    ├── full_session_summary.toon # Complete audit log (real-time)
    └── backup_*.py              # Source file backups
```

## Key Concepts

### Failure Signature

Unique error identifier (line numbers excluded as they change):
- Format: `{file_path}::{function_name}::{error_type}`
- Example: `tests/test_api.py::test_login::AssertionError`

### TOON Format

Compact data format for LLM communication:
```toon
[3] {id, name, status}
1 | Alice | active
2 | Bob | inactive
3 | Charlie | active
```

See [spec.md Appendix A](spec.md#appendix-a-toon-format-reference) for details.

### Dual-History Architecture

**LLM View (Active Context)**: Only unresolved errors, filtered for efficiency
**User View (Audit Log)**: Complete history including all attempts and pruned issues

## Configuration

### Environment Variables

| Variable | Type | Default | Description | Required |
|----------|------|---------|-------------|----------|
| `LLM_API_KEY` | string | - | API key for LLM service | Yes |
| `LLM_MODEL` | string | - | Model identifier (gpt-4, claude-3, etc.) | Yes |
| `REPAIR_MAX_RETRIES` | int | 5 | Maximum repair iterations | No |
| `REPAIR_LOG_LEVEL` | str | INFO | Logging verbosity | No |
| `REPAIR_LOG_DIR` | str | ./repair_logs | Base directory for session logs | No |
| `LLM_TIMEOUT` | int | 300 | LLM request timeout in seconds | No |
| `REPAIR_ENABLE_RUFF` | bool | true | Enable/disable Ruff auto-fix | No |

### CLI Options

```bash
--max-retries N       Maximum repair iterations (default: 5)
--log-level LEVEL     Logging verbosity: DEBUG, INFO, WARNING, ERROR
--log-dir PATH        Custom log directory
--disable-ruff        Skip Ruff pre-processing
```

## Error Handling

ARR includes robust error handling with specific strategies for different failure modes:

- **LLM Timeout**: Retry with increased timeout
- **TOON Validation**: Retry with format hints, fallback to plain diff
- **Patch Application**: Restore from backup on failure
- **Cycle Detection**: Terminate session with detailed report
- **Test Execution**: Retry with verbose output

See [spec.md Section 7](spec.md#error-handling-strategy) for complete error handling matrix.

## Troubleshooting

**Module not found errors:**
```bash
# Use the arr.py script instead of installed arr command
python arr.py repair tests/test_example.py
```

**LLM connection issues:**
```bash
# Verify API key is set
echo $LLM_API_KEY
echo $LLM_MODEL
```

**Ruff not found:**
```bash
pip install ruff
```

## Documentation

- **[spec.md](spec.md)** - Complete system specification (architecture, data structures, modules, constraints)
- **[STRUCTURE.md](STRUCTURE.md)** - File structure, import organization, entry points
- **[USAGE.md](USAGE.md)** - Detailed usage guide, examples, troubleshooting

## Project Structure

```
ARR/
├── spec.md                          # System specification
├── STRUCTURE.md                    # File organization
├── USAGE.md                        # Quick start guide
├── README.md                       # This file
├── arr.py                          # Main CLI entry point
├── demo.py                         # Demo script
├── src/                            # Source directory
│   ├── cli.py                      # CLI implementation
│   ├── agent_orchestrator.py       # Main controller
│   └── modules/                    # Core modules
│       ├── data_types.py           # Data structures
│       ├── toon_utils.py           # TOON parser/encoder
│       ├── static_fixer.py         # Ruff integration
│       ├── debugging_context.py    # Pytest integration
│       ├── cycle_detector.py       # Loop prevention
│       ├── history_manager.py      # Dual-history tracking
│       ├── patch_manager.py        # Safe patch application
├── sample_project/                 # Sample project for testing
└── tools/                         # External tool integrations
```

## Safety & Constraints

- **Atomic File Operations**: Uses `.tmp` + `rename` to prevent corruption
- **Cycle Prevention**: Detects duplicate patches and signature cycles (A→B→A patterns)
- **Backup Safety**: Always creates backup before patch application
- **Session Isolation**: Each session in separate timestamped directory
- **Audit Trail**: Complete preservation of all repair attempts

## Status Codes

| Code | Description |
|------|-------------|
| SUCCESS | All tests passed, repair complete |
| MAX_RETRIES_EXCEEDED | Maximum iteration limit reached |
| CYCLE_DETECTED | Duplicate patch or signature cycle detected |
| SESSION_INIT_ERROR | Failed to create session directory |
| TEST_EXECUTION_ERROR | Pytest failed to run |
| LLM_COMMUNICATION_ERROR | LLM request failed after retries |
| PATCH_APPLY_ERROR | Failed to apply patch to source file |

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| ruff | ≥0.1.0 | Static analysis and auto-fix |
| pytest | ≥7.0.0 | Test execution |
| pydantic | ≥2.0.0 | Data validation |

## License

See project repository for licensing information.

## TOON Reference

TOON (Token-Oriented Object Notation) is a compact data format optimized for LLM input. Full specification: https://github.com/toon-format/toon

**Syntax:**
- `[N]` declares array size
- `{field1, field2}` declares column headers (once per table)
- Values separated by `|` pipes
- Indentation for nesting

**Example:**
```toon
[2] {id, name, status}
1 | Alice | active
2 | Bob | inactive
```
