---
name: dbgctxt
description: Automated test failure analysis and context generation for LLM-based code repair using pytest and TOON artifacts
supported-languages: python
interactive: false
stream-output: true
allowed-tools: Read, Write, Bash
invocable: true
---

# Dbgctxt Skill

Synthesizes static analysis data (from TOON artifacts) and dynamic test results (from pytest) to generate context-aware fix proposals for LLM-based code repair.

## How to Invoke This Skill

### Quick Invocation (Recommended)
When the user requests test debugging or failure analysis, use the Skill tool:
```
User: "Debug the failing tests"
Assistant: [Uses Skill tool with skill: "dbgctxt"]
```

This will automatically:
1. Run pytest to capture test failures
2. Load or generate `structure.toon` (codebase structure)
3. Load or generate `qa_report.toon` (quality analysis)
4. Deduplicate and enrich failure data
5. Generate `fix_payload.toon` with context-aware repair suggestions

### Manual Invocation (Advanced)
For more control, run the generator directly:
```bash
cd /home/vscode/.claude/skills/dbgctxt
python -m dbgctxt /path/to/workspace
```

**Command Options:**
- `workspace_path` (required): Path to the workspace containing tests
- `--test-case <test>`: Run only a specific test case (e.g., `tests/test_example.py::test_function`)

**Examples:**
```bash
# Analyze all test failures
python -m dbgctxt /workspaces/my-project

# Focus on specific test file
python -m dbgctxt /workspaces/my-project --test-case tests/test_math.py

# Debug single test function
python -m dbgctxt /workspaces/my-project --test-case tests/test_math.py::test_addition
```

## What This Skill Does

### 1. Artifact Loading
- **Load static analysis**: Reads `structure.toon` (codebase structure from cdscan)
- **Load quality data**: Reads `qa_report.toon` (quality issues from cdqa)
- **Auto-generate missing**: Automatically runs `cdscan` and `cdqa` if TOON files don't exist
- **Parse TOON format**: Efficiently loads token-optimized data structures

**Workspace Requirements:**
- Test files for pytest execution
- (Optional) `structure.toon` - Auto-generated if missing
- (Optional) `qa_report.toon` - Auto-generated if missing

### 2. Dynamic Verification
- **Execute pytest**: Runs tests and captures failures, errors, and successes
- **Parse results**: Extracts test outcomes, error messages, tracebacks
- **Early exit**: Terminates immediately when all tests pass
- **Selective execution**: Supports single test case debugging with `--test-case`

**Output**: Test results with failure types, locations, and error messages

### 3. Context Mapping
- **Deduplicate failures**: Groups failures by unique signatures to prevent context overflow
- **Enrich with AST**: Maps runtime errors to abstract syntax tree structure
- **Link quality issues**: Connects failures to static analysis findings (ruff, mypy, semgrep)
- **Identify root causes**: Correlates test failures with code complexity and quality metrics

**Use Cases**: Efficient debugging, focused code repairs, automated fix generation

### 4. Prompt Assembly
- **Generate TOON payload**: Serializes enriched context into token-optimized format
- **Include fix suggestions**: Provides actionable repair recommendations
- **Preserve context**: Maintains file paths, line numbers, and code snippets
- **Optimize for LLMs**: Minimizes token usage (~40% fewer tokens than JSON)

**Output**: `fix_payload.toon` ready for LLM consumption

## Output Structure

The generator creates a comprehensive debugging payload in **TOON format** (Token-Oriented Object Notation), optimized for LLM consumption.

### TOON Format Output

```toon
# Test Failure Analysis and Repair Context
# Generated: 2025-12-31T10:00:00Z
# Workspace: /path/to/project

test_summary:
  total_tests: 45
  passed: 38
  failed: 7
  errors: 0
  skipped: 0
  execution_time_ms: 2341

failures:
  [3] {test_id, file, line, failure_type, signature}
  test_math::test_divide | tests/test_math.py | 42 | AssertionError | ZeroDivisionError not raised
  test_api::test_auth | tests/test_api.py | 78 | TypeError | missing 1 required positional argument
  test_db::test_query | tests/test_db.py | 156 | AssertionError | Query returned 0 rows, expected 5

enriched_context:
  [3] {test_id, affected_files, related_issues, complexity}
  test_math::test_divide:
    affected_files:
      [1] {file, function, lines}
      src/math_utils.py | divide | 23-28
    related_issues:
      [2] {tool, severity, issue}
      ruff | ERROR | F821: undefined name 'x'
      radon | WARNING | Complexity 12 (C-grade)
    root_cause: "Missing zero division check in divide() function"

  test_api::test_auth:
    affected_files:
      [1] {file, function, lines}
      src/api/auth.py | authenticate | 45-67
    related_issues:
      [2] {tool, severity, issue}
      mypy | ERROR | Missing argument 'password' in call
      semgrep | WARNING | Insecure password storage
    root_cause: "API signature changed but tests not updated"

fix_recommendations:
  [3] {priority, test_id, action, estimated_effort}
  1 | test_math::test_divide | "Add zero check: if divisor == 0: raise ZeroDivisionError" | 2min
  2 | test_api::test_auth | "Update test call to include 'password' parameter" | 1min
  3 | test_db::test_query | "Verify database seed data exists before query" | 5min

code_snippets:
  test_math::test_divide:
    test_code: |
      def test_divide():
          assert divide(10, 0) raises ZeroDivisionError  # Line 42

    implementation: |
      def divide(a, b):  # src/math_utils.py:23
          return a / b  # Missing zero check

    suggested_fix: |
      def divide(a, b):
          if b == 0:
              raise ZeroDivisionError("Cannot divide by zero")
          return a / b

quality_context:
  total_quality_issues: 127
  affecting_failed_tests: 18
  by_severity:
    [3] {severity, count, related_failures}
    ERROR | 5 | 3
    WARNING | 8 | 2
    INFO | 5 | 0
```

## When to Use This Skill

Use when you need to:
- ✅ **Debug test failures** - Understand why tests are failing with enriched context
- ✅ **Generate fix proposals** - Get actionable repair suggestions based on static and dynamic analysis
- ✅ **Analyze test coverage** - Identify gaps in test coverage related to failures
- ✅ **Automated code repair** - Feed context to LLMs for automated fix generation
- ✅ **Root cause analysis** - Correlate test failures with code quality issues
- ✅ **Focus debugging** - Use `--test-case` to debug specific failing tests
- ✅ **CI/CD integration** - Generate structured failure reports in pipelines

**Don't use for:**
- ❌ Passing tests (tool exits early with success message)
- ❌ Non-Python projects (requires pytest)
- ❌ Projects without tests (no test files to analyze)
- ❌ Real-time debugging (use IDE debugger instead)

## Pipeline Architecture

The tool follows a four-stage pipeline:

### Stage 1: Artifact Loading
```python
from src.artifact_manager import ArtifactManager

manager = ArtifactManager(workspace="/workspaces/project")
structure = manager.load_structure_toon()  # Loads or generates structure.toon
qa_report = manager.load_qa_report_toon()  # Loads or generates qa_report.toon
```

### Stage 2: Dynamic Verification
```python
from src.verification_runner import VerificationRunner

runner = VerificationRunner(workspace="/workspaces/project")
results = runner.run_pytest(test_case=None)  # Or specify --test-case

# Results include:
# - passed: List of passing tests
# - failed: List of failures with tracebacks
# - errors: List of test errors
# - skipped: List of skipped tests
```

### Stage 3: Context Mapping
```python
from src.context_resolver import ContextResolver

resolver = ContextResolver(structure, qa_report)
enriched = resolver.deduplicate_and_enrich(results.failed)

# Enriched data includes:
# - Unique failure signatures (prevents duplicates)
# - AST structure for affected files
# - Related quality issues (ruff, mypy, semgrep)
# - Complexity metrics (radon)
# - Root cause analysis
```

### Stage 4: Prompt Assembly
```python
from src.prompt_builder import PromptBuilder

builder = PromptBuilder()
payload = builder.build_toon_payload(enriched, structure, qa_report)

# Payload saved to: fix_payload.toon
# Ready for LLM consumption
```

## Prerequisites

### Required Tools

Install all required tools:

```bash
pip install -r requirements.txt
```

**1. pytest** (test execution)
```bash
pip install pytest
pytest --version
```

**2. cdscan** (optional, auto-invoked)
- Pre-installed as sibling skill
- Auto-runs if `structure.toon` missing

**3. cdqa** (optional, auto-invoked)
- Pre-installed as sibling skill
- Auto-runs if `qa_report.toon` missing

## Integration Examples

### As Part of TDD Workflow

```bash
# 1. Write failing tests
# 2. Run debugging context generator
python -m dbgctxt /workspaces/my-project

# 3. Review fix_payload.toon
cat fix_payload.toon

# 4. Apply suggested fixes
# 5. Re-run tests to verify
pytest
```

### CI/CD Integration

```yaml
# .github/workflows/debug.yml
name: Test Failure Analysis

on: [push, pull_request]

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run tests and generate debug context
        run: |
          python -m dbgctxt .
        continue-on-error: true

      - name: Upload debug payload
        uses: actions/upload-artifact@v3
        with:
          name: debug-payload
          path: fix_payload.toon
```

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: debug-context
        name: Generate Debug Context
        entry: python -m dbgctxt .
        language: system
        pass_filenames: false
        stages: [pre-push]
        always_run: false  # Only runs when tests fail
```

## Implementation Files

```
dbgctxt/
├── SKILL.md                          # This file
├── README.md                         # Quick start guide
├── __main__.py                       # CLI entry point
├── pyproject.toml                    # Package configuration
├── requirements.txt                  # Python dependencies
├── src/
│   ├── pipeline_orchestrator.py      # Main workflow orchestration
│   ├── artifact_manager.py           # Static artifact loading
│   ├── verification_runner.py        # Test execution and result parsing
│   ├── context_resolver.py           # Failure deduplication and enrichment
│   └── prompt_builder.py             # TOON payload generation
└── utils/
    ├── path_utils.py                 # Path handling utilities
    ├── toon_parser.py                # TOON format parsing
    └── data_structures.py            # Shared data structures
```

## Troubleshooting

### Tests not found
```bash
# Error: "No tests found in workspace"
# Ensure pytest can discover tests:
pytest --collect-only

# Or specify test directory:
python -m dbgctxt . --test-case tests/
```

### Missing TOON artifacts
```bash
# If structure.toon or qa_report.toon are missing,
# they will be auto-generated by running:
# - cdscan (for structure.toon)
# - cdqa (for qa_report.toon)

# To manually generate:
cd /home/vscode/.claude/skills/cdscan
python run_code_review.py --workspace /path/to/project

cd /home/vscode/.claude/skills/cdqa
python run_QA.py --workspace /path/to/project
```

### Pytest failures not captured
```bash
# Verify pytest is installed and working:
pytest --version

# Run manually to debug:
cd /path/to/workspace
pytest -v
```

### Empty fix_payload.toon
```bash
# If all tests pass, the tool exits early
# Check test status:
pytest

# If tests should fail but don't, verify test logic
```

## Comparison with Other Skills

| Aspect | cdscan | cdqa | dbgctxt |
|--------|--------|------|---------|
| **Purpose** | Understand structure | Check quality | Debug test failures |
| **Input** | Source code | Source code | Tests + TOON artifacts |
| **Tools** | tree-sitter, ctags, ripgrep | ruff, mypy, semgrep, radon | pytest + static analysis |
| **Focus** | Architecture, patterns | Errors, types, security | Test failures, root causes |
| **Output** | structure.toon | qa_report.toon | fix_payload.toon |
| **Use Case** | Exploration, planning | Pre-commit, audits | Test debugging, automated repair |

## Example Workflow

```bash
# User: "My tests are failing, help me debug them"

# 1. Run debugging context generator
cd /home/vscode/.claude/skills/dbgctxt
python -m dbgctxt /workspaces/my-project

# 2. Read the generated payload
cat /workspaces/my-project/fix_payload.toon

# 3. Summarize findings for the user:
# - 7 tests failed out of 45
# - 3 unique failure types identified
# - Root causes: missing zero check, API signature mismatch, missing seed data
# - Suggested fixes provided with estimated effort

# 4. Apply fixes based on recommendations
# 5. Re-run tests to verify
pytest
```
