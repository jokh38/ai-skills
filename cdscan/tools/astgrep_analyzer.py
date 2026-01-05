"""
ast-grep structural search integration.

Provides high-level pattern matching and linting on top of tree-sitter.
"""

import subprocess
import json
from pathlib import Path
from typing import Dict, List, Any
import logging

from utils import check_tool_availability


class AstGrepAnalyzer:
    """Wrapper for ast-grep structural search and linting."""

    def __init__(self, workspace: str):
        """
        Initialize ast-grep analyzer.

        Args:
            workspace: Root directory to analyze
        """
        self.workspace = Path(workspace)
        self.logger = logging.getLogger(__name__)
        self.available = self._check_astgrep()

    def _check_astgrep(self) -> bool:
        """Check if ast-grep is installed."""
        return check_tool_availability(['ast-grep', '--version'], 'ast-grep')
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            self.logger.warning(f"ast-grep not found: {e}")
            return False

    def search_pattern(
        self, pattern: str, language: str = "python"
    ) -> List[Dict[str, Any]]:
        """
        Search for structural pattern.

        Args:
            pattern: ast-grep pattern (e.g., "function $NAME($$$ARGS) { $$$ }")
            language: Target language (python, javascript, cpp, etc.)

        Returns:
            List of matches with file, line, and matched code
        """
        if not self.available:
            return []

        try:
            cmd = [
                "ast-grep",
                "scan",
                "--pattern",
                pattern,
                "--lang",
                language,
                "--json",
                str(self.workspace),
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.stdout:
                return json.loads(result.stdout)
            return []

        except subprocess.TimeoutExpired:
            self.logger.error("ast-grep search timed out")
            return []
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse ast-grep output: {e}")
            return []
        except Exception as e:
            self.logger.error(f"ast-grep search failed: {e}")
            return []

    def lint(self, rules_file: str) -> Dict[str, Any]:
        """
        Run ast-grep linting with rules file.

        Args:
            rules_file: Path to YAML rules file

        Returns:
            Dictionary with linting results
        """
        if not self.available:
            return {"total": 0, "findings": []}

        try:
            cmd = [
                "ast-grep",
                "scan",
                "--config",
                rules_file,
                "--json",
                str(self.workspace),
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            if result.stdout:
                data = json.loads(result.stdout)
                return self._process_lint_results(data)
            return {"total": 0, "findings": []}

        except Exception as e:
            self.logger.error(f"ast-grep lint failed: {e}")
            return {"total": 0, "findings": []}

    def find_common_patterns(self, language: str = "python") -> Dict[str, List[Dict]]:
        """
        Search for common code patterns.

        Args:
            language: Target language

        Returns:
            Dictionary of pattern matches by pattern type
        """
        if not self.available:
            return {}

        patterns = self._get_common_patterns(language)
        results = {}

        for pattern_name, pattern in patterns.items():
            matches = self.search_pattern(pattern, language)
            if matches:
                results[pattern_name] = self._format_pattern_matches(
                    matches, pattern_name
                )

        return results

    def _get_common_patterns(self, language: str) -> Dict[str, str]:
        """Get common patterns for language."""
        if language == "python":
            return {
                "unused_vars": "def $FUNC($$$PARAMS):\n    $VAR = $$$\n    $$$",
                "complex_comprehensions": "[$$$FOR $$$FOR $$$]",
                "bare_except": "try:\n    $$$\nexcept:\n    $$$",
                "mutable_defaults": "def $FUNC($ARG=[]): $$$",
            }
        elif language in ["javascript", "typescript"]:
            return {
                "console_log": "console.log($$$)",
                "var_declarations": "var $VAR = $$$",
                "async_without_await": "async function $F($$$) { $$$ }",
            }
        elif language == "cpp":
            return {
                "raw_pointers": "$TYPE* $VAR = new $$$",
                "manual_memory": "delete $$$",
                "c_style_cast": "($TYPE)$VAR",
            }
        return {}

    def _format_pattern_matches(
        self, matches: List[Dict], pattern_type: str
    ) -> List[Dict]:
        """Format pattern matches for output."""
        formatted = []

        for match in matches:
            formatted.append(
                {
                    "file": match.get("file", ""),
                    "line": match.get("range", {}).get("start", {}).get("line", 0),
                    "column": match.get("range", {}).get("start", {}).get("column", 0),
                    "code": match.get("text", "")[:200],  # Limit code snippet
                    "pattern": pattern_type,
                }
            )

        return formatted[:20]  # Limit results

    def _process_lint_results(self, data: Dict) -> Dict[str, Any]:
        """Process raw lint results."""
        findings = []

        for item in data.get("results", []):
            findings.append(
                {
                    "file": item.get("file", ""),
                    "line": item.get("range", {}).get("start", {}).get("line", 0),
                    "rule": item.get("rule", ""),
                    "message": item.get("message", ""),
                    "severity": item.get("severity", "warning"),
                }
            )

        return {"total": len(findings), "findings": findings}


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        workspace = sys.argv[1]
        analyzer = AstGrepAnalyzer(workspace)

        if analyzer.available:
            print("Testing ast-grep pattern search...")
            patterns = analyzer.find_common_patterns("python")
            print(f"Found patterns: {list(patterns.keys())}")
            for pattern_name, matches in patterns.items():
                print(f"\n{pattern_name}: {len(matches)} matches")
                for match in matches[:3]:
                    print(f"  {match['file']}:{match['line']} - {match['code'][:50]}")
        else:
            print("ast-grep not available. Install with: cargo install ast-grep")
    else:
        print("Usage: python astgrep_analyzer.py <workspace_path>")
