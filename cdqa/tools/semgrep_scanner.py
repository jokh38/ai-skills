"""
Semgrep security scanner integration for pattern-based analysis.

Runs semgrep with security rules and parses findings.
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any
import logging


class SemgrepScanner:
    """Wrapper for semgrep security scanner."""

    def __init__(self, workspace: str):
        """
        Initialize semgrep scanner.

        Args:
            workspace: Root directory to analyze
        """
        self.workspace = Path(workspace)
        self.logger = logging.getLogger(__name__)

    def scan(self, pattern: str = "**/*.py") -> Dict[str, Any]:
        """
        Run semgrep security scan on workspace.

        Args:
            pattern: File pattern to scan

        Returns:
            Dictionary with security findings
        """
        try:
            # Check if semgrep is installed
            version_result = subprocess.run(
                ["semgrep", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if version_result.returncode != 0:
                self.logger.error("semgrep not installed")
                return self._empty_results()

            version = version_result.stdout.strip().split('\n')[0]

            # Run semgrep with auto config (uses registry rules)
            cmd = [
                "semgrep",
                "scan",
                "--config=auto",
                "--json",
                "--quiet",
                str(self.workspace)
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes for security scan
            )

            # Parse JSON output
            if result.stdout:
                data = json.loads(result.stdout)
                findings = data.get("results", [])
            else:
                findings = []

            # Process results
            return self._process_results(findings, version)

        except subprocess.TimeoutExpired:
            self.logger.error("semgrep scan timed out")
            return self._empty_results()
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse semgrep JSON output: {e}")
            return self._empty_results()
        except Exception as e:
            self.logger.error(f"semgrep scan failed: {e}")
            return self._empty_results()

    def _process_results(self, findings: List[Dict], version: str) -> Dict[str, Any]:
        """Process raw semgrep results into structured format."""
        # Count by severity
        severity_counts = {"ERROR": 0, "WARNING": 0, "INFO": 0}

        # Track categories
        categories = {}

        # Collect all findings
        all_findings = []

        for finding in findings:
            # Extract key fields
            severity = finding.get("extra", {}).get("severity", "INFO").upper()
            if severity not in severity_counts:
                severity = "INFO"

            severity_counts[severity] += 1

            # Extract metadata
            metadata = finding.get("extra", {}).get("metadata", {})
            category = metadata.get("category", "security")
            cwe = metadata.get("cwe", ["CWE-unknown"])
            if isinstance(cwe, list):
                cwe = cwe[0] if cwe else "CWE-unknown"

            # Track category
            category_key = f"{category}"
            if category_key not in categories:
                categories[category_key] = {"cwe": cwe, "count": 0, "max_severity": severity}
            categories[category_key]["count"] += 1

            # Get location
            path = finding.get("path", "")
            try:
                rel_path = str(Path(path).relative_to(self.workspace))
            except ValueError:
                rel_path = path

            all_findings.append({
                "severity": severity,
                "category": category,
                "cwe": cwe,
                "file": rel_path,
                "line": finding.get("start", {}).get("line", 0),
                "rule_id": finding.get("check_id", "unknown"),
                "message": finding.get("extra", {}).get("message", "Security finding"),
                "confidence": metadata.get("confidence", "MEDIUM")
            })

        # Build category summary
        by_severity = [
            {
                "severity": sev,
                "category": ", ".join([cat for cat, data in categories.items() if data["max_severity"] == sev]),
                "count": count
            }
            for sev, count in severity_counts.items()
            if count > 0
        ]

        return {
            "version": version,
            "total": len(findings),
            "by_severity": by_severity,
            "severity_counts": severity_counts,
            "findings": all_findings
        }

    def _empty_results(self) -> Dict[str, Any]:
        """Return empty results structure."""
        return {
            "version": "unknown",
            "total": 0,
            "by_severity": [],
            "severity_counts": {"ERROR": 0, "WARNING": 0, "INFO": 0},
            "findings": []
        }
