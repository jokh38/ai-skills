"""Static fixer module using Ruff for auto-fixing"""

import subprocess
from pathlib import Path
import logging

from modules.data_types import FixReport


logger = logging.getLogger(__name__)


class StaticFixer:
    """Pre-LLM mechanical error elimination using Ruff"""

    def __init__(self, ruff_rules: str = "E,F,W"):
        self.ruff_rules = ruff_rules

    def execute_autofix(self, target_path: Path) -> FixReport:
        """
        Execute Ruff auto-fix on target file

        Args:
            target_path: Path to the file to fix

        Returns:
            FixReport with details of applied fixes
        """
        if not target_path.exists():
            return FixReport(
                target_path=str(target_path),
                fixes_applied=[],
                summary=f"File not found: {target_path}",
                success=False,
            )

        try:
            cmd = [
                "ruff",
                "check",
                "--fix",
                "--select",
                self.ruff_rules,
                str(target_path),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                stdout = result.stdout.strip()
                if "fixed" in stdout.lower() or result.stderr:
                    fixes = self._parse_fixes(stdout + result.stderr)
                    return FixReport(
                        target_path=str(target_path),
                        fixes_applied=fixes,
                        summary=f"Applied {len(fixes)} fixes",
                        success=True,
                    )
                else:
                    return FixReport(
                        target_path=str(target_path),
                        fixes_applied=[],
                        summary="No fixes needed",
                        success=True,
                    )
            else:
                return FixReport(
                    target_path=str(target_path),
                    fixes_applied=[],
                    summary=f"Ruff failed: {result.stderr}",
                    success=False,
                )

        except FileNotFoundError:
            return FixReport(
                target_path=str(target_path),
                fixes_applied=[],
                summary="Ruff not found. Install with: pip install ruff",
                success=False,
            )
        except subprocess.TimeoutExpired:
            return FixReport(
                target_path=str(target_path),
                fixes_applied=[],
                summary="Ruff execution timed out",
                success=False,
            )
        except Exception as e:
            return FixReport(
                target_path=str(target_path),
                fixes_applied=[],
                summary=f"Unexpected error: {str(e)}",
                success=False,
            )

    def _parse_fixes(self, output: str) -> list[str]:
        """Parse Ruff output to extract fix descriptions"""
        fixes = []
        lines = output.split("\n")

        for line in lines:
            if "fixed" in line.lower() or "Found" in line:
                fixes.append(line.strip())

        return fixes

    def validate_fixes(self, target_path: Path) -> bool:
        """
        Validate that fixes were successful by running Ruff check again

        Args:
            target_path: Path to validate

        Returns:
            True if no errors found, False otherwise
        """
        try:
            cmd = [
                "ruff",
                "check",
                "--select",
                self.ruff_rules,
                str(target_path),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )

            return result.returncode == 0

        except Exception:
            return False
