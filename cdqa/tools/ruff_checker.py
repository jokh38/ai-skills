"""
Ruff linter integration for Python code quality checking.

Runs ruff with JSON output and parses linting issues.
"""

from typing import Dict, Any
from base_checker import BaseToolChecker


class RuffChecker(BaseToolChecker):
    """Wrapper for ruff linter."""

    def __init__(self, workspace: str):
        """
        Initialize ruff checker.

        Args:
            workspace: Root directory to analyze
        """
        super().__init__(workspace, "ruff")

    def check(self, pattern: str = "**/*.py") -> Dict[str, Any]:
        """
        Run ruff linting on workspace.

        Args:
            pattern: File pattern to check

        Returns:
            Dictionary with linting results
        """
        is_installed, version = self._check_tool_version(["ruff", "--version"])
        if not is_installed:
            return self._empty_results()

        try:
            cmd = ["ruff", "check", str(self.workspace), "--output-format=json"]
            result = self._run_tool(cmd, timeout=120)

            issues = self._parse_json_output(result.stdout) if result.stdout else []
            return self._process_results(issues, version)

        except Exception:
            return self._empty_results()

    def _process_results(self, issues: list, version: str) -> Dict[str, Any]:
        """Process raw ruff results into structured format."""
        severity_counts = {"error": 0, "warning": 0, "info": 0}
        category_counts = {}
        fixable_count = 0
        all_issues = []

        for issue in issues:
            code = issue.get("code", "")

            if code.startswith(("E", "F")):
                severity = "error"
            elif code.startswith(("W", "C")):
                severity = "warning"
            else:
                severity = "info"

            severity_counts[severity] += 1

            category_prefix = code[0] if code else "?"
            category_counts[category_prefix] = (
                category_counts.get(category_prefix, 0) + 1
            )

            if issue.get("fix"):
                fixable_count += 1

            all_issues.append(
                {
                    "file": self._normalize_path(issue.get("filename", "")),
                    "line": issue.get("location", {}).get("row", 0),
                    "column": issue.get("location", {}).get("column", 0),
                    "code": code,
                    "message": issue.get("message", ""),
                    "severity": severity,
                    "fixable": bool(issue.get("fix")),
                }
            )

        category_names = {
            "F": "pyflakes-errors",
            "E": "pycodestyle-errors",
            "W": "warnings",
            "N": "naming",
            "C": "complexity",
            "I": "isort",
        }

        categories = [
            {
                "code": code,
                "category": category_names.get(code, "other"),
                "count": count,
            }
            for code, count in sorted(category_counts.items(), key=lambda x: -x[1])
        ]

        return {
            "version": version,
            "total": len(issues),
            "auto_fixable": fixable_count,
            "severity_counts": severity_counts,
            "categories": categories,
            "issues": all_issues,
        }

    def _empty_results(self) -> Dict[str, Any]:
        """Return empty results structure."""
        return {
            "version": "unknown",
            "total": 0,
            "auto_fixable": 0,
            "severity_counts": {"error": 0, "warning": 0, "info": 0},
            "categories": [],
            "issues": [],
        }
