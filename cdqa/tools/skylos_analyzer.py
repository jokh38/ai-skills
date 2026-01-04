"""
Skylos dead code and security analyzer integration.

Detects unused functions, dead code, and security issues by building
a reference graph of the entire codebase. Framework-aware for Django,
Flask, and FastAPI.
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, Any
import logging


class SkylosAnalyzer:
    """Wrapper for skylos dead code analyzer."""

    def __init__(self, workspace: str, confidence: int = 60):
        """
        Initialize skylos analyzer.

        Args:
            workspace: Root directory to analyze
            confidence: Confidence threshold (20=comprehensive, 30=framework,
                       60=safe default). Lower = more aggressive detection.
        """
        self.workspace = Path(workspace)
        self.confidence = confidence
        self.logger = logging.getLogger(__name__)

    def scan(self, pattern: str = "**/*.py") -> Dict[str, Any]:
        """
        Run skylos dead code detection on workspace.

        Args:
            pattern: File pattern to scan

        Returns:
            Dictionary with dead code findings
        """
        try:
            # Check if skylos is installed
            version_result = subprocess.run(
                ["skylos", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if version_result.returncode != 0:
                self.logger.error("skylos not installed")
                return self._empty_results()

            version = version_result.stdout.strip()

            # Run skylos with JSON output
            cmd = [
                "skylos",
                str(self.workspace),
                "--confidence", str(self.confidence),
                "--json"
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )

            # Parse JSON output
            if result.stdout:
                try:
                    data = json.loads(result.stdout)
                except json.JSONDecodeError:
                    # Try parsing line-by-line
                    data = {"findings": []}
                    for line in result.stdout.strip().split('\n'):
                        if line:
                            try:
                                item = json.loads(line)
                                if "findings" in item:
                                    data = item
                                    break
                            except json.JSONDecodeError:
                                continue
            else:
                data = {"findings": []}

            # Process results
            return self._process_results(data, version)

        except subprocess.TimeoutExpired:
            self.logger.error("skylos scan timed out")
            return self._empty_results()
        except Exception as e:
            self.logger.error(f"skylos scan failed: {e}")
            return self._empty_results()

    def _process_results(self, data: Dict, version: str) -> Dict[str, Any]:
        """Process raw skylos results into structured format."""
        dead_functions = []
        unused_imports = []
        security_findings = []

        # Extract findings
        findings = data.get("findings", data.get("results", []))

        for finding in findings:
            file_path = finding.get("file", finding.get("path", ""))
            try:
                rel_path = str(Path(file_path).relative_to(self.workspace))
            except ValueError:
                rel_path = file_path

            finding_type = finding.get("type", finding.get("kind", ""))
            confidence_score = finding.get("confidence", 100)

            if finding_type in ["unused_function", "dead_function", "unused-function"]:
                dead_functions.append({
                    "file": rel_path,
                    "line": finding.get("line", 0),
                    "function": finding.get("name", finding.get("symbol", "unknown")),
                    "confidence": confidence_score
                })
            elif finding_type in ["unused_import", "unused-import"]:
                unused_imports.append({
                    "file": rel_path,
                    "line": finding.get("line", 0),
                    "import": finding.get("name", finding.get("symbol", "unknown"))
                })
            elif finding_type in ["security", "security_issue", "vulnerability"]:
                security_findings.append({
                    "file": rel_path,
                    "line": finding.get("line", 0),
                    "severity": finding.get("severity", "WARNING"),
                    "category": finding.get("category", "security"),
                    "message": finding.get("message", "Security issue detected")
                })

        # Sort by confidence (highest first)
        dead_functions.sort(key=lambda x: x["confidence"], reverse=True)

        return {
            "version": version,
            "total_dead_code": len(dead_functions) + len(unused_imports),
            "dead_functions": dead_functions,
            "unused_imports": unused_imports,
            "security_findings": security_findings,
            "confidence_level": self.confidence
        }

    def _empty_results(self) -> Dict[str, Any]:
        """Return empty results structure."""
        return {
            "version": "unknown",
            "total_dead_code": 0,
            "dead_functions": [],
            "unused_imports": [],
            "security_findings": [],
            "confidence_level": self.confidence
        }
