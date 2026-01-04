"""
Ruff linter integration for Python code quality checking.

Runs ruff with JSON output and parses linting issues.
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any
import logging


class RuffChecker:
    """Wrapper for ruff linter."""

    def __init__(self, workspace: str):
        """
        Initialize ruff checker.

        Args:
            workspace: Root directory to analyze
        """
        self.workspace = Path(workspace)
        self.logger = logging.getLogger(__name__)

    def check(self, pattern: str = "**/*.py") -> Dict[str, Any]:
        """
        Run ruff linting on workspace.

        Args:
            pattern: File pattern to check

        Returns:
            Dictionary with linting results
        """
        try:
            # Check if ruff is installed
            version_result = subprocess.run(
                ["ruff", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if version_result.returncode != 0:
                self.logger.error("ruff not installed")
                return self._empty_results()

            version = version_result.stdout.strip()

            # Run ruff with JSON output
            cmd = [
                "ruff", "check",
                str(self.workspace),
                "--output-format=json"
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )

            # Parse JSON output
            if result.stdout:
                issues = json.loads(result.stdout)
            else:
                issues = []

            # Process and categorize results
            return self._process_results(issues, version)

        except subprocess.TimeoutExpired:
            self.logger.error("ruff check timed out")
            return self._empty_results()
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse ruff JSON output: {e}")
            return self._empty_results()
        except Exception as e:
            self.logger.error(f"ruff check failed: {e}")
            return self._empty_results()

    def _process_results(self, issues: List[Dict], version: str) -> Dict[str, Any]:
        """Process raw ruff results into structured format."""
        # Count by severity
        severity_counts = {"error": 0, "warning": 0, "info": 0}

        # Count by category (first letter of code)
        category_counts = {}

        # Track fixable issues
        fixable_count = 0

        # Collect all issues with details
        all_issues = []

        for issue in issues:
            code = issue.get("code", "")

            # Determine severity based on code
            if code.startswith(("E", "F")):
                severity = "error"
            elif code.startswith(("W", "C")):
                severity = "warning"
            else:
                severity = "info"

            severity_counts[severity] += 1

            # Track category
            category_prefix = code[0] if code else "?"
            if category_prefix not in category_counts:
                category_counts[category_prefix] = 0
            category_counts[category_prefix] += 1

            # Track fixable
            if issue.get("fix"):
                fixable_count += 1

            # Store issue details
            all_issues.append({
                "file": str(Path(issue.get("filename", "")).relative_to(self.workspace) if "filename" in issue else ""),
                "line": issue.get("location", {}).get("row", 0),
                "column": issue.get("location", {}).get("column", 0),
                "code": code,
                "message": issue.get("message", ""),
                "severity": severity,
                "fixable": bool(issue.get("fix"))
            })

        # Build category details
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
                "count": count
            }
            for code, count in sorted(category_counts.items(), key=lambda x: -x[1])
        ]

        return {
            "version": version,
            "total": len(issues),
            "auto_fixable": fixable_count,
            "severity_counts": severity_counts,
            "categories": categories,
            "issues": all_issues
        }

    def _empty_results(self) -> Dict[str, Any]:
        """Return empty results structure."""
        return {
            "version": "unknown",
            "total": 0,
            "auto_fixable": 0,
            "severity_counts": {"error": 0, "warning": 0, "info": 0},
            "categories": [],
            "issues": []
        }
