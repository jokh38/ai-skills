"""
Tree-sitter based code analyzer for syntax parsing and structure extraction.

Parses source code into abstract syntax trees (AST) and extracts:
- Functions and classes
- Module dependencies
- Complexity metrics
- Call graphs
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
import json
import logging

from utils import should_exclude_file, extract_module_name, NodeTraversalHelper

try:
    from tree_sitter import Language, Parser, Node

    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    logging.warning("tree-sitter not available. Install with: pip install tree-sitter")
    Language = None
    Parser = None
    Node = None


class TreeSitterAnalyzer:
    """Analyzes code structure using tree-sitter parsers."""

    LANGUAGE_EXTENSIONS = {
        "python": [".py"],
        "javascript": [".js", ".jsx"],
        "typescript": [".ts", ".tsx"],
        "cpp": [".cpp", ".cc", ".cxx", ".hpp", ".h"],
        "java": [".java"],
        "go": [".go"],
        "rust": [".rs"],
    }

    def __init__(self, workspace: str):
        """
        Initialize analyzer.

        Args:
            workspace: Root directory to analyze
        """
        self.workspace = Path(workspace)
        self.parsers = {}
        self.results = {
            "files": [],
            "total_functions": 0,
            "total_classes": 0,
            "complexity_hotspots": [],
            "imports": [],
            "entry_points": [],
            "file_purposes": [],
            "call_graph": [],
        }

        if not TREE_SITTER_AVAILABLE:
            logging.error("tree-sitter not installed. Analysis will be limited.")
            return

        self._load_parsers()

    def _load_parsers(self):
        """Load tree-sitter parsers for supported languages."""
        if not TREE_SITTER_AVAILABLE:
            return

        # Try to load parsers for each language
        for lang in ["python", "javascript", "typescript", "cpp", "java", "go", "rust"]:
            try:
                # Attempt to import language-specific parser
                if lang == "python":
                    import tree_sitter_python as tspython

                    PY_LANGUAGE = Language(tspython.language())
                    parser = Parser(PY_LANGUAGE)
                    self.parsers["python"] = parser
                    logging.info(f"Loaded parser for {lang}")
                elif lang == "cpp":
                    import tree_sitter_cpp as tscpp

                    CPP_LANGUAGE = Language(tscpp.language())
                    parser = Parser(CPP_LANGUAGE)
                    self.parsers["cpp"] = parser
                    logging.info(f"Loaded parser for {lang}")
                elif lang == "javascript":
                    import tree_sitter_javascript as tsjs

                    JS_LANGUAGE = Language(tsjs.language())
                    parser = Parser(JS_LANGUAGE)
                    self.parsers["javascript"] = parser
                    logging.info(f"Loaded parser for {lang}")
                elif lang == "typescript":
                    import tree_sitter_typescript.typescript as tsts

                    TS_LANGUAGE = Language(tsts.language())
                    parser = Parser(TS_LANGUAGE)
                    self.parsers["typescript"] = parser
                    logging.info(f"Loaded parser for {lang}")
                # Add other languages as needed
            except ImportError:
                logging.debug(f"Parser for {lang} not available")
            except Exception as e:
                logging.warning(f"Failed to load parser for {lang}: {e}")

    def analyze_directory(self, pattern: str = "**/*.py") -> Dict[str, Any]:
        """
        Analyze all files matching pattern in workspace.

        Args:
            pattern: Glob pattern for files to analyze

        Returns:
            Dictionary with analysis results
        """
        if not TREE_SITTER_AVAILABLE or not self.parsers:
            return self._fallback_analysis(pattern)

        files = []
        for ext in ["**/*.py", "**/*.js", "**/*.ts", "**/*.cpp", "**/*.java"]:
            for f in self.workspace.glob(ext):
                if not should_exclude_file(f):
                    files.append(f)

        logging.info(f"Found {len(files)} files (after filtering)")

        for file_path in files:
            try:
                self._analyze_file(file_path)
            except Exception as e:
                logging.error(f"Failed to analyze {file_path}: {e}")

        # Identify complexity hotspots (top 20 most complex functions)
        self.results["complexity_hotspots"] = sorted(
            self.results.get("all_functions", []),
            key=lambda f: f.get("complexity", 0),
            reverse=True,
        )[:20]

        # Build import graph from AST data
        self.results["import_graph"] = self._build_import_graph()

        # Build global call graph from per-file calls
        self.results["call_graph"] = self._build_call_graph()

        # Simplify imports in each file for compact output
        for file_info in self.results.get("files", []):
            file_info["imports"] = self._simplify_imports(file_info.get("imports", []))

        return self.results

    def _analyze_file(self, file_path: Path):
        """
        Analyze a single file.

        Args:
            file_path: Path to source file
        """
        # Detect language from extension
        ext = file_path.suffix
        language = None
        for lang, exts in self.LANGUAGE_EXTENSIONS.items():
            if ext in exts:
                language = lang
                break

        if not language or language not in self.parsers:
            logging.debug(f"No parser for {file_path}")
            return

        parser = self.parsers[language]

        with open(file_path, "rb") as f:
            source_code = f.read()

        tree = parser.parse(source_code)
        root_node = tree.root_node

        file_result = {
            "path": str(file_path.relative_to(self.workspace)),
            "language": language,
            "functions": [],
            "classes": [],
            "imports": [],
            "docstring": None,
            "entry_point": None,
            "calls": [],
        }

        # Extract functions, classes, imports based on language
        if language == "python":
            self._extract_structure(root_node, file_result, source_code, "python")
            self._extract_python_docstring(root_node, file_result, source_code)
            self._extract_python_entry_point(root_node, file_result, source_code)
            self._extract_python_calls(root_node, file_result, source_code)
        elif language == "cpp":
            self._extract_structure(root_node, file_result, source_code, "cpp")

        self.results["files"].append(file_result)
        self.results["total_functions"] += len(file_result["functions"])
        self.results["total_classes"] += len(file_result["classes"])

        # Add entry point if found
        if file_result.get("entry_point"):
            self.results["entry_points"].append(
                {
                    "file": file_result["path"],
                    "type": file_result["entry_point"]["type"],
                    "line": file_result["entry_point"]["line"],
                }
            )

        # Add file purpose if docstring found
        if file_result.get("docstring"):
            self.results["file_purposes"].append(
                {
                    "path": file_result["path"],
                    "purpose": file_result["docstring"][:100],  # Truncate for brevity
                }
            )

    def _extract_structure(
        self, node: "Node", file_result: Dict, source: bytes, language: str
    ):
        """
        Extract structure from AST using language-specific configuration.

        Args:
            node: Tree-sitter node
            file_result: Dictionary to store results
            source: Source code bytes
            language: Programming language
        """
        # Language-specific extraction configuration
        lang_configs = {
            "python": {
                "function_types": ["function_definition"],
                "class_types": ["class_definition"],
                "import_types": ["import_statement", "import_from_statement"],
                "get_function_name": self._get_function_name,
                "get_function_params": self._get_function_params,
                "get_class_name": self._get_class_name,
                "get_class_methods": self._get_class_methods,
                "get_import_info": self._get_import_info,
            },
            "cpp": {
                "function_types": ["function_definition"],
                "class_types": ["class_specifier", "struct_specifier"],
                "import_types": ["preproc_include"],
                "get_function_name": self._get_cpp_function_name,
                "get_function_params": self._get_cpp_function_params,
                "get_class_name": self._get_cpp_class_name,
                "get_class_methods": self._get_cpp_class_methods,
                "get_import_info": self._get_cpp_include_info,
            },
        }

        config = lang_configs.get(language, lang_configs["python"])

        def traverse(n: "Node", depth: int = 0):
            # Extract functions
            if n.type in config["function_types"]:
                func_name = config["get_function_name"](n, source)
                params = config["get_function_params"](n, source)
                file_result["functions"].append(
                    {
                        "name": func_name,
                        "line": n.start_point[0] + 1,
                        "params": params,
                        "complexity": self._estimate_complexity(n),
                        "nesting_depth": depth,
                    }
                )

            # Extract classes
            elif n.type in config["class_types"]:
                class_name = config["get_class_name"](n, source)
                methods = config["get_class_methods"](n, source)
                file_result["classes"].append(
                    {
                        "name": class_name,
                        "line": n.start_point[0] + 1,
                        "methods": methods,
                    }
                )

            # Extract imports
            elif n.type in config["import_types"]:
                import_info = config["get_import_info"](n, source)
                if import_info:
                    file_result["imports"].append(import_info)

            # Recurse to children
            for child in n.children:
                traverse(child, depth + 1)

        traverse(node)

    def _get_function_name(self, node: "Node", source: bytes) -> str:
        """Extract function name from node."""
        return NodeTraversalHelper.extract_name(node, source, ["identifier"])

    def _get_function_params(self, node: "Node", source: bytes) -> List[str]:
        """Extract function parameters."""
        params = []
        param_list = NodeTraversalHelper.find_child_by_type(node, "parameters")
        if param_list:
            for param in param_list.children:
                if param.type == "identifier":
                    params.append(NodeTraversalHelper.extract_text(param, source))
        return params

    def _get_class_name(self, node: "Node", source: bytes) -> str:
        """Extract class name from node."""
        return NodeTraversalHelper.extract_name(node, source, ["identifier"])

    def _get_class_methods(self, node: "Node", source: bytes) -> List[str]:
        """Extract method names from class."""
        methods = []
        block = NodeTraversalHelper.find_child_by_type(node, "block")
        if block:
            for stmt in block.children:
                if stmt.type == "function_definition":
                    methods.append(self._get_function_name(stmt, source))
        return methods

    def _get_import_info(self, node: "Node", source: bytes) -> Optional[Dict]:
        """Extract import information."""
        import_text = NodeTraversalHelper.extract_text(node, source)
        return {
            "statement": import_text,
            "line": node.start_point[0] + 1,
        }

    def _extract_python_docstring(self, node: "Node", file_result: Dict, source: bytes):
        """
        Extract module-level docstring from Python file.

        The module docstring is the first expression statement that is a string.
        """
        for child in node.children:
            if child.type == "expression_statement":
                for subchild in child.children:
                    if subchild.type == "string":
                        docstring = source[
                            subchild.start_byte : subchild.end_byte
                        ].decode("utf-8")
                        # Clean up the docstring (remove quotes and whitespace)
                        docstring = docstring.strip("\"' \n\r\t")
                        if docstring:
                            # Get first line/sentence as purpose
                            first_line = docstring.split("\n")[0].strip()
                            file_result["docstring"] = first_line
                        return
            # Stop at first non-docstring statement
            elif child.type not in ["comment", "expression_statement"]:
                return

    def _extract_python_entry_point(
        self, node: "Node", file_result: Dict, source: bytes
    ):
        """
        Extract entry point from Python file.

        Detects `if __name__ == '__main__':` blocks.
        """
        for child in node.children:
            if child.type == "if_statement":
                # Check if this is the __name__ == '__main__' pattern
                for subchild in child.children:
                    if subchild.type == "comparison_operator":
                        condition_text = source[
                            subchild.start_byte : subchild.end_byte
                        ].decode("utf-8")
                        if (
                            "__name__" in condition_text
                            and "__main__" in condition_text
                        ):
                            file_result["entry_point"] = {
                                "type": "main_block",
                                "line": child.start_point[0] + 1,
                            }
                            return

    def _extract_python_calls(self, node: "Node", file_result: Dict, source: bytes):
        """
        Extract function calls within functions to build call graph.

        Captures which functions call which other functions.
        """
        current_function = None
        calls_map = {}  # function_name -> [called_functions]

        def traverse(n: "Node", in_function: str = None):
            nonlocal current_function

            if n.type == "function_definition":
                # Get function name
                func_name = self._get_function_name(n, source)
                if func_name not in calls_map:
                    calls_map[func_name] = set()
                # Recurse into function body with this function as context
                for child in n.children:
                    if child.type == "block":
                        traverse(child, func_name)
                return

            if n.type == "call":
                # Extract called function name
                for child in n.children:
                    if child.type == "identifier":
                        called = source[child.start_byte : child.end_byte].decode(
                            "utf-8"
                        )
                        if (
                            in_function and called != in_function
                        ):  # Avoid self-recursion noise
                            calls_map.setdefault(in_function, set()).add(called)
                        break
                    elif child.type == "attribute":
                        # method calls like obj.method()
                        attr_text = source[child.start_byte : child.end_byte].decode(
                            "utf-8"
                        )
                        if in_function:
                            calls_map.setdefault(in_function, set()).add(attr_text)
                        break

            # Recurse
            for child in n.children:
                traverse(child, in_function)

        traverse(node)

        # Convert to list format for serialization
        for caller, callees in calls_map.items():
            for callee in callees:
                file_result["calls"].append(
                    {
                        "caller": caller,
                        "callee": callee,
                    }
                )

    def _estimate_complexity(self, node: "Node") -> int:
        """
        Estimate cyclomatic complexity of a function.

        Counts decision points: if, elif, for, while, except, and, or, etc.
        """
        complexity = 1  # Base complexity

        def count_branches(n: "Node"):
            nonlocal complexity
            # Control flow keywords that increase complexity
            if n.type in [
                "if_statement",
                "elif_clause",
                "for_statement",
                "while_statement",
                "except_clause",
                "boolean_operator",
            ]:
                complexity += 1

            for child in n.children:
                count_branches(child)

        count_branches(node)
        return complexity

    def _get_cpp_function_name(self, node: "Node", source: bytes) -> str:
        """Extract C++ function name from node."""
        declarator = NodeTraversalHelper.find_child_by_type(node, "function_declarator")
        if declarator:
            name = NodeTraversalHelper.extract_name(
                declarator, source, ["identifier", "field_identifier"]
            )
            if name != "unknown":
                return name

            # Handle qualified identifiers
            qual_id = NodeTraversalHelper.find_child_by_type(
                declarator, "qualified_identifier"
            )
            if qual_id:
                for qchild in qual_id.children:
                    if qchild.type == "identifier":
                        return NodeTraversalHelper.extract_text(qchild, source)

        return "unknown"

    def _get_cpp_function_params(self, node: "Node", source: bytes) -> List[str]:
        """Extract C++ function parameters."""
        params = []
        declarator = NodeTraversalHelper.find_child_by_type(node, "function_declarator")
        if declarator:
            param_list = NodeTraversalHelper.find_child_by_type(
                declarator, "parameter_list"
            )
            if param_list:
                for param in param_list.children:
                    if param.type == "parameter_declaration":
                        param_name = NodeTraversalHelper.find_child_by_type(
                            param, "identifier"
                        )
                        if param_name:
                            params.append(
                                NodeTraversalHelper.extract_text(param_name, source)
                            )
        return params

    def _get_cpp_class_name(self, node: "Node", source: bytes) -> str:
        """Extract C++ class/struct name from node."""
        return NodeTraversalHelper.extract_name(node, source, ["type_identifier"])

    def _get_cpp_class_methods(self, node: "Node", source: bytes) -> List[str]:
        """Extract method names from C++ class."""
        methods = []
        field_list = NodeTraversalHelper.find_child_by_type(
            node, "field_declaration_list"
        )
        if field_list:
            for stmt in field_list.children:
                if stmt.type == "function_definition":
                    methods.append(self._get_cpp_function_name(stmt, source))
        return methods

    def _get_cpp_include_info(self, node: "Node", source: bytes) -> Optional[Dict]:
        """Extract C++ include information."""
        include_text = NodeTraversalHelper.extract_text(node, source)
        return {
            "statement": include_text,
            "line": node.start_point[0] + 1,
        }

    def _build_import_graph(self) -> Dict[str, Any]:
        """
        Build import/dependency graph from AST data.

        Returns:
            Dictionary with import information extracted from AST
        """
        modules = {}
        external_deps = set()
        total_imports = 0

        for file_info in self.results.get("files", []):
            file_path = file_info["path"]
            language = file_info.get("language", "unknown")

            for import_info in file_info.get("imports", []):
                total_imports += 1
                statement = import_info.get("statement", "")

                # Extract module name based on language
                module = extract_module_name(statement, language)

                if module:
                    # Check if external (no relative path)
                    if not module.startswith(".") and not module.startswith("/"):
                        external_deps.add(module)

                    # Track which files import this module
                    if module not in modules:
                        modules[module] = []
                    modules[module].append(file_path)

        return {
            "total_imports": total_imports,
            "unique_modules": len(modules),
            "external_dependencies": sorted(list(external_deps))[:30],
            "most_imported": sorted(
                [(mod, len(files)) for mod, files in modules.items()],
                key=lambda x: x[1],
                reverse=True,
            )[:15],
            "source": "ast",  # Indicate this came from AST parsing
        }

    def _build_call_graph(self) -> List[Dict[str, str]]:
        """
        Build global call graph from per-file call data.

        Returns:
            List of {caller, callee, file} dicts
        """
        call_graph = []

        for file_info in self.results.get("files", []):
            file_path = file_info["path"]
            for call in file_info.get("calls", []):
                call_graph.append(
                    {
                        "caller": call["caller"],
                        "callee": call["callee"],
                        "file": file_path,
                    }
                )

        # Limit to most interesting calls (filter out common builtins)
        common_builtins = {
            "print",
            "len",
            "str",
            "int",
            "float",
            "list",
            "dict",
            "set",
            "tuple",
            "range",
            "enumerate",
            "zip",
            "map",
            "filter",
            "sorted",
            "reversed",
            "open",
            "isinstance",
            "hasattr",
            "getattr",
            "setattr",
            "super",
            "type",
        }

        filtered = [c for c in call_graph if c["callee"] not in common_builtins]

        return filtered[:50]  # Limit for output size

    def _simplify_imports(self, imports: List[Dict]) -> Dict[str, List[str]]:
        """
        Simplify imports from [{statement, line}, ...] to categorized format.

        Returns:
            Dict with 'stdlib', 'internal', 'external' lists
        """
        stdlib = set()
        internal = set()
        external = set()

        # Common Python standard library modules
        stdlib_modules = {
            "os",
            "sys",
            "re",
            "json",
            "typing",
            "pathlib",
            "logging",
            "datetime",
            "collections",
            "itertools",
            "functools",
            "operator",
            "subprocess",
            "argparse",
            "unittest",
            "io",
            "tempfile",
            "shutil",
            "copy",
            "math",
            "random",
            "time",
            "threading",
            "multiprocessing",
            "socket",
            "http",
            "urllib",
            "email",
            "html",
            "xml",
            "sqlite3",
            "csv",
            "pickle",
            "hashlib",
            "base64",
            "ast",
            "inspect",
            "traceback",
            "contextlib",
            "abc",
            "dataclasses",
            "enum",
            "textwrap",
            "string",
            "struct",
            "array",
            "queue",
            "heapq",
            "bisect",
            "weakref",
            "types",
            "warnings",
            "dis",
            "gc",
            "platform",
            "signal",
        }

        for imp in imports:
            statement = imp.get("statement", "")

            # Extract module name
            module = None
            if statement.startswith("import "):
                parts = statement[7:].split()
                if parts:
                    module = parts[0].strip(",").split(".")[0]
            elif statement.startswith("from "):
                parts = statement[5:].split(" import")
                if parts:
                    module = parts[0].strip().split(".")[0]

            if module:
                # Categorize
                if module.startswith("."):
                    internal.add(module)
                elif module in stdlib_modules:
                    stdlib.add(module)
                elif module.startswith("_") or module in ["tools", "src", "lib"]:
                    internal.add(module)
                else:
                    external.add(module)

        result = {}
        if stdlib:
            result["stdlib"] = sorted(stdlib)
        if internal:
            result["internal"] = sorted(internal)
        if external:
            result["external"] = sorted(external)

        return result

    def _extract_python_structure_fallback(self, code: str) -> Dict[str, Any]:
        """
        Extract Python structure from code string (simplified version using ast module).

        Args:
            code: Python source code string

        Returns:
            Dictionary with extracted structure
        """
        import ast

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return {"functions": [], "classes": [], "imports": []}

        result = {"functions": [], "classes": [], "imports": []}

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                result["functions"].append(
                    {
                        "name": node.name,
                        "lineno": node.lineno,
                        "args": [arg.arg for arg in node.args.args],
                    }
                )
            elif isinstance(node, ast.ClassDef):
                result["classes"].append({"name": node.name, "lineno": node.lineno})
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        result["imports"].append({"name": alias.name})
                else:
                    result["imports"].append({"module": node.module or ""})

        return result

    def _estimate_complexity_fallback(self, code: str) -> int:
        """
        Estimate complexity from code string (fallback method).

        Args:
            code: Source code string

        Returns:
            Complexity score
        """
        complexity = 1
        keywords = ["if", "elif", "for", "while", "except", "and", "or"]

        for keyword in keywords:
            complexity += code.count(f" {keyword} ") + code.count(f"{keyword}(")

        return complexity

    def _get_imports(self, code: str) -> List[str]:
        """
        Extract imports from code string.

        Args:
            code: Source code string

        Returns:
            List of import statements
        """
        import ast

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return []

        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")

        return imports

    def search_pattern(self, pattern: str) -> List[Dict[str, Any]]:
        """
        Search for pattern in analyzed files.

        Args:
            pattern: Pattern to search for

        Returns:
            List of matches
        """
        matches = []
        for file_info in self.results.get("files", []):
            file_path = self.workspace / file_info["path"]
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        if pattern in line:
                            matches.append(
                                {
                                    "file": file_info["path"],
                                    "line": line_num,
                                    "content": line.strip(),
                                }
                            )
            except Exception:
                pass

        return matches[:100]

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of analysis results.

        Returns:
            Summary dictionary
        """
        return {
            "tool": "treesitter",
            "available": TREE_SITTER_AVAILABLE,
            "files_analyzed": len(self.results.get("files", [])),
            "total_functions": self.results.get("total_functions", 0),
            "total_classes": self.results.get("total_classes", 0),
            "workspace": str(self.workspace),
        }

    def cleanup(self):
        """Clean up temporary resources."""
        pass

    def _fallback_analysis(self, pattern: str) -> Dict[str, Any]:
        """
        Fallback analysis when tree-sitter is not available.

        Uses simple line counting and basic heuristics.
        """
        files = list(self.workspace.glob(pattern))
        logging.warning(f"Using fallback analysis for {len(files)} files")

        total_functions = 0
        total_classes = 0

        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Simple heuristic: count function/class definitions
                    total_functions += content.count("def ")
                    total_classes += content.count("class ")
            except Exception as e:
                logging.error(f"Failed to read {file_path}: {e}")

        return {
            "files": [{"path": str(f.relative_to(self.workspace))} for f in files],
            "total_functions": total_functions,
            "total_classes": total_classes,
            "complexity_hotspots": [],
            "imports": [],
            "warning": "Limited analysis - tree-sitter not available",
        }


if __name__ == "__main__":
    # Test the analyzer
    import sys

    if len(sys.argv) > 1:
        workspace = sys.argv[1]
        analyzer = TreeSitterAnalyzer(workspace)
        results = analyzer.analyze_directory()
        print(json.dumps(results, indent=2))
    else:
        print("Usage: python treesitter_analyzer.py <workspace_path>")
