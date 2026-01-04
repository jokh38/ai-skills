"""zgit tool integration for RRD system"""

import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

from core.config_loader import RRDConfig
from core.toon_utils import parse_toon


@dataclass
class CommitResult:
    """Result from zgit commit operation"""

    success: bool
    commit_hash: str
    context_saved: bool
    context_file: Optional[str]
    message: str
    raw_output: str


class ZgitIntegration:
    """Wrapper for zgit context-preserving commits"""

    def __init__(self, config: RRDConfig):
        self.config = config
        try:
            self.tool_path = str(config.get_tool_path("zgit"))
        except KeyError:
            self.tool_path = "zgit"

    def commit_with_context(
        self,
        message: str,
        context: Dict[str, Any],
        stage_all: bool = True,
        output_file: Optional[Path] = None,
    ) -> CommitResult:
        """Commit using zgit with RRD context

        Args:
            message: Commit message
            context: RRD context dict to preserve
            stage_all: Stage all changes before commit
            output_file: Optional path to save commit output

        Returns:
            CommitResult with commit details
        """
        try:
            cmd = [self.tool_path, "commit", "-m", message, "--prompt", "--context"]

            if stage_all:
                cmd.append("--all")

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120, input=str(context)
            )

            success = result.returncode == 0

            commit_hash = self._extract_commit_hash(result.stdout)
            context_saved = "--context" in result.stdout or "context" in result.stdout.lower()
            context_file = self._extract_context_file(result.stdout)

            output = result.stdout if success else result.stderr

            if output_file:
                output_file.write_text(output)

            return CommitResult(
                success=success,
                commit_hash=commit_hash,
                context_saved=context_saved,
                context_file=context_file,
                message=message,
                raw_output=output,
            )

        except subprocess.TimeoutExpired:
            raise TimeoutError("zgit commit timed out after 2 minutes")
        except FileNotFoundError:
            raise RuntimeError(f"zgit tool not found at {self.tool_path}")

    def _extract_commit_hash(self, output: str) -> str:
        """Extract commit hash from zgit output"""
        import re

        match = re.search(r"[0-9a-f]{40}", output)
        return match.group(0) if match else ""

    def _extract_context_file(self, output: str) -> Optional[str]:
        """Extract context file path from zgit output"""
        import re

        match = re.search(r"context.*?:\s*(.+?\.toon)", output, re.IGNORECASE)
        return match.group(1).strip() if match else None

    def check_repo_status(self) -> Dict[str, Any]:
        """Check git repository status

        Returns:
            Dict with status information
        """
        try:
            cmd = ["git", "status", "--porcelain"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            return {
                "has_changes": bool(result.stdout.strip()),
                "output": result.stdout,
                "error": result.stderr,
            }
        except Exception as e:
            return {"has_changes": False, "output": "", "error": str(e)}

    def get_last_commit(self) -> Dict[str, Any]:
        """Get information about last commit

        Returns:
            Dict with commit details
        """
        try:
            cmd = ["git", "log", "-1", "--format=%H|%s|%an|%ai"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0 and result.stdout:
                parts = result.stdout.strip().split("|")
                return {
                    "hash": parts[0] if len(parts) > 0 else "",
                    "message": parts[1] if len(parts) > 1 else "",
                    "author": parts[2] if len(parts) > 2 else "",
                    "date": parts[3] if len(parts) > 3 else "",
                }

            return {}
        except Exception:
            return {}

    def stage_files(self, files: list[str]) -> bool:
        """Stage specific files for commit

        Args:
            files: List of file paths to stage

        Returns:
            True if successful
        """
        try:
            cmd = ["git", "add"] + files
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            return result.returncode == 0
        except Exception:
            return False

    def unstage_files(self, files: list[str]) -> bool:
        """Unstage specific files

        Args:
            files: List of file paths to unstage

        Returns:
            True if successful
        """
        try:
            cmd = ["git", "reset", "HEAD"] + files
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            return result.returncode == 0
        except Exception:
            return False
