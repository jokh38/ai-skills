---
name: cdqa
description: Integrated Python code quality analysis using ruff, ty, semgrep, complexipy, and skylos
supported-languages: python
interactive: false
stream-output: true
allowed-tools: Read, Write, Bash
invocable: true
---

# Cdqa Skill v2.0

Comprehensive Python code quality analysis using modern Rust-based tools: ruff (linting), ty (type checking), semgrep (security), complexipy (cognitive complexity), and skylos (dead code detection).

## How to Invoke This Skill

### Quick Invocation
```bash
cd /home/vscode/.claude/skills/cdqa
python run_QA.py --workspace /workspaces/your-project
```

This will automatically:
1. Run ruff linting with JSON output
2. Run ty type checking (10-100x faster than mypy)
3. Run semgrep security scanning
4. Run complexipy cognitive complexity analysis
5. Run skylos dead code detection
6. Generate comprehensive report in `quality_report.toon`

### Command Options
- `--workspace <dir>`: Project directory to analyze (required)
- `--pattern <glob>`: File pattern to analyze (default: "**/*.py")
- `--output <file>`: Output file (default: quality_report.toon in workspace)
- `--verbose`: Enable detailed logging
- `--max-issues <N>`: Maximum number of issues to display (default: 50)
- `--filtered`: Filter results to top issues only (default: unfiltered/all issues)

### Filtering Modes

**Default (unfiltered)**: Returns all raw data from tools
```bash
python run_QA.py --workspace /path/to/project
```
- All 77 ruff issues with full details
- All semgrep findings with CWE metadata
- All complexity hotspots
- All type errors
- Complete severity_counts and by_category breakdowns

**Filtered**: Returns summarized top issues only
```bash
python run_QA.py --workspace /path/to/project --filtered
```
- Top 50 critical issues (sorted by severity)
- Top 6 ruff categories
- Top 5 mypy error types
- Top 10 complexity hotspots
- Top 5 maintainability issues

Use **unfiltered** (default) for:
- Complete code quality audits
- Generating detailed reports
- Historical tracking of all issues
- Debugging specific problems

Use **filtered** for:
- Quick pre-commit checks
- CI/CD quality gates
- High-level summary views
- Identifying immediate priorities

## What This Skill Does

### 1. Ruff Linting
- **Fast Python linter** (written in Rust, 10-100x faster than flake8)
- **Check code style** using pycodestyle, pyflakes, isort rules
- **Find bugs** like undefined names, unused imports
- **Auto-fix** many issues automatically
- **Categorize issues** by severity and rule code

**Output**: Linting issues categorized by severity (error, warning, info) and rule code (F, E, W, N, C, I)

### 2. Ty Type Checking (v2.0)
- **Ultra-fast type checker** for Python type hints (10-100x faster than mypy)
- **Verify type annotations** and detect type mismatches
- **Calculate type coverage** percentage
- **Find common errors**: missing attributes, argument type mismatches, undefined names
- **Categorize by error code**: attr-defined, no-untyped-def, arg-type, etc.

**Output**: Type errors with location, error code, and type coverage metrics

### 3. Semgrep Security Scanning
- **Pattern-based security analysis** using SAST rules
- **Detect vulnerabilities**: SQL injection, XSS, hardcoded secrets, weak crypto
- **Find anti-patterns**: insecure deserialization, shell injection, eval usage
- **CWE mapping**: Map findings to Common Weakness Enumeration
- **Severity levels**: ERROR (critical), WARNING (review needed), INFO (best practice)

**Output**: Security findings with CWE, severity, confidence, and fix recommendations

### 4. Complexipy Complexity Metrics (v2.0)
- **Cognitive Complexity**: Measure how hard code is for humans to understand
- **Score functions**: A (simple) to F (critically complex)
- **Identify hotspots**: Functions with high cognitive complexity needing refactoring
- **Better than cyclomatic complexity**: Accounts for nesting, logical operators, and control flow

**Output**: Cognitive complexity scores and graded functions per file

### 5. Skylos Dead Code Detection (v2.0)
- **Find unused functions** with confidence scoring
- **Detect unused imports** across modules
- **Identify dead code** that can be safely removed
- **Confidence levels**: High (90%+), Medium, Low

**Output**: Dead code locations with confidence percentages

## Output Structure

The analyzer generates a comprehensive quality report in **TOON format** (Token-Oriented Object Notation), optimized for LLM consumption.

### TOON Format Output

```toon
# Code Quality Report
# Generated: 2025-12-30T10:30:00Z
# Workspace: /path/to/project

summary:
  files_analyzed: 45
  total_issues: 199
  quality_score: 72
  execution_time_ms: 4647

quality_gates:
  [5] {gate, threshold, actual, status}
  linting_errors | <50 | 127 | FAIL
  type_coverage | >80% | 68% | FAIL
  security_critical | 0 | 2 | FAIL
  cognitive_complexity | <12 | 18 | FAIL
  dead_code | <5 | 8 | FAIL

critical_issues:
  [10] {severity, tool, file, line, issue}
  ERROR | semgrep | src/api/database.py | 156 | SQL injection via string formatting
  ERROR | semgrep | src/config/settings.py | 15 | Hardcoded API key detected
  WARNING | complexipy | src/api/routes.py | 45 | Cognitive complexity 18 (D-grade)
  WARNING | skylos | src/utils/legacy.py | 42 | Unused function 'old_handler' (92%)
  ...

ruff:
  total: 127
  auto_fixable: 89
  by_category:
    [4] {code, category, count}
    F | pyflakes-errors | 34
    E | pycodestyle-errors | 28
    W | warnings | 25
    N | naming | 18

ty:
  total: 67
  type_coverage: 68%
  by_error:
    [3] {code, description, count}
    attr-defined | Missing attributes | 23
    no-untyped-def | Missing annotations | 18
    arg-type | Type mismatch | 12

semgrep:
  total: 5
  by_severity:
    [3] {severity, category, count}
    ERROR | sql-injection, hardcoded-secret | 2
    WARNING | xss, weak-crypto | 2
    INFO | insecure-deserialization | 1

complexipy:
  complexity_hotspots:
    [5] {file, function, complexity, grade}
    src/api/routes.py | handle_api_call | 18 | D
    src/database/query.py | build_query | 14 | C
    ...

skylos:
  dead_code:
    [5] {file, symbol, type, confidence}
    src/utils/legacy.py | old_handler | function | 92%
    src/models/user.py | User.old_field | attribute | 87%
    ...

immediate_fixes:
  [5] {priority, action, effort}
  1 | "Run: ruff check --fix src/" | 2min
  2 | "Fix SQL injection: src/api/database.py:156" | 10min
  3 | "Move API_KEY to environment variable" | 5min
  ...

next_steps:
  - "Add type annotations to reach 80% coverage (currently 68%)"
  - "Refactor 3 high-cognitive-complexity functions (D/F grade)"
  - "Review and remove 8 dead code items"
  - "Review and fix security warnings"
```

## When to Use This Skill

Use when you need to:
- ✅ **Check code quality** before committing or merging
- ✅ **Find bugs and errors** in Python code
- ✅ **Verify type safety** and type coverage
- ✅ **Security audit** for vulnerabilities
- ✅ **Identify complexity** hotspots needing refactoring
- ✅ **Enforce quality gates** in CI/CD pipelines
- ✅ **Generate quality metrics** for reporting

**Don't use for:**
- ❌ Non-Python projects (use language-specific tools)
- ❌ Single file quick checks (use tools directly)
- ❌ Real-time IDE feedback (use IDE integrations)

## Prerequisites

### Required Tools

Install all required tools:

```bash
pip install ruff ty semgrep complexipy skylos
```

**1. Ruff** (linting)
```bash
pip install ruff
ruff --version
```

**2. Ty** (type checking - v2.0 replacement for mypy)
```bash
pip install ty
# Or with uv for faster installation:
uv tool install ty
ty --version
```

**3. Semgrep** (security scanning)
```bash
pip install semgrep
semgrep --version
```

**4. Complexipy** (cognitive complexity - v2.0 replacement for radon)
```bash
pip install complexipy
complexipy --version
```

**5. Skylos** (dead code detection - new in v2.0)
```bash
pip install skylos
skylos --version
```

## Quality Gates

The tool evaluates code against these default thresholds:

| Gate | Threshold | Description |
|------|-----------|-------------|
| **linting_errors** | < 50 | Total ruff linting issues |
| **type_coverage** | > 80% | Ty type annotation coverage |
| **security_critical** | 0 | Semgrep ERROR-level findings |
| **cognitive_complexity** | < 12 | Max cognitive complexity (stricter than cyclomatic) |
| **dead_code** | < 5 | Number of unused functions/imports |

**Status**: `PASS` or `FAIL` for each gate

## Integration Examples

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
        stages: [commit]
```

### GitHub Actions

```yaml
# .github/workflows/quality.yml
name: Code Quality

on: [push, pull_request]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install tools
        run: pip install ruff mypy semgrep radon

      - name: Run quality check
        run: |
          python tools/cdqa/run_QA.py --workspace .

      - name: Check quality gates
        run: |
          if grep -q "status: FAIL" quality_report.toon; then
            echo "Quality gates failed!"
            exit 1
          fi
```

### GitLab CI

```yaml
# .gitlab-ci.yml
quality_check:
  stage: test
  script:
    - pip install ruff mypy semgrep radon
    - python tools/cdqa/run_QA.py --workspace .
    - grep -q "status: FAIL" quality_report.toon && exit 1 || exit 0
  artifacts:
    paths:
      - quality_report.toon
    expire_in: 1 week
```

## Implementation Files

```
cdqa/
├── SKILL.md                          # This file
├── README.md                         # Quick start guide
├── run_QA.py                         # Main entry point (v2.0)
├── cdqa_cli.py                       # CLI interface
└── tools/
    ├── ruff_checker.py               # Ruff linting integration
    ├── ty_checker.py                 # Ty type checking integration (v2.0)
    ├── semgrep_scanner.py            # Semgrep security scanning integration
    ├── complexipy_metrics.py         # Complexipy cognitive complexity (v2.0)
    ├── skylos_analyzer.py            # Skylos dead code detection (v2.0)
    ├── pattern_analyzer.py           # Pattern consistency analyzer
    └── toon_serializer.py            # TOON format output
```

## Comparison with cdscan

| Aspect | cdscan | cdqa |
|--------|--------|------|
| **Purpose** | Understand codebase structure | Check code quality and errors |
| **Tools** | tree-sitter, ctags, ripgrep | ruff, ty, semgrep, complexipy, skylos |
| **Focus** | Architecture, patterns, design | Errors, types, security, complexity |
| **Output** | Codebase map and insights | Issue report with fixes |
| **Use Case** | Initial exploration, planning | Pre-commit, CI/CD, audits |

## Migration from v1.x to v2.0

cdqa v2.0 introduces significant tool replacements for better performance:

**Tool Changes:**
- **mypy → ty**: 10-100x faster type checking (Astral/Rust-based)
- **radon → complexipy**: Cognitive complexity analysis (more human-focused)
- **NEW: skylos**: Dead code detection with confidence scoring

**Migration Steps:**
```bash
# 1. Uninstall old tools (optional)
pip uninstall mypy radon

# 2. Install new tools
pip install ty complexipy skylos

# 3. Note output format changes:
#    - "mypy" section → "ty" section
#    - "radon" section → "complexipy" section
#    - New "skylos" section added
#    - Quality gate "max_complexity" → "cognitive_complexity" (stricter: <12 vs <15)
```

**Benefits:**
- Faster CI/CD pipelines (ty is 10-100x faster than mypy)
- Better complexity metrics (cognitive complexity measures human understanding)
- New dead code detection capability
- Consistent Rust-based toolchain (ty from Astral, same as ruff)

## Troubleshooting

### Tool not found
```bash
# Error: "ty not installed"
pip install ruff ty semgrep complexipy skylos

# Verify all tools
ruff --version && ty --version && semgrep --version && complexipy --version && skylos --version
```

### Timeout errors
```bash
# Semgrep timeout on large codebases
# Edit semgrep_scanner.py and increase timeout value
# Or run on specific directories:
python run_QA.py --workspace /path/to/project/src
```

### Empty results
```bash
# No Python files found
# Check pattern matches files:
ls **/*.py

# Or specify custom pattern:
python run_QA.py --workspace . --pattern "src/**/*.py"
```
