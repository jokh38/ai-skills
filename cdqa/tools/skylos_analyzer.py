"""
Skylos dead code and security analyzer integration.

Detects unused functions, dead code, and security issues by building
a reference graph of the entire codebase. Framework-aware for Django,
Flask, and FastAPI.
"""

from typing import Dict, Any
from base_checker import BaseToolChecker


class SkylosAnalyzer(BaseToolChecker):
    """Wrapper for skylos dead code analyzer."""

    def __init__(self, workspace: str, confidence: int = 60):
        """
        Initialize skylos analyzer.

        Args:
            workspace: Root directory to analyze
            confidence: Confidence threshold (20=comprehensive, 30=framework,
                       60=safe default). Lower = more aggressive detection.
        """
        super().__init__(workspace, "skylos")
        self.confidence = confidence

    def scan(self, pattern: str = "**/*.py") -> Dict[str, Any]:
        """
        Run skylos dead code detection on workspace.

        Args:
            pattern: File pattern to scan

        Returns:
            Dictionary with dead code findings
        """
        is_installed, version = self._check_tool_version(["skylos", "--version"])
        if not is_installed:
            return self._empty_results()

        try:
            cmd = [
                "skylos",
                str(self.workspace),
                "--confidence",
                str(self.confidence),
                "--json",
            ]
            result = self._run_tool(cmd, timeout=120)

            data = (
                self._parse_json_output(result.stdout, line_by_line=True)
                if result.stdout
                else {}
            )
            findings = data.get("findings", data.get("results", []))

            return self._process_results(findings, version)

        except Exception:
            return self._empty_results()

    def _process_results(self, findings: list, version: str) -> Dict[str, Any]:
        """Process raw skylos results into structured format."""
        dead_functions = []
        unused_imports = []
        security_findings = []

        for finding in findings:
            file_path = finding.get("file", finding.get("path", ""))
            rel_path = self._normalize_path(file_path)

            finding_type = finding.get("type", finding.get("kind", ""))
            confidence_score = finding.get("confidence", 100)

            if finding_type in ["unused_function", "dead_function", "unused-function"]:
                dead_functions.append(
                    {
                        "file": rel_path,
                        "line": finding.get("line", 0),
                        "function": finding.get(
                            "name", finding.get("symbol", "unknown")
                        ),
                        "confidence": confidence_score,
                    }
                )
            elif finding_type in ["unused_import", "unused-import"]:
                unused_imports.append(
                    {
                        "file": rel_path,
                        "line": finding.get("line", 0),
                        "import": finding.get("name", finding.get("symbol", "unknown")),
                    }
                )
            elif finding_type in ["security", "security_issue", "vulnerability"]:
                security_findings.append(
                    {
                        "file": rel_path,
                        "line": finding.get("line", 0),
                        "severity": finding.get("severity", "WARNING"),
                        "category": finding.get("category", "security"),
                        "message": finding.get("message", "Security issue detected"),
                    }
                )

        dead_functions.sort(key=lambda x: x["confidence"], reverse=True)

        return {
            "version": version,
            "total_dead_code": len(dead_functions) + len(unused_imports),
            "dead_functions": dead_functions,
            "unused_imports": unused_imports,
            "security_findings": security_findings,
            "confidence_level": self.confidence,
        }

    def _empty_results(self) -> Dict[str, Any]:
        """Return empty results structure."""
        return {
            "version": "unknown",
            "total_dead_code": 0,
            "dead_functions": [],
            "unused_imports": [],
            "security_findings": [],
            "confidence_level": self.confidence,
        }
