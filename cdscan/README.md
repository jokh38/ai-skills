# Cdscan Skill v2.0

Multi-tool code review using tree-sitter, ctags, ripgrep, ast-grep, and ugrep for comprehensive codebase analysis.

## New Features in v2.0 ✨

- **Universal Ctags Verification**: Auto-detects and logs ctags version (Universal Ctags recommended)
- **ast-grep Integration**: Structural pattern matching for deeper code analysis (optional)
- **ugrep Advanced Search**: Fuzzy search, archive search, and PDF search capabilities (optional)
- **Graceful Fallback**: Works with or without optional tools installed

### v1.x Features
- **C++ Support**: Full AST parsing for C++ (classes, functions, methods, includes)
- **AST-based Import Parsing**: Accurate import graphs extracted from AST instead of regex
- **Configurable Limits**: Control output size with `--max-files`, `--max-hotspots`, `--max-apis`, `--max-search-results`

## Quick Start

### Option 1: Using run_code_review.py (Full Features)

```bash
# Basic usage
cd /home/vscode/.claude/skills/cdscan
python run_code_review.py --workspace /path/to/project

# Python codebase
python run_code_review.py --workspace /path/to/project --pattern "**/*.py"

# C++ codebase with limits
python run_code_review.py \
  --workspace /path/to/cpp-project \
  --pattern "**/*.{cpp,hpp,h}" \
  --language cpp \
  --max-files 30 \
  --max-hotspots 10

# JavaScript/TypeScript with verbose output
python run_code_review.py \
  --workspace /workspaces/webapp \
  --pattern "**/*.{js,ts}" \
  --language javascript \
  --verbose
```

### Option 2: Using cdscan_cli.py (Simplified CLI)

```bash
# Basic analysis
cd /home/vscode/.claude/skills/cdscan
python cdscan_cli.py --workspace /path/to/project

# With context and language
python cdscan_cli.py --workspace /path/to/project --language python

# Custom output and pattern
python cdscan_cli.py --workspace . --pattern "**/*.py" --output analysis.toon

# Limit output size
python cdscan_cli.py --workspace . --max-files 10 --max-hotspots 5

# With user request context
python cdscan_cli.py --workspace . --request "Find authentication logic"

# Verbose output
python cdscan_cli.py --workspace . --verbose
```

## What It Does

1. **Tree-sitter Analysis** - Parse syntax trees, extract functions/classes, identify complexity, build import graphs from AST
2. **Ctags Indexing** - Generate symbol index, categorize public APIs vs internal functions (Universal Ctags detected)
3. **Ripgrep Search** - Find tests, error patterns, TODOs, security issues
4. **ast-grep Structural Analysis** - Find common code patterns (bare except, mutable defaults, console.log, etc.)
5. **ugrep Advanced Search** - Fuzzy search, archive search, and PDF search (optional)
6. **Synthesis** - Combine findings into actionable insights

## Output

Generates `codebase_structure.toon` in **TOON format** (Token-Oriented Object Notation) with:
- Codebase summary (files, functions, classes)
- Structure analysis (modules, design patterns)
- Definition index (public APIs, internal functions)
- Pattern findings (tests, errors, technical debt, **import graph with AST source**)
- Code quality metrics (complexity, security)
- Recommendations (refactoring, improvements)
- Integration points (databases, APIs, frameworks)

**TOON format** uses ~40% fewer tokens than JSON, optimized for LLM consumption.

## Command Options

### run_code_review.py Options
```
--workspace <dir>          # Project directory (required)
--pattern <glob>           # File glob pattern (default: **/*.py)
--language <lang>          # Primary language: python, javascript, cpp, etc.
--output <file>            # Output file path (default: codebase_structure.toon)
--verbose                  # Enable detailed logging
--max-files <N>            # Max files in results (default: 20)
--max-hotspots <N>         # Max complexity hotspots (default: 15)
--max-apis <N>             # Max public APIs to list (default: 20)
--max-search-results <N>   # Max search results per pattern (default: 100)
--enable-astgrep           # Enable ast-grep structural analysis (default: True)
--disable-astgrep          # Disable ast-grep analysis
--enable-ugrep             # Enable ugrep advanced search (default: True)
--disable-ugrep            # Disable ugrep search
```

### cdscan_cli.py Options
```
--workspace PATH           # Project directory to analyze (required)
--pattern GLOB             # File glob pattern (default: **/*.py)
--language LANG            # Primary programming language (default: python)
--output FILE              # Output file path (default: <workspace>/codebase_structure.toon)
--request TEXT             # User request/context for the analysis
--verbose                  # Enable verbose logging output
--max-files N              # Maximum number of files to include in results (default: 20)
--max-hotspots N           # Maximum number of complexity hotspots (default: 15)
--max-apis N               # Maximum number of public APIs to list (default: 20)
--max-search-results N     # Maximum search results per pattern (default: 100)
--version                  # Show program version number
```

## Prerequisites

### Required Tools

**1. Tree-sitter** (syntax parsing)
```bash
pip install tree-sitter tree-sitter-python tree-sitter-javascript tree-sitter-cpp tree-sitter-typescript
```

**2. Ctags** (symbol indexing)
```bash
# macOS (Universal Ctags)
brew install universal-ctags

# Ubuntu/Debian
sudo apt-get install universal-ctags

# Verify
ctags --version  # Should show "Universal Ctags"
```

**3. Ripgrep** (fast search)
```bash
# macOS
brew install ripgrep

# Ubuntu/Debian
apt-get install ripgrep

# Verify
rg --version
```

### Optional Tools (Enhanced Features)

**4. ast-grep** (structural pattern matching)
```bash
# Install via cargo (recommended)
cargo install ast-grep

# Or via npm
npm install -g @ast-grep/cli

# Or via brew (macOS)
brew install ast-grep

# Verify
ast-grep --version
```

**5. ugrep** (advanced search with fuzzy matching)
```bash
# macOS
brew install ugrep

# Ubuntu/Debian
sudo apt-get install ugrep

# Verify
ugrep --version
```

### Language Parsers

```bash
# Python
pip install tree-sitter-python

# JavaScript/TypeScript
pip install tree-sitter-javascript tree-sitter-typescript

# C++ (Full AST support for classes, functions, includes)
pip install tree-sitter-cpp

# Verify all parsers
python -c "import tree_sitter_python, tree_sitter_cpp, tree_sitter_javascript; print('All parsers installed')"
```

**Note**: Modern tree-sitter (v0.25+) uses a simplified API:
```python
import tree_sitter_python as tspython
from tree_sitter import Language, Parser

PY_LANGUAGE = Language(tspython.language())
parser = Parser(PY_LANGUAGE)
tree = parser.parse(bytes(code, "utf8"))
```

## Example Workflows

**Note**: All examples use `run_code_review.py` for full feature access. You can also use `cdscan_cli.py` with the same core options (without `--enable-astgrep`/`--enable-ugrep` flags).

### Python Project Analysis
```bash
python run_code_review.py \
  --workspace /workspaces/myapp \
  --pattern "**/*.py" \
  --max-files 25
```

### C++ Security Audit
```bash
python run_code_review.py \
  --workspace /workspaces/cpp-project \
  --pattern "**/*.{cpp,hpp,h,cc,cxx}" \
  --language cpp \
  --output security_audit.toon

# Review the TOON output
cat security_audit.toon
```

### JavaScript Codebase Overview
```bash
python run_code_review.py \
  --workspace /workspaces/webapp \
  --pattern "**/*.{js,ts}" \
  --language javascript

# Review the structured output
cat codebase_structure.toon
```

### Focused Module Analysis
```bash
# Analyze only authentication module
python run_code_review.py \
  --workspace /workspaces/platform \
  --pattern "src/auth/**/*.py" \
  --output auth_analysis.toon

# Review findings
cat auth_analysis.toon
```

### Enhanced Analysis with ast-grep and ugrep (Option B)
```bash
# Full analysis with all optional tools
python run_code_review.py \
  --workspace /workspaces/myproject \
  --pattern "**/*.py" \
  --enable-astgrep \
  --enable-ugrep \
  --verbose

# Results will include:
# - Structural patterns from ast-grep (bare except, mutable defaults, etc.)
# - Archive search findings from ugrep
# - Fuzzy search results
# - Documentation keyword search
```

### Selective Tool Usage
```bash
# Enable only ast-grep (structural patterns)
python run_code_review.py \
  --workspace /workspaces/myproject \
  --pattern "**/*.py" \
  --enable-astgrep \
  --disable-ugrep

# Enable only ugrep (archive/search features)
python run_code_review.py \
  --workspace /workspaces/myproject \
  --pattern "**/*.py" \
  --disable-astgrep \
  --enable-ugrep

# Disable both (Option A - conservative)
python run_code_review.py \
  --workspace /workspaces/myproject \
  --pattern "**/*.py" \
  --disable-astgrep \
  --disable-ugrep
```

## Best Practices

### Performance Optimization

**Use specific patterns** - Narrow scope with globs
```bash
--pattern "src/**/*.py"           # Only src directory
--pattern "**/*.{js,ts}"          # Multiple extensions
--pattern "**/*.{cpp,hpp,h}"      # C++ files
```

**Configure limits** - Adjust for large codebases
```bash
python run_code_review.py \
  --workspace /workspaces/large-project \
  --max-files 10 \
  --max-hotspots 5 \
  --max-apis 15 \
  --max-search-results 50
```

**Cache results** - Reuse existing analysis
```bash
# Only re-run if significant changes
if [[ $(git diff --name-only HEAD~1 | wc -l) -gt 10 ]]; then
  python run_code_review.py --workspace .
fi
```

## Troubleshooting

### ast-grep not available
```bash
# If you see "ast-grep not available, skipping structural analysis"
# Install it with one of these methods:

# Method 1: cargo (recommended, if you have Rust)
cargo install ast-grep

# Method 2: npm
npm install -g @ast-grep/cli

# Method 3: brew (macOS)
brew install ast-grep

# Verify installation
ast-grep --version
```

### ugrep not available
```bash
# If you see "ugrep not available, skipping advanced search"
# Install it:

# macOS
brew install ugrep

# Ubuntu/Debian
sudo apt-get install ugrep

# Verify installation
ugrep --version
```

### Tree-sitter parser not found
```bash
# Error: "Parser for Python not found"
pip install tree-sitter-python tree-sitter-cpp

# Verify installation (modern API)
python -c "import tree_sitter_python as tspython; from tree_sitter import Language, Parser; lang = Language(tspython.language()); parser = Parser(lang); print('OK')"
```

### Tree-sitter API errors
```bash
# Error: "language must be assigned a tree_sitter.Language object"
# You're using old API. Update to modern API (v0.25+):

# ❌ Old (deprecated)
# parser.set_language(language())

# ✅ New (v0.25+)
from tree_sitter import Language, Parser
import tree_sitter_python as tspython
PY_LANGUAGE = Language(tspython.language())
parser = Parser(PY_LANGUAGE)
```

### Ctags not generating tags
```bash
# Ensure it's exuberant-ctags or universal-ctags, not BSD ctags
which ctags
ctags --version  # Should be "Exuberant Ctags" or "Universal Ctags"

# macOS: Replace BSD ctags
brew install ctags
```

### Ripgrep search too slow
```bash
# Use file type filters
rg --type py "pattern"  # Faster than **/*.py

# Exclude large directories
rg "pattern" --glob '!node_modules' --glob '!.venv' --glob '!build'
```

## Tool Structure

```
cdscan/
├── SKILL.md                      # Complete skill documentation
├── README.md                     # This quick start guide
├── run_code_review.py            # Main entry point (orchestrator)
├── cdscan_cli.py                 # CLI interface
└── tools/
    ├── treesitter_analyzer.py    # AST parsing and import graphs
    ├── ctags_indexer.py          # Symbol indexing (Universal Ctags)
    ├── ripgrep_searcher.py       # Pattern search
    ├── astgrep_analyzer.py       # Structural pattern matching (optional)
    ├── ugrep_searcher.py         # Advanced search (optional)
    └── toon_serializer.py        # TOON format output
```

## v2.0 Upgrade Notes

### What Changed
- **Universal Ctags Detection**: Automatically detects ctags version and logs if using Universal Ctags
- **ast-grep Integration**: Optional structural pattern matching added
- **ugrep Integration**: Optional advanced search capabilities added
- **Graceful Degradation**: Works without optional tools, just with enhanced features when available
- **Configurable Tool Enablement**: Enable/disable optional tools via command-line flags

### Migration from v1.x
No breaking changes! Simply:
1. Ensure you're using Universal Ctags (check with `ctags --version`)
2. Optionally install ast-grep for structural analysis
3. Optionally install ugrep for advanced search
4. Run the same commands as before

### Option A vs Option B

**Option A (Conservative - Default)**:
- Universal Ctags verification
- Optional ast-grep (structural patterns)
- Optional ugrep (basic advanced search)
- Tools enabled by default but gracefully skipped if not installed
- Minimal overhead

**Option B (Enhanced - With Optional Tools Installed)**:
- All Option A features
- ast-grep finds: bare except, mutable defaults, console.log, etc.
- ugrep provides: fuzzy search, archive search, PDF search, documentation keywords
- Best for projects needing deeper analysis and advanced search
- Install optional tools to unlock full potential

### Why Upgrade?
- **Universal Ctags**: Better language support and active development
- **ast-grep**: Deeper code analysis with structural patterns
- **ugrep**: Fuzzy search, archive/PDF search, documentation keywords
- **Configurable**: Enable only the tools you need

### Performance Impact
- Minimal performance overhead (optional tools run only if installed/enabled)
- All existing functionality preserved
- New features add ~2-5 seconds to analysis time when enabled
- Can disable tools completely with `--disable-astgrep --disable-ugrep`

## See Also

- [SKILL.md](SKILL.md) - Complete skill documentation
- [Tree-sitter Documentation](https://tree-sitter.github.io/tree-sitter/)
- [Ctags Documentation](https://ctags.io/)
- [Ripgrep Documentation](https://github.com/BurntSushi/ripgrep)
