"""
Shared utility functions for CDQA.

Contains common functions used by both run_QA.py and cdqa_cli.py
to reduce code duplication.
"""

from pathlib import Path
from typing import Dict, Any
from toon_serializer import ToonSerializer


def run_analysis(
    checker, output_path: str = None, workspace: str = "."
) -> tuple[int, Dict[str, Any]]:
    """
    Run code quality analysis and write results to file.

    Args:
        checker: CodeQualityChecker instance
        output_path: Custom output file path (optional)
        workspace: Workspace directory for default output path

    Returns:
        Tuple of (exit_code, results_dict)
    """
    try:
        results = checker.analyze()

        if output_path:
            output_file = Path(output_path)
        else:
            output_file = Path(workspace) / "quality_report.toon"

        serializer = ToonSerializer(indent_size=2)
        serializer.dump(results, str(output_file))

        print(f"\n✅ Quality check complete! Results written to: {output_file}")
        print("\n📊 Summary:")
        print(f"  Quality Score: {results['summary']['quality_score']}/100")
        print(f"  Total Issues: {results['summary']['total_issues']}")
        print(f"  Critical Issues: {len(results['critical_issues'])}")
        print(
            f"  Quality Gates: {sum(1 for g in results['quality_gates'] if g['status'] == 'FAIL')} FAILED"
        )

        return 0, results

    except KeyboardInterrupt:
        print("\n\n⚠️  Quality check interrupted by user")
        return 1, {}
    except Exception as e:
        print(f"\n❌ Quality check failed: {e}")
        return 1, {}
