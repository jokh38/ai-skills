"""Patch manager module for safe patch application"""

from pathlib import Path
from typing import Optional
import shutil
import logging
from datetime import datetime

from modules.data_types import PatchToon


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
            content = target_path.read_text()
            lines = content.split("\n")

            start_idx = patch.line_range[0] - 1
            end_idx = patch.line_range[1]

            if start_idx < 0 or end_idx > len(lines):
                logger.error(
                    f"Invalid line range {patch.line_range} for file with {len(lines)} lines"
                )
                if backup_path and backup_path.exists():
                    self.restore_backup(backup_path, target_path)
                return False

            old_lines = lines[start_idx:end_idx]
            old_code = "\n".join(old_lines)

            # Smart matching: if single line in patch, match stripped versions
            # If multi-line, require exact match
            if '\n' in patch.old_code:
                # Multi-line patch: find exact match
                file_text = "\n".join(lines)
                if patch.old_code not in file_text:
                    logger.warning("Multi-line old_code not found in file")
                    logger.debug(f"Searching for:\n{patch.old_code}")
                    # Try to find line with old_code in it
                    for i, line in enumerate(lines):
                        if patch.old_code.split('\n')[0] in line:
                            # Use this line as start
                            start_idx = i
                            # Determine end based on new_code line count
                            end_idx = i + len(patch.old_code.split('\n'))
                            break
            else:
                # Single line patch: match stripped versions
                if old_code.strip() != patch.old_code.strip():
                    logger.warning("Old code doesn't match (trying to find in file)")
                    logger.debug(f"Expected: {patch.old_code}")
                    logger.debug(f"Actual: {old_code}")
                    # Try to find the line containing old_code
                    for i, line in enumerate(lines):
                        if patch.old_code.strip() in line:
                            logger.info(f"Found matching line at {i+1}")
                            start_idx = i
                            end_idx = i + 1
                            break

            if start_idx >= end_idx or start_idx >= len(lines) or end_idx > len(lines):
                logger.error(f"Invalid line range after adjustment: ({start_idx+1}, {end_idx})")
                if backup_path and backup_path.exists():
                    self.restore_backup(backup_path, target_path)
                return False

            new_lines = patch.new_code.split("\n")
            lines[start_idx:end_idx] = new_lines

            new_content = "\n".join(lines)
            self.atomic_write(target_path, new_content)

            verified = self.verify_patch(target_path, patch)
            if not verified:
                logger.warning("Patch verification failed")
                if backup_path and backup_path.exists():
                    self.restore_backup(backup_path, target_path)
                return False

            logger.info(f"Successfully applied patch to {target_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to apply patch: {e}")
            if backup_path and backup_path.exists():
                self.restore_backup(backup_path, target_path)
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
                logger.debug(f"Verified: new_code found in file")
                return True
            
            # If not found, try stripped comparison
            if patch.new_code.strip() in content:
                logger.debug(f"Verified: new_code (stripped) found in file")
                return True
            
            logger.warning(f"Verification failed: new_code not found in file")
            return False

        except Exception as e:
            logger.error(f"Verification error: {e}")
            return False
