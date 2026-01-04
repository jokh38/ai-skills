"""Phase Executor for RRD workflow"""

import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from core.config_loader import RRDConfig
from core.toon_utils import parse_toon
from core.data_types import PatchToon, ActiveContext
from integrations.cdqa_integration import (
    CdqaIntegration,
    QualityReport,
    GateResults,
    AutoFix,
)
from integrations.cdscan_integration import CdscanIntegration, CodebaseAnalysis
from integrations.dbgctxt_integration import DbgctxtIntegration, DebugContext
from integrations.zgit_integration import ZgitIntegration
from llm.llm_client import LLMClient


@dataclass
class L1Result:
    """Result from L1 (Context & Setup) phase"""

    tests_generated: List[Path]
    knowledge_kernel: List[Dict[str, Any]]
    codebase_analysis: Optional[CodebaseAnalysis]
    status: str


@dataclass
class L2Result:
    """Result from L2 (Red-Green-Blue) phase"""

    implementation_files: List[Path]
    quality_report: QualityReport
    gate_results: GateResults
    cycle_count: int
    status: str


@dataclass
class L3Result:
    """Result from L3 (Hardening) phase"""

    security_findings: List[Dict[str, Any]]
    quality_score: float
    quality_report: QualityReport
    gate_results: GateResults
    status: str


@dataclass
class L4Result:
    """Result from L4 (Documentation & Commit) phase"""

    commit_hash: str
    documentation_generated: bool
    knowledge_updated: bool
    status: str


@dataclass
class GreenResult:
    """Result from Green phase implementation"""

    files_created: List[Path]
    attempts: int
    success: bool
    quality_score: float


@dataclass
class QAResult:
    """Result from QA analysis"""

    quality_report: QualityReport
    gate_results: GateResults
    auto_fixes: List[AutoFix]
    status: str


@dataclass
class ReviewResult:
    """Result from adversarial review"""

    findings: List[Dict[str, Any]]
    critical_count: int
    high_count: int
    status: str


class PhaseExecutor:
    """Executes individual L1-L4 phases"""

    def __init__(self, config: RRDConfig, workspace: Path):
        self.config = config
        self.workspace = workspace
        self.cdqa = CdqaIntegration(config)
        self.cdscan = CdscanIntegration(config)
        self.dbgctxt = DbgctxtIntegration(config)
        self.zgit = ZgitIntegration(config)
        self.llm = LLMClient(config)

    def l1_load_knowledge(self) -> List[Dict[str, Any]]:
        """Load filtered knowledge kernel

        Returns:
            List of knowledge entries for context
        """
        kernel_path = self.workspace / ".specify" / "memory" / "knowledge_kernel.toon"

        if not kernel_path.exists():
            return []

        try:
            toon_data = kernel_path.read_text()
            parsed = parse_toon(toon_data)

            if isinstance(parsed, list):
                return parsed
            elif isinstance(parsed, dict):
                return [parsed]
            else:
                return []
        except Exception:
            return []

    def l1_analyze_codebase(self) -> CodebaseAnalysis:
        """Run cdscan for structure analysis

        Returns:
            CodebaseAnalysis with structure information
        """
        return self.cdscan.analyze_codebase(
            workspace=self.workspace, pattern="**/*.py", incremental=False
        )

    def l1_generate_adversarial_tests(
        self, spec: str, analysis: Optional[CodebaseAnalysis] = None
    ) -> List[Path]:
        """Generate pytest tests using LLM

        Args:
            spec: Feature specification
            analysis: Optional codebase analysis for context

        Returns:
            List of generated test file paths
        """
        tests_dir = self.workspace / "rrd" / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)

        test_code = self.llm.generate_adversarial_tests(
            spec=spec, codebase_analysis=analysis
        )

        if not test_code or test_code.startswith("Error"):
            raise RuntimeError("Failed to generate tests with LLM")

        # Write test file
        test_file = tests_dir / "test_feature.py"
        test_file.write_text(test_code)

        return [test_file]

    def l2_red_create_skeleton(self, spec: str) -> List[Path]:
        """Create interfaces only (NotImplementedError)

        Args:
            spec: Feature specification

        Returns:
            List of skeleton file paths
        """
        skeleton_code = self.llm.generate_skeleton(spec)

        if not skeleton_code or skeleton_code.startswith("Error"):
            raise RuntimeError("Failed to generate skeleton with LLM")

        # Determine file path from spec
        skeleton_file = self.workspace / "rrd" / "skeleton.py"
        skeleton_file.write_text(skeleton_code)

        return [skeleton_file]

    def l2_green_implement(
        self,
        test_file: Path,
        skeleton_file: Optional[Path] = None,
        max_attempts: int = 4,
        context: Optional[ActiveContext] = None,
    ) -> GreenResult:
        """Implement code to pass tests with progressive backoff

        Args:
            test_file: Path to test file
            skeleton_file: Optional skeleton file
            max_attempts: Maximum implementation attempts
            context: Active context for learning

        Returns:
            GreenResult with implementation details
        """
        implementation_dir = self.workspace / "rrd" / "src"
        implementation_dir.mkdir(parents=True, exist_ok=True)

        test_code = test_file.read_text()
        skeleton_code = ""

        if skeleton_file and skeleton_file.exists():
            skeleton_code = skeleton_file.read_text()

        for attempt in range(1, max_attempts + 1):
            try:
                # Generate implementation
                impl_code = self.llm.generate_implementation(
                    test_code=test_code, skeleton=skeleton_code, context=context
                )

                if not impl_code or impl_code.startswith("Error"):
                    raise RuntimeError("LLM failed to generate implementation")

                # Write implementation
                impl_file = implementation_dir / "implementation.py"
                impl_file.write_text(impl_code)

                # Run tests
                test_result = subprocess.run(
                    ["pytest", str(test_file), "-v"],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )

                if test_result.returncode == 0:
                    # Tests pass - run quality check
                    quality_report = self.cdqa.run_quality_check(
                        workspace=self.workspace, mode="drafting"
                    )

                    return GreenResult(
                        files_created=[impl_file],
                        attempts=attempt,
                        success=True,
                        quality_score=quality_report.quality_score,
                    )
                else:
                    # Tests failed - use dbgctxt for repair
                    debug_context = self.dbgctxt.analyze_test_failures(
                        test_file=test_file, workspace=self.workspace
                    )

                    # Apply fix proposals
                    for proposal in debug_context.fix_proposals:
                        from core.patch_manager import PatchManager

                        patch_mgr = PatchManager()
                        patch_mgr.apply_patch(self.workspace, proposal)

                    # Update context with failure
                    if context:
                        from core.data_types import FailureSignature

                        failure = FailureSignature(
                            test_name=test_file.name,
                            error_message=test_result.stderr[:200],
                            stack_trace="",
                            file_context=impl_code[:500],
                        )
                        context.history.append(failure)

            except Exception as e:
                print(f"Attempt {attempt} failed: {e}")

                # Progressive backoff: wait longer on later attempts
                if attempt < max_attempts:
                    import time

                    time.sleep(attempt * 5)

        # All attempts failed
        return GreenResult(
            files_created=[], attempts=max_attempts, success=False, quality_score=0.0
        )

    def l2_blue_qa_analysis(self, mode: str = "drafting") -> QAResult:
        """Run quality analysis (L2=drafting, L3=hardening)

        Args:
            mode: Quality mode ("drafting" or "hardening")

        Returns:
            QAResult with quality information
        """
        quality_report = self.cdqa.run_quality_check(
            workspace=self.workspace, mode=mode
        )

        thresholds = {
            "drafting": {
                "max_critical": 5,
                "max_type_errors": 10,
                "max_security_high": 2,
                "min_quality_score": 70.0,
            },
            "hardening": {
                "max_critical": 0,
                "max_type_errors": 0,
                "max_security_high": 0,
                "min_quality_score": 85.0,
            },
        }.get(mode, thresholds["drafting"])

        gate_results = self.cdqa.check_quality_gates(quality_report, thresholds)

        auto_fixes = self.cdqa.get_auto_fixes(quality_report)

        return QAResult(
            quality_report=quality_report,
            gate_results=gate_results,
            auto_fixes=auto_fixes,
            status="passed" if gate_results.passed else "failed",
        )

    def l3_adversarial_review(
        self, code: str, qa_report: Optional[QualityReport] = None
    ) -> ReviewResult:
        """Critic mode: attack code for vulnerabilities

        Args:
            code: Code to review
            qa_report: Optional quality analysis

        Returns:
            ReviewResult with security findings
        """
        findings = self.llm.adversarial_review(code=code, qa_report=qa_report)

        critical_count = sum(1 for f in findings if f.get("severity") == "CRITICAL")
        high_count = sum(1 for f in findings if f.get("severity") == "HIGH")

        return ReviewResult(
            findings=findings,
            critical_count=critical_count,
            high_count=high_count,
            status="passed"
            if critical_count == 0 and high_count == 0
            else "needs_review",
        )

    def l3_hardening_qa(self) -> QAResult:
        """Run strict quality analysis in hardening mode

        Returns:
            QAResult with hardening-level quality information
        """
        return self.l2_blue_qa_analysis(mode="hardening")

    def l4_update_knowledge_kernel(self, session_data: Dict[str, Any]):
        """Record failures and patterns

        Args:
            session_data: Session data to record in kernel
        """
        kernel_path = self.workspace / ".specify" / "memory" / "knowledge_kernel.toon"

        existing_entries = []
        if kernel_path.exists():
            toon_data = kernel_path.read_text()
            parsed = parse_toon(toon_data)
            if isinstance(parsed, list):
                existing_entries = parsed

        # Add new entry
        new_entry = {
            "timestamp": session_data.get("updated_at", ""),
            "session_id": session_data.get("session_id", ""),
            "phases": session_data.get("phases_completed", []),
            "failures": [fs.__dict__ for fs in session_data.get("failures", [])],
        }

        existing_entries.append(new_entry)

        # Write back
        from core.toon_utils import dumps

        kernel_path.write_text(dumps(existing_entries))

    def l4_commit_with_context(self, message: str, context: Dict[str, Any]) -> str:
        """Commit using zgit with context preservation

        Args:
            message: Commit message
            context: RRD context to preserve

        Returns:
            Commit hash
        """
        result = self.zgit.commit_with_context(
            message=message, context=context, stage_all=True
        )

        return result.commit_hash
