"""Patch manager module for safe patch application

IMPORTANT: This module uses pathlib for cross-platform path handling.
Always use PatchManager.are_paths_equal() or Path.samefile() for comparing paths
to handle different OS path separators, symbolic links, and relative paths correctly.
"""

from pathlib import Path
from typing import Optional
import shutil
import logging
from datetime import datetime

from core.data_types import PatchToon


logger = logging.getLogger(__name__)


class PatchManager:
    """Safe application of code patches with backup and verification"""

    def __init__(self, create_backups: bool = True):
        """
        Initialize patch manager

        Args:
            create_backups: Whether to create backups before patching
        """
        self.create_backups = create_backups
        self._base_dir = Path.cwd()

    @staticmethod
    def are_paths_equal(path1: Path | str, path2: Path | str) -> bool:
        """
        Compare two paths for equality using cross-platform safe method.

        CRITICAL: Always use this method (or os.path.samefile/Path.samefile) for path comparisons.
        This handles:
        - Different path separators (/ vs \\ on Windows)
        - Symbolic links
        - Relative vs absolute paths
        - Case sensitivity differences across OS

        Args:
            path1: First path to compare
            path2: Second path to compare

        Returns:
            True if paths refer to the same file/directory, False otherwise

        Example:
            >>> pm = PatchManager()
            >>> pm.are_paths_equal("/tmp/file.txt", "/tmp/../tmp/file.txt")
            True  # Same file, even with different path strings
        """
        p1 = Path(path1).resolve()
        p2 = Path(path2).resolve()

        # Check if both paths exist
        if p1.exists() and p2.exists():
            # Use samefile() for existing paths (handles symlinks correctly)
            try:
                return p1.samefile(p2)
            except (OSError, ValueError):
                # Fallback to string comparison if samefile fails
                return p1 == p2
        else:
            # For non-existent paths, compare resolved paths
            return p1 == p2

    def _resolve_file_path(self, file_path: str) -> Path:
        """
        Resolve file path to absolute path, handling both relative and absolute paths

        Args:
            file_path: File path (can be relative or absolute)

        Returns:
            Resolved absolute Path object
        """
        path = Path(file_path)

        if path.is_absolute():
            return path

        # For relative paths, try to find the file from current directory
        # and also from parent directories
        search_paths = [
            self._base_dir,
            self._base_dir / "sample_test_project",
        ]

        for search_path in search_paths:
            resolved = search_path / file_path
            if resolved.exists():
                return resolved

        # If not found, return the original path (will fail existence check later)
        return self._base_dir / file_path

    def _read_file_content(self, target_path: Path) -> list[str]:
        """
        Read file content and return as lines

        Args:
            target_path: Path to file to read

        Returns:
            List of lines from file
        """
        content = target_path.read_text()
        return content.split("\n")

    def _validate_line_range(
        self,
        start_idx: int,
        end_idx: int,
        num_lines: int,
        patch_line_range: tuple[int, int],
    ) -> bool:
        """
        Validate that line range is within file bounds

        Args:
            start_idx: Start index (0-based)
            end_idx: End index
            num_lines: Total number of lines in file
            patch_line_range: Original line range from patch

        Returns:
            True if valid, False otherwise
        """
        if start_idx < 0 or end_idx > num_lines:
            logger.error(
                f"Invalid line range {patch_line_range} for file with {num_lines} lines"
            )
            return False

        if start_idx >= end_idx or start_idx >= num_lines or end_idx > num_lines:
            logger.error(
                f"Invalid line range after adjustment: ({start_idx + 1}, {end_idx})"
            )
            return False

        return True

    def _find_multiline_match(
        self, lines: list[str], patch: PatchToon
    ) -> tuple[int, int]:
        """
        Find multi-line old_code match in file

        Args:
            lines: List of file lines
            patch: Patch to find match for

        Returns:
            Tuple of (start_idx, end_idx) for match location, or (0, 0) if not found
        """
        file_text = "\n".join(lines)
        if patch.old_code not in file_text:
            logger.warning("Multi-line old_code not found in file")
            logger.debug(f"Searching for:\n{patch.old_code}")

            for i, line in enumerate(lines):
                if patch.old_code.split("\n")[0] in line:
                    start_idx = i
                    end_idx = i + len(patch.old_code.split("\n"))
                    return start_idx, end_idx

        return 0, 0

    def _find_single_line_match(
        self, lines: list[str], patch: PatchToon, start_idx: int, end_idx: int
    ) -> tuple[int, int]:
        """
        Find single-line old_code match in file

        Args:
            lines: List of file lines
            patch: Patch to find match for
            start_idx: Initial start index
            end_idx: Initial end index

        Returns:
            Tuple of (start_idx, end_idx) for match location
        """
        old_code = "\n".join(lines[start_idx:end_idx])

        if old_code.strip() == patch.old_code.strip():
            return start_idx, end_idx

        logger.warning("Old code doesn't match (trying to find in file)")
        logger.debug(f"Expected: {patch.old_code}")
        logger.debug(f"Actual: {old_code}")

        for i, line in enumerate(lines):
            if patch.old_code.strip() in line:
                logger.info(f"Found matching line at {i + 1}")
                return i, i + 1

        return start_idx, end_idx

    def _apply_code_replacement(
        self, lines: list[str], start_idx: int, end_idx: int, new_code: str
    ) -> str:
        """
        Apply code replacement to lines

        Args:
            lines: List of file lines
            start_idx: Start index for replacement
            end_idx: End index for replacement
            new_code: New code to insert

        Returns:
            Updated file content as string
        """
        new_lines = new_code.split("\n")
        lines[start_idx:end_idx] = new_lines
        return "\n".join(lines)

    def _rollback_on_failure(
        self, backup_path: Optional[Path], target_path: Path
    ) -> None:
        """
        Rollback file from backup if backup exists

        Args:
            backup_path: Path to backup file
            target_path: Path to restore
        """
        if backup_path and backup_path.exists():
            self.restore_backup(backup_path, target_path)

    def _locate_and_validate_code_match(
        self, lines: list[str], patch: PatchToon
    ) -> tuple[int, int] | None:
        """
        Locate and validate code match in file

        Args:
            lines: File lines
            patch: Patch to locate

        Returns:
            Tuple of (start_idx, end_idx) if valid, None otherwise
        """
        start_idx = patch.line_range[0] - 1
        end_idx = patch.line_range[1]

        if not self._validate_line_range(
            start_idx, end_idx, len(lines), patch.line_range
        ):
            return None

        if "\n" in patch.old_code:
            start_idx, end_idx = self._find_multiline_match(lines, patch)
        else:
            start_idx, end_idx = self._find_single_line_match(
                lines, patch, start_idx, end_idx
            )

        if not self._validate_line_range(
            start_idx, end_idx, len(lines), patch.line_range
        ):
            return None

        return start_idx, end_idx

    def apply_patch(self, patch: PatchToon) -> bool:
        """
        Apply LLM-generated patch to source file

        Args:
            patch: Patch to apply

        Returns:
            True if successful, False otherwise
        """
        target_path = self._resolve_file_path(patch.file_path)

        if not target_path.exists():
            logger.error(f"Target file not found: {target_path}")
            return False

        backup_path = None
        if self.create_backups:
            backup_path = self.create_backup(target_path)
            if not backup_path:
                logger.warning(f"Failed to create backup for {target_path}")

        try:
            lines = self._read_file_content(target_path)

            match_result = self._locate_and_validate_code_match(lines, patch)
            if match_result is None:
                self._rollback_on_failure(backup_path, target_path)
                return False

            start_idx, end_idx = match_result

            new_content = self._apply_code_replacement(
                lines, start_idx, end_idx, patch.new_code
            )
            self.atomic_write(target_path, new_content)

            if not self.verify_patch(target_path, patch):
                logger.warning("Patch verification failed")
                self._rollback_on_failure(backup_path, target_path)
                return False

            logger.info(f"Successfully applied patch to {target_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to apply patch: {e}")
            self._rollback_on_failure(backup_path, target_path)
            return False

    def create_backup(self, target_path: Path) -> Optional[Path]:
        """
        Create backup of target file before patch application

        Args:
            target_path: Path to file to backup

        Returns:
            Path to backup file, or None if failed
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{timestamp}_{target_path.name}"
            backup_dir = target_path.parent / ".repair_backups"
            backup_dir.mkdir(exist_ok=True)
            backup_path = backup_dir / backup_name

            shutil.copy2(target_path, backup_path)
            logger.info(f"Created backup: {backup_path}")
            return backup_path

        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None

    def restore_backup(self, backup_path: Path, target_path: Path) -> bool:
        """
        Restore file from backup

        Args:
            backup_path: Path to backup file
            target_path: Path to restore to

        Returns:
            True if successful, False otherwise
        """
        try:
            shutil.copy2(backup_path, target_path)
            logger.info(f"Restored {target_path} from backup")
            return True
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            return False

    def atomic_write(self, target_path: Path, content: str) -> None:
        """
        Atomically write content to file (POSIX-safe)

        Args:
            target_path: Path to write to
            content: Content to write

        Raises:
            IOError: If write fails
        """
        tmp_path = target_path.with_suffix(".tmp")
        tmp_path.write_text(content)
        tmp_path.rename(target_path)
        logger.debug(f"Atomically wrote to {target_path}")

    def verify_patch(self, target_path: Path, patch: PatchToon) -> bool:
        """
        Verify that patch was successfully applied

        Args:
            target_path: Path to verify
            patch: Patch that was applied

        Returns:
            True if verification passed, False otherwise
        """
        try:
            content = target_path.read_text()

            # For verification, check if new_code is in the file
            if patch.new_code in content:
                logger.debug("Verified: new_code found in file")
                return True

            # If not found, try stripped comparison
            if patch.new_code.strip() in content:
                logger.debug("Verified: new_code (stripped) found in file")
                return True

            logger.warning("Verification failed: new_code not found in file")
            return False

        except Exception as e:
            logger.error(f"Verification error: {e}")
            return False
