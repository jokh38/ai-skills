"""dbgctxt tool integration for RRD system"""

import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from core.config_loader import RRDConfig
from core.toon_utils import ToonParser, parse_toon
from core.data_types import PatchToon


@dataclass
class DebugContext:
    """Context from dbgctxt test failure analysis"""

    test_file: str
    test_name: str
    failure_message: str
    traceback: str
    failing_code: str
    related_files: List[str]
    root_cause_analysis: str
    fix_proposals: List[PatchToon]
    raw_output: str


class DbgctxtIntegration:
    """Wrapper for dbgctxt test failure analysis tool"""

    def __init__(self, config: RRDConfig):
        self.config = config
        try:
            self.tool_path = str(config.get_tool_path("dbgctxt"))
        except KeyError:
            self.tool_path = "dbgctxt"
        self.parser = ToonParser()

    def analyze_test_failures(
        self,
        test_file: Path,
        workspace: Path,
        test_filter: Optional[str] = None,
        output_file: Optional[Path] = None,
    ) -> DebugContext:
        """Run pytest via dbgctxt and get repair context

        Args:
            test_file: Path to test file
            workspace: Path to project workspace
            test_filter: Optional test filter (e.g., "test_specific_function")
            output_file: Optional path to save TOON output

        Returns:
            DebugContext with failure analysis and fix proposals
        """
        try:
            cmd = [
                self.tool_path,
                str(test_file),
                "--workspace",
                str(workspace),
                "--format",
                "toon",
            ]

            if test_filter:
                cmd.extend(["--filter", test_filter])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

            if result.returncode != 0:
                raise RuntimeError(f"dbgctxt failed: {result.stderr}")

            toon_output = result.stdout

            if output_file:
                output_file.write_text(toon_output)

            return self._parse_debug_context(toon_output)

        except subprocess.TimeoutExpired:
            raise TimeoutError("dbgctxt analysis timed out after 10 minutes")
        except FileNotFoundError:
            raise RuntimeError(f"dbgctxt tool not found at {self.tool_path}")

    def _parse_debug_context(self, toon_output: str) -> DebugContext:
        """Parse TOON output from dbgctxt into structured context"""
        try:
            parsed = self.parser.parse(toon_output)

            if isinstance(parsed, list) and len(parsed) > 0:
                data = parsed[0]
            else:
                data = parsed if isinstance(parsed, dict) else {}

            test_file = data.get("test_file", "")
            test_name = data.get("test_name", "")
            failure_message = data.get("failure_message", "")
            traceback = data.get("traceback", "")
            failing_code = data.get("failing_code", "")
            related_files = data.get("related_files", [])
            root_cause_analysis = data.get("root_cause_analysis", "")

            fix_proposals = self._parse_fix_proposals(data.get("fix_proposals", []))

            return DebugContext(
                test_file=test_file,
                test_name=test_name,
                failure_message=failure_message,
                traceback=traceback,
                failing_code=failing_code,
                related_files=related_files,
                root_cause_analysis=root_cause_analysis,
                fix_proposals=fix_proposals,
                raw_output=toon_output,
            )
        except Exception as e:
            return DebugContext(
                test_file="",
                test_name="",
                failure_message="",
                traceback="",
                failing_code="",
                related_files=[],
                root_cause_analysis="",
                fix_proposals=[],
                raw_output=toon_output,
            )

    def _parse_fix_proposals(self, proposals_data: List[Dict[str, Any]]) -> List[PatchToon]:
        """Parse fix proposals into PatchToon objects"""
        proposals = []

        for prop in proposals_data:
            try:
                proposal = PatchToon(
                    file_path=prop.get("file_path", ""),
                    line_range=tuple(prop.get("line_range", [0, 0])),
                    old_code=prop.get("old_code", ""),
                    new_code=prop.get("new_code", ""),
                )
                proposals.append(proposal)
            except Exception:
                continue

        return proposals

    def get_fix_proposals(self, context: DebugContext) -> List[PatchToon]:
        """Extract LLM-generated fix proposals from context

        Args:
            context: DebugContext from dbgctxt

        Returns:
            List of PatchToon fix proposals
        """
        return context.fix_proposals

    def get_root_cause(self, context: DebugContext) -> str:
        """Extract root cause analysis from context

        Args:
            context: DebugContext from dbgctxt

        Returns:
            Root cause analysis string
        """
        return context.root_cause_analysis

    def get_related_files(self, context: DebugContext) -> List[str]:
        """Extract related files from context

        Args:
            context: DebugContext from dbgctxt

        Returns:
            List of related file paths
        """
        return context.related_files
