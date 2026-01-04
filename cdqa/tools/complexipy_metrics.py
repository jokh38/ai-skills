"""
Complexipy cognitive complexity integration for code complexity analysis.

Rust-based cognitive complexity analyzer that measures how hard code is
to understand by humans (not machines), based on SonarSource research.
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, Any
import logging


class ComplexipyMetrics:
    """Wrapper for complexipy cognitive complexity analyzer."""

    def __init__(self, workspace: str):
        """
        Initialize complexipy metrics analyzer.

        Args:
            workspace: Root directory to analyze
        """
        self.workspace = Path(workspace)
        self.logger = logging.getLogger(__name__)

    def measure(self, pattern: str = "**/*.py") -> Dict[str, Any]:
        """
        Run complexipy cognitive complexity analysis on workspace.

        Args:
            pattern: File pattern to analyze

        Returns:
            Dictionary with complexity metrics
        """
        json_file_path = None
        try:
            # Check if complexipy is installed
            version_result = subprocess.run(
                ["complexipy", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if version_result.returncode != 0:
                self.logger.error("complexipy not installed")
                return self._empty_results()

            version = version_result.stdout.strip()

            # Run complexipy with JSON output
            # Note: complexipy saves to a file in current working directory, stdout only contains progress
            cmd = [
                "complexipy",
                str(self.workspace),
                "--output-json",
                "--quiet"
            ]

            subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(self.workspace)
            )

            # Find the generated JSON file (complexipy saves to the cwd we specified, which is workspace)
            json_files = sorted(self.workspace.glob("complexipy_results_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

            if json_files:
                json_file_path = json_files[0]
                try:
                    with open(json_file_path, 'r') as f:
                        content = f.read()
                        # Parse the JSON array directly
                        functions_array = json.loads(content)
                        data = {"files": functions_array}
                except (json.JSONDecodeError, IOError) as e:
                    self.logger.error(f"Failed to read complexipy JSON file: {e}")
                    return self._empty_results()
            else:
                self.logger.warning("No complexipy results file found")
                return self._empty_results()

            # Process and combine results
            results = self._process_results(data, version)

            # Clean up the temporary JSON file
            if json_file_path and json_file_path.exists():
                try:
                    json_file_path.unlink()
                    self.logger.debug(f"Removed temporary complexipy file: {json_file_path.name}")
                except Exception as e:
                    self.logger.warning(f"Failed to remove temporary file {json_file_path}: {e}")

            return results

        except Exception as e:
            self.logger.error(f"complexipy analysis failed: {e}")
            return self._empty_results()

    def _process_results(self, data: Dict, version: str) -> Dict[str, Any]:
        """Process raw complexipy results into structured format."""
        hotspots = []
        
        # Process complexity results
        functions = data.get("files", [])
        for func in functions:
            file_path = func.get("path", "")
            try:
                rel_path = str(Path(file_path).relative_to(self.workspace))
            except ValueError:
                rel_path = file_path
            
            # complexipy uses 'complexity' key
            complexity_value = func.get("complexity", 0)
            grade = self._complexity_to_grade(complexity_value)
            
            function_name = func.get("function_name", "unknown")
            
            hotspots.append({
                "file": rel_path,
                "function": function_name,
                "complexity": complexity_value,
                "grade": grade
            })
        
        # Sort by complexity (highest first)
        hotspots.sort(key=lambda x: x["complexity"], reverse=True)
        
        # Calculate average complexity
        if hotspots:
            avg_complexity = sum(h["complexity"] for h in hotspots) / len(hotspots)
        else:
            avg_complexity = 0
        
        return {
            "version": version,
            "avg_complexity": round(avg_complexity, 1),
            "total_functions": len(hotspots),
            "complexity_hotspots": hotspots
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
            "complexity_hotspots": []
        }
