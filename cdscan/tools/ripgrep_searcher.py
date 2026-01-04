"""
Ripgrep-based pattern searcher for fast keyword and pattern matching.

Searches for:
- Test files and patterns
- Error handling (try/except, raise)
- Technical debt (TODO, FIXME, HACK)
- Custom patterns
"""

import subprocess
import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Any


class RipgrepSearcher:
    """Fast pattern search using ripgrep."""

    # Common test file patterns
    TEST_PATTERNS = [
        r'test_.*\.py$',  # Python: test_*.py
        r'.*_test\.py$',  # Python: *_test.py
        r'.*\.test\.(js|ts)$',  # JavaScript/TypeScript: *.test.js
        r'.*\.spec\.(js|ts)$',  # JavaScript/TypeScript: *.spec.js
        r'test.*\.java$',  # Java: Test*.java
    ]

    # Error handling patterns by language
    ERROR_PATTERNS = {
        'python': [
            r'\btry\s*:',  # try blocks
            r'\braise\s+\w+',  # raise statements
            r'except\s+\w+',  # except clauses
        ],
        'javascript': [
            r'\btry\s*\{',  # try blocks
            r'\bthrow\s+',  # throw statements
            r'\bcatch\s*\(',  # catch clauses
        ],
        'java': [
            r'\btry\s*\{',  # try blocks
            r'\bthrow\s+new\s+',  # throw statements
            r'\bcatch\s*\(',  # catch clauses
        ],
    }

    # Technical debt markers
    DEBT_PATTERNS = [
        r'\bTODO\b',
        r'\bFIXME\b',
        r'\bHACK\b',
        r'\bXXX\b',
        r'\bNOTE\b',
    ]

    def __init__(self, workspace: str):
        """
        Initialize searcher.

        Args:
            workspace: Root directory to search
        """
        self.workspace = Path(workspace)
        self.rg_available = self._check_ripgrep()

    def _check_ripgrep(self) -> bool:
        """Check if ripgrep is installed."""
        try:
            result = subprocess.run(
                ['rg', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.splitlines()[0]
                logging.info(f"ripgrep found: {version}")
                return True
            else:
                logging.warning("ripgrep not available")
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logging.warning(f"ripgrep not found: {e}")
            return False

    def _get_exclude_patterns(self) -> List[str]:
        """
        Get list of glob patterns to exclude from search.

        Returns:
            List of glob patterns for ripgrep --glob option
        """
        exclude_dirs = [
            '**/__pycache__/**',
            '**/.pytest_cache/**',
            '**/.tox/**',
            '**/.eggs/**',
            '**/build/**',
            '**/dist/**',
            '**/*.egg-info/**',
            '**/node_modules/**',
            '**/.venv/**',
            '**/venv/**',
            '**/env/**',
            '**/.git/**',
            '**/.svn/**',
            '**/.hg/**',
            '**/.idea/**',
            '**/.vscode/**',
            '**/target/**',
            '**/cmake-build-*/**',
        ]

        exclude_files = [
            '**/*.pyc',
            '**/*.pyo',
            '**/*.pyd',
            '**/*.so',
            '**/*.dylib',
            '**/*.dll',
            '**/*.exe',
            '**/*.bin',
            '**/*.o',
            '**/*.a',
            '**/*.lib',
            '**/*.obj',
            '**/*.class',
            '**/*.jar',
            '**/*.war',
            '**/*.min.js',
            '**/*.min.css',
        ]

        return exclude_dirs + exclude_files

    def search_pattern(
        self,
        pattern: str,
        file_type: Optional[str] = None,
        case_sensitive: bool = False,
        max_results: int = 100
    ) -> List[Dict]:
        """
        Search for a pattern in workspace.

        Args:
            pattern: Regex pattern to search for
            file_type: File type filter (e.g., 'py', 'js')
            case_sensitive: Whether to use case-sensitive search
            max_results: Maximum number of results to return

        Returns:
            List of matches with file, line number, and content
        """
        if not self.rg_available:
            logging.error("ripgrep not available. Install with: brew install ripgrep (macOS) or apt-get install ripgrep (Linux)")
            return []

        cmd = ['rg', '--json', pattern, str(self.workspace)]

        # Add exclusion patterns
        for exclude_pattern in self._get_exclude_patterns():
            cmd.extend(['--glob', '!' + exclude_pattern])

        if not case_sensitive:
            cmd.insert(1, '-i')

        if file_type:
            cmd.extend(['-t', file_type])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            matches = []
            for line in result.stdout.splitlines():
                try:
                    data = json.loads(line)
                    if data.get('type') == 'match':
                        match_data = data.get('data', {})
                        matches.append({
                            'file': match_data.get('path', {}).get('text', ''),
                            'line': match_data.get('line_number', 0),
                            'content': match_data.get('lines', {}).get('text', '').strip(),
                        })

                        if len(matches) >= max_results:
                            break
                except json.JSONDecodeError:
                    continue

            logging.info(f"Found {len(matches)} matches for pattern: {pattern}")
            return matches

        except subprocess.TimeoutExpired:
            logging.error(f"Search timed out for pattern: {pattern}")
            return []
        except Exception as e:
            logging.error(f"Search failed: {e}")
            return []

    def get_test_files(self) -> Dict[str, Any]:
        """
        Find all test files in the workspace.

        Returns:
            Dictionary with test file information
        """
        test_files = []

        for pattern in self.TEST_PATTERNS:
            cmd = ['rg', '--files', '--glob', pattern, str(self.workspace)]

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode == 0:
                    for file_path in result.stdout.splitlines():
                        if file_path and Path(file_path).exists():
                            test_files.append(str(Path(file_path).relative_to(self.workspace)))

            except Exception as e:
                logging.debug(f"Pattern {pattern} search failed: {e}")

        # Deduplicate
        test_files = list(set(test_files))

        # Detect test frameworks
        frameworks = self._detect_test_frameworks(test_files)

        return {
            'count': len(test_files),
            'files': sorted(test_files)[:50],  # Limit to first 50
            'frameworks': frameworks,
        }

    def _detect_test_frameworks(self, test_files: List[str]) -> List[str]:
        """Detect which test frameworks are used."""
        frameworks = set()

        # Search for framework imports
        framework_patterns = {
            'pytest': r'import pytest|from pytest',
            'unittest': r'import unittest|from unittest',
            'jest': r'from [\'"]jest[\'"]|describe\(',
            'mocha': r'from [\'"]mocha[\'"]|describe\(',
            'junit': r'import.*junit|@Test',
        }

        for framework, pattern in framework_patterns.items():
            matches = self.search_pattern(pattern, max_results=1)
            if matches:
                frameworks.add(framework)

        return sorted(list(frameworks))

    def search_error_patterns(self, workspace: Optional[str] = None, language: str = 'python') -> Dict[str, Any]:
        """
        Search for error handling patterns.

        Args:
            workspace: Workspace path (compatibility param, not used)
            language: Programming language to search for

        Returns:
            Dictionary with error handling statistics
        """
        if workspace:
            self.workspace = Path(workspace)

        patterns = self.ERROR_PATTERNS.get(language, self.ERROR_PATTERNS['python'])

        results = {
            'language': language,
            'try_blocks': [],
            'raise_statements': [],
            'except_clauses': [],
            'total_error_handlers': 0,
        }

        # Search for each pattern
        for pattern in patterns:
            matches = self.search_pattern(pattern, max_results=50)

            if 'try' in pattern:
                results['try_blocks'] = matches
            elif 'raise' in pattern or 'throw' in pattern:
                results['raise_statements'] = matches
            elif 'except' in pattern or 'catch' in pattern:
                results['except_clauses'] = matches

        results['total_error_handlers'] = (
            len(results['try_blocks']) +
            len(results['raise_statements']) +
            len(results['except_clauses'])
        )

        return results

    def search_todo_fixme(self) -> Dict[str, Any]:
        """
        Search for technical debt markers (TODO, FIXME, etc.).

        Returns:
            Dictionary with technical debt findings
        """
        results = {
            'total_count': 0,
            'by_type': {},
            'locations': [],
        }

        all_matches = []

        for pattern in self.DEBT_PATTERNS:
            matches = self.search_pattern(pattern, max_results=100)
            marker = pattern.replace(r'\b', '').replace(r'\\', '')

            results['by_type'][marker] = len(matches)
            all_matches.extend(matches)

        # Deduplicate and sort by file
        seen = set()
        unique_matches = []
        for match in all_matches:
            key = (match['file'], match['line'])
            if key not in seen:
                seen.add(key)
                unique_matches.append(match)

        results['locations'] = sorted(unique_matches, key=lambda x: x['file'])[:50]
        results['total_count'] = len(unique_matches)

        return results

    def search_security_patterns(self) -> Dict[str, Any]:
        """
        Search for potential security issues.

        Returns:
            Dictionary with security findings
        """
        security_patterns = {
            'sql_injection_risk': r'execute\s*\(\s*["\'].*%s.*["\']',  # SQL string formatting
            'hardcoded_secrets': r'(password|secret|api_key)\s*=\s*["\'][^"\']+["\']',
            'eval_usage': r'\beval\s*\(',
            'pickle_usage': r'pickle\.(load|loads)',  # Unsafe deserialization
            'shell_injection': r'(os\.system|subprocess\.call).*\+',  # Command concatenation
        }

        results = {
            'total_issues': 0,
            'by_severity': {},
            'findings': [],
        }

        for issue_type, pattern in security_patterns.items():
            matches = self.search_pattern(pattern, max_results=20)

            if matches:
                severity = 'high' if issue_type in ['sql_injection_risk', 'shell_injection'] else 'medium'

                for match in matches:
                    results['findings'].append({
                        'type': issue_type,
                        'severity': severity,
                        'file': match['file'],
                        'line': match['line'],
                        'content': match['content'],
                    })

                results['by_severity'][severity] = results['by_severity'].get(severity, 0) + len(matches)

        results['total_issues'] = len(results['findings'])

        return results

    def get_import_graph(self, language: str = 'python') -> Dict[str, Any]:
        """
        Build import/dependency graph.

        Args:
            language: Programming language

        Returns:
            Dictionary with import information
        """
        if language == 'python':
            import_pattern = r'^(import |from .*import )'
        elif language in ['javascript', 'typescript']:
            import_pattern = r'^(import .* from |require\()'
        else:
            import_pattern = r'^import '

        matches = self.search_pattern(import_pattern, max_results=500)

        # Extract module names
        modules = {}
        external_deps = set()

        for match in matches:
            content = match['content']

            # Extract module name (simplified)
            if 'import' in content:
                parts = content.split()
                if len(parts) >= 2:
                    module = parts[1].strip(',;')

                    # Check if external (no relative path)
                    if not module.startswith('.'):
                        external_deps.add(module)

                    # Track which files import this module
                    if module not in modules:
                        modules[module] = []
                    modules[module].append(match['file'])

        return {
            'total_imports': len(matches),
            'unique_modules': len(modules),
            'external_dependencies': sorted(list(external_deps))[:30],
            'most_imported': sorted(
                [(mod, len(files)) for mod, files in modules.items()],
                key=lambda x: x[1],
                reverse=True
            )[:15],
        }

    def find_test_files(self, workspace: str) -> List[str]:
        """Find test files in workspace."""
        test_info = self.get_test_files()
        return test_info.get('files', [])

    def search_technical_debt(self, workspace: str) -> Dict[str, Any]:
        """Search for technical debt markers."""
        return self.search_todo_fixme()

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of searcher capabilities."""
        total_matches = sum(
            len(self.search_pattern(pattern, max_results=1000))
            for pattern in ['def ', 'class ', 'import ']
        )
        return {
            'tool': 'ripgrep',
            'available': self.rg_available,
            'workspace': str(self.workspace),
            'total_matches': total_matches,
            'status': 'available' if self.rg_available else 'unavailable'
        }

    def cleanup(self):
        """Clean up any temporary resources."""
        pass


if __name__ == '__main__':
    # Test the searcher
    import sys
    if len(sys.argv) > 1:
        workspace = sys.argv[1]
        searcher = RipgrepSearcher(workspace)

        print("=== Test Files ===")
        print(json.dumps(searcher.get_test_files(), indent=2))

        print("\n=== Error Patterns ===")
        print(json.dumps(searcher.search_error_patterns(), indent=2))

        print("\n=== Technical Debt ===")
        print(json.dumps(searcher.search_todo_fixme(), indent=2))

        print("\n=== Security Patterns ===")
        print(json.dumps(searcher.search_security_patterns(), indent=2))

    else:
        print("Usage: python ripgrep_searcher.py <workspace_path>")
