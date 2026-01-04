"""Debugging context module for test execution and error collection"""

import subprocess
import os
from pathlib import Path
from typing import List, Dict, Any
import logging
import re

from modules.data_types import FailurePayload, FailureSignature
from modules.toon_utils import ToonEncoder


logger = logging.getLogger(__name__)


class DebuggingContext:
    """Test execution and error formatting (TOON conversion)"""

    def __init__(self):
        self.encoder = ToonEncoder()

    def get_current_context(self, test_file: Path) -> FailurePayload:
        """
        Run tests and collect failure information

        Args:
            test_file: Path to test file

        Returns:
            FailurePayload with test failure data
        """
        try:
            # Use absolute path but run from project root to ensure proper module resolution
            # Find project root by going up from test directory
            test_file_abs = test_file.resolve()
            test_dir = test_file_abs.parent
            
            # Try to find project root (directory with pytest.ini or pyproject.toml)
            project_root = test_dir
            for parent in [test_dir] + list(test_dir.parents):
                if (parent / "pytest.ini").exists() or (parent / "pyproject.toml").exists():
                    project_root = parent
                    break
            
            # Use relative path from project root
            relative_path = test_file_abs.relative_to(project_root)
            
            # Get current environment and add project root to PYTHONPATH
            current_env = os.environ.copy()
            # Ensure project root is in PYTHONPATH for module resolution
            pythonpath = current_env.get('PYTHONPATH', '')
            if pythonpath:
                current_env['PYTHONPATH'] = f"{str(project_root)}:{pythonpath}"
            else:
                current_env['PYTHONPATH'] = str(project_root)
            
            result = subprocess.run(
                ["pytest", str(relative_path), "--tb=short", "-v"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(project_root),
                env=current_env,
            )

            # Extract source code for context
            source_files = self._extract_source_files_from_test(test_file)

            if result.returncode == 0:
                return FailurePayload(
                    failures=[],
                    traceback_snippets={},
                    context={
                        "status": "passed",
                        "source_code": source_files,
                    },
                )

            payload = self._parse_test_output(result.stdout, result.stderr)
            # Add source code to context
            payload.context["source_code"] = source_files
            return payload

        except subprocess.TimeoutExpired:
            return FailurePayload(
                failures=[],
                traceback_snippets={},
                context={"error": "Test execution timed out"},
            )
        except Exception as e:
            return FailurePayload(
                failures=[],
                traceback_snippets={},
                context={"error": str(e)},
            )

    def _parse_test_output(self, stdout: str, stderr: str) -> FailurePayload:
        """Parse pytest output to extract failures"""
        failures: List[FailureSignature] = []
        snippets: Dict[str, str] = {}

        lines = (stdout + stderr).split("\n")

        for i, line in enumerate(lines):
            if "FAILED" in line:
                sig = self._extract_failure_signature(line)
                if sig:
                    failures.append(sig)

            if "AssertionError" in line or line.strip().startswith("assert"):
                if i > 0 and failures:
                    snippets[str(failures[-1])] = self._extract_traceback(lines, i)

        return FailurePayload(
            failures=failures,
            traceback_snippets=snippets,
            context={"raw_output": stdout + stderr},
        )

    def _extract_failure_signature(self, line: str) -> FailureSignature | None:
        """Extract failure signature from pytest output"""
        # More flexible regex to handle various pytest output formats
        match = re.search(r"FAILED\s+(.+?)::(.+?)\s+-\s+(.+)", line)
        if match:
            file_path = match.group(1).split()[0]
            function_name = match.group(2)
            error_msg = match.group(3)
            
            # Extract error type from message
            # Handle cases like "AssertionError", "AssertionErr...", "Failed: DID NOT RAISE..."
            error_type = "Unknown"
            if "Error" in error_msg:
                # Extract the error type, removing "..." truncation
                error_type = error_msg.split()[0].replace("...", "")
            elif "Exception" in error_msg:
                error_type = error_msg.split()[0].replace("...", "")
            elif "AssertionError" in error_msg:
                error_type = "AssertionError"
            elif "DID NOT RAISE" in error_msg:
                error_type = "AssertionError"  # Missing exception assertion
            else:
                # Default to AssertionError for assertion failures
                error_type = "AssertionError"
            
            return FailureSignature(
                file_path=file_path,
                function_name=function_name,
                error_type=error_type,
            )
        return None

    def _extract_source_files_from_test(self, test_file: Path) -> Dict[str, str]:
        """
        Extract source code files imported by tests

        Args:
            test_file: Path to test file

        Returns:
            Dictionary mapping file paths to their contents
        """
        source_files = {}
        
        try:
            # Read the test file to find imported modules
            test_content = test_file.read_text()
            
            # Find import statements
            import_patterns = [
                r'^from\s+(\S+)\s+import',
                r'^import\s+(\S+)',
            ]
            
            imported_modules = set()
            for pattern in import_patterns:
                matches = re.findall(pattern, test_content, re.MULTILINE)
                imported_modules.update(matches)
            
            # Add the test file itself
            source_files[str(test_file)] = test_content
            
            # For each imported module, try to find and read the source file
            project_dir = test_file.parent
            
            for module in imported_modules:
                # Handle relative imports (from .something import X)
                if module.startswith('.'):
                    module = module.lstrip('.')
                
                # Try to find the module file
                # Convert dots to path separators
                module_path = module.replace('.', os.sep)
                
                # Try .py file
                possible_files = [
                    project_dir / f"{module_path}.py",
                    project_dir / f"{module_path}__init__.py",
                    Path(str(project_dir).replace('tests', 'src')) / f"{module_path}.py",
                ]
                
                for possible_file in possible_files:
                    if possible_file.exists():
                        source_files[str(possible_file)] = possible_file.read_text()
                        break
                        
        except Exception as e:
            logger.debug(f"Failed to extract source files: {e}")
        
        return source_files

    def _extract_traceback(self, lines: List[str], start_idx: int) -> str:
        """Extract traceback snippet around failure"""
        snippet = []
        context_lines = 5

        for i in range(max(0, start_idx - context_lines), min(len(lines), start_idx + context_lines)):
            snippet.append(lines[i])

        return "\n".join(snippet)

    def generate_failure_payload(self, raw_output: Dict[str, Any]) -> FailurePayload:
        """
        Convert test results into TOON-formatted FailurePayload

        Args:
            raw_output: Raw test result data

        Returns:
            FailurePayload with TOON-formatted data
        """
        failures = []
        snippets = {}

        if "failures" in raw_output:
            for fail in raw_output["failures"]:
                sig = FailureSignature(
                    file_path=fail.get("file", ""),
                    function_name=fail.get("test", ""),
                    error_type=fail.get("error_type", "Unknown"),
                )
                failures.append(sig)

                if "traceback" in fail:
                    snippets[str(sig)] = fail["traceback"]

        return FailurePayload(
            failures=failures,
            traceback_snippets=snippets,
            context=raw_output.get("context", {}),
        )

    def filter_duplicate_failures(self, failures: List[FailureSignature]) -> List[FailureSignature]:
        """
        Deduplicate test failures to avoid redundant work

        Args:
            failures: List of failure signatures

        Returns:
            Deduplicated list of failure signatures
        """
        seen = set()
        unique = []

        for failure in failures:
            sig_str = str(failure)
            if sig_str not in seen:
                seen.add(sig_str)
                unique.append(failure)

        return unique

    def encode_failure_payload_toon(self, payload: FailurePayload) -> str:
        """
        Encode FailurePayload to TOON format for logging

        Args:
            payload: FailurePayload to encode

        Returns:
            TOON-formatted string
        """
        lines = [
            f"failure_payload[{len(payload.failures)}]{{type,message,location,traceback}}",
        ]

        for failure in payload.failures:
            sig_str = str(failure)
            parts = sig_str.split("::")
            error_type = parts[2] if len(parts) > 2 else "Unknown"
            message = "Test failed"
            location = f"{parts[0]}:{parts[1]}" if len(parts) > 1 else sig_str
            traceback = payload.traceback_snippets.get(sig_str, "...")

            lines.append(f'{error_type} | "{message}" | {location} | "{self.encoder._escape_value(traceback)}"')

        return "\n".join(lines)
