"""RRD Orchestrator - Main workflow automation"""

from pathlib import Path
from typing import Optional, Dict, Any

from core.config_loader import RRDConfig, load_rrd_config
from core.cycle_detector import CycleDetector
from core.data_types import ActiveContext, SessionSummary
from orchestrator.session_manager import SessionManager
from orchestrator.phase_executor import (
    PhaseExecutor,
    L1Result,
    L2Result,
    L3Result,
    L4Result,
)


class RRDOrchestrator:
    """Main workflow orchestrator for L1-L4 phases"""

    def __init__(self, config_path: Optional[str] = None, workspace: Optional[Path] = None):
        self.config = load_rrd_config(config_path)
        self.workspace = workspace or Path.cwd()

        self.session_manager = SessionManager(self.workspace)
        self.phase_executor = PhaseExecutor(self.config, self.workspace)
        self.cycle_detector = CycleDetector(window_size=3)

    def execute_full_workflow(
        self, spec_file: Path, output_dir: Optional[Path] = None, mode: str = "auto"
    ) -> SessionSummary:
        """Execute complete L1→L2→L3→L4 workflow

        Args:
            spec_file: Path to specification file
            output_dir: Optional output directory
            mode: Execution mode ("auto", "manual", "interactive")

        Returns:
            SessionSummary with workflow results
        """
        # Create session
        spec_content = spec_file.read_text()
        session = self.session_manager.create_session(
            metadata={
                "spec_file": str(spec_file),
                "mode": mode,
                "output_dir": str(output_dir) if output_dir else "",
            }
        )

        print(f"🚀 Starting RRD workflow (Session: {session.session_id})")
        print(f"📄 Spec: {spec_file}")
        print(f"📁 Workspace: {self.workspace}")

        try:
            # L1: Context & Setup
            print("\n" + "=" * 60)
            print("L1: Context & Setup Phase")
            print("=" * 60)
            l1_result = self.execute_l1_context(spec_file)

            if l1_result.status != "completed":
                raise RuntimeError(f"L1 phase failed: {l1_result.status}")

            # L2: Red-Green-Blue TDD Cycle
            print("\n" + "=" * 60)
            print("L2: Red-Green-Blue Phase")
            print("=" * 60)
            l2_result = self.execute_l2_cycle(spec_content)

            if l2_result.status != "completed":
                raise RuntimeError(f"L2 phase failed: {l2_result.status}")

            # L3: Hardening
            print("\n" + "=" * 60)
            print("L3: Hardening Phase")
            print("=" * 60)
            l3_result = self.execute_l3_hardening()

            if l3_result.status != "completed":
                raise RuntimeError(f"L3 phase failed: {l3_result.status}")

            # L4: Documentation & Commit
            print("\n" + "=" * 60)
            print("L4: Documentation & Commit Phase")
            print("=" * 60)
            l4_result = self.execute_l4_documentation(spec_file)

            if l4_result.status != "completed":
                raise RuntimeError(f"L4 phase failed: {l4_result.status}")

            # Finalize session
            summary = self.session_manager.get_session_summary()
            self.session_manager.finalize_session(
                status="completed", metadata={"total_phases": 4, "success": True}
            )

            print("\n" + "=" * 60)
            print("✅ Workflow Complete!")
            print("=" * 60)
            print(f"Session: {session.session_id}")
            print(f"Phases: {', '.join(summary.phases_completed)}")
            print(f"Commit: {l4_result.commit_hash}")

            return summary

        except Exception as e:
            print(f"\n❌ Workflow failed: {e}")
            self.session_manager.finalize_session(status="failed", metadata={"error": str(e)})
            raise

    def execute_l1_context(self, spec_file: Path) -> L1Result:
        """Phase 1: Load knowledge, analyze codebase, write tests

        Args:
            spec_file: Path to specification file

        Returns:
            L1Result with phase results
        """
        try:
            # Load knowledge kernel
            print("📚 Loading knowledge kernel...")
            knowledge = self.phase_executor.l1_load_knowledge()
            print(f"   ✓ Loaded {len(knowledge)} knowledge entries")

            # Save checkpoint
            self.session_manager.save_checkpoint(
                phase="L1_load_knowledge",
                status="completed",
                data={"knowledge_entries": len(knowledge)},
            )

            # Analyze codebase
            print("🔍 Analyzing codebase structure...")
            analysis = self.phase_executor.l1_analyze_codebase()
            print(f"   ✓ Found {len(analysis.file_summary)} files")

            # Save checkpoint
            self.session_manager.save_checkpoint(
                phase="L1_analyze",
                status="completed",
                data={"files_analyzed": len(analysis.file_summary)},
            )

            # Generate adversarial tests
            print("✍️  Generating adversarial tests...")
            spec_content = spec_file.read_text()
            test_files = self.phase_executor.l1_generate_adversarial_tests(
                spec=spec_content, analysis=analysis
            )
            print(f"   ✓ Generated {len(test_files)} test files")

            # Save checkpoint
            self.session_manager.save_checkpoint(
                phase="L1_generate_tests",
                status="completed",
                data={"test_files": [str(f) for f in test_files]},
            )

            return L1Result(
                tests_generated=test_files,
                knowledge_kernel=knowledge,
                codebase_analysis=analysis,
                status="completed",
            )

        except Exception as e:
            print(f"❌ L1 failed: {e}")
            return L1Result(
                tests_generated=[],
                knowledge_kernel=[],
                codebase_analysis=None,
                status="failed",
            )

    def execute_l2_cycle(self, spec: str) -> L2Result:
        """Phase 2: Red-Green-Blue TDD cycle

        Args:
            spec: Feature specification

        Returns:
            L2Result with phase results
        """
        try:
            cycle_count = 0

            # Red Phase: Create skeleton
            print("🔴 Red Phase: Creating skeleton...")
            skeleton_files = self.phase_executor.l2_red_create_skeleton(spec)
            print(f"   ✓ Created {len(skeleton_files)} skeleton files")

            # Save checkpoint
            self.session_manager.save_checkpoint(
                phase="L2_red",
                status="completed",
                data={"skeleton_files": [str(f) for f in skeleton_files]},
            )

            # Green Phase: Implement with progressive backoff
            print("🟢 Green Phase: Implementing with progressive backoff...")
            test_files = list((self.workspace / "rrd" / "tests").glob("*.py"))

            if not test_files:
                raise RuntimeError("No test files found from L1 phase")

            # Initialize active context
            context = ActiveContext(
                current_file=skeleton_files[0] if skeleton_files else None,
                history=[],
                metadata={},
            )

            green_result = self.phase_executor.l2_green_implement(
                test_file=test_files[0],
                skeleton_file=skeleton_files[0] if skeleton_files else None,
                max_attempts=4,
                context=context,
            )

            if not green_result.success:
                # Check for cycle
                cycle_detected = self.cycle_detector.check_signature_cycle(
                    [f.test_name for f in context.history]
                )

                if cycle_detected:
                    print("   ⚠️  Cycle detected - aborting")
                    cycle_count += 1

                raise RuntimeError("Green phase: Implementation failed after 4 attempts")

            print(f"   ✓ Implementation succeeded (attempt {green_result.attempts})")

            # Save checkpoint
            self.session_manager.save_checkpoint(
                phase="L2_green",
                status="completed",
                data={
                    "attempts": green_result.attempts,
                    "quality_score": green_result.quality_score,
                },
            )

            # Blue Phase: QA analysis (drafting mode)
            print("🔵 Blue Phase: Running QA analysis (drafting)...")
            qa_result = self.phase_executor.l2_blue_qa_analysis(mode="drafting")

            print(f"   ✓ Quality score: {qa_result.quality_report.quality_score}")
            print(f"   ✓ Quality gates: {'PASSED' if qa_result.gate_results.passed else 'FAILED'}")

            # Save checkpoint
            self.session_manager.save_checkpoint(
                phase="L2_blue",
                status="completed",
                data={
                    "quality_score": qa_result.quality_report.quality_score,
                    "gates_passed": qa_result.gate_results.passed,
                },
            )

            return L2Result(
                implementation_files=green_result.files_created,
                quality_report=qa_result.quality_report,
                gate_results=qa_result.gate_results,
                cycle_count=cycle_count,
                status="completed",
            )

        except Exception as e:
            print(f"❌ L2 failed: {e}")
            return L2Result(
                implementation_files=[],
                quality_report=None,
                gate_results=None,
                cycle_count=0,
                status="failed",
            )

    def execute_l3_hardening(self) -> L3Result:
        """Phase 3: Strict QA and performance optimization

        Returns:
            L3Result with phase results
        """
        try:
            # Run strict QA analysis
            print("🛡️  Running hardening QA analysis...")
            qa_result = self.phase_executor.l3_hardening_qa()

            print(f"   ✓ Quality score: {qa_result.quality_report.quality_score}")
            print(f"   ✓ Quality gates: {'PASSED' if qa_result.gate_results.passed else 'FAILED'}")

            if not qa_result.gate_results.passed:
                print("\n   Issues:")
                for gate in qa_result.gate_results.failed_gates:
                    print(f"      - {gate}")

            # Save checkpoint
            self.session_manager.save_checkpoint(
                phase="L3_hardening_qa",
                status="completed",
                data={
                    "quality_score": qa_result.quality_report.quality_score,
                    "gates_passed": qa_result.gate_results.passed,
                },
            )

            # Adversarial review
            print("\n🔍 Running adversarial security review...")
            impl_files = list((self.workspace / "rrd" / "src").glob("*.py"))

            if impl_files:
                code = impl_files[0].read_text()
                review_result = self.phase_executor.l3_adversarial_review(
                    code=code, qa_report=qa_result.quality_report
                )

                print(f"   ✓ Security findings: {len(review_result.findings)}")
                print(f"   ✓ Critical: {review_result.critical_count}")
                print(f"   ✓ High: {review_result.high_count}")

                if review_result.critical_count > 0:
                    print("\n   ⚠️  CRITICAL VULNERABILITIES FOUND!")
                    for finding in review_result.findings:
                        if finding.get("severity") == "CRITICAL":
                            print(f"      - {finding.get('description', 'Unknown')}")
            else:
                review_result = None
                print("   ⚠️  No implementation files found for review")

            # Save checkpoint
            self.session_manager.save_checkpoint(
                phase="L3_security_review",
                status="completed",
                data={
                    "findings": len(review_result.findings) if review_result else 0,
                    "critical": review_result.critical_count if review_result else 0,
                },
            )

            return L3Result(
                security_findings=review_result.findings if review_result else [],
                quality_score=qa_result.quality_report.quality_score,
                quality_report=qa_result.quality_report,
                gate_results=qa_result.gate_results,
                status="completed",
            )

        except Exception as e:
            print(f"❌ L3 failed: {e}")
            return L3Result(
                security_findings=[],
                quality_score=0.0,
                quality_report=None,
                gate_results=None,
                status="failed",
            )

    def execute_l4_documentation(self, spec_file: Path) -> L4Result:
        """Phase 4: Update knowledge kernel and commit

        Args:
            spec_file: Path to specification file

        Returns:
            L4Result with phase results
        """
        try:
            # Update knowledge kernel
            print("📝 Updating knowledge kernel...")
            session_data = self.session_manager.get_session_summary()
            self.phase_executor.l4_update_knowledge_kernel(session_data.__dict__)
            print("   ✓ Knowledge kernel updated")

            # Save checkpoint
            self.session_manager.save_checkpoint(
                phase="L4_update_kernel",
                status="completed",
                data={"kernel_updated": True},
            )

            # Generate documentation
            print("\n📚 Generating documentation...")
            impl_files = list((self.workspace / "rrd" / "src").glob("*.py"))
            test_files = list((self.workspace / "rrd" / "tests").glob("*.py"))

            if impl_files and test_files:
                impl_code = impl_files[0].read_text()
                test_code = test_files[0].read_text()

                documentation = self.phase_executor.llm.generate_documentation(
                    implementation=impl_code, tests=test_code, qa_report=None
                )

                docs_file = self.workspace / "rrd" / "docs" / "feature.md"
                docs_file.parent.mkdir(parents=True, exist_ok=True)
                docs_file.write_text(documentation)

                print("   ✓ Documentation generated")
                documentation_generated = True
            else:
                documentation_generated = False
                print("   ⚠️  No implementation/tests found")

            # Save checkpoint
            self.session_manager.save_checkpoint(
                phase="L4_generate_docs",
                status="completed",
                data={"docs_generated": documentation_generated},
            )

            # Commit with context
            print("\n💾 Committing changes...")
            commit_message = f"RRD: Implement feature from {spec_file.name}"

            context = {
                "session_id": session_data.session_id,
                "phases": session_data.phases_completed,
                "failures": len(session_data.failures),
            }

            commit_hash = self.phase_executor.l4_commit_with_context(
                message=commit_message, context=context
            )

            print(f"   ✓ Committed: {commit_hash}")

            return L4Result(
                commit_hash=commit_hash,
                documentation_generated=documentation_generated,
                knowledge_updated=True,
                status="completed",
            )

        except Exception as e:
            print(f"❌ L4 failed: {e}")
            return L4Result(
                commit_hash="",
                documentation_generated=False,
                knowledge_updated=False,
                status="failed",
            )
