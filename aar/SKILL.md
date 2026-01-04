# ARR Skill - Adaptive Recursive Repair

## Overview

The ARR (Adaptive Recursive Repair) skill is an automated Python code repair system that combines static analysis, dynamic testing, and LLM-powered reasoning to fix failing tests.

## Description

ARR automatically repairs failing Python tests through an intelligent feedback loop:
1. Static analysis (Ruff) eliminates mechanical errors
2. Dynamic testing (Pytest) identifies remaining failures
3. LLM reasoning generates targeted fixes
4. Cycle detection prevents infinite loops
5. Full audit trail for complete traceability

All data exchange uses TOON (Token-Oriented Object Notation) for ~40% fewer tokens than JSON.

## When to Use This Skill

Use the ARR skill when:
- You have failing Python unit tests that need automated repair
- You want to apply static analysis + LLM reasoning to fix code
- You need a systematic approach to eliminate test failures
- You want complete audit trails of repair attempts

Do NOT use this skill when:
- You just need to run tests without repair
- Working with non-Python code
- Tests are passing already
- You need manual control over each fix

## Usage

### Basic Usage

```bash
# From Claude Code
/arr repair path/to/test_file.py
```

### With Options

```bash
# Custom retry limit
/arr repair tests/test_api.py --max-retries 10

# Debug mode
/arr repair tests/test_api.py --log-level DEBUG

# Custom log directory
/arr repair tests/test_api.py --log-dir ./my_logs

# Disable Ruff pre-processing
/arr repair tests/test_api.py --disable-ruff
```

### List Sessions

```bash
# Show all repair sessions
/arr list

# Show status of latest session
/arr status
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `repair <test_file>` | command | - | Start repair process on test file |
| `--max-retries N` | int | 5 | Maximum repair iterations |
| `--log-level LEVEL` | str | INFO | Logging verbosity (DEBUG/INFO/WARNING/ERROR) |
| `--log-dir PATH` | str | ./repair_logs | Custom log directory |
| `--disable-ruff` | flag | false | Skip Ruff auto-fix pre-processing |

## Environment Variables

Required:
- `LLM_API_KEY`: API key for LLM service
- `LLM_MODEL`: Model identifier (e.g., gpt-4, claude-3)

Optional:
- `REPAIR_MAX_RETRIES`: Default max retries (default: 5)
- `REPAIR_LOG_LEVEL`: Default log level (default: INFO)
- `REPAIR_LOG_DIR`: Base log directory (default: ./repair_logs)
- `LLM_TIMEOUT`: LLM request timeout in seconds (default: 300)
- `REPAIR_ENABLE_RUFF`: Enable/disable Ruff (default: true)

## Output

Each repair session creates a timestamped directory with:

```
repair_logs/
└── session_20251231_143052/
    ├── session_metadata.json      # Configuration and metrics
    ├── iter_01_failure.toon      # Test failures (TOON format)
    ├── iter_01_patch.toon        # LLM-proposed patches
    ├── iter_01_context.toon      # Context sent to LLM
    ├── full_session_summary.toon # Complete audit log
    └── backup_*.py              # Source file backups
```

## Status Codes

| Code | Meaning |
|------|---------|
| SUCCESS | All tests passed |
| MAX_RETRIES_EXCEEDED | Hit iteration limit |
| CYCLE_DETECTED | Duplicate patch or signature cycle |
| SESSION_INIT_ERROR | Failed to create session |
| TEST_EXECUTION_ERROR | Pytest failed to run |
| LLM_COMMUNICATION_ERROR | LLM request failed |
| PATCH_APPLY_ERROR | Failed to apply patch |

## Examples

### Example 1: Basic Repair

```bash
/arr repair sample_project/tests/test_math.py
```

Output:
```
[ARR] Starting repair session for test_math.py
[ARR] Running Ruff auto-fix...
[ARR] Running tests...
[ARR] Found 3 failures, requesting LLM fix...
[ARR] Applied patch, re-testing...
[ARR] SUCCESS: All tests passed after 2 iterations
[ARR] Session log: repair_logs/session_20251231_143052/
```

### Example 2: Debug Mode with Custom Retries

```bash
/arr repair tests/test_api.py --max-retries 10 --log-level DEBUG
```

### Example 3: Check Session Status

```bash
/arr status
```

Output:
```
Latest Session: session_20251231_143052
Status: SUCCESS
Iterations: 2
Tests Fixed: 3
Duration: 45.2s
Log: repair_logs/session_20251231_143052/
```

## Key Features

- **Strict TOON I/O**: All data exchange in compact TOON format
- **Dual-History**: Pruned context for LLM, full audit for users
- **Active Issue Focus**: Only unresolved errors sent to LLM
- **Safe Operations**: Atomic writes, backups, cycle detection
- **Complete Audit**: Full traceability of all attempts

## TOON Format

TOON (Token-Oriented Object Notation) is a compact format optimized for LLM input:

```toon
[3] {id, name, status}
1 | Alice | active
2 | Bob | inactive
3 | Charlie | active
```

Benefits:
- ~40% fewer tokens than JSON
- Easier for LLMs to parse
- Human-readable

See: https://github.com/toon-format/toon

## Troubleshooting

**Module not found:**
```bash
# Ensure dependencies are installed
cd /home/vscode/.claude/skills/ARR
pip install -r src/requirements.txt
pip install -e src/
```

**LLM connection issues:**
```bash
# Verify environment variables
echo $LLM_API_KEY
echo $LLM_MODEL
```

**Ruff not found:**
```bash
pip install ruff
```

## Related Documentation

- [README.md](README.md) - Complete system overview
- [spec.md](spec.md) - Architecture and specifications
- [STRUCTURE.md](STRUCTURE.md) - File organization
- [USAGE.md](USAGE.md) - Detailed usage guide

## Dependencies

- Python ≥3.8
- ruff ≥0.1.0 (static analysis)
- pytest ≥7.0.0 (test execution)
- pydantic ≥2.0.0 (data validation)

## Architecture

```
[Test File] → [Ruff Auto-fix] → [Pytest] → [Failures?]
                                               │
                                               ├─→ Pass → [DONE]
                                               │
                                               └─→ Fail → [TOON Payload]
                                                          │
                                                          ↓
                                                      [LLM API]
                                                          │
                                                          ↓
                                                   [TOON Patch]
                                                          │
                                                          ↓
                                                   [Apply Patch]
                                                          │
                                                          └─→ (loop back to Ruff)
```

## Safety Features

- **Atomic File Operations**: Uses temp files + rename
- **Cycle Prevention**: Detects duplicate patches and loops
- **Backup Safety**: Creates backups before patching
- **Session Isolation**: Each session in separate directory
- **Audit Trail**: Complete preservation of all attempts

## License

See project repository for licensing information.
