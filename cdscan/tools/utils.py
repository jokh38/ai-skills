"""
Shared utility functions for cdscan tools.

This module contains common functionality used across multiple analyzer tools
to eliminate code duplication.
"""

import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional


def check_tool_availability(command: List[str], tool_name: str) -> bool:
    """
    Check if a command-line tool is installed and available.

    Args:
        command: Command to run (e.g., ['rg', '--version'])
        tool_name: Name of the tool for logging

    Returns:
        True if tool is available, False otherwise
    """
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version = result.stdout.splitlines()[0] if result.stdout else ""
            logging.info(f"{tool_name} found: {version}")
            return True
        else:
            logging.warning(f"{tool_name} not available")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logging.warning(f"{tool_name} not found: {e}")
        return False


def get_excluded_dirs() -> set:
    """
    Get list of directories to exclude from analysis.

    Returns:
        Set of directory names to exclude
    """
    return {
        "__pycache__",
        ".pytest_cache",
        ".tox",
        ".eggs",
        "build",
        "dist",
        "*.egg-info",
        "node_modules",
        ".venv",
        "venv",
        "env",
        ".git",
        ".svn",
        ".hg",
        ".idea",
        ".vscode",
        "target",
        "cmake-build-*",
    }


def get_excluded_extensions() -> set:
    """
    Get list of file extensions to exclude from analysis.

    Returns:
        Set of file extensions to exclude
    """
    return {
        ".pyc",
        ".pyo",
        ".pyd",
        ".so",
        ".dylib",
        ".dll",
        ".exe",
        ".bin",
        ".o",
        ".a",
        ".lib",
        ".obj",
        ".class",
        ".jar",
        ".war",
        ".min.js",
        ".min.css",
    }


def get_excluded_glob_patterns() -> List[str]:
    """
    Get list of glob patterns for ripgrep/ugrep exclusion.

    Returns:
        List of glob patterns
    """
    excluded_dirs = [f"**/{d}/**" for d in sorted(get_excluded_dirs())]
    excluded_files = [f"**/*{ext}" for ext in sorted(get_excluded_extensions())]
    return excluded_dirs + excluded_files


def should_exclude_file(file_path: Path) -> bool:
    """
    Check if a file should be excluded from analysis.

    Args:
        file_path: Path to check

    Returns:
        True if file should be excluded
    """
    excluded_dirs = get_excluded_dirs()
    excluded_extensions = get_excluded_extensions()

    for excluded_dir in excluded_dirs:
        if excluded_dir in file_path.parts:
            return True

    if file_path.suffix.lower() in excluded_extensions:
        return True

    if ".min." in file_path.name.lower():
        return True

    return False


def extract_module_name(statement: str, language: str) -> Optional[str]:
    """
    Extract module name from import statement.

    Args:
        statement: Import statement
        language: Programming language (python, cpp, javascript, typescript)

    Returns:
        Module name or None
    """
    import re

    if language == "python":
        if statement.startswith("import "):
            parts = statement[7:].split()
            if parts:
                return parts[0].strip(",;")
        elif statement.startswith("from "):
            parts = statement[5:].split("import")
            if parts:
                return parts[0].strip()

    elif language == "cpp":
        if "#include" in statement:
            match = re.search(r'#include\s+[<"]([^>"]+)[>"]', statement)
            if match:
                return match.group(1)

    elif language in ["javascript", "typescript"]:
        if "from" in statement:
            match = re.search(r"from\s+['\"]([^'\"]+)['\"]", statement)
            if match:
                return match.group(1)
        elif "require" in statement:
            match = re.search(r"require\s*\(\s*['\"]([^'\"]+)['\"]", statement)
            if match:
                return match.group(1)

    return None


def parse_tool_output(
    output: str, pattern: str = "", search_type: str = "code"
) -> List[Dict]:
    """
    Parse tool output (ripgrep/ugrep) into structured format.

    Args:
        output: Raw tool output
        pattern: Search pattern used (for metadata)
        search_type: Type of search performed

    Returns:
        List of matches with file, line, content
    """
    matches = []
    lines = output.strip().split("\n")

    for line in lines:
        if not line.strip():
            continue

        if ":" in line:
            parts = line.split(":", 2)
            if len(parts) >= 2:
                matches.append(
                    {
                        "file": parts[0],
                        "line": int(parts[1]) if parts[1].isdigit() else 0,
                        "content": parts[2] if len(parts) > 2 else "",
                        "pattern": pattern,
                        "search_type": search_type,
                    }
                )

    return matches[:200]


def print_analysis_summary(results: Dict[str, Any]):
    """
    Print analysis summary to console.

    Args:
        results: Analysis results dictionary
    """
    print("\n📊 Summary:")
    print(f"  Files analyzed: {results['codebase_summary'].get('total_files', 0)}")
    print(f"  Functions found: {results['codebase_summary'].get('total_functions', 0)}")
    print(f"  Classes found: {results['codebase_summary'].get('total_classes', 0)}")
    print(
        f"  Security issues: {len(results['code_quality'].get('security_concerns', []))}"
    )
    print(f"  Recommendations: {len(results['recommendations'])}")
