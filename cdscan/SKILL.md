---
name: cdscan
description: Multi-tool code review using tree-sitter, ctags, and ripgrep for comprehensive codebase analysis
supported-languages: python, javascript, typescript, cpp, java, go, rust
interactive: false
stream-output: true
allowed-tools: Read, Write, Bash
invocable: true
---

# Cdscan Skill

Comprehensive codebase analysis using three complementary tools: tree-sitter (syntax parsing), ctags (definition indexing), and ripgrep (pattern search).

## How to Invoke This Skill

### Quick Invocation (Recommended)
When the user requests code analysis, use the Skill tool:
```
User: "Analyze this codebase"
Assistant: [Uses Skill tool with skill: "cdscan"]
```

This will automatically:
1. Analyze the current workspace directory
2. Auto-detect the primary language
3. Generate a comprehensive analysis report
4. Save results to `codebase_structure.toon`

### Manual Invocation (Advanced)
For more control, run the analyzer directly:

**Using run_code_review.py (full options with optional tools):**
```bash
cd /home/vscode/.claude/skills/cdscan
python run_code_review.py --workspace /workspaces/your-project --pattern "**/*.py"
```

**Using cdscan_cli.py (simplified CLI):**
```bash
cd /home/vscode/.claude/skills/cdscan
python cdscan_cli.py --workspace /workspaces/your-project --pattern "**/*.py"
```

**Command Options:**
- `--workspace <dir>`: Project directory to analyze (required)
- `--pattern <glob>`: File pattern to analyze (default: "**/*.py")
- `--language <lang>`: Primary language - python, javascript, cpp, etc. (auto-detected if not specified)
- `--output <file>`: Output file (default: codebase_structure.toon in workspace)
- `--verbose`: Enable detailed logging
- `--max-files <N>`: Maximum number of files to include in results (default: 20)
- `--max-hotspots <N>`: Maximum number of complexity hotspots (default: 15)
- `--max-apis <N>`: Maximum number of public APIs to list (default: 20)
- `--max-search-results <N>`: Maximum search results per pattern (default: 100)
- `--enable-astgrep` / `--disable-astgrep`: Enable/disable ast-grep structural analysis
- `--enable-ugrep` / `--disable-ugrep`: Enable/disable ugrep advanced search

### 3. Monitor Analysis
The analyzer runs through four stages:
1. **Tree-sitter Analysis** - Parse syntax trees, extract functions/classes
2. **Ctags Indexing** - Generate symbol definitions
3. **Ripgrep Pattern Search** - Find tests, errors, TODOs
4. **Synthesis** - Combine findings into actionable insights

### 4. Review Results
Check the output file for:
- Codebase summary (file counts, languages, structure)
- Design patterns and architecture
- Code quality metrics
- Security concerns
- Technical debt
- Integration points

## Quick Example

```bash
# User: "Analyze the Python codebase"
# You should:

# 1. Navigate to skill directory and run analyzer
cd /home/vscode/.claude/skills/cdscan
python run_code_review.py --workspace /workspaces/my-project --pattern "**/*.py" --verbose

# 2. Read the generated report
Read /workspaces/my-project/codebase_structure.toon

# 3. Summarize findings for the user
```

## What This Skill Does

### 0. Orchestrator (run_code_review.py)
- **Coordinates all analysis tools**: Tree-sitter, Ctags, Ripgrep, ast-grep, ugrep
- **Merges results**: Combines findings from all tools into unified report
- **Graceful degradation**: Works with or without optional tools installed

### 1. Tree-sitter Analysis
- **Parse source code** into abstract syntax trees (AST)
- **Extract structure**: functions, classes, methods, imports, decorators
- **Identify complexity hotspots**: deeply nested code, long functions
- **Map dependencies**: module imports, call graphs, inheritance hierarchies
- **AST-based import parsing**: Accurate import graph extraction without regex

**Supported Languages**: Python, JavaScript/TypeScript, **C++** (full support), Java, Go, Rust

### 2. Ctags Indexing
- **Generate definition index** for all symbols (functions, classes, variables)
- **Categorize APIs**: public vs internal functions, exported vs private
- **Build navigation structure**: file-to-symbol mapping
- **Track signatures**: function parameters, return types, decorators

**Output**: Tag file with searchable symbol database

### 3. Ripgrep Pattern Search
- **Fast regex matching** across entire codebase (faster than grep/ack)
- **Find test patterns**: pytest, unittest, jest patterns
- **Identify error handling**: try/except blocks, raise statements, error classes
- **Locate technical debt**: TODO, FIXME, HACK comments
- **Custom pattern search**: user-requested keywords and patterns
- **Fallback import parsing**: Uses regex when AST parsing unavailable

**Use Cases**: Security audits, test coverage analysis, deprecation tracking

### 4. ast-grep Structural Analysis (Optional)
- **Structural pattern matching**: Find code patterns (bare except, mutable defaults, console.log)
- **Anti-pattern detection**: Identify common code smells
- **Cross-language patterns**: Works across Python, JavaScript, TypeScript, C++
- **Fast and precise**: AST-based matching, not regex

**Requires**: ast-grep CLI tool (cargo/npm/brew)

### 5. ugrep Advanced Search (Optional)
- **Fuzzy search**: Approximate matching for typos and variations
- **Archive search**: Search inside .zip, .tar, .gz archives
- **PDF search**: Extract and search text from PDF files
- **Boolean expressions**: Complex search logic with AND/OR/NOT

**Requires**: ugrep CLI tool (brew/apt)

### 6. Synthesis (LLM-powered)
Combine all findings into structured insights:
- **Design patterns**: Singleton, Factory, Observer, etc.
- **Architecture style**: Microservices, monolith, layered, etc.
- **Security concerns**: SQL injection risks, XSS vulnerabilities, hardcoded secrets
- **Code quality**: Duplication, complexity, naming conventions
- **Refactoring opportunities**: Extract method, consolidate duplicates, simplify logic
- **Integration points**: APIs, database layers, external services

## Output Structure

The analyzer generates a comprehensive analysis report in **TOON format** (Token-Oriented Object Notation), optimized for LLM consumption with ~40% fewer tokens than JSON.

### TOON Format Basics

**Syntax:**
- `[N]` - Array size declaration
- `{field1, field2}` - Column headers (declared once, not per row)
- `|` - Value separator
- Indentation shows nesting

**Example TOON output:**
```toon
[3] {file, functions, complexity}
auth.py | 12 | medium
database.py | 8 | low
api.py | 25 | high
```

**When to use TOON vs JSON:**
- Use TOON for large uniform datasets (5+ rows) - more compact
- Use JSON for small/irregular/deeply nested data - more flexible

### Report Contents

The generated report includes:
- **Codebase Summary**: File counts, primary languages, directory structure
- **Architecture Analysis**: Design patterns, architectural style, component organization
- **Code Quality Metrics**: Complexity scores, duplication analysis, naming conventions
- **Security Findings**: Potential vulnerabilities (SQL injection, XSS, hardcoded secrets)
- **Technical Debt**: TODO/FIXME items, deprecated code, refactoring opportunities
- **API Inventory**: Public APIs, internal functions, integration points
- **Test Coverage**: Test file locations, test patterns, untested modules
- **Dependency Graph**: Import relationships, module coupling, circular dependencies

**Example output snippet:**
```toon
complexity_hotspots:
  [3] {file, function, lines, nesting_depth}
  utils/parser.py | parse_expression | 145 | 7
  api/handlers.py | process_request | 203 | 6
  core/engine.py | execute_pipeline | 178 | 5

security_findings:
  [2] {severity, type, location, description}
  high | sql_injection | db/queries.py:42 | Direct string interpolation in SQL query
  medium | hardcoded_secret | config/settings.py:15 | API key visible in source code
```

## When to Use This Skill

Use when you need to:
- ✅ **Understand new codebase** - Quickly grasp architecture and structure
- ✅ **Plan refactoring** - Identify code smells and improvement opportunities
- ✅ **Security audit** - Find potential vulnerabilities (SQL injection, XSS, etc.)
- ✅ **Design review** - Validate patterns and architectural decisions
- ✅ **Technical debt assessment** - Locate TODOs, FIXMEs, and legacy code
- ✅ **Integration planning** - Find APIs, database layers, external services
- ✅ **Documentation generation** - Create codebase maps and references

**Don't use for:**
- ❌ Greenfield projects (no existing code to analyze)
- ❌ Single-file analysis (use Read tool instead)
- ❌ Real-time linting (use ruff, eslint, etc.)


## Analysis Process

### Stage 1: Tree-sitter Parsing

```python
from tools.treesitter_analyzer import TreeSitterAnalyzer

analyzer = TreeSitterAnalyzer(workspace="/workspaces/project")
results = analyzer.analyze_directory(pattern="**/*.py")

# Results include:
# - Function definitions (name, parameters, line numbers)
# - Class hierarchies (inheritance, methods, attributes)
# - Import statements (modules, symbols, aliases) - extracted from AST
# - Complexity metrics (nesting depth, cyclomatic complexity)
# - Import graph built from AST (not regex)
```

**C++ Support**: Fully parses classes, functions, methods, namespaces, and `#include` directives:
```python
# Analyze C++ codebase
results = analyzer.analyze_directory(pattern="**/*.{cpp,hpp,h}")
# Extracts: class definitions, function signatures, includes, templates
```

### Stage 2: Ctags Indexing

```python
from tools.ctags_indexer import CtagsIndexer

indexer = CtagsIndexer(workspace="/workspaces/project")
indexer.generate_tags()  # Creates tags file

# Query results:
public_apis = indexer.get_public_apis()        # Functions/classes without _prefix
internal = indexer.get_internal_functions()    # _private functions
all_symbols = indexer.search_symbol("User")    # Find all User references
```

### Stage 3: Ripgrep Search

```python
from tools.ripgrep_searcher import RipgrepSearcher

searcher = RipgrepSearcher(workspace="/workspaces/project")

# Find test files
test_files = searcher.get_test_files()  # pytest, unittest, jest patterns

# Find error patterns
errors = searcher.search_error_patterns()  # try/except, raise, error classes

# Find technical debt
todos = searcher.search_todo_fixme()  # TODO, FIXME, HACK, XXX

# Custom search
results = searcher.search_pattern(r"sql.*execute", file_type="py")
```

### Stage 4: LLM Synthesis

The analyzer uses a language model (GLM-4 or similar) to:
1. **Combine findings** from all three tools
2. **Identify patterns** (design patterns, anti-patterns)
3. **Assess quality** (complexity, duplication, test coverage)
4. **Generate recommendations** (refactoring, security fixes)
5. **Prioritize issues** (critical → low severity)


## Implementation Files

```
cdscan/
├── SKILL.md                          # This file
├── run_code_review.py                # Main entry point (orchestrator)
├── cdscan_cli.py                     # CLI interface
├── tools/
│   ├── treesitter_analyzer.py        # AST parsing and structure extraction
│   ├── ctags_indexer.py              # Symbol indexing and navigation
│   ├── ripgrep_searcher.py           # Pattern search and keyword finding
│   ├── astgrep_analyzer.py           # Structural pattern matching (optional)
│   ├── ugrep_searcher.py             # Advanced search capabilities (optional)
│   └── toon_serializer.py           # TOON format serialization
└── README.md                         # Quick start guide
```
