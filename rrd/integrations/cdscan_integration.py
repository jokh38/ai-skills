"""cdscan tool integration for RRD system"""

import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from core.config_loader import RRDConfig
from core.toon_utils import ToonParser


@dataclass
class ComplexityHotspot:
    """High complexity function/location"""

    file_path: str
    function_name: str
    complexity: int
    line_range: tuple[int, int]
    issues: List[str]


@dataclass
class CodebaseAnalysis:
    """Analysis results from cdscan"""

    structure: Dict[str, Any]
    file_summary: List[Dict[str, Any]]
    function_summary: List[Dict[str, Any]]
    imports: Dict[str, List[str]]
    hotspots: List[ComplexityHotspot]
    raw_output: str


class CdscanIntegration:
    """Wrapper for cdscan codebase structure analysis tool"""

    def __init__(self, config: RRDConfig):
        self.config = config
        try:
            self.tool_path = str(config.get_tool_path("cdscan"))
        except KeyError:
            self.tool_path = "cdscan"
        self.parser = ToonParser()

    def analyze_codebase(
        self,
        workspace: Path,
        pattern: str = "**/*.py",
        incremental: bool = False,
        output_file: Optional[Path] = None,
    ) -> CodebaseAnalysis:
        """Run cdscan and parse structure

        Args:
            workspace: Path to codebase to analyze
            pattern: File pattern to include (e.g., "**/*.py")
            incremental: Use incremental analysis (faster, less complete)
            output_file: Optional path to save TOON output

        Returns:
            CodebaseAnalysis with structure information
        """
        try:
            cmd = [self.tool_path, str(workspace), "--format", "toon"]
            cmd.extend(["--pattern", pattern])

            if incremental:
                cmd.append("--incremental")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

            if result.returncode != 0:
                raise RuntimeError(f"cdscan failed: {result.stderr}")

            toon_output = result.stdout

            if output_file:
                output_file.write_text(toon_output)

            return self._parse_codebase_analysis(toon_output)

        except subprocess.TimeoutExpired:
            raise TimeoutError("cdscan analysis timed out after 10 minutes")
        except FileNotFoundError:
            raise RuntimeError(f"cdscan tool not found at {self.tool_path}")

    def _parse_codebase_analysis(self, toon_output: str) -> CodebaseAnalysis:
        """Parse TOON output from cdscan into structured analysis"""
        try:
            parsed = self.parser.parse(toon_output)

            if isinstance(parsed, list) and len(parsed) > 0:
                data = parsed[0]
            else:
                data = parsed if isinstance(parsed, dict) else {}

            structure = data.get("structure", {})
            file_summary = data.get("file_summary", [])
            function_summary = data.get("function_summary", [])
            imports = data.get("imports", {})

            hotspots = self._extract_hotspots(function_summary)

            return CodebaseAnalysis(
                structure=structure,
                file_summary=file_summary,
                function_summary=function_summary,
                imports=imports,
                hotspots=hotspots,
                raw_output=toon_output,
            )
        except Exception as e:
            return CodebaseAnalysis(
                structure={},
                file_summary=[],
                function_summary=[],
                imports={},
                hotspots=[],
                raw_output=toon_output,
            )

    def _extract_hotspots(
        self, function_summary: List[Dict[str, Any]], threshold: int = 12
    ) -> List[ComplexityHotspot]:
        """Extract high complexity functions

        Args:
            function_summary: List of function metrics
            threshold: Complexity threshold for hotspots

        Returns:
            List of ComplexityHotspot objects
        """
        hotspots = []

        for func in function_summary:
            complexity = func.get("cognitive_complexity", 0)
            if complexity >= threshold:
                issues = []
                if complexity > 20:
                    issues.append("High cognitive complexity")
                if func.get("lines_of_code", 0) > 100:
                    issues.append("Function too long")
                if func.get("parameter_count", 0) > 7:
                    issues.append("Too many parameters")

                hotspots.append(
                    ComplexityHotspot(
                        file_path=func.get("file", ""),
                        function_name=func.get("name", ""),
                        complexity=complexity,
                        line_range=(func.get("start_line", 0), func.get("end_line", 0)),
                        issues=issues,
                    )
                )

        return sorted(hotspots, key=lambda h: h.complexity, reverse=True)

    def get_complexity_hotspots(
        self, analysis: CodebaseAnalysis, threshold: int = 12
    ) -> List[ComplexityHotspot]:
        """Extract high-complexity functions from analysis

        Args:
            analysis: CodebaseAnalysis from cdscan
            threshold: Complexity threshold (default: 12)

        Returns:
            List of ComplexityHotspot objects sorted by complexity
        """
        return self._extract_hotspots(analysis.function_summary, threshold)

    def get_test_files(self, analysis: CodebaseAnalysis) -> List[Path]:
        """Find existing test files from analysis

        Args:
            analysis: CodebaseAnalysis from cdscan

        Returns:
            List of Path objects pointing to test files
        """
        test_files = []

        for file_info in analysis.file_summary:
            file_path = file_info.get("path", "")
            if "test" in file_path.lower():
                test_files.append(Path(file_path))

        return test_files

    def get_source_files(self, analysis: CodebaseAnalysis) -> List[Path]:
        """Find source (non-test) files from analysis

        Args:
            analysis: CodebaseAnalysis from cdscan

        Returns:
            List of Path objects pointing to source files
        """
        source_files = []

        for file_info in analysis.file_summary:
            file_path = file_info.get("path", "")
            if "test" not in file_path.lower():
                source_files.append(Path(file_path))

        return source_files

    def get_import_dependencies(self, analysis: CodebaseAnalysis) -> Dict[str, List[str]]:
        """Get import dependency graph

        Args:
            analysis: CodebaseAnalysis from cdscan

        Returns:
            Dict mapping file paths to list of imported modules
        """
        return analysis.imports

    def get_file_by_function(
        self, analysis: CodebaseAnalysis, function_name: str
    ) -> Optional[Path]:
        """Find file containing a specific function

        Args:
            analysis: CodebaseAnalysis from cdscan
            function_name: Name of function to find

        Returns:
            Path to file containing function, or None if not found
        """
        for func in analysis.function_summary:
            if func.get("name") == function_name:
                return Path(func.get("file", ""))
        return None
