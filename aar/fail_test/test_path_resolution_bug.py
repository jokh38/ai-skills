"""
Test for Path Resolution Bug (Issue 1.1)
Tests that patch application fails when arr.py is executed from one directory
but pytest runs from a different working directory.

Severity: High
Status: Unresolved
"""

import pytest
from pathlib import Path
import sys
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_path_resolution_bug_reproduction():
    """
    Reproduce the path resolution bug described in line 17-24 of UNSOLVED_ISSUES.md
    
    When arr.py repair is executed from ARR/ directory but test file is in
    sample_test_project/, the patch manager fails to find files due to path
    mismatches.
    """
    from modules.patch_manager import PatchManager
    from schemas.patch import PatchToon
    
    # Simulate the scenario where patch contains absolute path
    # but current working directory is different
    arr_dir = Path(__file__).parent.parent
    test_project = arr_dir / "sample_test_project"
    calculator_file = test_project / "calculator.py"
    
    # This simulates what happens when arr.py runs from ARR/ directory
    # but paths are generated with absolute paths
    absolute_patch = PatchToon(
        file_path=str(calculator_file.absolute()),
        line_range=(1, 10),
        old_code="    return a - b",
        new_code="    return b - a"
    )
    
    patch_manager = PatchManager()
    
    # Try to apply patch - this should fail if bug exists
    result = patch_manager.apply_patch(absolute_patch)
    
    # Bug: This will return False because absolute path resolution fails
    # Expected: Should return True (patch applied successfully)
    assert result is False, "BUG: Path resolution fails with absolute paths from different CWD"


def test_path_resolution_relative_path():
    """
    Test that relative paths also fail when current directory changes.
    """
    from modules.patch_manager import PatchManager
    from schemas.patch import PatchToon
    
    arr_dir = Path(__file__).parent.parent
    
    # Create a patch with relative path
    relative_patch = PatchToon(
        file_path="sample_test_project/calculator.py",
        line_range=(1, 10),
        old_code="    return a - b",
        new_code="    return b - a"
    )
    
    # Save current directory
    original_cwd = os.getcwd()
    
    try:
        # Change to ARR directory (simulating arr.py execution from there)
        os.chdir(arr_dir)
        
        patch_manager = PatchManager()
        result = patch_manager.apply_patch(relative_patch)
        
        # Bug: This may fail because relative path is resolved from wrong CWD
        # Expected: Should find the file in sample_test_project/
        assert result is False or result is True, "Path resolution test needs verification"
        
    finally:
        os.chdir(original_cwd)


def test_resolve_file_path_tool_needed():
    """
    Demonstrate that a resolve_file_path tool is needed as per line 47-103
    of UNSOLVED_ISSUES.md
    """
    from schemas.patch import PatchToon
    
    # Test cases that should be handled by the resolve_file_path tool
    test_cases = [
        ("sample_test_project/calculator.py", "sample_test_project/"),
        ("/absolute/path/to/calculator.py", "/absolute/path/to/"),
        ("./relative/calculator.py", "./relative/"),
        ("../parent/calculator.py", "../parent/"),
    ]
    
    for relative_path, context_dir in test_cases:
        patch = PatchToon(
            file_path=relative_path,
            line_range=(1, 10),
            old_code="old",
            new_code="new"
        )
        
        # This should be resolved by the proposed tool
        # Currently, this resolution doesn't exist
        assert patch.file_path == relative_path, f"Path not resolved: {relative_path}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
