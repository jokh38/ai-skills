"""
Ctags-based symbol indexer for definition navigation and API categorization.

Generates symbol index for:
- Public APIs vs internal functions
- Function signatures
- Class hierarchies
- Symbol locations
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
import json

from utils import check_tool_availability, should_exclude_file, run_command


class CtagsIndexer:
    """Indexes code symbols using ctags."""

    def __init__(self, workspace: str):
        """
        Initialize indexer.

        Args:
            workspace: Root directory to index
        """
        self.workspace = Path(workspace)
        self.tags_file = self.workspace / "tags"
        self.tags_data = []
        self.ctags_version = None

        # Check if ctags is available
        self.ctags_available, self.ctags_version = self._check_ctags()

    def _check_ctags(self) -> tuple:
        """Check if ctags is installed and accessible."""
        is_available = check_tool_availability(["ctags", "--version"], "ctags")

        if not is_available:
            return False, None

        # Determine ctags version
        result = run_command(["ctags", "--version"], timeout=5)
        if result and result.returncode == 0:
            version_line = result.stdout.splitlines()[0]
            if "Universal Ctags" in version_line:
                return True, "universal"
            elif "Exuberant Ctags" in version_line:
                return True, "exuberant"
            else:
                return True, "unknown"

        return True, None

    def _find_files_by_pattern(self, pattern: str) -> List[str]:
        """
        Find files matching pattern in workspace.

        Args:
            pattern: Glob pattern for files

        Returns:
            List of file paths
        """
        files = []
        if pattern.startswith("**"):
            suffix = pattern[3:] if len(pattern) > 3 else "*"
            files = [str(f) for f in self.workspace.rglob(suffix) if f.is_file()]
        elif "*" in pattern:
            files = [str(f) for f in self.workspace.glob(pattern) if f.is_file()]
        else:
            files = [str(f) for f in self.workspace.glob(pattern) if f.is_file()]

        return [f for f in files if not should_exclude_file(Path(f))]

    def generate_tags(self, pattern: str = "**/*") -> bool:
        """
        Generate ctags index for all files in workspace.

        Args:
            pattern: Glob pattern for files to index

        Returns:
            True if successful, False otherwise
        """
        if not self.ctags_available:
            logging.error(
                "ctags not available. Install with: brew install ctags (macOS) or apt-get install exuberant-ctags (Linux)"
            )
            return False

        # Find files matching pattern
        files = self._find_files_by_pattern(pattern)

        if not files:
            logging.warning(f"No files found matching {pattern} after filtering")
            return False

        logging.info(f"Generating tags for {len(files)} files...")

        # Create a temp file with list of files to analyze
        files_list_file = self.workspace / ".ctags_files_list.txt"

        try:
            with open(files_list_file, "w") as f:
                for file_path in files:
                    f.write(str(file_path) + "\n")

            # Run ctags with options for detailed output
            cmd = [
                "ctags",
                "--fields=+nkKzS",  # Include extra fields: line number, kind, signature
                "--output-format=json",  # JSON output (if supported)
                "-f",
                str(self.tags_file),  # Output file
                "-L",
                str(files_list_file),  # Read file list from file
            ]

            result = run_command(cmd, cwd=str(self.workspace), timeout=60)

            if not result or result.returncode != 0:
                logging.error(
                    f"ctags failed: {result.stderr if result else 'Unknown error'}"
                )
                # Try simpler command without JSON format
                return self._generate_tags_simple(pattern)

            # Parse generated tags file
            self._parse_tags_file(str(self.tags_file))
            logging.info(f"Generated {len(self.tags_data)} tags")

            return True

        except Exception as e:
            logging.error(f"Failed to generate tags: {e}")
            return False
        finally:
            # Cleanup temp file
            try:
                if files_list_file.exists():
                    files_list_file.unlink()
            except:
                pass

    def _generate_tags_simple(self, pattern: str = "**/*") -> bool:
        """Generate tags using basic ctags command (fallback)."""
        try:
            # Find files matching pattern
            files = self._find_files_by_pattern(pattern)

            if not files:
                return False

            # Create a temp file with list of files to analyze
            files_list_file = self.workspace / ".ctags_files_list.txt"
            with open(files_list_file, "w") as f:
                for file_path in files:
                    f.write(str(file_path) + "\n")

            cmd = [
                "ctags",
                "--fields=+n",  # Include line numbers
                "-f",
                str(self.tags_file),
                "-L",
                str(files_list_file),
            ]

            result = run_command(cmd, cwd=str(self.workspace), timeout=60)

            if result and result.returncode == 0:
                self._parse_tags_file(str(self.tags_file))
                logging.info(f"Generated {len(self.tags_data)} tags (simple format)")
                return True
            else:
                logging.error(
                    f"Simple ctags also failed: {result.stderr if result else 'Unknown error'}"
                )
                return False

        except Exception as e:
            logging.error(f"Fallback ctags failed: {e}")
            return False

    def _parse_tags_file(self, tags_file_path: Optional[str] = None):
        """Parse generated tags file."""
        file_path = Path(tags_file_path) if tags_file_path else self.tags_file

        if not file_path.exists():
            logging.warning(f"Tags file not found: {file_path}")
            return

        self.tags_data = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    # Skip comments and metadata
                    if line.startswith("!_TAG_"):
                        continue

                    # Parse tag line
                    tag = self._parse_tag_line(line)
                    if tag:
                        self.tags_data.append(tag)

        except Exception as e:
            logging.error(f"Failed to parse tags file: {e}")

    def _parse_tag_line(self, line: str) -> Optional[Dict]:
        """
        Parse a single ctags line.

        Format: <name>\t<file>\t<address>;\"\t<kind>\t<extra fields>
        """
        parts = line.strip().split("\t")
        if len(parts) < 3:
            return None

        tag = {
            "name": parts[0],
            "file": parts[1],
            "kind": None,
            "line": None,
            "signature": None,
        }

        # Parse extra fields
        for part in parts[3:]:
            if part.startswith("kind:"):
                tag["kind"] = part.split(":", 1)[1]
            elif part.startswith("line:"):
                try:
                    tag["line"] = int(part.split(":", 1)[1])
                except ValueError:
                    pass
            elif part.startswith("signature:"):
                tag["signature"] = part.split(":", 1)[1]

        return tag

    def get_public_apis(self) -> List[Dict]:
        """
        Get public API symbols (functions/classes without _ prefix).

        Returns:
            List of public symbols
        """
        public_symbols = [
            tag
            for tag in self.tags_data
            if tag["kind"] in ["function", "class", "method"]
            and not tag["name"].startswith("_")
        ]

        # Sort by name and limit to top 50
        return sorted(public_symbols, key=lambda x: x["name"])[:50]

    def get_internal_functions(self) -> List[Dict]:
        """
        Get internal/private functions (starting with _).

        Returns:
            List of private symbols
        """
        internal_symbols = [
            tag
            for tag in self.tags_data
            if tag["kind"] in ["function", "method"]
            and tag["name"].startswith("_")
            and not tag["name"].startswith("__")  # Exclude magic methods
        ]

        return sorted(internal_symbols, key=lambda x: x["name"])[:30]

    def search_symbol(self, name: str) -> List[Dict]:
        """
        Search for symbols by name (supports partial matching).

        Args:
            name: Symbol name to search for

        Returns:
            List of matching symbols
        """
        matches = [tag for tag in self.tags_data if name.lower() in tag["name"].lower()]

        return sorted(matches, key=lambda x: x["name"])[:20]

    def get_symbol_categories(self) -> Dict[str, int]:
        """
        Get count of symbols by category (function, class, variable, etc.).

        Returns:
            Dictionary mapping category to count
        """
        categories = {}
        for tag in self.tags_data:
            kind = tag.get("kind", "unknown")
            categories[kind] = categories.get(kind, 0) + 1

        return categories

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of indexed symbols.

        Returns:
            Summary dictionary with counts and categories
        """
        return {
            "total_symbols": len(self.tags_data),
            "public_apis": len(self.get_public_apis()),
            "internal_functions": len(self.get_internal_functions()),
            "categories": self.get_symbol_categories(),
            "tags_file": str(self.tags_file) if self.tags_file.exists() else None,
        }

    def cleanup(self):
        """Remove generated tags file."""
        if self.tags_file.exists():
            try:
                self.tags_file.unlink()
                logging.info(f"Removed tags file: {self.tags_file}")
            except Exception as e:
                logging.warning(f"Failed to remove tags file: {e}")


if __name__ == "__main__":
    # Test the indexer
    import sys

    if len(sys.argv) > 1:
        workspace = sys.argv[1]
        indexer = CtagsIndexer(workspace)
        if indexer.generate_tags():
            print(json.dumps(indexer.get_summary(), indent=2))
            print("\nPublic APIs:")
            for api in indexer.get_public_apis()[:10]:
                print(f"  {api['name']} ({api['kind']}) - {api['file']}:{api['line']}")
    else:
        print("Usage: python ctags_indexer.py <workspace_path>")
