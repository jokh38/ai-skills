#!/usr/bin/env python3
"""
Code Quality Checker - Main Entry Point

Orchestrates ruff, mypy, semgrep, and radon to generate
comprehensive code quality report.

Usage:
    python run_QA.py --workspace /path/to/project
"""

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add tools directory and src/modules to path
sys.path.insert(0, str(Path(__file__).parent / 'tools'))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from ruff_checker import RuffChecker
from mypy_analyzer import MypyAnalyzer
from semgrep_scanner import SemgrepScanner
from radon_metrics import RadonMetrics
from modules.toon_utils import ToonSerializer


class CodeQualityChecker:
    """Main analyzer that orchestrates all quality checking tools."""

    def __init__(
        self,
        workspace: str,
        pattern: str = "**/*.py",
        verbose: bool = False,
        max_issues: int = 50,
        filtered: bool = False
    ):
        """
        Initialize code quality checker.

        Args:
            workspace: Project directory to analyze
            pattern: File glob pattern to analyze
            verbose: Enable verbose logging
            max_issues: Maximum number of issues to display per category
            filtered: Filter results to top issues (default: False/unfiltered)
        """
        self.workspace = Path(workspace).resolve()
        self.pattern = pattern
        self.verbose = verbose
        self.max_issues = max_issues
        self.filtered = filtered

        # Setup logging
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

        self.logger = logging.getLogger(__name__)

        # Initialize checkers
        self.ruff = RuffChecker(str(self.workspace))
        self.mypy = MypyAnalyzer(str(self.workspace))
        self.semgrep = SemgrepScanner(str(self.workspace))
        self.radon = RadonMetrics(str(self.workspace))

        # Results storage
        self.results = {
            'timestamp': datetime.now().astimezone().isoformat(),
            'workspace': str(self.workspace),
        }

    def analyze(self) -> Dict[str, Any]:
        """
        Run complete quality check pipeline.

        Returns:
            Dictionary with all quality check results
        """
        self.logger.info(f"Starting code quality check of {self.workspace}")

        # Stage 1: Ruff linting
        self.logger.info("=== Stage 1: Ruff Linting ===")
        ruff_results = self.ruff.check(self.pattern)

        # Stage 2: Mypy type checking
        self.logger.info("=== Stage 2: Mypy Type Checking ===")
        mypy_results = self.mypy.analyze(self.pattern)

        # Stage 3: Semgrep security scanning
        self.logger.info("=== Stage 3: Semgrep Security Scanning ===")
        semgrep_results = self.semgrep.scan(self.pattern)

        # Stage 4: Radon complexity analysis
        self.logger.info("=== Stage 4: Radon Complexity Analysis ===")
        radon_results = self.radon.measure(self.pattern)

        # Stage 5: Synthesis
        self.logger.info("=== Stage 5: Synthesis ===")
        self._synthesize_results(ruff_results, mypy_results, semgrep_results, radon_results)

        self.logger.info("Quality check complete!")
        return self.results

    def _synthesize_results(
        self,
        ruff: Dict,
        mypy: Dict,
        semgrep: Dict,
        radon: Dict
    ):
        """Synthesize all results into TOON-compatible structure."""

        # Calculate total issues
        total_issues = ruff["total"] + mypy["total"] + semgrep["total"]

        # Calculate quality score (0-100)
        quality_score = self._calculate_quality_score(ruff, mypy, semgrep, radon)

        # Build summary section
        self.results['summary'] = {
            'files_analyzed': mypy.get('files_checked', 0),
            'total_issues': total_issues,
            'quality_score': quality_score,
            'execution_time_ms': 0  # Will be calculated if needed
        }

        # Build quality gates
        max_complexity = max([h['complexity'] for h in radon['complexity_hotspots']], default=0)
        self.results['quality_gates'] = [
            {
                'gate': 'linting_errors',
                'threshold': '<50',
                'actual': ruff['total'],
                'status': 'PASS' if ruff['total'] < 50 else 'FAIL'
            },
            {
                'gate': 'type_coverage',
                'threshold': '>80%',
                'actual': f"{mypy.get('type_coverage', 0)}%",
                'status': 'PASS' if mypy.get('type_coverage', 0) > 80 else 'FAIL'
            },
            {
                'gate': 'security_critical',
                'threshold': '0',
                'actual': semgrep['severity_counts'].get('ERROR', 0),
                'status': 'PASS' if semgrep['severity_counts'].get('ERROR', 0) == 0 else 'FAIL'
            },
            {
                'gate': 'max_complexity',
                'threshold': '<15',
                'actual': max_complexity,
                'status': 'PASS' if max_complexity < 15 else 'FAIL'
            }
        ]

        # Build critical issues list (filtered or unfiltered)
        self.results['critical_issues'] = self._build_critical_issues(ruff, mypy, semgrep, radon)

        # Store tool-specific results
        self.results['ruff'] = self._format_ruff_results(ruff)
        self.results['mypy'] = self._format_mypy_results(mypy)
        self.results['semgrep'] = self._format_semgrep_results(semgrep)
        self.results['radon'] = self._format_radon_results(radon)

        # Generate recommendations
        self.results['immediate_fixes'] = self._generate_immediate_fixes(ruff, mypy, semgrep, radon)
        self.results['next_steps'] = self._generate_next_steps(ruff, mypy, semgrep, radon)

    def _calculate_quality_score(self, ruff: Dict, mypy: Dict, semgrep: Dict, radon: Dict) -> int:
        """Calculate overall quality score (0-100)."""
        score = 100

        # Deduct for linting issues
        score -= min(20, ruff['total'] // 5)

        # Deduct for type coverage
        type_cov = mypy.get('type_coverage', 100)
        score -= max(0, (100 - type_cov) // 5)

        # Deduct for security issues
        score -= semgrep['severity_counts'].get('ERROR', 0) * 10
        score -= semgrep['severity_counts'].get('WARNING', 0) * 5

        # Deduct for complexity
        for hotspot in radon['complexity_hotspots'][:5]:
            if hotspot['complexity'] > 20:
                score -= 5

        return max(0, min(100, score))

    def _build_critical_issues(self, ruff: Dict, mypy: Dict, semgrep: Dict, radon: Dict) -> List[Dict]:
        """Build prioritized list of critical issues."""
        issues = []

        # Add security errors (highest priority)
        for finding in semgrep['findings']:
            if finding['severity'] == 'ERROR':
                issues.append({
                    'severity': 'ERROR',
                    'tool': 'semgrep',
                    'file': finding['file'],
                    'line': finding['line'],
                    'issue': f"{finding['category']}: {finding['message']}"
                })

        # Add critical complexity issues
        for hotspot in radon['complexity_hotspots']:
            if hotspot['grade'] in ['F', 'D']:
                issues.append({
                    'severity': 'ERROR' if hotspot['grade'] == 'F' else 'WARNING',
                    'tool': 'radon',
                    'file': hotspot['file'],
                    'line': 0,
                    'issue': f"Complexity {hotspot['complexity']} ({hotspot['grade']}-grade) in {hotspot['function']}"
                })

        # Add critical mypy errors
        mypy_limit = 5 if self.filtered else len(mypy['errors'])
        for error in mypy['errors'][:mypy_limit]:
            if error['severity'] == 'error':
                issues.append({
                    'severity': 'ERROR',
                    'tool': 'mypy',
                    'file': error['file'],
                    'line': error['line'],
                    'issue': error['message']
                })

        # Add critical ruff errors
        for issue in ruff['issues']:
            if issue['severity'] == 'error' and issue['code'].startswith('F'):
                issues.append({
                    'severity': 'ERROR',
                    'tool': 'ruff',
                    'file': issue['file'],
                    'line': issue['line'],
                    'issue': f"{issue['code']}: {issue['message']}"
                })

        # Sort by severity and return top N (or all if not filtered)
        severity_order = {'ERROR': 0, 'WARNING': 1, 'INFO': 2}
        issues.sort(key=lambda x: severity_order.get(x['severity'], 3))

        if self.filtered:
            return issues[:self.max_issues]
        else:
            return issues

    def _format_ruff_results(self, ruff: Dict) -> Dict:
        """Format ruff results for TOON output."""
        result = {
            'total': ruff['total'],
            'auto_fixable': ruff['auto_fixable'],
        }
        
        if self.filtered:
            result['by_category'] = ruff['categories'][:6]
        else:
            result['by_category'] = ruff['categories']
            result['severity_counts'] = ruff['severity_counts']
            result['all_issues'] = ruff['issues']
        
        return result

    def _format_mypy_results(self, mypy: Dict) -> Dict:
        """Format mypy results for TOON output."""
        result = {
            'total': mypy['total'],
            'type_coverage': f"{mypy.get('type_coverage', 0)}%",
        }
        
        if self.filtered:
            result['by_error'] = mypy['by_error'][:5]
        else:
            result['by_error'] = mypy['by_error']
            result['files_checked'] = mypy.get('files_checked', 0)
            result['files_with_errors'] = mypy.get('files_with_errors', 0)
            result['all_errors'] = mypy['errors']
        
        return result

    def _format_semgrep_results(self, semgrep: Dict) -> Dict:
        """Format semgrep results for TOON output."""
        result = {
            'total': semgrep['total'],
        }
        
        if self.filtered:
            result['by_severity'] = semgrep['by_severity']
        else:
            result['by_severity'] = semgrep['by_severity']
            result['severity_counts'] = semgrep['severity_counts']
            result['all_findings'] = semgrep['findings']
        
        return result

    def _format_radon_results(self, radon: Dict) -> Dict:
        """Format radon results for TOON output."""
        result = {}
        
        if self.filtered:
            result['complexity_hotspots'] = radon['complexity_hotspots'][:10]
            result['maintainability'] = radon['maintainability'][:5]
        else:
            result['avg_complexity'] = radon.get('avg_complexity', 0)
            result['total_functions'] = radon.get('total_functions', 0)
            result['complexity_hotspots'] = radon['complexity_hotspots']
            result['maintainability'] = radon['maintainability']
        
        return result

    def _generate_immediate_fixes(self, ruff: Dict, mypy: Dict, semgrep: Dict, radon: Dict) -> List[Dict]:
        """Generate immediate fix recommendations."""
        fixes = []

        priority = 1

        # Auto-fixable linting
        if ruff['auto_fixable'] > 0:
            fixes.append({
                'priority': priority,
                'action': 'Run: ruff check --fix src/',
                'effort': '2min'
            })
            priority += 1

        # Security fixes
        fix_limit = 5 if self.filtered else len(semgrep['findings'])
        for finding in semgrep['findings'][:fix_limit]:
            if finding['severity'] == 'ERROR':
                fixes.append({
                    'priority': priority,
                    'action': f"Fix {finding['category']}: {finding['file']}:{finding['line']}",
                    'effort': '10min'
                })
                priority += 1
                if self.filtered and priority > 5:
                    break

        # Critical complexity
        hotpot_limit = 5 if self.filtered else len(radon['complexity_hotspots'])
        for hotspot in radon['complexity_hotspots'][:hotpot_limit]:
            if hotspot['grade'] == 'F':
                fixes.append({
                    'priority': priority,
                    'action': f"Refactor: {hotspot['file']} (complexity {hotspot['complexity']}→<15)",
                    'effort': '2hrs'
                })
                priority += 1
                if self.filtered and priority > 5:
                    break

        return fixes

    def _generate_next_steps(self, ruff: Dict, mypy: Dict, semgrep: Dict, radon: Dict) -> List[str]:
        """Generate next steps recommendations."""
        steps = []

        # Type coverage
        if mypy.get('type_coverage', 100) < 80:
            steps.append(f"Add type annotations to reach 80% coverage (currently {mypy.get('type_coverage', 0)}%)")

        # Complexity
        high_complexity = len([h for h in radon['complexity_hotspots'] if h['grade'] in ['F', 'D']])
        if high_complexity > 0:
            steps.append(f"Refactor {high_complexity} high-complexity functions (F/D grade)")

        # Security warnings
        if semgrep['severity_counts'].get('WARNING', 0) > 0:
            steps.append("Review and fix security warnings")

        # General improvements
        if mypy.get('type_coverage', 0) > 80:
            steps.append("Enable mypy strict mode after reaching >80% coverage")

        return steps[:5]


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Check code quality using ruff, mypy, semgrep, and radon'
    )
    parser.add_argument(
        '--workspace',
        required=True,
        help='Project directory to analyze'
    )
    parser.add_argument(
        '--pattern',
        default='**/*.py',
        help='File glob pattern (default: **/*.py)'
    )
    parser.add_argument(
        '--output',
        help='Output file (default: <workspace>/quality_report.toon)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--max-issues',
        type=int,
        default=50,
        help='Maximum number of issues to display (default: 50)'
    )
    parser.add_argument(
        '--filtered',
        action='store_true',
        help='Filter results to top issues (default: unfiltered)'
    )

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
