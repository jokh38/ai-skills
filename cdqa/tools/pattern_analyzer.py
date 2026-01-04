#!/usr/bin/env python3
"""
Pattern Analyzer - Detects code consistency issues across a codebase.

Analyzes patterns for:
- Error handling styles (try/except patterns)
- Naming conventions (snake_case vs camelCase)
- Import organization patterns
- Docstring styles

Output is designed for AI-assisted code review to identify inconsistencies.
"""

import ast
import logging
import re
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict


class PatternAnalyzer:
    """Analyzes code patterns for consistency across a codebase."""

    def __init__(self, workspace: str):
        """
        Initialize pattern analyzer.

        Args:
            workspace: Root directory of the project
        """
        self.workspace = Path(workspace).resolve()
        self.logger = logging.getLogger(__name__)

    def analyze(self, pattern: str = "**/*.py") -> Dict[str, Any]:
        """
        Analyze code patterns across the codebase.

        Args:
            pattern: Glob pattern for files to analyze

        Returns:
            Dictionary with pattern analysis results
        """
        files = list(self.workspace.glob(pattern))

        # Skip common non-source directories
        files = [f for f in files if not any(
            p in f.parts for p in ['venv', '.venv', 'node_modules', '__pycache__', '.git']
        )]

        results = {
            'total_files': len(files),
            'consistency_issues': [],
            'total_inconsistencies': 0
        }

        # Collect patterns across all files
        error_handling = defaultdict(list)
        naming_styles = defaultdict(list)
        import_styles = defaultdict(list)
        docstring_styles = defaultdict(list)

        for file_path in files:
            try:
                self._analyze_file(
                    file_path,
                    error_handling,
                    naming_styles,
                    import_styles,
                    docstring_styles
                )
            except Exception as e:
                self.logger.debug(f"Skipping {file_path}: {e}")
                continue  # Skip files that can't be parsed

        # Build consistency issues from collected patterns
        results['consistency_issues'] = self._build_consistency_issues(
            error_handling, naming_styles, import_styles, docstring_styles
        )
        results['total_inconsistencies'] = len(results['consistency_issues'])

        return results

    def _analyze_file(
        self,
        file_path: Path,
        error_handling: Dict,
        naming_styles: Dict,
        import_styles: Dict,
        docstring_styles: Dict
    ):
        """Analyze a single file for patterns."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            tree = ast.parse(content)
        except SyntaxError as e:
            self.logger.debug(f"Syntax error in {file_path}: {e}")
            return

        rel_path = str(file_path.relative_to(self.workspace))

        # Analyze error handling patterns
        self._analyze_error_handling(tree, rel_path, error_handling)

        # Analyze naming conventions
        self._analyze_naming(tree, rel_path, naming_styles)

        # Analyze import styles
        self._analyze_imports(tree, rel_path, import_styles)

        # Analyze docstring styles
        self._analyze_docstrings(tree, rel_path, docstring_styles)

    def _analyze_error_handling(self, tree: ast.AST, file_path: str, patterns: Dict):
        """Analyze try/except patterns."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                for handler in node.handlers:
                    if handler.type is None:
                        patterns['bare_except'].append(file_path)
                    elif isinstance(handler.type, ast.Name):
                        if handler.type.id == 'Exception':
                            # Check if there's logging in the handler
                            has_logging = any(
                                isinstance(n, ast.Call) and
                                isinstance(n.func, ast.Attribute) and
                                n.func.attr in ('error', 'exception', 'warning', 'info', 'debug')
                                for n in ast.walk(handler)
                            )
                            if has_logging:
                                patterns['except_with_logging'].append(file_path)
                            else:
                                patterns['except_no_logging'].append(file_path)
                        else:
                            patterns['specific_except'].append(file_path)

    def _analyze_naming(self, tree: ast.AST, file_path: str, patterns: Dict):
        """Analyze naming conventions."""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                name = node.name
                if name.startswith('_'):
                    name = name.lstrip('_')
                if not name:
                    continue

                if self._is_snake_case(name):
                    patterns['func_snake_case'].append(file_path)
                elif self._is_camel_case(name):
                    patterns['func_camelCase'].append(file_path)

            elif isinstance(node, ast.ClassDef):
                name = node.name
                if self._is_pascal_case(name):
                    patterns['class_PascalCase'].append(file_path)
                elif self._is_snake_case(name):
                    patterns['class_snake_case'].append(file_path)

    def _analyze_imports(self, tree: ast.AST, file_path: str, patterns: Dict):
        """Analyze import organization."""
        imports = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.append(node)

        if not imports:
            return

        # Check if imports are grouped (stdlib, third-party, local)
        # Simple heuristic: check if there are blank lines between import groups
        has_from_imports = any(isinstance(i, ast.ImportFrom) for i in imports)
        has_regular_imports = any(isinstance(i, ast.Import) for i in imports)

        if has_from_imports and has_regular_imports:
            patterns['mixed_import_styles'].append(file_path)
        elif has_from_imports:
            patterns['from_imports_only'].append(file_path)
        else:
            patterns['import_only'].append(file_path)

    def _analyze_docstrings(self, tree: ast.AST, file_path: str, patterns: Dict):
        """Analyze docstring styles."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                docstring = ast.get_docstring(node)
                if docstring:
                    if ':param' in docstring or ':type' in docstring:
                        patterns['docstring_sphinx'].append(file_path)
                    elif 'Args:' in docstring or 'Returns:' in docstring:
                        patterns['docstring_google'].append(file_path)
                    elif 'Parameters' in docstring and '----------' in docstring:
                        patterns['docstring_numpy'].append(file_path)
                    else:
                        patterns['docstring_plain'].append(file_path)
                else:
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        # Only flag public functions without docstrings
                        if not node.name.startswith('_'):
                            patterns['no_docstring'].append(file_path)

    def _is_snake_case(self, name: str) -> bool:
        """Check if name is snake_case."""
        return bool(re.match(r'^[a-z][a-z0-9_]*$', name))

    def _is_camel_case(self, name: str) -> bool:
        """Check if name is camelCase."""
        return bool(re.match(r'^[a-z][a-zA-Z0-9]*$', name)) and any(c.isupper() for c in name)

    def _is_pascal_case(self, name: str) -> bool:
        """Check if name is PascalCase."""
        return bool(re.match(r'^[A-Z][a-zA-Z0-9]*$', name))

    def _build_consistency_issues(
        self,
        error_handling: Dict,
        naming_styles: Dict,
        import_styles: Dict,
        docstring_styles: Dict
    ) -> List[Dict]:
        """Build list of consistency issues from collected patterns."""
        issues = []

        # Error handling consistency
        eh_variants = []
        if error_handling['bare_except']:
            eh_variants.append({
                'style': 'bare except',
                'files': list(set(error_handling['bare_except']))[:5],
                'count': len(error_handling['bare_except'])
            })
        if error_handling['except_with_logging']:
            eh_variants.append({
                'style': 'try/except with logging',
                'files': list(set(error_handling['except_with_logging']))[:5],
                'count': len(error_handling['except_with_logging'])
            })
        if error_handling['except_no_logging']:
            eh_variants.append({
                'style': 'try/except without logging',
                'files': list(set(error_handling['except_no_logging']))[:5],
                'count': len(error_handling['except_no_logging'])
            })

        if len(eh_variants) > 1:
            # Find dominant style
            dominant = max(eh_variants, key=lambda x: x['count'])
            issues.append({
                'pattern': 'error_handling',
                'variants': eh_variants,
                'recommendation': f"Standardize on '{dominant['style']}' pattern"
            })

        # Naming convention consistency
        naming_variants = []
        if naming_styles['func_snake_case']:
            naming_variants.append({
                'style': 'snake_case functions',
                'count': len(set(naming_styles['func_snake_case']))
            })
        if naming_styles['func_camelCase']:
            naming_variants.append({
                'style': 'camelCase functions',
                'files': list(set(naming_styles['func_camelCase']))[:5],
                'count': len(set(naming_styles['func_camelCase']))
            })

        if len(naming_variants) > 1 and naming_styles['func_camelCase']:
            issues.append({
                'pattern': 'naming_convention',
                'variants': naming_variants,
                'recommendation': "Use snake_case for function names (PEP 8)"
            })

        # Docstring style consistency
        doc_variants = []
        for style, key in [
            ('Google style', 'docstring_google'),
            ('Sphinx style', 'docstring_sphinx'),
            ('NumPy style', 'docstring_numpy'),
            ('Plain docstrings', 'docstring_plain')
        ]:
            if docstring_styles[key]:
                doc_variants.append({
                    'style': style,
                    'count': len(set(docstring_styles[key]))
                })

        if len(doc_variants) > 1:
            dominant = max(doc_variants, key=lambda x: x['count'])
            issues.append({
                'pattern': 'docstring_style',
                'variants': doc_variants,
                'recommendation': f"Standardize on {dominant['style']}"
            })

        # Missing docstrings
        if docstring_styles['no_docstring']:
            missing_files = list(set(docstring_styles['no_docstring']))
            if len(missing_files) > 3:
                issues.append({
                    'pattern': 'missing_docstrings',
                    'variants': [{
                        'style': 'functions without docstrings',
                        'files': missing_files[:5],
                        'count': len(missing_files)
                    }],
                    'recommendation': "Add docstrings to public functions"
                })

        return issues
