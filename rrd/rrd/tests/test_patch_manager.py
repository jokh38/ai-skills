"""Tests for patch_manager module"""

import tempfile
import shutil
from pathlib import Path
import pytest

from core.patch_manager import PatchManager
from core.data_types import PatchToon


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files"""
    temp = Path(tempfile.mkdtemp())
    yield temp
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def patch_manager(temp_dir):
    """Create PatchManager with temp directory"""
    manager = PatchManager(create_backups=True)
    manager._base_dir = temp_dir
    return manager


class TestPatchManager:
    """Test suite for PatchManager class"""

    def test_initialization(self, temp_dir):
        """Test PatchManager initialization"""
        pm = PatchManager(create_backups=True)
        assert pm.create_backups is True
        assert pm._base_dir == Path.cwd()

    def test_are_paths_equal_absolute(self, patch_manager, temp_dir):
        """Test path equality with absolute paths"""
        file1 = temp_dir / "test.txt"
        file2 = Path(str(file1))
        assert patch_manager.are_paths_equal(file1, file2) is True

    def test_are_paths_equal_relative_absolute(self, patch_manager, temp_dir):
        """Test path equality with relative and absolute paths"""
        file1 = temp_dir / "test.txt"
        file1.touch()
        file2 = temp_dir / "test.txt"
        assert patch_manager.are_paths_equal(file1, file2) is True

    def test_are_paths_equal_different(self, patch_manager, temp_dir):
        """Test path equality with different files"""
        file1 = temp_dir / "test1.txt"
        file2 = temp_dir / "test2.txt"
        assert patch_manager.are_paths_equal(file1, file2) is False

    def test_resolve_file_path_absolute(self, patch_manager, temp_dir):
        """Test resolving absolute file path"""
        file_path = temp_dir / "test.txt"
        file_path.touch()
        resolved = patch_manager._resolve_file_path(str(file_path))
        assert resolved == file_path

    def test_resolve_file_path_not_found(self, patch_manager, temp_dir):
        """Test resolving non-existent file path"""
        resolved = patch_manager._resolve_file_path("nonexistent.txt")
        assert resolved == temp_dir / "nonexistent.txt"

    def test_create_backup(self, patch_manager, temp_dir):
        """Test creating backup of file"""
        test_file = temp_dir / "test.txt"
        test_file.write_text("original content")

        backup_path = patch_manager.create_backup(test_file)

        assert backup_path is not None
        assert backup_path.exists()
        assert backup_path.read_text() == "original content"
        assert "backup_" in backup_path.name

    def test_restore_backup(self, patch_manager, temp_dir):
        """Test restoring file from backup"""
        test_file = temp_dir / "test.txt"
        test_file.write_text("original")

        backup_file = temp_dir / ".repair_backups" / "backup_test.txt"
        backup_file.parent.mkdir(parents=True, exist_ok=True)
        backup_file.write_text("restored content")

        success = patch_manager.restore_backup(backup_file, test_file)

        assert success is True
        assert test_file.read_text() == "restored content"

    def test_atomic_write(self, patch_manager, temp_dir):
        """Test atomic write to file"""
        test_file = temp_dir / "test.txt"
        patch_manager.atomic_write(test_file, "new content")

        assert test_file.exists()
        assert test_file.read_text() == "new content"

    def test_apply_patch_simple(self, patch_manager, temp_dir):
        """Test applying simple single-line patch"""
        test_file = temp_dir / "test.py"
        test_file.write_text("def foo():\n    pass\n")

        patch = PatchToon(
            file_path=str(test_file),
            line_range=(2, 3),
            old_code="    pass",
            new_code="    return True",
        )

        result = patch_manager.apply_patch(patch)

        assert result is True
        assert "return True" in test_file.read_text()

    def test_apply_patch_multiline(self, patch_manager, temp_dir):
        """Test applying multi-line patch"""
        test_file = temp_dir / "test.py"
        test_file.write_text("def foo():\n    x = 1\n    y = 2\n    return x + y\n")

        patch = PatchToon(
            file_path=str(test_file),
            line_range=(2, 3),
            old_code="    x = 1",
            new_code="    x, y = 1, 2",
        )

        result = patch_manager.apply_patch(patch)

        assert result is True
        assert "x, y = 1, 2" in test_file.read_text()

    def test_apply_patch_nonexistent_file(self, patch_manager):
        """Test applying patch to non-existent file"""
        patch = PatchToon(
            file_path="nonexistent.py",
            line_range=(1, 2),
            old_code="old",
            new_code="new",
        )

        result = patch_manager.apply_patch(patch)
        assert result is False

    def test_verify_patch_success(self, patch_manager, temp_dir):
        """Test successful patch verification"""
        test_file = temp_dir / "test.py"
        test_file.write_text("def foo():\n    return True\n")

        patch = PatchToon(
            file_path=str(test_file),
            line_range=(1, 2),
            old_code="def foo():",
            new_code="return True",
        )

        result = patch_manager.verify_patch(test_file, patch)
        assert result is True

    def test_verify_patch_failure(self, patch_manager, temp_dir):
        """Test failed patch verification"""
        test_file = temp_dir / "test.py"
        test_file.write_text("def foo():\n    return False\n")

        patch = PatchToon(
            file_path=str(test_file),
            line_range=(2, 3),
            old_code="    return False",
            new_code="    return True",
        )

        result = patch_manager.verify_patch(test_file, patch)
        assert result is False
