"""
Base class for all tool checker integrations.

Provides common functionality for version checking, subprocess execution,
path normalization, and error handling to reduce code duplication.
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
import logging


class BaseToolChecker:
    """Base class for tool checkers with common functionality."""

    def __init__(self, workspace: str, tool_name: str):
        """
        Initialize base tool checker.

        Args:
            workspace: Root directory to analyze
            tool_name: Name of the tool (for logging)
        """
        self.workspace = Path(workspace)
        self.tool_name = tool_name
        self.logger = logging.getLogger(__name__)

    def _check_tool_version(self, cmd: list) -> tuple[bool, str]:
        """
        Check if tool is installed and get version.

        Args:
            cmd: Command to check version (e.g., ["ruff", "--version"])

        Returns:
            Tuple of (is_installed, version_string)
        """
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                self.logger.error(f"{self.tool_name} not installed")
                return False, "unknown"

            version = result.stdout.strip()
            if "\n" in version:
                version = version.split("\n")[0]
            return True, version
        except Exception as e:
            self.logger.error(f"Failed to check {self.tool_name} version: {e}")
            return False, "unknown"

    def _normalize_path(self, file_path: str) -> str:
        """
        Convert file path to relative path from workspace.

        Args:
            file_path: Absolute or relative file path

        Returns:
            Relative path from workspace, or original path if conversion fails
        """
        if not file_path:
            return file_path

        try:
            return str(Path(file_path).relative_to(self.workspace))
        except ValueError:
            return file_path

    def _run_tool(self, cmd: list, timeout: int = 60) -> subprocess.CompletedProcess:
        """
        Run tool command with standardized error handling.

        Args:
            cmd: Command to execute
            timeout: Timeout in seconds

        Returns:
            CompletedProcess with stdout, stderr, returncode
        """
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired as e:
            self.logger.error(f"{self.tool_name} timed out")
            raise
        except Exception as e:
            self.logger.error(f"{self.tool_name} failed: {e}")
            raise

    def _parse_json_output(self, stdout: str, line_by_line: bool = False) -> Any:
        """
        Parse JSON output from tool.

        Args:
            stdout: Stdout from tool command
            line_by_line: If True, parse each line as separate JSON object

        Returns:
            Parsed JSON data or empty list/dict
        """
        if not stdout:
            return []

        if line_by_line:
            results = []
            for line in stdout.strip().split("\n"):
                if line:
                    try:
                        results.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            return results

        try:
            return json.loads(stdout)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse {self.tool_name} JSON: {e}")
            return []
