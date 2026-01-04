"""Agent orchestrator - main pipeline controller

This module coordinates the repair pipeline:
- Runs static fixes (Ruff)
- Gathers debugging context
- Requests LLM fixes via LLMGateway
- Applies patches
- Detects cycles
"""

from pathlib import Path
from datetime import datetime
import logging
import os
import json
from typing import Optional

from modules.data_types import (
    PatchToon,
    Config,
)
from modules.static_fixer import StaticFixer
from modules.debugging_context import DebuggingContext
from modules.history_manager import HistoryManager
from modules.cycle_detector import CycleDetector
from modules.patch_manager import PatchManager
from modules.toon_utils import ToonEncoder
from modules.llm_gateway import LLMGateway


logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Main pipeline controller for repair agent

    Coordinates the repair workflow:
    1. Static fixing with Ruff
    2. Test execution and failure collection
    3. LLM-based fix generation
    4. Patch application
    5. Cycle detection
    """

    def __init__(self, config: Config | None = None):
        """
        Initialize orchestrator

        Args:
            config: Configuration object (uses defaults if None)
        """
        self.config = config or Config.from_env()

        self.static_fixer = StaticFixer(
            ruff_rules=self.config.ruff_rules,
        )
        self.debugging_context = DebuggingContext()
        self.patch_manager = PatchManager(
            create_backups=self.config.backup_before_patch,
        )
        self.cycle_detector = CycleDetector(
            window_size=self.config.cycle_window,
        )

        self.encoder = ToonEncoder()

        self.history_manager: HistoryManager | None = None
        self.session_dir: Path | None = None

        # Initialize LLM Gateway with environment variables
        api_key = (
            os.getenv("ZAI_API_KEY") or
            os.getenv("OPENAI_API_KEY") or
            os.getenv("ANTHROPIC_API_KEY") or
            os.getenv("LLM_API_KEY")
        )
        # Check LLM_MODEL first (explicit override), then DEFAULT_MODEL (from .env)
        model = os.getenv("LLM_MODEL") or os.getenv("DEFAULT_MODEL")

        if not api_key:
            logger.warning(
                "LLM credentials not found in environment. Using mock LLM gateway."
            )

        self.llm_gateway = LLMGateway(
            api_key=api_key,
            model=model or "gpt-4",
            timeout=self.config.llm_timeout_seconds,
            max_retries=self.config.max_toon_retries,
        )

    def run_repair_session(
        self, target_file: Path, max_retries: int | None = None
    ) -> str:
        """
        Run repair session on target file

        Args:
            target_file: Path to file to repair
            max_retries: Maximum retry attempts (uses config if None)

        Returns:
            Status code: SUCCESS, MAX_RETRIES_EXCEEDED, CYCLE_DETECTED
        """
        max_retries = max_retries or self.config.max_retries

        try:
            session_dir = self._init_session()
            self.history_manager = HistoryManager(session_dir)
            self.cycle_detector.reset()

            logger.info(f"Starting repair session: {session_dir.name}")
            logger.info(f"Target: {target_file}")
            logger.info(f"Max retries: {max_retries}")

            for i in range(1, max_retries + 1):
                logger.info(f"--- Iteration {i} ---")

                try:
                    result = self._run_iteration(target_file, i)

                    if result == "SUCCESS":
                        logger.info("All tests passed, repair complete")
                        self.history_manager.save_session_summary(i, "SUCCESS")
                        return "SUCCESS"

                except Exception as e:
                    logger.error(f"Iteration {i} failed: {e}")
                    self.history_manager.recorder.append_log(
                        iteration=i,
                        patch=None,
                        outcome=[],
                        pruned=[],
                        status="error",
                    )

            logger.warning(f"Max retries ({max_retries}) exceeded")
            self.history_manager.save_session_summary(max_retries, "MAX_RETRIES_EXCEEDED")
            return "MAX_RETRIES_EXCEEDED"

        except Exception as e:
            logger.critical(f"Session failed: {e}")
            return "SESSION_INIT_ERROR"

    def _run_iteration(self, target_file: Path, iteration: int) -> str:
        """Run a single repair iteration"""
        if self.history_manager is None:
            raise RuntimeError("History manager not initialized")
        if self.session_dir is None:
            raise RuntimeError("Session directory not initialized")
        
        current_failures: list = []

        if self.config.ruff_enabled:
            logger.debug("Running Ruff auto-fix")
            fix_report = self.static_fixer.execute_autofix(target_file)
            if fix_report.fixes_applied:
                logger.info(f"Ruff applied {len(fix_report.fixes_applied)} fixes")

        logger.debug("Running tests")
        test_payload = self.debugging_context.get_current_context(target_file)

        if not test_payload.failures:
            logger.info("Tests passed")
            if self.history_manager:
                self.history_manager.recorder.append_log(
                    iteration=iteration,
                    patch=None,
                    outcome=[],
                    pruned=[],
                    status="success",
                )
            return "SUCCESS"

        logger.info(f"Found {len(test_payload.failures)} failures")

        filtered_failures = self.debugging_context.filter_duplicate_failures(
            test_payload.failures
        )
        current_failures = filtered_failures

        sig_set = {str(f) for f in current_failures}

        logger.debug("Generating active context")
        active_context = self.history_manager.pruner.get_active_context(
            current_failures, iteration
        )

        if self.session_dir is None:
            raise RuntimeError("Session directory not initialized")
        context_file = self.session_dir / f"iter_{iteration:02d}_context.toon"
        with open(context_file, "w") as f:
            f.write(self.encoder.encode_active_context(active_context))

        logger.debug("Requesting LLM fix")
        patch = self.llm_gateway.request_fix(active_context)

        if self.cycle_detector.check_duplicate_patch(patch):
            logger.warning("Duplicate patch detected, terminating session")
            raise RuntimeError("CYCLE_DETECTED")

        # Update cycle detection history only after getting a patch
        self.cycle_detector.update_history(patch, sig_set)

        patch_file = self.session_dir / f"iter_{iteration:02d}_patch.toon"
        with open(patch_file, "w") as f:
            f.write(self.encoder.encode_patch_toon(patch))

        logger.debug("Applying patch")
        applied = self.patch_manager.apply_patch(patch)

        if not applied:
            logger.error("Failed to apply patch")
            if self.history_manager:
                self.history_manager.recorder.append_log(
                    iteration=iteration,
                    patch=patch,
                    outcome=current_failures,
                    pruned=self.history_manager.pruner.get_last_pruned_items(),
                    status="failed",
                )
            return "FAILED"

        if current_failures:
            self.history_manager.pruner.log_attempt(
                current_failures[0],
                iteration,
                f"Applied patch to {patch.file_path}",
                "Applied",
            )

        for failure in self.history_manager.pruner.get_last_pruned_items():
            if failure:
                self.history_manager.pruner.mark_resolved(failure)

        failure_file = self.session_dir / f"iter_{iteration:02d}_failure.toon"
        with open(failure_file, "w") as f:
            f.write(
                self.debugging_context.encode_failure_payload_toon(
                    test_payload
                )
            )

        if self.history_manager:
            self.history_manager.recorder.append_log(
                iteration=iteration,
                patch=patch,
                outcome=current_failures,
                pruned=self.history_manager.pruner.get_last_pruned_items(),
                status="in_progress",
            )

        return "CONTINUE"

    def _init_session(self) -> Path:
        """Initialize session directory"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_name = f"session_{timestamp}"

        log_dir = Path(os.getenv("REPAIR_LOG_DIR", "./repair_logs"))
        session_dir = log_dir / session_name
        session_dir.mkdir(parents=True, exist_ok=True)

        self.session_dir = session_dir

        metadata = {
            "session_id": session_name,
            "timestamp": datetime.now().isoformat(),
            "max_retries": self.config.max_retries,
            "ruff_enabled": self.config.ruff_enabled,
            "cycle_window": self.config.cycle_window,
        }

        with open(session_dir / "session_metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        return session_dir

    def validate_session_state(self) -> bool:
        """Validate that session state is consistent"""
        return self.history_manager is not None and self.session_dir is not None

    def detect_cycles(self) -> str | None:
        """Detect if cycles are occurring"""
        pattern = self.cycle_detector.detect_pattern()
        if pattern:
            return " | ".join(pattern)
        return None


def run_repair_session(
    target_file: Path,
    max_retries: int = 5,
    config: Config | None = None,
) -> str:
    """
    Convenience function to run a repair session

    Args:
        target_file: Path to file to repair
        max_retries: Maximum retry attempts
        config: Optional configuration

    Returns:
        Status code
    """
    orchestrator = AgentOrchestrator(config)
    return orchestrator.run_repair_session(target_file, max_retries)
