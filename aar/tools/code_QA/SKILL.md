---
name: code-quality-checker
description: Integrated Python code quality analysis using ruff, mypy, semgrep, and radon
supported-languages: python
interactive: false
stream-output: true
allowed-tools: Read, Write, Bash
invocable: true
---

# Code Quality Checker Skill

Comprehensive Python code quality analysis using four complementary tools: ruff (linting), mypy (type checking), semgrep (security), and radon (complexity).

## How to Invoke This Skill

### Quick Invocation
```bash
cd /home/vscode/.claude/skills/code_QA
python run_QA.py --workspace /workspaces/your-project
```

This will automatically:
1. Run ruff linting with JSON output
2. Run mypy type checking
3. Run semgrep security scanning
4. Run radon complexity analysis
5. Generate comprehensive report in `quality_report.toon`

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

### 2. Mypy Type Checking
- **Static type checker** for Python type hints
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

### 4. Radon Complexity Metrics
- **Cyclomatic Complexity (CC)**: Measure code branching and decision points
- **Maintainability Index (MI)**: Overall maintainability score (0-100)
- **Grade functions**: A (simple) to F (critically complex)
- **Identify hotspots**: Functions with high complexity needing refactoring

**Output**: Complexity hotspots and maintainability scores per file

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
  [4] {gate, threshold, actual, status}
  linting_errors | <50 | 127 | FAIL
  type_coverage | >80% | 68% | FAIL
  security_critical | 0 | 2 | FAIL
  max_complexity | <15 | 32 | FAIL

critical_issues:
  [10] {severity, tool, file, line, issue}
  ERROR | semgrep | src/api/database.py | 156 | SQL injection via string formatting
  ERROR | semgrep | src/config/settings.py | 15 | Hardcoded API key detected
  ERROR | radon | src/api/routes.py | 45 | Complexity 32 (F-grade) - refactor urgently
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

mypy:
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

radon:
  complexity_hotspots:
    [5] {file, function, complexity, grade}
    src/api/routes.py | handle_api_call | 32 | F
    src/database/query.py | build_query | 24 | D
    ...

  maintainability:
    [3] {file, mi_score, grade}
    src/api/routes.py | 23.4 | Poor
    src/database/query.py | 38.7 | Moderate
    ...

immediate_fixes:
  [5] {priority, action, effort}
  1 | "Run: ruff check --fix src/" | 2min
  2 | "Fix SQL injection: src/api/database.py:156" | 10min
  3 | "Move API_KEY to environment variable" | 5min
  ...

next_steps:
  - "Add type annotations to reach 80% coverage (currently 68%)"
  - "Refactor 3 high-complexity functions (F/D grade)"
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
pip install ruff mypy semgrep radon
```

**1. Ruff** (linting)
```bash
pip install ruff
ruff --version
```

**2. Mypy** (type checking)
```bash
pip install mypy
mypy --version
```

**3. Semgrep** (security scanning)
```bash
pip install semgrep
semgrep --version
```

**4. Radon** (complexity metrics)
```bash
pip install radon
radon --version
```

## Quality Gates

The tool evaluates code against these default thresholds:

| Gate | Threshold | Description |
|------|-----------|-------------|
| **linting_errors** | < 50 | Total ruff linting issues |
| **type_coverage** | > 80% | Mypy type annotation coverage |
| **security_critical** | 0 | Semgrep ERROR-level findings |
| **max_complexity** | < 15 | Highest cyclomatic complexity |

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
        entry: python tools/code_QA/run_QA.py --workspace .
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
          python tools/code_QA/run_QA.py --workspace .

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
    - python tools/code_QA/run_QA.py --workspace .
    - grep -q "status: FAIL" quality_report.toon && exit 1 || exit 0
  artifacts:
    paths:
      - quality_report.toon
    expire_in: 1 week
```

## Implementation Files

```
code_QA/
├── SKILL.md                          # This file
├── README.md                         # Quick start guide
├── run_QA.py                         # Main entry point
├── analyze.py                        # Wrapper script
└── tools/
    ├── ruff_checker.py               # Ruff linting integration
    ├── mypy_analyzer.py              # Mypy type checking integration
    ├── semgrep_scanner.py            # Semgrep security scanning integration
    ├── radon_metrics.py              # Radon complexity metrics integration
    └── toon_serializer.py            # TOON format output
```

## Comparison with code-analyzer

| Aspect | code-analyzer | code-quality-checker |
|--------|---------------|----------------------|
| **Purpose** | Understand codebase structure | Check code quality and errors |
| **Tools** | tree-sitter, ctags, ripgrep | ruff, mypy, semgrep, radon |
| **Focus** | Architecture, patterns, design | Errors, types, security, complexity |
| **Output** | Codebase map and insights | Issue report with fixes |
| **Use Case** | Initial exploration, planning | Pre-commit, CI/CD, audits |

## Troubleshooting

### Tool not found
```bash
# Error: "ruff not installed"
pip install ruff mypy semgrep radon

# Verify all tools
ruff --version && mypy --version && semgrep --version && radon --version
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
