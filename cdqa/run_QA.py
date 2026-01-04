#!/usr/bin/env python3
"""
Code Quality Checker v2.0 - Main Entry Point

Orchestrates ruff, ty, semgrep, complexipy, and skylos to generate
comprehensive code quality report with modern, fast tools.

Changes in v2.0:
- Replaced mypy with ty (10-100x faster type checking)
- Replaced radon with complexipy (cognitive complexity)
- Added skylos (dead code detection)

Usage:
    python run_QA.py --workspace /path/to/project
"""

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add tools directory to path
sys.path.insert(0, str(Path(__file__).parent / 'tools'))

from ruff_checker import RuffChecker
from ty_checker import TyChecker
from semgrep_scanner import SemgrepScanner
from complexipy_metrics import ComplexipyMetrics
from skylos_analyzer import SkylosAnalyzer
from pattern_analyzer import PatternAnalyzer
from toon_serializer import ToonSerializer


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
        self.ty = TyChecker(str(self.workspace))
        self.semgrep = SemgrepScanner(str(self.workspace))
        self.complexipy = ComplexipyMetrics(str(self.workspace))
        self.skylos = SkylosAnalyzer(str(self.workspace))
        self.pattern_analyzer = PatternAnalyzer(str(self.workspace))

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

        # Stage 2: ty type checking
        self.logger.info("=== Stage 2: ty Type Checking ===")
        ty_results = self.ty.analyze(self.pattern)

        # Stage 3: Semgrep security scanning
        self.logger.info("=== Stage 3: Semgrep Security Scanning ===")
        semgrep_results = self.semgrep.scan(self.pattern)

        # Stage 4: Complexipy cognitive complexity
        self.logger.info("=== Stage 4: Complexipy Cognitive Complexity ===")
        complexipy_results = self.complexipy.measure(self.pattern)

        # Stage 5: Skylos dead code detection
        self.logger.info("=== Stage 5: Skylos Dead Code Detection ===")
        skylos_results = self.skylos.scan(self.pattern)

        # Stage 6: Pattern consistency analysis
        self.logger.info("=== Stage 6: Pattern Consistency Analysis ===")
        pattern_results = self.pattern_analyzer.analyze(self.pattern)

        # Stage 7: Synthesis
        self.logger.info("=== Stage 7: Synthesis ===")
        self._synthesize_results(ruff_results, ty_results, semgrep_results,
                                complexipy_results, skylos_results, pattern_results)

        self.logger.info("Quality check complete!")
        return self.results

    def _synthesize_results(
        self,
        ruff: Dict,
        ty: Dict,
        semgrep: Dict,
        complexipy: Dict,
        skylos: Dict,
        pattern: Dict
    ):
        """Synthesize all results into TOON-compatible structure."""

        # Calculate total issues (including dead code and pattern inconsistencies)
        total_issues = (ruff["total"] + ty["total"] + semgrep["total"] +
                       skylos["total_dead_code"] + pattern.get("total_inconsistencies", 0))

        # Calculate quality score (0-100)
        quality_score = self._calculate_quality_score(ruff, ty, semgrep, complexipy, skylos)

        # Build summary section
        self.results['summary'] = {
            'files_analyzed': ty.get('files_checked', 0),
            'total_issues': total_issues,
            'quality_score': quality_score,
            'tools_used': ['ruff', 'ty', 'semgrep', 'complexipy', 'skylos', 'pattern_analyzer'],
            'execution_time_ms': 0  # Will be calculated if needed
        }

        # Build quality gates
        max_complexity = max([h['complexity'] for h in complexipy['complexity_hotspots']], default=0)
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
                'actual': f"{ty.get('type_coverage', 0)}%",
                'status': 'PASS' if ty.get('type_coverage', 0) > 80 else 'FAIL'
            },
            {
                'gate': 'security_critical',
                'threshold': '0',
                'actual': semgrep['severity_counts'].get('ERROR', 0),
                'status': 'PASS' if semgrep['severity_counts'].get('ERROR', 0) == 0 else 'FAIL'
            },
            {
                'gate': 'cognitive_complexity',
                'threshold': '<12',
                'actual': max_complexity,
                'status': 'PASS' if max_complexity < 12 else 'FAIL'
            },
            {
                'gate': 'dead_code',
                'threshold': '<5',
                'actual': len(skylos['dead_functions']),
                'status': 'PASS' if len(skylos['dead_functions']) < 5 else 'FAIL'
            }
        ]

        # Build critical issues list (filtered or unfiltered)
        self.results['critical_issues'] = self._build_critical_issues(ruff, ty, semgrep, complexipy, skylos)

        # Store tool-specific results
        self.results['ruff'] = self._format_ruff_results(ruff)
        self.results['ty'] = self._format_ty_results(ty)
        self.results['semgrep'] = self._format_semgrep_results(semgrep)
        self.results['complexipy'] = self._format_complexipy_results(complexipy)
        self.results['skylos'] = self._format_skylos_results(skylos)

        # Pattern consistency results (Priority 2)
        self.results['consistency_issues'] = pattern.get('consistency_issues', [])

        # Issue clustering (Priority 3)
        self.results['issue_clusters'] = self._cluster_issues(
            self.results['critical_issues'], ruff, ty, semgrep, complexipy, skylos
        )

        # Generate recommendations
        self.results['immediate_fixes'] = self._generate_immediate_fixes(ruff, ty, semgrep, complexipy, skylos)
        self.results['next_steps'] = self._generate_next_steps(ruff, ty, semgrep, complexipy, skylos)

    def _calculate_quality_score(self, ruff: Dict, ty: Dict, semgrep: Dict,
                                 complexipy: Dict, skylos: Dict) -> int:
        """Calculate overall quality score (0-100)."""
        score = 100

        # Deduct for linting issues
        score -= min(20, ruff['total'] // 5)

        # Deduct for type coverage
        type_cov = ty.get('type_coverage', 100)
        score -= max(0, (100 - type_cov) // 5)

        # Deduct for security issues
        score -= semgrep['severity_counts'].get('ERROR', 0) * 10
        score -= semgrep['severity_counts'].get('WARNING', 0) * 5

        # Deduct for cognitive complexity (stricter than cyclomatic)
        for hotspot in complexipy['complexity_hotspots'][:5]:
            if hotspot['complexity'] > 12:  # Cognitive complexity threshold
                score -= 5

        # Deduct for dead code (new)
        score -= min(15, len(skylos['dead_functions']) * 2)
        score -= min(5, len(skylos['unused_imports']))

        return max(0, min(100, score))

    def _build_critical_issues(self, ruff: Dict, ty: Dict, semgrep: Dict,
                               complexipy: Dict, skylos: Dict) -> List[Dict]:
        """Build prioritized list of critical issues with code snippets."""
        issues = []

        # Add security errors (highest priority)
        for finding in semgrep['findings']:
            if finding['severity'] == 'ERROR':
                snippet_data = self._extract_snippet(finding['file'], finding['line'])
                issues.append({
                    'severity': 'ERROR',
                    'tool': 'semgrep',
                    'file': finding['file'],
                    'line': finding['line'],
                    'issue': f"{finding['category']}: {finding['message']}",
                    **snippet_data
                })

        # Add critical complexity issues (cognitive complexity)
        for hotspot in complexipy['complexity_hotspots']:
            if hotspot['grade'] in ['F', 'D']:
                # Complexipy doesn't provide line numbers, so we can't extract snippets
                issues.append({
                    'severity': 'ERROR' if hotspot['grade'] == 'F' else 'WARNING',
                    'tool': 'complexipy',
                    'file': hotspot['file'],
                    'line': 0,
                    'issue': f"Cognitive complexity {hotspot['complexity']} ({hotspot['grade']}-grade) in {hotspot['function']}",
                    'snippet': '',
                    'context_before': [],
                    'context_after': []
                })

        # Add critical ty errors
        ty_limit = 5 if self.filtered else len(ty['errors'])
        for error in ty['errors'][:ty_limit]:
            if error['severity'] == 'error':
                snippet_data = self._extract_snippet(error['file'], error['line'])
                issues.append({
                    'severity': 'ERROR',
                    'tool': 'ty',
                    'file': error['file'],
                    'line': error['line'],
                    'issue': error['message'],
                    **snippet_data
                })

        # Add critical ruff errors
        for issue in ruff['issues']:
            if issue['severity'] == 'error' and issue['code'].startswith('F'):
                snippet_data = self._extract_snippet(issue['file'], issue['line'])
                issues.append({
                    'severity': 'ERROR',
                    'tool': 'ruff',
                    'file': issue['file'],
                    'line': issue['line'],
                    'issue': f"{issue['code']}: {issue['message']}",
                    **snippet_data
                })

        # Add dead code with high confidence (new)
        for dead_func in skylos['dead_functions']:
            if dead_func['confidence'] >= 80:
                snippet_data = self._extract_snippet(dead_func['file'], dead_func['line'])
                issues.append({
                    'severity': 'WARNING',
                    'tool': 'skylos',
                    'file': dead_func['file'],
                    'line': dead_func['line'],
                    'issue': f"Unused function '{dead_func['function']}' (confidence: {dead_func['confidence']}%)",
                    **snippet_data
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

    def _format_ty_results(self, ty: Dict) -> Dict:
        """Format ty results for TOON output."""
        result = {
            'total': ty['total'],
            'type_coverage': f"{ty.get('type_coverage', 0)}%",
        }

        if self.filtered:
            result['by_error'] = ty['by_error'][:5]
        else:
            result['by_error'] = ty['by_error']
            result['files_checked'] = ty.get('files_checked', 0)
            result['files_with_errors'] = ty.get('files_with_errors', 0)
            result['all_errors'] = ty['errors']

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

    def _format_complexipy_results(self, complexipy: Dict) -> Dict:
        """Format complexipy results for TOON output."""
        result = {}

        if self.filtered:
            result['complexity_hotspots'] = complexipy['complexity_hotspots'][:10]
        else:
            result['avg_complexity'] = complexipy.get('avg_complexity', 0)
            result['total_functions'] = complexipy.get('total_functions', 0)
            result['complexity_hotspots'] = complexipy['complexity_hotspots']

        return result

    def _format_skylos_results(self, skylos: Dict) -> Dict:
        """Format skylos results for TOON output."""
        result = {
            'total_dead_code': skylos['total_dead_code'],
            'confidence_level': skylos['confidence_level']
        }

        if self.filtered:
            result['dead_functions'] = skylos['dead_functions'][:10]
            result['unused_imports'] = skylos['unused_imports'][:10]
        else:
            result['dead_functions'] = skylos['dead_functions']
            result['unused_imports'] = skylos['unused_imports']
            result['security_findings'] = skylos.get('security_findings', [])

        return result

    def _generate_immediate_fixes(self, ruff: Dict, ty: Dict, semgrep: Dict,
                                  complexipy: Dict, skylos: Dict) -> List[Dict]:
        """Generate immediate fix recommendations."""
        fixes = []

        priority = 1

        # Auto-fixable linting
        if ruff['auto_fixable'] > 0:
            fixes.append({
                'priority': priority,
                'action': 'Run: ruff check --fix .',
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

        # Dead code removal (new - high priority)
        if len(skylos['dead_functions']) > 0:
            fixes.append({
                'priority': priority,
                'action': f"Remove {len(skylos['dead_functions'])} unused functions",
                'effort': '30min'
            })
            priority += 1

        # Critical cognitive complexity
        hotpot_limit = 5 if self.filtered else len(complexipy['complexity_hotspots'])
        for hotspot in complexipy['complexity_hotspots'][:hotpot_limit]:
            if hotspot['grade'] == 'F':
                fixes.append({
                    'priority': priority,
                    'action': f"Refactor: {hotspot['file']} (cognitive complexity {hotspot['complexity']}→<12)",
                    'effort': '2hrs'
                })
                priority += 1
                if self.filtered and priority > 5:
                    break

        return fixes

    def _extract_snippet(self, file_path: str, line: int, context: int = 1) -> Dict[str, Any]:
        """
        Extract code snippet with context from a file.

        Args:
            file_path: Path to the source file
            line: Line number of the issue (1-indexed)
            context: Number of context lines before/after

        Returns:
            Dict with snippet, context_before, context_after
        """
        try:
            full_path = self.workspace / file_path
            if not full_path.exists():
                return {'snippet': '', 'context_before': [], 'context_after': []}

            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            # Convert to 0-indexed
            idx = line - 1
            if idx < 0 or idx >= len(lines):
                return {'snippet': '', 'context_before': [], 'context_after': []}

            # Extract snippet and context
            snippet = lines[idx].rstrip()
            context_before = [line.rstrip() for line in lines[max(0, idx - context):idx]]
            context_after = [line.rstrip() for line in lines[idx + 1:idx + 1 + context]]

            return {
                'snippet': snippet,
                'context_before': context_before,
                'context_after': context_after
            }
        except Exception as e:
            self.logger.debug(f"Failed to extract snippet from {file_path}:{line}: {e}")
            return {'snippet': '', 'context_before': [], 'context_after': []}

    def _cluster_issues(self, critical_issues: List[Dict], ruff: Dict, ty: Dict,
                        semgrep: Dict, complexipy: Dict, skylos: Dict) -> List[Dict]:
        """
        Cluster related issues for easier bulk fixing.

        Groups issues by:
        - Same file (file-level clusters)
        - Same category/pattern (thematic clusters)
        - Same fix type (action clusters)

        Returns:
            List of issue clusters with themes and suggested actions
        """
        clusters = []
        cluster_id = 1

        # Cluster by file
        file_issues: Dict[str, List[Dict]] = {}
        for issue in critical_issues:
            file_key = issue.get('file', 'unknown')
            if file_key not in file_issues:
                file_issues[file_key] = []
            file_issues[file_key].append(issue)

        # Create file-based clusters (only for files with 2+ issues)
        for file_path, issues in file_issues.items():
            if len(issues) >= 2:
                clusters.append({
                    'cluster_id': cluster_id,
                    'theme': f"Multiple issues in {Path(file_path).name}",
                    'file': file_path,
                    'issue_count': len(issues),
                    'tools': list(set(i.get('tool', '') for i in issues)),
                    'suggested_action': f"Review and fix {len(issues)} issues in {file_path}"
                })
                cluster_id += 1

        # Cluster dead code
        dead_funcs = skylos.get('dead_functions', [])
        unused_imports = skylos.get('unused_imports', [])
        if len(dead_funcs) + len(unused_imports) >= 2:
            clusters.append({
                'cluster_id': cluster_id,
                'theme': "Dead code cleanup",
                'file': None,
                'issue_count': len(dead_funcs) + len(unused_imports),
                'tools': ['skylos'],
                'suggested_action': f"Remove {len(dead_funcs)} unused functions and {len(unused_imports)} unused imports"
            })
            cluster_id += 1

        # Cluster security issues
        security_issues = [f for f in semgrep.get('findings', []) if f.get('severity') in ['ERROR', 'WARNING']]
        if len(security_issues) >= 2:
            clusters.append({
                'cluster_id': cluster_id,
                'theme': "Security vulnerabilities",
                'file': None,
                'issue_count': len(security_issues),
                'tools': ['semgrep'],
                'suggested_action': "Review and fix security issues before deployment"
            })
            cluster_id += 1

        # Cluster complexity hotspots
        complex_funcs = [h for h in complexipy.get('complexity_hotspots', []) if h.get('grade') in ['F', 'D']]
        if len(complex_funcs) >= 2:
            clusters.append({
                'cluster_id': cluster_id,
                'theme': "High cognitive complexity",
                'file': None,
                'issue_count': len(complex_funcs),
                'tools': ['complexipy'],
                'suggested_action': "Refactor complex functions to improve maintainability"
            })
            cluster_id += 1

        # Cluster type errors by category
        ty_errors = ty.get('errors', [])
        if len(ty_errors) >= 3:
            clusters.append({
                'cluster_id': cluster_id,
                'theme': "Type annotation gaps",
                'file': None,
                'issue_count': len(ty_errors),
                'tools': ['ty'],
                'suggested_action': f"Add type annotations to fix {len(ty_errors)} type errors"
            })
            cluster_id += 1

        return clusters[:10]  # Limit to top 10 clusters

    def _generate_next_steps(self, ruff: Dict, ty: Dict, semgrep: Dict,
                            complexipy: Dict, skylos: Dict) -> List[str]:
        """Generate next steps recommendations."""
        steps = []

        # Type coverage
        if ty.get('type_coverage', 100) < 80:
            steps.append(f"Add type annotations to reach 80% coverage (currently {ty.get('type_coverage', 0)}%)")

        # Cognitive complexity
        high_complexity = len([h for h in complexipy['complexity_hotspots'] if h['grade'] in ['F', 'D']])
        if high_complexity > 0:
            steps.append(f"Refactor {high_complexity} high cognitive complexity functions (F/D grade)")

        # Dead code cleanup
        if len(skylos['dead_functions']) > 0:
            steps.append(f"Remove {len(skylos['dead_functions'])} dead functions to reduce maintenance burden")

        if len(skylos['unused_imports']) > 10:
            steps.append("Clean up unused imports (automated with ruff --fix)")

        # Security warnings
        if semgrep['severity_counts'].get('WARNING', 0) > 0:
            steps.append("Review and fix security warnings")

        # General improvements
        if ty.get('type_coverage', 0) > 80:
            steps.append("Enable ty strict mode for enhanced type safety")

        return steps[:5]


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Check code quality using ruff, ty, semgrep, complexipy, and skylos (v2.0)'
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
