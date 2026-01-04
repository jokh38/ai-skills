#!/usr/bin/env python3
"""
DBGCTXT - Debug Context Generator CLI

Command-line interface for automated test failure analysis and
LLM-based code repair context generation.
"""

import argparse
import sys
from pathlib import Path
from textwrap import dedent

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.pipeline_orchestrator import RepairWorkflowEngine


def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser with comprehensive help."""
    parser = argparse.ArgumentParser(
        prog='dbgctxt',
        description=dedent('''
            DBGCTXT v2.0 - Debug Context Generator

            Intelligent test failure analysis pipeline that:
            • Runs pytest to detect test failures
            • Correlates failures with quality metrics (cdqa)
            • Analyzes codebase structure (cdscan)
            • Identifies root causes with confidence scoring
            • Generates smart fix suggestions
            • Provides safe dead code removal guidance

            Integrates cdqa (ty, complexipy, skylos, semgrep) and cdscan
            (tree-sitter, ctags, ripgrep) for comprehensive analysis.
        '''),
        epilog=dedent('''
            Examples:
              # Run all tests and analyze failures with v2.0 features
              dbgctxt /path/to/workspace

              # Run specific test case
              dbgctxt /path/to/workspace --test-case tests/test_auth.py::test_login

              # Analyze failures in current directory
              dbgctxt .

            Prerequisites:
              The workspace should contain:
              - Python tests (pytest compatible)
              - Optional: codebase_structure.toon (from cdscan)
              - Optional: quality_report.toon (from cdqa)

              If TOON artifacts are missing, dbgctxt will attempt to
              generate them automatically using cdscan and cdqa.

            New v2.0 Features:
              - Root Cause Correlation Engine
                Correlates test failures with:
                • Cognitive complexity scores (complexipy)
                • Type errors (ty)
                • Security issues (semgrep)
                • Dead code (skylos)
                • Anti-patterns (ruff)

              - Smart Fix Suggestions
                Generates context-aware fix recommendations:
                • Security fixes (SQL injection, XSS, etc.)
                • Complexity refactoring (extract functions, guard clauses)
                • Type error fixes (missing annotations, type mismatches)
                • Error handling improvements (bare except → specific exceptions)
                • Dead code removal guidance

              - Dead Code Safe Removal Guide
                Before suggesting removal, verifies:
                • No direct/indirect references
                • Test coverage exists for dependents
                • Not in hot path
                • No security impact
                • No TODO/FIXME comments
                • High confidence score (>80%)

            Output:
              Creates a fix_payload.toon file containing:
              - Test execution summary
              - Unique failure analysis (deduplicated)
              - Root cause correlations with confidence scores
              - Smart fix suggestions with priority and effort
              - Enriched context from structure and quality data

            Exit Codes:
              0: Analysis completed successfully
              1: Pipeline execution failed
        '''),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Required arguments
    parser.add_argument(
        'workspace',
        type=Path,
        metavar='WORKSPACE',
        help='Path to workspace containing tests and code (required)'
    )

    # Optional arguments
    parser.add_argument(
        '--test-case',
        type=str,
        metavar='TEST',
        help='Run specific test case (e.g., tests/test_example.py::test_function)'
    )

    parser.add_argument(
        '--output',
        type=Path,
        metavar='FILE',
        help='Output file path (default: <workspace>/fix_payload.toon)'
    )

    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 2.0.0'
    )

    return parser


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Validate workspace
    if not args.workspace.exists():
        print(f"❌ Error: Workspace does not exist: {args.workspace}")
        return 1

    if not args.workspace.is_dir():
        print(f"❌ Error: Workspace is not a directory: {args.workspace}")
        return 1

    try:
        engine = RepairWorkflowEngine()

        # Run pipeline
        if args.test_case:
            print(f"🧪 Running test case: {args.test_case}")
        else:
            print(f"🧪 Running all tests in: {args.workspace}")
        
        print(f"🔍 Analyzing with cdqa and cdscan v2.0...")

        output_path = engine.execute_pipeline(args.workspace, args.test_case)

        # Use custom output path if specified
        if args.output:
            import shutil
            shutil.move(str(output_path), str(args.output))
            output_path = args.output

        print(f"\n✅ Analysis completed! Output: {output_path}")
        print("\n📊 Summary:")
        print("  • Root cause correlations: Identify likely causes")
        print("  • Smart fix suggestions: Priority-ranked fixes with effort estimates")
        print("  • Enriched context: Code structure, quality metrics, error details")
        print("\nUse the generated fix_payload.toon with an LLM to get code repair suggestions.")

        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️  Analysis interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Pipeline execution failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
