"""
ty type checker integration for Python type analysis.

Extremely fast Rust-based type checker from Astral (creators of ruff).
Runs ty with JSON output and parses type checking errors.
"""

from pathlib import Path
from typing import Dict, Any
from base_checker import BaseToolChecker


class TyChecker(BaseToolChecker):
    """Wrapper for ty type checker."""

    def __init__(self, workspace: str):
        """
        Initialize ty type checker.

        Args:
            workspace: Root directory to analyze
        """
        super().__init__(workspace, "ty")

    def analyze(self, pattern: str = "**/*.py") -> Dict[str, Any]:
        """
        Run ty type checking on workspace.

        Args:
            pattern: File pattern to check (currently uses whole workspace)

        Returns:
            Dictionary with type checking results
        """
        is_installed, version = self._check_tool_version(["ty", "--version"])
        if not is_installed:
            return self._empty_results()

        try:
            cmd = ["ty", "check", str(self.workspace), "--output-format", "json"]
            result = self._run_tool(cmd, timeout=60)

            errors = (
                self._parse_json_output(result.stdout, line_by_line=True)
                if result.stdout
                else []
            )
            return self._process_results(errors, version)

        except Exception:
            return self._empty_results()

    def _process_results(self, errors: list, version: str) -> Dict[str, Any]:
        """Process raw ty results into structured format (compatible with mypy)."""
        error_counts = {}
        all_errors = []
        files_with_errors = set()

        python_files = list(self.workspace.rglob("*.py"))
        total_files = len(python_files)

        for error in errors:
            code = error.get("code", error.get("rule", "general"))
            severity = error.get("severity", "error")

            if severity == "note":
                continue

            error_counts[code] = error_counts.get(code, 0) + 1

            file_path = error.get("file", error.get("path", ""))
            if file_path:
                rel_path = self._normalize_path(file_path)
                files_with_errors.add(rel_path)

                all_errors.append(
                    {
                        "file": rel_path,
                        "line": error.get(
                            "line", error.get("location", {}).get("line", 0)
                        ),
                        "column": error.get(
                            "column", error.get("location", {}).get("column", 0)
                        ),
                        "code": code,
                        "severity": severity,
                        "message": error.get("message", ""),
                    }
                )

        by_error = [
            {
                "code": code,
                "description": self._get_error_description(code),
                "count": count,
            }
            for code, count in sorted(error_counts.items(), key=lambda x: -x[1])
        ]

        type_coverage = (
            max(0, (1 - len(files_with_errors) / total_files) * 100)
            if total_files > 0
            else 0
        )
        total_errors = len([e for e in all_errors if e["severity"] == "error"])

        return {
            "version": version,
            "total": total_errors,
            "type_coverage": round(type_coverage, 1),
            "files_checked": total_files,
            "files_with_errors": len(files_with_errors),
            "by_error": by_error,
            "errors": all_errors,
        }

    def _get_error_description(self, code: str) -> str:
        """Get human-readable description for error code."""
        descriptions = {
            "attr-defined": "Missing attributes",
            "no-untyped-def": "Missing annotations",
            "arg-type": "Type mismatch",
            "return-value": "Return type mismatch",
            "name-defined": "Name not defined",
            "override": "Override mismatch",
            "assignment": "Assignment type error",
            "call-arg": "Call argument error",
            "incompatible-type": "Incompatible types",
            "type-error": "Type error",
            "undefined-name": "Undefined name",
        }
        return descriptions.get(code, "Type error")

    def _empty_results(self) -> Dict[str, Any]:
        """Return empty results structure."""
        return {
            "version": "unknown",
            "total": 0,
            "type_coverage": 0,
            "files_checked": 0,
            "files_with_errors": 0,
            "by_error": [],
            "errors": [],
        }
