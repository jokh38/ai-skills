"""
Semgrep security scanner integration for pattern-based analysis.

Runs semgrep with security rules and parses findings.
"""

from typing import Dict, Any
from base_checker import BaseToolChecker


class SemgrepScanner(BaseToolChecker):
    """Wrapper for semgrep security scanner."""

    def __init__(self, workspace: str):
        """
        Initialize semgrep scanner.

        Args:
            workspace: Root directory to analyze
        """
        super().__init__(workspace, "semgrep")

    def scan(self, pattern: str = "**/*.py") -> Dict[str, Any]:
        """
        Run semgrep security scan on workspace.

        Args:
            pattern: File pattern to scan

        Returns:
            Dictionary with security findings
        """
        is_installed, version = self._check_tool_version(["semgrep", "--version"])
        if not is_installed:
            return self._empty_results()

        try:
            cmd = [
                "semgrep",
                "scan",
                "--config=auto",
                "--json",
                "--quiet",
                str(self.workspace),
            ]
            result = self._run_tool(cmd, timeout=300)

            data = self._parse_json_output(result.stdout) if result.stdout else {}
            findings = data.get("results", [])

            return self._process_results(findings, version)

        except Exception:
            return self._empty_results()

    def _process_results(self, findings: list, version: str) -> Dict[str, Any]:
        """Process raw semgrep results into structured format."""
        severity_counts = {"ERROR": 0, "WARNING": 0, "INFO": 0}
        categories = {}
        all_findings = []

        for finding in findings:
            severity = finding.get("extra", {}).get("severity", "INFO").upper()
            if severity not in severity_counts:
                severity = "INFO"

            severity_counts[severity] += 1

            metadata = finding.get("extra", {}).get("metadata", {})
            category = metadata.get("category", "security")
            cwe = metadata.get("cwe", ["CWE-unknown"])
            if isinstance(cwe, list):
                cwe = cwe[0] if cwe else "CWE-unknown"

            category_key = f"{category}"
            if category_key not in categories:
                categories[category_key] = {
                    "cwe": cwe,
                    "count": 0,
                    "max_severity": severity,
                }
            categories[category_key]["count"] += 1
            categories[category_key]["max_severity"] = severity

            all_findings.append(
                {
                    "severity": severity,
                    "category": category,
                    "cwe": cwe,
                    "file": self._normalize_path(finding.get("path", "")),
                    "line": finding.get("start", {}).get("line", 0),
                    "rule_id": finding.get("check_id", "unknown"),
                    "message": finding.get("extra", {}).get(
                        "message", "Security finding"
                    ),
                    "confidence": metadata.get("confidence", "MEDIUM"),
                }
            )

        by_severity = [
            {
                "severity": sev,
                "category": ", ".join(
                    [
                        cat
                        for cat, data in categories.items()
                        if data["max_severity"] == sev
                    ]
                ),
                "count": count,
            }
            for sev, count in severity_counts.items()
            if count > 0
        ]

        return {
            "version": version,
            "total": len(findings),
            "by_severity": by_severity,
            "severity_counts": severity_counts,
            "findings": all_findings,
        }

    def _empty_results(self) -> Dict[str, Any]:
        """Return empty results structure."""
        return {
            "version": "unknown",
            "total": 0,
            "by_severity": [],
            "severity_counts": {"ERROR": 0, "WARNING": 0, "INFO": 0},
            "findings": [],
        }
