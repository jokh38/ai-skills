"""History manager module for dual-history tracking"""

from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import logging

from modules.data_types import FailureSignature, PatchToon, ActiveContext, SessionSummary
from modules.toon_utils import ToonEncoder


logger = logging.getLogger(__name__)


class ContextPruner:
    """For LLM: Maintain active context, filter resolved issues"""

    def __init__(self):
        self.issue_log: List[Dict[str, Any]] = []
        self.last_pruned_items: List[FailureSignature] = []

    def get_active_context(
        self, current_failures: List[FailureSignature], iteration: int
    ) -> ActiveContext:
        """
        Filter active issues for LLM context (only unresolved issues)

        Args:
            current_failures: Current list of failure signatures
            iteration: Current iteration number

        Returns:
            ActiveContext with filtered history
        """
        current_sig_strings = {str(f) for f in current_failures}

        active_history = []
        pruned_this_round = []

        for entry in self.issue_log:
            entry_sig = entry.get("target_signature", "")
            if entry_sig in current_sig_strings:
                active_history.append(entry)
            else:
                pruned_this_round.append(entry.get("signature"))
                logger.debug(f"Pruning resolved issue: {entry_sig}")

        self.last_pruned_items = [s for s in pruned_this_round if s is not None]

        return ActiveContext(
            active_history=active_history,
            current_failures=current_failures,
            iteration=iteration,
        )

    def log_attempt(
        self,
        signature: FailureSignature,
        iteration: int,
        action: str,
        result: str,
    ) -> None:
        """
        Log a repair attempt

        Args:
            signature: Failure signature
            iteration: Iteration number
            action: Action taken
            result: Result of action
        """
        entry = {
            "target_signature": str(signature),
            "signature": signature,
            "attempts": [
                {
                    "iter": iteration,
                    "action": action,
                    "result": result,
                }
            ],
        }

        existing = next(
            (
                e
                for e in self.issue_log
                if e.get("target_signature") == str(signature)
            ),
            None,
        )

        if existing:
            existing["attempts"].append(entry["attempts"][0])
        else:
            self.issue_log.append(entry)

    def mark_resolved(self, signature: FailureSignature) -> None:
        """
        Mark an issue as resolved

        Args:
            signature: Failure signature to mark resolved
        """
        sig_str = str(signature)
        for entry in self.issue_log:
            if entry.get("target_signature") == sig_str:
                entry["resolved"] = True
                entry["resolved_at"] = datetime.now().isoformat()

    def is_active(self, signature: FailureSignature) -> bool:
        """
        Check if a signature is still active (unresolved)

        Args:
            signature: Failure signature to check

        Returns:
            True if active, False if resolved
        """
        sig_str = str(signature)
        for entry in self.issue_log:
            if entry.get("target_signature") == sig_str:
                return not entry.get("resolved", False)
        return True

    def get_last_pruned_items(self) -> List[FailureSignature]:
        """
        Get items pruned in last operation

        Returns:
            List of pruned failure signatures
        """
        return self.last_pruned_items

    def reset(self) -> None:
        """Reset history log"""
        self.issue_log.clear()
        self.last_pruned_items.clear()


class SessionRecorder:
    """For User: Append-only logging, preserve all history"""

    def __init__(self, session_dir: Path):
        """
        Initialize session recorder

        Args:
            session_dir: Path to session directory
        """
        self.session_dir = session_dir
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.summary_file = session_dir / "full_session_summary.toon"
        self.encoder = ToonEncoder()
        self.iterations: List[Dict[str, Any]] = []

    def append_log(
        self,
        iteration: int,
        patch: PatchToon | None,
        outcome: List[FailureSignature],
        pruned: List[FailureSignature],
        status: str,
    ) -> None:
        """
        Append full iteration log

        Args:
            iteration: Iteration number
            patch: Applied patch (if any)
            outcome: List of failure outcomes
            pruned: List of pruned issues
            status: Status of iteration
        """
        entry = {
            "iteration": iteration,
            "status": status,
            "outcome_count": len(outcome),
            "pruned_count": len(pruned),
            "timestamp": datetime.now().isoformat(),
        }

        if patch:
            entry["patch"] = {
                "file_path": patch.file_path,
                "line_range": patch.line_range,
                "summary": f"Modified lines {patch.line_range[0]}-{patch.line_range[1]}",
            }

        if outcome:
            entry["failures"] = [str(f) for f in outcome]

        if pruned:
            entry["pruned"] = [str(p) for p in pruned]

        self.iterations.append(entry)

        with open(self.summary_file, "a") as f:
            f.write(self._encode_log_entry(entry))
            f.write("\n")

    def _encode_log_entry(self, entry: Dict[str, Any]) -> str:
        """Encode log entry to TOON format"""
        lines = [
            "---",
            f"iteration{{{entry['iteration']}}}",
            f"status{{{entry['status']}}}",
            f"timestamp{{{entry['timestamp']}}}",
        ]

        if "patch" in entry:
            patch = entry["patch"]
            lines.append(
                f"action{{{patch['summary']}}}"
            )

        if "failures" in entry:
            lines.append(f"failures[{len(entry['failures'])}]")
            for fail in entry["failures"]:
                lines.append(f"  {fail}")

        if "pruned" in entry:
            lines.append(f"pruned[{len(entry['pruned'])}]")
            for pruned in entry["pruned"]:
                lines.append(f"  {pruned}")

        return "\n".join(lines)

    def save_session_summary(self, total_iterations: int, status: str) -> SessionSummary:
        """
        Generate and save final session summary

        Args:
            total_iterations: Total iterations in session
            status: Final session status

        Returns:
            SessionSummary with session metrics
        """
        session_id = self.session_dir.name
        timestamp = datetime.now().isoformat()

        success_count = sum(
            1 for iter in self.iterations if iter.get("status") == "success"
        )
        success_rate = (
            success_count / total_iterations if total_iterations > 0 else 0.0
        )

        summary = SessionSummary(
            session_id=session_id,
            timestamp=timestamp,
            total_iterations=total_iterations,
            status=status,
            success_rate=success_rate,
        )

        summary_text = self.encoder.encode_session_summary(summary)

        with open(self.summary_file, "a") as f:
            f.write(f"\n{summary_text}\n")

        return summary

    def get_session_history(self) -> List[Dict[str, Any]]:
        """
        Get complete session history

        Returns:
            List of all iteration entries
        """
        return self.iterations


class HistoryManager:
    """Dual-history tracking combining ContextPruner and SessionRecorder"""

    def __init__(self, session_dir: Path):
        """
        Initialize history manager

        Args:
            session_dir: Path to session directory
        """
        self.pruner = ContextPruner()
        self.recorder = SessionRecorder(session_dir)

    def get_pruner(self) -> ContextPruner:
        """Get context pruner instance"""
        return self.pruner

    def get_recorder(self) -> SessionRecorder:
        """Get session recorder instance"""
        return self.recorder

    def save_session_summary(
        self, total_iterations: int, status: str
    ) -> SessionSummary:
        """
        Save final session summary

        Args:
            total_iterations: Total iterations
            status: Final status

        Returns:
            SessionSummary
        """
        return self.recorder.save_session_summary(total_iterations, status)
