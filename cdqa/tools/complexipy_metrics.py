"""
Complexipy cognitive complexity integration for code complexity analysis.

Rust-based cognitive complexity analyzer that measures how hard code is
to understand by humans (not machines), based on SonarSource research.
"""

from typing import Dict, Any
from base_checker import BaseToolChecker


class ComplexipyMetrics(BaseToolChecker):
    """Wrapper for complexipy cognitive complexity analyzer."""

    def __init__(self, workspace: str):
        """
        Initialize complexipy metrics analyzer.

        Args:
            workspace: Root directory to analyze
        """
        super().__init__(workspace, "complexipy")

    def measure(self, pattern: str = "**/*.py") -> Dict[str, Any]:
        """
        Run complexipy cognitive complexity analysis on workspace.

        Args:
            pattern: File pattern to analyze

        Returns:
            Dictionary with complexity metrics
        """
        is_installed, version = self._check_tool_version(["complexipy", "--version"])
        if not is_installed:
            return self._empty_results()

        json_file_path = None
        try:
            cmd = ["complexipy", str(self.workspace), "--output-json", "--quiet"]
            self._run_tool(cmd, timeout=60, capture_output=False)

            json_files = sorted(
                self.workspace.glob("complexipy_results_*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )

            if json_files:
                json_file_path = json_files[0]
                import json

                with open(json_file_path, "r") as f:
                    functions_array = json.loads(f.read())
                    data = {"files": functions_array}
            else:
                self.logger.warning("No complexipy results file found")
                return self._empty_results()

            results = self._process_results(data, version)

            if json_file_path and json_file_path.exists():
                try:
                    json_file_path.unlink()
                    self.logger.debug(
                        f"Removed temporary complexipy file: {json_file_path.name}"
                    )
                except Exception as e:
                    self.logger.warning(
                        f"Failed to remove temporary file {json_file_path}: {e}"
                    )

            return results

        except Exception:
            return self._empty_results()

    def _run_tool(
        self, cmd: list, timeout: int = 60, capture_output: bool = True
    ) -> Any:
        """
        Override to run tool without capturing stdout for complexipy.
        """
        import subprocess

        try:
            if capture_output:
                return super()._run_tool(cmd, timeout)
            else:
                return subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=str(self.workspace),
                )
        except subprocess.TimeoutExpired as e:
            self.logger.error(f"{self.tool_name} timed out")
            raise
        except Exception as e:
            self.logger.error(f"{self.tool_name} failed: {e}")
            raise

    def _process_results(self, data: dict, version: str) -> Dict[str, Any]:
        """Process raw complexipy results into structured format."""
        hotspots = []

        for func in data.get("files", []):
            file_path = func.get("path", "")
            rel_path = self._normalize_path(file_path)

            complexity_value = func.get("complexity", 0)
            grade = self._complexity_to_grade(complexity_value)

            function_name = func.get("function_name", "unknown")

            hotspots.append(
                {
                    "file": rel_path,
                    "function": function_name,
                    "complexity": complexity_value,
                    "grade": grade,
                }
            )

        hotspots.sort(key=lambda x: x["complexity"], reverse=True)

        avg_complexity = (
            sum(h["complexity"] for h in hotspots) / len(hotspots) if hotspots else 0
        )

        return {
            "version": version,
            "avg_complexity": round(avg_complexity, 1),
            "total_functions": len(hotspots),
            "complexity_hotspots": hotspots,
        }

    def _complexity_to_grade(self, complexity: int) -> str:
        """
        Convert cognitive complexity score to letter grade.

        Note: Cognitive complexity thresholds are stricter than cyclomatic
        because cognitive complexity measures human understanding difficulty.

        Thresholds based on SonarSource recommendations:
        - 0-5: Simple, easy to understand (A)
        - 6-10: Moderate complexity (B)
        - 11-15: Complex, should be reviewed (C)
        - 16-20: Very complex, needs refactoring (D)
        - 20+: Extremely complex, high maintenance risk (F)
        """
        if complexity <= 5:
            return "A"
        elif complexity <= 10:
            return "B"
        elif complexity <= 15:
            return "C"
        elif complexity <= 20:
            return "D"
        else:
            return "F"

    def _empty_results(self) -> Dict[str, Any]:
        """Return empty results structure."""
        return {
            "version": "unknown",
            "avg_complexity": 0,
            "total_functions": 0,
            "complexity_hotspots": [],
        }
