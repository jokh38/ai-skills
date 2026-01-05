#!/usr/bin/env python3
"""
CDSCAN - Code Structure Scanner CLI

Command-line interface for comprehensive codebase analysis using
tree-sitter, ctags, and ripgrep.
"""

import argparse
import sys
from pathlib import Path
from textwrap import dedent

# Add tools directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from run_code_review import CodeReviewAnalyzer, ToonSerializer
from tools.utils import print_analysis_summary


def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser with comprehensive help."""
    parser = argparse.ArgumentParser(
        prog="cdscan",
        description=dedent("""
            CDSCAN - Code Structure Scanner

            Multi-tool codebase analysis that combines:
            • Tree-sitter: AST-based code parsing (functions, classes, complexity)
            • Ctags: Symbol indexing (public APIs, definitions)
            • Ripgrep: Fast pattern search (imports, tests, security patterns)

            Ideal for understanding unfamiliar codebases, code reviews,
            and preparing context for LLM-assisted development.
        """),
        epilog=dedent("""
            Examples:
              # Basic analysis of current directory
              cdscan --workspace .

              # Analyze Python project with context
              cdscan --workspace /path/to/project --language python

              # Analyze with user request context
              cdscan --workspace . --request "Find authentication logic"

              # Custom output and file pattern
              cdscan --workspace . --pattern "**/*.py" --output analysis.toon

              # Limit output size for large codebases
              cdscan --workspace . --max-files 10 --max-hotspots 5

              # Verbose output for debugging
              cdscan --workspace . --verbose

            Output:
              Creates a codebase_structure.toon file containing:
              - Codebase summary (files, functions, classes)
              - Structure analysis (complexity hotspots, design patterns)
              - Definition index (public APIs, internal functions)
              - Pattern findings (tests, imports, technical debt)
              - Code quality metrics
              - Actionable recommendations

            Exit Codes:
              0: Analysis completed successfully
              1: Analysis failed or interrupted
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Required arguments
    parser.add_argument(
        "--workspace",
        required=True,
        metavar="PATH",
        help="Project directory to analyze (required)",
    )

    # Optional arguments
    parser.add_argument(
        "--pattern",
        default="**/*.py",
        metavar="GLOB",
        help="File glob pattern to analyze (default: **/*.py)",
    )

    parser.add_argument(
        "--language",
        default="python",
        metavar="LANG",
        help="Primary programming language (default: python)",
    )

    parser.add_argument(
        "--output",
        metavar="FILE",
        help="Output file path (default: <workspace>/codebase_structure.toon)",
    )

    parser.add_argument(
        "--request",
        default="",
        metavar="TEXT",
        help="User request/context for the analysis",
    )

    parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose logging output"
    )

    parser.add_argument(
        "--max-files",
        type=int,
        default=20,
        metavar="N",
        help="Maximum number of files to include in results (default: 20)",
    )

    parser.add_argument(
        "--max-hotspots",
        type=int,
        default=15,
        metavar="N",
        help="Maximum number of complexity hotspots (default: 15)",
    )

    parser.add_argument(
        "--max-apis",
        type=int,
        default=20,
        metavar="N",
        help="Maximum number of public APIs to list (default: 20)",
    )

    parser.add_argument(
        "--max-search-results",
        type=int,
        default=100,
        metavar="N",
        help="Maximum search results per pattern (default: 100)",
    )

    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")

    return parser


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Create analyzer
    analyzer = CodeReviewAnalyzer(
        workspace=args.workspace,
        pattern=args.pattern,
        language=args.language,
        user_request=args.request,
        verbose=args.verbose,
        max_files=args.max_files,
        max_hotspots=args.max_hotspots,
        max_apis=args.max_apis,
        max_search_results=args.max_search_results,
    )

    try:
        # Run analysis
        results = analyzer.analyze()

        # Determine output file
        if args.output:
            output_file = Path(args.output)
        else:
            output_file = Path(args.workspace) / "codebase_structure.toon"

        # Write results in TOON format
        serializer = ToonSerializer(indent_size=2)
        serializer.dump(results, str(output_file))

        print(f"\n✅ Analysis complete! Results written to: {output_file}")
        print_analysis_summary(results)

        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️  Analysis interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1
    finally:
        analyzer.cleanup()


if __name__ == "__main__":
    sys.exit(main())
