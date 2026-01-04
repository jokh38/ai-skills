#!/usr/bin/env python3
"""
CDQA - Code Quality Analysis CLI

Command-line interface for integrated Python code quality analysis
using ruff, mypy, semgrep, and radon.
"""

import argparse
import sys
from pathlib import Path
from textwrap import dedent

# Add tools directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from run_QA import CodeQualityChecker, ToonSerializer


def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser with comprehensive help."""
    parser = argparse.ArgumentParser(
        prog='cdqa',
        description=dedent('''
            CDQA - Code Quality Analysis

            Comprehensive Python code quality analysis tool that integrates:
            • Ruff: Fast Python linter (checks code style, finds bugs)
            • Mypy: Static type checker (ensures type safety)
            • Semgrep: Security and bug pattern scanner
            • Radon: Code complexity metrics analyzer

            Generates detailed quality reports in TOON format for optimal
            LLM consumption and human readability.
        '''),
        epilog=dedent('''
            Examples:
              # Basic analysis of current directory
              cdqa --workspace .

              # Analyze specific directory with verbose output
              cdqa --workspace /path/to/project --verbose

              # Filter to top issues only
              cdqa --workspace . --filtered

              # Custom output location
              cdqa --workspace . --output /tmp/quality_report.toon

              # Analyze only specific file pattern
              cdqa --workspace . --pattern "src/**/*.py"

            Output:
              Creates a quality_report.toon file containing:
              - Quality score (0-100)
              - Critical issues prioritized by severity
              - Quality gates (pass/fail checks)
              - Immediate fix recommendations
              - Tool-specific detailed findings

            Exit Codes:
              0: Analysis completed successfully
              1: Analysis failed or interrupted
        '''),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Required arguments
    parser.add_argument(
        '--workspace',
        required=True,
        metavar='PATH',
        help='Project directory to analyze (required)'
    )

    # Optional arguments
    parser.add_argument(
        '--pattern',
        default='**/*.py',
        metavar='GLOB',
        help='File glob pattern to analyze (default: **/*.py)'
    )

    parser.add_argument(
        '--output',
        metavar='FILE',
        help='Output file path (default: <workspace>/quality_report.toon)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging output'
    )

    parser.add_argument(
        '--max-issues',
        type=int,
        default=50,
        metavar='N',
        help='Maximum number of issues to display per category (default: 50)'
    )

    parser.add_argument(
        '--filtered',
        action='store_true',
        help='Filter results to top priority issues only (reduces output size)'
    )

    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 0.1.0'
    )

    return parser


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Create checker
    checker = CodeQualityChecker(
        workspace=args.workspace,
        pattern=args.pattern,
        verbose=args.verbose,
        max_issues=args.max_issues,
        filtered=args.filtered
    )

    try:
        # Run analysis
        results = checker.analyze()

        # Determine output file
        if args.output:
            output_file = Path(args.output)
        else:
            output_file = Path(args.workspace) / 'quality_report.toon'

        # Write results in TOON format
        serializer = ToonSerializer(indent_size=2)
        serializer.dump(results, str(output_file))

        print(f"\n✅ Quality check complete! Results written to: {output_file}")
        print("\n📊 Summary:")
        print(f"  Quality Score: {results['summary']['quality_score']}/100")
        print(f"  Total Issues: {results['summary']['total_issues']}")
        print(f"  Critical Issues: {len(results['critical_issues'])}")
        print(f"  Quality Gates: {sum(1 for g in results['quality_gates'] if g['status'] == 'FAIL')} FAILED")

        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️  Quality check interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Quality check failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
