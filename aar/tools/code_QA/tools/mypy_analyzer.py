"""
Mypy type checker integration for Python type analysis.

Runs mypy with JSON output and parses type checking errors.
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any
import logging


class MypyAnalyzer:
    """Wrapper for mypy type checker."""

    def __init__(self, workspace: str):
        """
        Initialize mypy analyzer.

        Args:
            workspace: Root directory to analyze
        """
        self.workspace = Path(workspace)
        self.logger = logging.getLogger(__name__)

    def analyze(self, pattern: str = "**/*.py") -> Dict[str, Any]:
        """
        Run mypy type checking on workspace.

        Args:
            pattern: File pattern to check (currently uses whole workspace)

        Returns:
            Dictionary with type checking results
        """
        try:
            # Check if mypy is installed
            version_result = subprocess.run(
                ["mypy", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if version_result.returncode != 0:
                self.logger.error("mypy not installed")
                return self._empty_results()

            version = version_result.stdout.strip()

            # Run mypy with JSON output
            cmd = [
                "mypy",
                str(self.workspace),
                "--output=json",
                "--no-error-summary"
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180
            )

            # Parse JSON output (one JSON object per line)
            errors = []
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        try:
                            errors.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue

            # Process results
            return self._process_results(errors, version)

        except subprocess.TimeoutExpired:
            self.logger.error("mypy check timed out")
            return self._empty_results()
        except Exception as e:
            self.logger.error(f"mypy check failed: {e}")
            return self._empty_results()

    def _process_results(self, errors: List[Dict], version: str) -> Dict[str, Any]:
        """Process raw mypy results into structured format."""
        # Count by error code
        error_counts = {}

        # Collect all errors
        all_errors = []

        # Track files with errors
        files_with_errors = set()

        # Track total files checked (approximate)
        python_files = list(self.workspace.rglob("*.py"))
        total_files = len(python_files)

        for error in errors:
            # Only process actual errors, not notes
            severity = error.get("severity", "error")
            if severity not in ["error", "note"]:
                continue

            # Extract error code (e.g., "attr-defined")
            message = error.get("message", "")
            code = self._extract_error_code(message)

            if severity == "error":
                if code not in error_counts:
                    error_counts[code] = 0
                error_counts[code] += 1

            # Track file
            file_path = error.get("file", "")
            if file_path:
                try:
                    rel_path = str(Path(file_path).relative_to(self.workspace))
                    files_with_errors.add(rel_path)
                except ValueError:
                    rel_path = file_path

                all_errors.append({
                    "file": rel_path,
                    "line": error.get("line", 0),
                    "column": error.get("column", 0),
                    "code": code,
                    "severity": severity,
                    "message": message
                })

        # Build error code details with descriptions
        error_descriptions = {
            "attr-defined": "Missing attributes",
            "no-untyped-def": "Missing annotations",
            "arg-type": "Type mismatch",
            "return-value": "Return type mismatch",
            "name-defined": "Name not defined",
            "override": "Override mismatch",
            "assignment": "Assignment type error",
            "call-arg": "Call argument error"
        }

        by_error = [
            {
                "code": code,
                "description": error_descriptions.get(code, "Type error"),
                "count": count
            }
            for code, count in sorted(error_counts.items(), key=lambda x: -x[1])
        ]

        # Calculate type coverage (rough estimate)
        # Files without errors = better coverage
        if total_files > 0:
            type_coverage = max(0, (1 - len(files_with_errors) / total_files) * 100)
        else:
            type_coverage = 0

        total_errors = sum(1 for e in all_errors if e["severity"] == "error")

        return {
            "version": version,
            "total": total_errors,
            "type_coverage": round(type_coverage, 1),
            "files_checked": total_files,
            "files_with_errors": len(files_with_errors),
            "by_error": by_error,
            "errors": all_errors
        }

    def _extract_error_code(self, message: str) -> str:
        """Extract error code from mypy message."""
        # Mypy messages often end with [error-code]
        if "[" in message and "]" in message:
            start = message.rfind("[")
            end = message.rfind("]")
            if start < end:
                return message[start + 1:end]
        return "general"

    def _empty_results(self) -> Dict[str, Any]:
        """Return empty results structure."""
        return {
            "version": "unknown",
            "total": 0,
            "type_coverage": 0,
            "files_checked": 0,
            "files_with_errors": 0,
            "by_error": [],
            "errors": []
        }
