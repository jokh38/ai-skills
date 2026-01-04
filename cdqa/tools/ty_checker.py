"""
ty type checker integration for Python type analysis.

Extremely fast Rust-based type checker from Astral (creators of ruff).
Runs ty with JSON output and parses type checking errors.
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any
import logging


class TyChecker:
    """Wrapper for ty type checker."""

    def __init__(self, workspace: str):
        """
        Initialize ty type checker.

        Args:
            workspace: Root directory to analyze
        """
        self.workspace = Path(workspace)
        self.logger = logging.getLogger(__name__)

    def analyze(self, pattern: str = "**/*.py") -> Dict[str, Any]:
        """
        Run ty type checking on workspace.

        Args:
            pattern: File pattern to check (currently uses whole workspace)

        Returns:
            Dictionary with type checking results
        """
        try:
            # Check if ty is installed
            version_result = subprocess.run(
                ["ty", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if version_result.returncode != 0:
                self.logger.error("ty not installed")
                return self._empty_results()

            version = version_result.stdout.strip()

            # Run ty with JSON output
            cmd = [
                "ty", "check",
                str(self.workspace),
                "--output-format", "json"
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60  # Much faster than mypy (10-100x)
            )

            # Parse JSON output
            if result.stdout:
                try:
                    data = json.loads(result.stdout)
                    errors = data.get("diagnostics", [])
                except json.JSONDecodeError:
                    # ty might output line-by-line JSON like mypy
                    errors = []
                    for line in result.stdout.strip().split('\n'):
                        if line:
                            try:
                                errors.append(json.loads(line))
                            except json.JSONDecodeError:
                                continue
            else:
                errors = []

            # Process results
            return self._process_results(errors, version)

        except subprocess.TimeoutExpired:
            self.logger.error("ty check timed out")
            return self._empty_results()
        except Exception as e:
            self.logger.error(f"ty check failed: {e}")
            return self._empty_results()

    def _process_results(self, errors: List[Dict], version: str) -> Dict[str, Any]:
        """Process raw ty results into structured format (compatible with mypy)."""
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
            # Extract error code and severity
            code = error.get("code", error.get("rule", "general"))
            severity = error.get("severity", "error")

            # Skip notes
            if severity == "note":
                continue

            # Count errors
            if code not in error_counts:
                error_counts[code] = 0
            error_counts[code] += 1

            # Track file
            file_path = error.get("file", error.get("path", ""))
            if file_path:
                try:
                    rel_path = str(Path(file_path).relative_to(self.workspace))
                    files_with_errors.add(rel_path)
                except ValueError:
                    rel_path = file_path

                all_errors.append({
                    "file": rel_path,
                    "line": error.get("line", error.get("location", {}).get("line", 0)),
                    "column": error.get("column", error.get("location", {}).get("column", 0)),
                    "code": code,
                    "severity": severity,
                    "message": error.get("message", "")
                })

        # Build error code details
        by_error = [
            {
                "code": code,
                "description": self._get_error_description(code),
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

        total_errors = len([e for e in all_errors if e["severity"] == "error"])

        return {
            "version": version,
            "total": total_errors,
            "type_coverage": round(type_coverage, 1),
            "files_checked": total_files,
            "files_with_errors": len(files_with_errors),
            "by_error": by_error,
            "errors": all_errors
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
            "errors": []
        }
