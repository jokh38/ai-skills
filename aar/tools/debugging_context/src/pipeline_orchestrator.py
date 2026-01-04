import logging
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.artifact_manager import ReportContextLoader
from src.verification_runner import TestSuiteExecutor
from src.context_resolver import FailureContextMapper
from src.prompt_builder import ToonPayloadGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RepairWorkflowEngine:
    
    def __init__(self):
        self.loader = ReportContextLoader()
        self.runner = TestSuiteExecutor()
        self.mapper = FailureContextMapper()
        self.builder = ToonPayloadGenerator()
    
    def _ensure_structure_toon(self, workspace: Path) -> Path:
        structure_path = workspace / "structure.toon"
        if not structure_path.exists():
            logger.info("structure.toon not found, running code_analyzer...")
            code_analyzer_path = Path(__file__).parent.parent / ".." / "code_analyzer" / "run_code_review.py"
            cmd = [
                sys.executable,
                str(code_analyzer_path),
                "--workspace", str(workspace.resolve()),
                "--output", str(structure_path.resolve())
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"code_analyzer failed: {result.stderr}")
                raise RuntimeError("Failed to generate structure.toon")
            logger.info(f"Generated structure.toon at {structure_path}")
        return structure_path

    def _ensure_qa_report_toon(self, workspace: Path) -> Path:
        quality_path = workspace / "qa_report.toon"
        if not quality_path.exists():
            logger.info("qa_report.toon not found, running code_QA...")
            code_qa_path = Path(__file__).parent.parent / ".." / "code_QA" / "run_QA.py"
            cmd = [
                sys.executable,
                str(code_qa_path),
                "--workspace", str(workspace.resolve()),
                "--output", str(quality_path.resolve())
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"code_QA failed: {result.stderr}")
                raise RuntimeError("Failed to generate qa_report.toon")
            logger.info(f"Generated qa_report.toon at {quality_path}")
        return quality_path

    def execute_pipeline(self, workspace: Path, test_case: str | None = None) -> Path:
        logger.info(f"Starting workflow for workspace: {workspace}")
        
        structure_path = self._ensure_structure_toon(workspace)
        quality_path = self._ensure_qa_report_toon(workspace)
        output_path = workspace / "fix_payload.toon"
        
        if test_case:
            logger.info(f"Running specific test case: {test_case}")
        result = self.runner.trigger_verification(target_dir=workspace, test_case=test_case)
        
        if result.exit_code == 0:
            logger.info("All tests passed. Generating success notice.")
            success_payload = self.builder.construct_success_notice()
            self.builder.save_payload(success_payload, output_path)
            logger.info(f"Success payload saved to: {output_path}")
            return output_path
        
        logger.info(f"Test failures detected: {result.failed_tests} failures out of {result.total_tests} tests")
        
        failures = self.runner.extract_failure_metadata(result.report_path)
        
        if not failures:
            logger.warning("No failure metadata extracted. Generating success notice.")
            success_payload = self.builder.construct_success_notice()
            self.builder.save_payload(success_payload, output_path)
            return output_path
        
        static_map = self.loader.load_static_context(structure_path, quality_path)
        
        deduplicated_failures = self.mapper.deduplicate_failures(failures)
        
        enriched_contexts = self.mapper.enrich_failure_data(
            deduplicated_failures,
            static_map.structure_map,
            static_map.quality_map
        )
        
        fix_payload = self.builder.construct_fix_request(enriched_contexts)
        self.builder.save_payload(fix_payload, output_path)
        
        logger.info(f"Fix proposal payload saved to: {output_path}")
        logger.info(f"Total unique failures: {len(enriched_contexts)}")
        
        return output_path
    
    def handle_exception(self, exception: Exception) -> None:
        logger.error(f"Pipeline execution failed: {exception}", exc_info=True)
        raise


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Automated Test Repair Payload Generator"
    )
    parser.add_argument(
        'workspace',
        type=Path,
        help='Path to the workspace containing tests and TOON artifacts'
    )
    parser.add_argument(
        '--test-case',
        type=str,
        default=None,
        help='Run only a specific test case (e.g., tests/test_example.py::test_function)'
    )
    
    args = parser.parse_args()
    
    if not args.workspace.exists():
        logger.error(f"Workspace does not exist: {args.workspace}")
        sys.exit(1)
    
    try:
        engine = RepairWorkflowEngine()
        output_path = engine.execute_pipeline(args.workspace, args.test_case)
        print(f"Workflow completed. Output: {output_path}")
        sys.exit(0)
    except Exception as e:
        engine = RepairWorkflowEngine()
        engine.handle_exception(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
