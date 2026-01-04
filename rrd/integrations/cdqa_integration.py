"""cdqa tool integration for RRD system"""

import subprocess
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from core.config_loader import RRDConfig
from core.toon_utils import parse_toon, ToonParser


@dataclass
class QualityReport:
    """Report from cdqa code quality analysis"""

    lint_issues: List[Dict[str, Any]]
    type_errors: List[Dict[str, Any]]
    security_issues: List[Dict[str, Any]]
    complexity_metrics: Dict[str, Any]
    quality_score: float
    raw_output: str


@dataclass
class GateResults:
    """Results from quality gate checks"""

    passed: bool
    failed_gates: List[str]
    details: Dict[str, Any]


@dataclass
class AutoFix:
    """Auto-fixable issue from cdqa"""

    file_path: str
    line: int
    issue_type: str
    fix_command: str
    description: str


class CdqaIntegration:
    """Wrapper for cdqa code quality analysis tool"""

    def __init__(self, config: RRDConfig):
        self.config = config
        try:
            self.tool_path = str(config.get_tool_path("cdqa"))
        except KeyError:
            self.tool_path = "cdqa"
        self.parser = ToonParser()

    def run_quality_check(
        self,
        workspace: Path,
        mode: str = "drafting",
        output_file: Optional[Path] = None,
    ) -> QualityReport:
        """Run cdqa analysis and parse TOON output

        Args:
            workspace: Path to codebase to analyze
            mode: Quality mode - "drafting" (lenient) or "hardening" (strict)
            output_file: Optional path to save TOON output

        Returns:
            QualityReport with analysis results
        """
        try:
            cmd = [self.tool_path, str(workspace), "--format", "toon"]
            if mode == "hardening":
                cmd.extend(["--mode", "strict"])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode != 0:
                raise RuntimeError(f"cdqa failed: {result.stderr}")

            toon_output = result.stdout

            if output_file:
                output_file.write_text(toon_output)

            return self._parse_quality_report(toon_output)

        except subprocess.TimeoutExpired:
            raise TimeoutError("cdqa analysis timed out after 5 minutes")
        except FileNotFoundError:
            raise RuntimeError(f"cdqa tool not found at {self.tool_path}")

    def _parse_quality_report(self, toon_output: str) -> QualityReport:
        """Parse TOON output from cdqa into structured report"""
        try:
            parsed = self.parser.parse(toon_output)

            if isinstance(parsed, list) and len(parsed) > 0:
                data = parsed[0]
            else:
                data = parsed if isinstance(parsed, dict) else {}

            lint_issues = data.get("lint_issues", [])
            type_errors = data.get("type_errors", [])
            security_issues = data.get("security_issues", [])
            complexity_metrics = data.get("complexity_metrics", {})
            quality_score = float(data.get("quality_score", 0.0))

            return QualityReport(
                lint_issues=lint_issues,
                type_errors=type_errors,
                security_issues=security_issues,
                complexity_metrics=complexity_metrics,
                quality_score=quality_score,
                raw_output=toon_output,
            )
        except Exception as e:
            return QualityReport(
                lint_issues=[],
                type_errors=[],
                security_issues=[],
                complexity_metrics={},
                quality_score=0.0,
                raw_output=toon_output,
            )

    def check_quality_gates(
        self, report: QualityReport, thresholds: Optional[Dict[str, Any]] = None
    ) -> GateResults:
        """Verify all quality gates pass

        Args:
            report: Quality report from cdqa
            thresholds: Custom thresholds (uses defaults if None)

        Returns:
            GateResults with pass/fail status
        """
        defaults = {
            "max_critical": 0,
            "max_type_errors": 0,
            "max_security_high": 0,
            "min_quality_score": 85.0,
        }

        thresholds = {**defaults, **(thresholds or {})}

        failed_gates = []
        details = {}

        critical_issues = [i for i in report.lint_issues if i.get("severity") == "critical"]
        if len(critical_issues) > thresholds["max_critical"]:
            failed_gates.append(
                f"Critical lint issues: {len(critical_issues)} > {thresholds['max_critical']}"
            )

        if len(report.type_errors) > thresholds["max_type_errors"]:
            failed_gates.append(
                f"Type errors: {len(report.type_errors)} > {thresholds['max_type_errors']}"
            )

        high_security = [i for i in report.security_issues if i.get("severity") == "high"]
        if len(high_security) > thresholds["max_security_high"]:
            failed_gates.append(
                f"High severity security issues: {len(high_security)} > {thresholds['max_security_high']}"
            )

        if report.quality_score < thresholds["min_quality_score"]:
            failed_gates.append(
                f"Quality score: {report.quality_score} < {thresholds['min_quality_score']}"
            )

        details = {
            "critical_issues": len(critical_issues),
            "type_errors": len(report.type_errors),
            "high_security": len(high_security),
            "quality_score": report.quality_score,
        }

        return GateResults(
            passed=len(failed_gates) == 0, failed_gates=failed_gates, details=details
        )

    def get_auto_fixes(self, report: QualityReport) -> List[AutoFix]:
        """Extract auto-fixable issues from quality report

        Args:
            report: Quality report from cdqa

        Returns:
            List of AutoFix objects
        """
        auto_fixes = []

        for issue in report.lint_issues:
            if issue.get("autofixable"):
                fix_cmd = issue.get("fix_command", "")
                if fix_cmd:
                    auto_fixes.append(
                        AutoFix(
                            file_path=issue.get("file", ""),
                            line=issue.get("line", 0),
                            issue_type=issue.get("code", ""),
                            fix_command=fix_cmd,
                            description=issue.get("message", ""),
                        )
                    )

        for error in report.type_errors:
            if error.get("autofixable"):
                fix_cmd = error.get("fix_command", "")
                if fix_cmd:
                    auto_fixes.append(
                        AutoFix(
                            file_path=error.get("file", ""),
                            line=error.get("line", 0),
                            issue_type="type_error",
                            fix_command=fix_cmd,
                            description=error.get("message", ""),
                        )
                    )

        return auto_fixes

    def apply_auto_fix(self, fix: AutoFix) -> bool:
        """Apply a single auto-fix

        Args:
            fix: AutoFix object with fix details

        Returns:
            True if fix was applied successfully
        """
        try:
            result = subprocess.run(
                fix.fix_command, shell=True, capture_output=True, text=True, timeout=60
            )
            return result.returncode == 0
        except Exception:
            return False
