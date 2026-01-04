# cdqa - Code Quality Analyzer v2.0

Fast, comprehensive Python code quality analysis with modern Rust-based tools.

## What's New in v2.0

**Major Tool Replacements:**
- ✅ **mypy → ty**: 10-100x faster type checking (Astral/Rust-based)
- ✅ **radon → complexipy**: Cognitive complexity analysis (measures human understanding)
- ✅ **NEW: skylos**: Dead code detection with confidence scoring
- ✅ **NEW: pattern_analyzer**: Consistency checks across codebase

**Why These Changes?**
- **Performance**: ty is 10-100x faster than mypy → faster CI/CD
- **Better Metrics**: Cognitive complexity > cyclomatic (measures human understanding)
- **New Capability**: Dead code detection (unused functions, imports)
- **Ecosystem Consistency**: ty from Astral (same as ruff) → aligned toolchain

## Quick Start

```bash
# Basic usage
cd /home/vscode/.claude/skills/cdqa
python run_QA.py --workspace /path/to/project

# With custom output
python run_QA.py \
  --workspace /path/to/project \
  --output quality_report.toon \
  --verbose
```

## What It Does

1. **Ruff Linting** - Check code style, find bugs, enforce best practices
2. **ty Type Checking** - Ultra-fast type verification (10-100x faster than mypy)
3. **Semgrep Security Scanning** - Detect security vulnerabilities and anti-patterns
4. **Complexipy Complexity** - Measure cognitive complexity (how hard for humans to understand)
5. **Skylos Dead Code** - Find unused functions, imports, and dead code

## Output

Generates `quality_report.toon` in TOON format with:
- Quality summary and overall score (0-100)
- Quality gates status (pass/fail thresholds)
- Critical issues prioritized by severity
- Tool-specific findings (ruff, ty, semgrep, complexipy, skylos)
- Immediate fixes and next steps

**Example output:**
```toon
summary:
  quality_score: 87
  total_issues: 45
  tools_used: [ruff, ty, semgrep, complexipy, skylos]

quality_gates:
  [5] {gate, threshold, actual, status}
  linting_errors | <50 | 12 | PASS
  type_coverage | >80% | 92% | PASS
  security_critical | 0 | 0 | PASS
  cognitive_complexity | <12 | 8 | PASS
  dead_code | <5 | 2 | PASS

critical_issues:
  [3] {severity, tool, file, line, issue}
  WARNING | complexipy | src/api/routes.py | 0 | Cognitive complexity 15 (D-grade)
  WARNING | skylos | src/utils/old.py | 42 | Unused function 'legacy_handler' (95%)
  ...
```

## Prerequisites

Install required tools:

```bash
# Install all v2.0 tools
pip install ruff ty semgrep complexipy skylos

# Or with uv (recommended for ty)
uv tool install ruff ty semgrep complexipy skylos

# Verify installations
ruff --version
ty --version
semgrep --version
complexipy --version
skylos --version
```

## Migration from v1.x

If you're upgrading from cdqa v1.x:

```bash
# 1. Uninstall old tools (optional)
pip uninstall mypy radon

# 2. Install new tools
pip install ty complexipy skylos

# 3. Note: Output format has changed
# - "mypy" section → "ty" section
# - "radon" section → "complexipy" section
# - New "skylos" section added
# - Quality gate "max_complexity" → "cognitive_complexity" (stricter: <12 vs <15)
```

## Command Options

```
--workspace <dir>      # Project directory (required)
--pattern <glob>       # File pattern (default: **/*.py)
--output <file>        # Output file (default: quality_report.toon)
--verbose              # Enable detailed logging
--max-issues <N>       # Max issues to display (default: 50)
```

## Tool Structure

```
cdqa/
├── README.md                     # This file (v2.0 documentation)
├── run_QA.py                     # Main orchestrator
└── tools/
    ├── ruff_checker.py           # Ruff linting
    ├── ty_checker.py             # ty type checking (NEW in v2.0)
    ├── semgrep_scanner.py        # Security scanning
    ├── complexipy_metrics.py     # Cognitive complexity (NEW in v2.0)
    ├── skylos_analyzer.py        # Dead code detection (NEW in v2.0)
    └── toon_serializer.py        # TOON output formatter
```

## Quality Gates

| Gate | Threshold | Description |
|------|-----------|-------------|
| **linting_errors** | < 50 | Total ruff linting issues |
| **type_coverage** | > 80% | Percentage of typed code |
| **security_critical** | 0 | Critical security issues (semgrep) |
| **cognitive_complexity** | < 12 | Max cognitive complexity score |
| **dead_code** | < 5 | Number of unused functions |

## Example Workflow

```bash
# 1. Run quality check
python run_QA.py --workspace /workspaces/myapp

# 2. Review report
cat /workspaces/myapp/quality_report.toon

# 3. Fix auto-fixable issues
cd /workspaces/myapp
ruff check --fix src/

# 4. Re-run to verify improvements
python run_QA.py --workspace /workspaces/myapp
```

## Integration

### Pre-commit Hook
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: quality-check
        name: Code Quality Check
        entry: python tools/cdqa/run_QA.py --workspace .
        language: system
        pass_filenames: false
```

### CI/CD
```yaml
# GitHub Actions
- name: Run Quality Check
  run: |
    python tools/cdqa/run_QA.py --workspace .
    if grep -q "FAIL" quality_report.toon; then exit 1; fi
```
