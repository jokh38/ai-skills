"""
Radon complexity metrics integration for code complexity analysis.

Runs radon to measure cyclomatic complexity and maintainability index.
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any
import logging


class RadonMetrics:
    """Wrapper for radon complexity analyzer."""

    def __init__(self, workspace: str):
        """
        Initialize radon metrics analyzer.

        Args:
            workspace: Root directory to analyze
        """
        self.workspace = Path(workspace)
        self.logger = logging.getLogger(__name__)

    def measure(self, pattern: str = "**/*.py") -> Dict[str, Any]:
        """
        Run radon complexity analysis on workspace.

        Args:
            pattern: File pattern to analyze

        Returns:
            Dictionary with complexity metrics
        """
        try:
            # Check if radon is installed
            version_result = subprocess.run(
                ["radon", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if version_result.returncode != 0:
                self.logger.error("radon not installed")
                return self._empty_results()

            version = version_result.stdout.strip()

            # Get complexity metrics
            complexity_results = self._run_complexity()

            # Get maintainability index
            mi_results = self._run_maintainability()

            # Process and combine results
            return self._process_results(complexity_results, mi_results, version)

        except Exception as e:
            self.logger.error(f"radon analysis failed: {e}")
            return self._empty_results()

    def _run_complexity(self) -> List[Dict]:
        """Run cyclomatic complexity analysis."""
        try:
            cmd = [
                "radon", "cc",
                str(self.workspace),
                "-j",  # JSON output
                "-a",  # Average
                "-s"   # Show complexity
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.stdout:
                return json.loads(result.stdout)
            return {}

        except Exception as e:
            self.logger.error(f"radon cc failed: {e}")
            return {}

    def _run_maintainability(self) -> Dict:
        """Run maintainability index analysis."""
        try:
            cmd = [
                "radon", "mi",
                str(self.workspace),
                "-j"  # JSON output
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.stdout:
                return json.loads(result.stdout)
            return {}

        except Exception as e:
            self.logger.error(f"radon mi failed: {e}")
            return {}

    def _process_results(self, complexity: Dict, maintainability: Dict, version: str) -> Dict[str, Any]:
        """Process raw radon results into structured format."""
        hotspots = []
        mi_scores = []

        # Process complexity results
        for file_path, data in complexity.items():
            try:
                rel_path = str(Path(file_path).relative_to(self.workspace))
            except ValueError:
                rel_path = file_path

            # Extract function/method complexity
            if isinstance(data, list):
                for item in data:
                    if item.get("type") in ["function", "method"]:
                        complexity_value = item.get("complexity", 0)
                        grade = self._complexity_to_grade(complexity_value)

                        hotspots.append({
                            "file": rel_path,
                            "function": item.get("name", "unknown"),
                            "complexity": complexity_value,
                            "grade": grade
                        })

        # Process maintainability results
        for file_path, data in maintainability.items():
            try:
                rel_path = str(Path(file_path).relative_to(self.workspace))
            except ValueError:
                rel_path = file_path

            mi_value = data.get("mi", 0)
            grade = self._mi_to_grade(mi_value)

            mi_scores.append({
                "file": rel_path,
                "mi_score": round(mi_value, 1),
                "grade": grade
            })

        # Sort by complexity (highest first)
        hotspots.sort(key=lambda x: x["complexity"], reverse=True)

        # Sort MI by score (lowest first - worst maintainability)
        mi_scores.sort(key=lambda x: x["mi_score"])

        # Calculate average complexity
        if hotspots:
            avg_complexity = sum(h["complexity"] for h in hotspots) / len(hotspots)
        else:
            avg_complexity = 0

        return {
            "version": version,
            "avg_complexity": round(avg_complexity, 1),
            "total_functions": len(hotspots),
            "complexity_hotspots": hotspots[:10],  # Top 10
            "maintainability": mi_scores[:10]  # Bottom 10 (worst)
        }

    def _complexity_to_grade(self, complexity: int) -> str:
        """Convert complexity score to letter grade."""
        if complexity <= 5:
            return "A"
        elif complexity <= 10:
            return "B"
        elif complexity <= 20:
            return "C"
        elif complexity <= 30:
            return "D"
        else:
            return "F"

    def _mi_to_grade(self, mi: float) -> str:
        """Convert maintainability index to descriptive grade."""
        if mi >= 80:
            return "Excellent"
        elif mi >= 60:
            return "Good"
        elif mi >= 40:
            return "Moderate"
        elif mi >= 20:
            return "Poor"
        else:
            return "Critical"

    def _empty_results(self) -> Dict[str, Any]:
        """Return empty results structure."""
        return {
            "version": "unknown",
            "avg_complexity": 0,
            "total_functions": 0,
            "complexity_hotspots": [],
            "maintainability": []
        }
