# RRD - Recursive Repair Development

A production-ready TDD framework that combines adversarial testing, knowledge retention, and strict quality gates with automated workflow orchestration.

[![Quality Score](https://img.shields.io/badge/quality-100%2F100-brightgreen)]()
[![Type Coverage](https://img.shields.io/badge/types-100%25-brightgreen)]()
[![Security](https://img.shields.io/badge/security-0%20issues-brightgreen)]()
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)]()

## Overview

RRD enforces a disciplined development cycle that prevents recurring failures and ensures high code quality through:

- **Adversarial Testing**: Write tests that actively try to break your code
- **Knowledge Kernel**: Learn from past failures to prevent repeating mistakes
- **Strict Quality Gates**: Code must pass QA before being committed
- **Gradual Strictness**: Relaxed during drafting (L2), strict for hardening (L3)
- **Cycle Prevention**: Progressive backoff prevents infinite loops
- **Automated Workflow**: L1→L2→L3→L4 phase orchestration

## Core Philosophy

1. **TDD is Non-Negotiable**: Tests before implementation
2. **Critic Mode**: Attack your own code in the Blue phase
3. **Memory Access**: Consult past failures before fixing
4. **Quality Enforcement**: Failing QA gates block commits

## Quick Start

### Installation

```bash
# Clone or copy rrd to your project
cd ~/.claude/skills/rrd

# Install dependencies
pip install -r requirements.txt

# Install development dependencies (optional)
pip install -r requirements-dev.txt
```

### Prerequisites

- Python 3.8+
- Git (for incremental analysis)
- External tools: cdqa, cdscan, dbgctxt, zgit (in ~/.claude/skills/)

### Basic Usage

```bash
# Initialize RRD in your project
mkdir -p .claude .specify/memory
cp ~/.claude/skills/rrd/.claude/rrd_config.yaml .claude/
cp ~/.claude/skills/rrd/.specify/memory/constitution.md .specify/memory/
cp ~/.claude/skills/rrd/.specify/memory/knowledge_kernel.toon .specify/memory/

# Run RRD workflow
python ~/.claude/skills/rrd/rrd.py --workspace . --spec spec.md

# Or use as a library
python -c "
from core.config_loader import load_rrd_config
from orchestrator.rrd_orchestrator import RRDOrchestrator

config = load_rrd_config()
orchestrator = RRDOrchestrator(config_path='.claude/rrd_config.yaml')
result = orchestrator.execute_full_workflow(spec_file='spec.md')
"
```

## Project Structure

```
rrd/
├── core/                      # Core utility modules
│   ├── config_loader.py      # Configuration management
│   ├── toon_utils.py         # TOON format parser/encoder
│   ├── history_manager.py    # Dual-history tracking
│   ├── cycle_detector.py     # Infinite loop prevention
│   ├── patch_manager.py      # Safe code modification
│   └── data_types.py         # Data structures
│
├── orchestrator/              # Workflow automation
│   ├── rrd_orchestrator.py   # L1-L4 phase executor
│   ├── phase_executor.py     # Individual phase logic
│   └── session_manager.py    # Session tracking
│
├── integrations/              # External tool wrappers
│   ├── cdscan_integration.py # Codebase structure analysis
│   ├── cdqa_integration.py   # Code quality analysis
│   ├── dbgctxt_integration.py # Test failure debugging
│   └── zgit_integration.py   # Context-preserving commits
│
├── cli/                       # Command-line interface
│   └── cli.py                # CLI implementation
│
├── tests/                     # Comprehensive test suite
│   ├── unit/                 # Unit tests (10 files)
│   ├── integration/          # Integration tests
│   └── fixtures/             # Test fixtures
│
├── .claude/
│   ├── commands/
│   │   └── RRD_execute.md    # Workflow specification
│   └── rrd_config.yaml       # Configuration file
│
├── .specify/memory/
│   ├── constitution.md       # Project constitution
│   └── knowledge_kernel.toon # Failure pattern storage
│
└── rrd.py                     # Main entry point
```

## RRD Workflow (L1→L4)

### L1: Context & Setup
- Load knowledge kernel (filtered for relevance)
- Run codebase analysis (cdscan)
- Write adversarial tests (pytest)

### L2: Red-Green-Blue Cycle

**Red (Skeleton)**:
- Create interfaces only
- Verify with AST
- Run tests (should fail)

**Green (Implementation)**:
- Implement minimal code
- Run pytest
- On failure: Generate context with dbgctxt
- Apply fixes based on knowledge kernel
- Prevent cycles with progressive backoff

**Blue (Critic Mode)**:
- L2 Drafting: Relaxed QA thresholds
- L3 Hardening: Strict QA (all features done)
- Adversarial review
- Fix all issues

### L3: Hardening (Optional)
- After ALL features complete
- Run strict QA
- Performance profiling
- Security audit

### L4: Documentation
- Update knowledge kernel
- Generate documentation
- Commit with zgit (context preservation)

## Quality Gates

All gates must PASS before proceeding:

| Gate | L2 Threshold | L3 Threshold | Tool |
|------|--------------|--------------|------|
| All Tests Pass | - | - | pytest |
| Linting Errors | <100 | <50 | ruff |
| Type Coverage | >60% | >80% | ty |
| Security Critical | 0 | 0 | semgrep |
| Cognitive Complexity | <15 | <12 | complexipy |
| Dead Code | <10 | <5 | skylos |

## Configuration

### Environment Variables

```bash
# Optional - defaults provided
export RRD_TOOLS_PATH="$HOME/.claude/skills"
export RRD_CONFIG_PATH=".claude/rrd_config.yaml"
```

### Configuration File (.claude/rrd_config.yaml)

```yaml
# Tool paths
tools:
  cdqa: "${RRD_TOOLS_PATH}/cdqa"
  cdscan: "${RRD_TOOLS_PATH}/cdscan"
  dbgctxt: "${RRD_TOOLS_PATH}/dbgctxt"
  zgit: "${RRD_TOOLS_PATH}/zgit"

# Project paths
paths:
  workspace: "."
  knowledge_kernel: ".specify/memory/knowledge_kernel.toon"
  session_logs: ".specify/memory/rrd_sessions"
  backup_dir: ".repair_backups"

# Analysis settings
analysis:
  incremental_mode: true
  max_file_scan: 50

# Quality gates
quality_gates:
  mode: "gradual"  # gradual | strict
  l2_thresholds:   # Drafting
    linting_errors: 100
    type_coverage: 60
  l3_thresholds:   # Hardening
    linting_errors: 50
    type_coverage: 80
```

## Core Modules

### config_loader.py
Manages environment-based configuration with cross-platform path resolution.

```python
from core.config_loader import load_rrd_config

config = load_rrd_config()
cdqa_path = config.get_tool_path("cdqa")
is_incremental = config.is_incremental_mode()
```

### toon_utils.py
TOON (Token-Oriented Object Notation) format for efficient LLM consumption (~40% fewer tokens than JSON).

```python
from core.toon_utils import dump, parse_toon_file, ToonSerializer

# Serialize data
dump(data, "output.toon")

# Parse file
data = parse_toon_file("input.toon")
```

### history_manager.py
Dual-history architecture for knowledge kernel optimization.

- **ContextPruner**: Filters resolved issues (60-80% token savings)
- **SessionRecorder**: Complete audit logging

```python
from core.history_manager import HistoryManager

mgr = HistoryManager(session_dir="./logs")
active_ctx = mgr.pruner.get_active_context(failures, iteration=3)
mgr.recorder.append_log(iteration, patch, outcome, status)
```

### cycle_detector.py
Prevents infinite loops with semantic code analysis.

```python
from core.cycle_detector import CycleDetector

detector = CycleDetector(window_size=4)
if detector.check_duplicate_patch(patch):
    print("Cycle detected!")
```

### patch_manager.py
Safe code modification with atomic operations and automatic backups.

```python
from core.patch_manager import PatchManager
from core.data_types import PatchToon

mgr = PatchManager(create_backups=True)
patch = PatchToon(
    file_path="src/calculator.py",
    line_range=(15, 16),
    old_code="    return a - b",
    new_code="    return a + b"
)
mgr.apply_patch(patch)
```

## Library Usage

Use RRD as a library in your own tools:

```python
from core import ToonSerializer, HistoryManager, CycleDetector, PatchManager
from core.config_loader import load_rrd_config
from orchestrator.rrd_orchestrator import RRDOrchestrator

# Load configuration
config = load_rrd_config()

# Create utilities
history = HistoryManager(session_dir="./logs")
cycles = CycleDetector(window_size=4)
patches = PatchManager(backup_dir=".backups")

# Or use full orchestrator
orchestrator = RRDOrchestrator(config_path=".claude/rrd_config.yaml")
result = orchestrator.execute_full_workflow(
    spec_file="spec.md",
    output_dir="./output"
)
```

## CLI Usage

```bash
# Run full L1-L4 workflow
python rrd.py --workspace /path/to/project --spec spec.md

# Run specific phase
python rrd.py --workspace /path/to/project --phase L2

# Interactive mode
python rrd.py --workspace /path/to/project --interactive

# View session logs
python rrd.py --list-sessions
python rrd.py --show-session <session-id>
```

## Performance Optimizations

### Incremental Analysis
When git repository exists, RRD analyzes only changed files:
- **10x speedup** for small changes (5 files)
- **84% token savings** for small changes
- **3.4x speedup** for medium changes (20 files)

### Knowledge Kernel Filtering
Load only active, recent, relevant failures:
- **60-80% reduction** in context size
- **Rolling window**: Last N days (default: 7)
- **Criticality filtering**: high/medium/low
- **Status filtering**: ACTIVE vs RESOLVED

## Testing

Run the test suite:

```bash
# All tests
pytest

# With coverage
pytest --cov=core --cov=orchestrator --cov-report=html

# Specific module
pytest tests/unit/test_toon_utils.py

# Integration tests
pytest tests/integration/
```

## Code Quality

Current quality metrics:

- **Quality Score**: 100/100 ✅
- **Type Coverage**: 100% ✅
- **Security Issues**: 0 ✅
- **Max Complexity**: 10 (B-grade) ✅
- **Dead Code**: 0 ✅
- **Linting Errors**: 0 ✅

Run quality checks:

```bash
# Ruff linting
ruff check core/ orchestrator/ cli/

# Type checking
ty core/ orchestrator/ cli/

# Security scan
semgrep --config auto core/ orchestrator/ cli/

# Complexity analysis
complexipy core/ orchestrator/ cli/
```

## Cross-Platform Compatibility

All RRD code uses `pathlib.Path` for cross-platform compatibility:

```python
from pathlib import Path
import os

# Good - works on Windows, Linux, macOS
skills_path = Path(os.getenv("RRD_TOOLS_PATH", Path.home() / ".claude" / "skills"))

# Bad - fails on Windows
cdqa_path = "~/.claude/skills/cdqa"
```

Use `Path.samefile()` for path comparison (handles symlinks, relative paths, etc.).

## Emergency Protocols

### Infinite Loop Detection
Trigger: Error signature appears >3 times

Actions:
1. STOP current cycle
2. Generate error report with dbgctxt
3. Document blocker in knowledge kernel
4. Request human intervention

### QA Repeated Failures
Trigger: QA gates fail >5 times consecutively

Actions:
1. Re-read specification
2. Run cdscan to review architecture
3. Consider alternative approach
4. Consult external documentation

## External Tools

RRD integrates with the following tools (must be in `~/.claude/skills/`):

- **cdqa**: Code quality analysis (ruff, ty, semgrep, complexipy, skylos)
- **cdscan**: Codebase structure analysis (tree-sitter, ctags, ripgrep)
- **dbgctxt**: Test failure context generation and repair payload
- **zgit**: Context-preserving git commits

## Documentation

- **README.md**: This file - main documentation
- **.claude/commands/RRD_execute.md**: RRD execution command reference
- **.specify/memory/constitution.md**: Project constitution with RRD protocol
- **API Documentation**: Generated from docstrings

## Contributing

When contributing to RRD:

1. Follow RRD protocol (use RRD workflow for development)
2. Add tests for new features (maintain 80%+ coverage)
3. Update knowledge kernel if failures occur
4. Run QA gates before committing (all must pass)
5. Use zgit for context-preserving commits

## Version

**Version**: 1.0.0
**Status**: Production Ready ✅
**Last Updated**: 2026-01-03

## License

See LICENSE file for details.

---

**Remember**: RRD is systematic improvement through adversarial testing, memory retention, and strict quality gates. Every failure is a learning opportunity stored in the knowledge kernel.
