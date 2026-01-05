"""
ugrep advanced search integration.

Provides fuzzy search, PDF/archive search, and interactive TUI capabilities.
"""

import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

from utils import check_tool_availability, parse_tool_output, run_command


class UgrepSearcher:
    """Wrapper for ugrep advanced search."""

    def __init__(self, workspace: str):
        """
        Initialize ugrep searcher.

        Args:
            workspace: Root directory to search
        """
        self.workspace = Path(workspace)
        self.logger = logging.getLogger(__name__)
        self.available = self._check_ugrep()

    def _check_ugrep(self) -> bool:
        """Check if ugrep is installed."""
        return check_tool_availability(["ugrep", "--version"], "ugrep")

    def search_archives(self, pattern: str, max_results: int = 100) -> List[Dict]:
        """
        Search through compressed archives (zip, tar.gz, etc.).

        Args:
            pattern: Regex pattern to search for
            max_results: Maximum number of results to return

        Returns:
            List of matches with file, line, and context
        """
        if not self.available:
            return []

        try:
            cmd = [
                "ugrep",
                "-z",  # Search archives
                "-r",  # Recursive
                "-l",  # List matching files
                "-C",
                "2",  # 2 lines context
                "--max-count",
                str(max_results),
                pattern,
                str(self.workspace),
            ]

            result = run_command(cmd, timeout=120)

            if result and result.stdout:
                return parse_tool_output(result.stdout, pattern, search_type="code")
            return []

        except Exception as e:
            self.logger.error(f"ugrep archive search failed: {e}")
            return []

    def fuzzy_search(
        self, pattern: str, distance: int = 2, max_results: int = 100
    ) -> List[Dict]:
        """
        Fuzzy pattern matching with edit distance.

        Args:
            pattern: Pattern to search for (allows typos)
            distance: Maximum edit distance (1-3)
            max_results: Maximum number of results

        Returns:
            List of fuzzy matches
        """
        if not self.available:
            return []

        try:
            cmd = [
                "ugrep",
                f"-Z{distance}",  # Fuzzy with edit distance
                "-r",  # Recursive
                "-n",  # Line numbers
                "--max-count",
                str(max_results),
                pattern,
                str(self.workspace),
            ]

            result = run_command(cmd, timeout=120)

            if result and result.stdout:
                return parse_tool_output(result.stdout, pattern, search_type="fuzzy")
            return []

        except Exception as e:
            self.logger.error(f"ugrep fuzzy search failed: {e}")
            return []

    def search_pdfs(self, pattern: str, max_results: int = 100) -> List[Dict]:
        """
        Search through PDF documentation files.

        Args:
            pattern: Pattern to search for
            max_results: Maximum results

        Returns:
            List of PDF matches
        """
        if not self.available:
            return []

        try:
            # ugrep requires pdftotext to be installed for PDF support
            cmd = [
                "ugrep",
                "-z",  # Handle archives (PDF is treated as archive)
                "-r",
                "-n",
                "--max-count",
                str(max_results),
                pattern,
                str(self.workspace),
            ]

            result = run_command(cmd, timeout=120)

            if result and result.stdout:
                return parse_tool_output(result.stdout, pattern, search_type="pdf")
            else:
                self.logger.info("PDF search returned no results (requires pdftotext)")
                return []

        except Exception as e:
            self.logger.error(f"ugrep PDF search failed: {e}")
            return []

    def boolean_search(self, pattern: str, max_results: int = 100) -> List[Dict]:
        """
        Boolean search with AND, OR, NOT operators.

        Args:
            pattern: Boolean pattern (e.g., "function AND test")
            max_results: Maximum results

        Returns:
            List of matches
        """
        if not self.available:
            return []

        try:
            cmd = [
                "ugrep",
                "--bool",  # Enable boolean search
                "-r",
                "-n",
                "--max-count",
                str(max_results),
                pattern,
                str(self.workspace),
            ]

            result = run_command(cmd, timeout=120)

            if result and result.stdout:
                return parse_tool_output(result.stdout, pattern, search_type="boolean")
            return []

        except Exception as e:
            self.logger.error(f"ugrep boolean search failed: {e}")
            return []

    def search_code(
        self, pattern: str, file_type: Optional[str] = None, max_results: int = 100
    ) -> List[Dict]:
        """
        Search code with ugrep (alternative to ripgrep).

        Args:
            pattern: Pattern to search for
            file_type: File type filter (e.g., 'py', 'js')
            max_results: Maximum results

        Returns:
            List of matches
        """
        if not self.available:
            return []

        try:
            cmd = [
                "ugrep",
                "-r",
                "-n",
                "--max-count",
                str(max_results),
            ]

            # Add file type filter if specified
            if file_type:
                cmd.extend(["-t", file_type])

            cmd.extend([pattern, str(self.workspace)])

            result = run_command(cmd, timeout=60)

            if result and result.stdout:
                return parse_tool_output(result.stdout, pattern, search_type="code")
            return []

        except Exception as e:
            self.logger.error(f"ugrep code search failed: {e}")
            return []

    def search_documentation(
        self, keywords: List[str], max_results: int = 50
    ) -> Dict[str, Any]:
        """
        Search for documentation patterns across codebase.

        Args:
            keywords: List of keywords to search for in documentation
            max_results: Maximum results per keyword

        Returns:
            Dictionary with documentation findings
        """
        if not self.available:
            return {"total": 0, "findings": []}

        findings = []

        for keyword in keywords:
            # Search for keyword in docstrings and comments
            patterns = [
                rf'["\']{keyword}["\']',  # In strings (docstrings)
                rf"# {keyword}",  # In comments
            ]

            for pattern in patterns:
                matches = self.search_code(pattern, max_results=max_results)
                for match in matches:
                    match["keyword"] = keyword
                    findings.append(match)

        return {
            "total": len(findings),
            "keywords_searched": keywords,
            "findings": findings[:100],  # Limit results
        }

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of ugrep capabilities.

        Returns:
            Dictionary with availability and features
        """
        return {
            "available": self.available,
            "features": {
                "archive_search": self.available,
                "fuzzy_search": self.available,
                "pdf_search": self.available,
                "boolean_search": self.available,
                "tui_mode": self.available,
            },
        }


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        workspace = sys.argv[1]
        searcher = UgrepSearcher(workspace)

        if searcher.available:
            print("Testing ugrep search capabilities...")

            # Test fuzzy search
            print("\n1. Fuzzy search for 'functon' (typo of 'function'):")
            results = searcher.fuzzy_search("functon", distance=2, max_results=5)
            for match in results[:3]:
                print(f"  {match['file']}:{match['line']} - {match['content'][:60]}")

            # Test code search
            print("\n2. Code search for 'import':")
            results = searcher.search_code("import", file_type="py", max_results=5)
            for match in results[:3]:
                print(f"  {match['file']}:{match['line']} - {match['content'][:60]}")

            print(f"\nSummary: {searcher.get_summary()}")
        else:
            print(
                "ugrep not available. Install with: brew install ugrep (macOS) or apt-get install ugrep (Linux)"
            )
    else:
        print("Usage: python ugrep_searcher.py <workspace_path>")
