"""
Root Cause Correlation Engine for dbgctxt v2.0

Correlates test failures with quality metrics from cdqa and structure data from cdscan
to identify most likely root causes.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import logging

from utils.data_structures import FailureData, RootCauseCorrelation

logger = logging.getLogger(__name__)


class RootCauseAnalyzer:
    
    def __init__(self, quality_data: Dict[str, Any], structure_data: Dict[str, Any]):
        self.quality_data = quality_data
        self.structure_data = structure_data
        self.logger = logging.getLogger(__name__)
    
    def analyze_failure(self, failure: FailureData) -> RootCauseCorrelation:
        scores = {}
        evidence = []
        
        filename = failure.source_file
        function_name = self._extract_function_name(failure)
        
        scores['complexity'] = self._check_complexity(function_name, filename)
        scores['type_errors'] = self._check_type_errors(filename, failure.line_number)
        scores['security'] = self._check_security_issues(filename, failure.line_number)
        scores['dead_code'] = self._check_dead_code(filename, function_name)
        scores['anti_patterns'] = self._check_anti_patterns(filename, function_name)
        
        sorted_causes = sorted(scores.items(), key=lambda x: -x[1] if x[1] else 0)
        
        primary_cause = sorted_causes[0][0] if sorted_causes[0][1] > 0 else "unknown"
        primary_confidence = sorted_causes[0][1] if sorted_causes[0][1] > 0 else 0
        
        secondary_causes = []
        for cause, score in sorted_causes[1:]:
            if score > 0.05:
                secondary_causes.append({cause: score})
        
        return RootCauseCorrelation(
            failure_id=failure.signature,
            primary_cause=primary_cause,
            confidence=primary_confidence,
            secondary_causes=secondary_causes,
            evidence=evidence
        )
    
    def _extract_function_name(self, failure: FailureData) -> Optional[str]:
        for line in failure.traceback.split('\n'):
            if 'in ' in line and '.py' in line:
                parts = line.split('in ')
                if len(parts) > 1:
                    func_name = parts[1].split('(')[0].strip()
                    return func_name
        return None
    
    def _check_complexity(self, function_name: Optional[str], filename: str) -> float:
        if not function_name:
            return 0.0
        
        complexipy_data = self.quality_data.get('complexipy', {})
        hotspots = complexipy_data.get('complexity_hotspots', [])
        
        for hotspot in hotspots:
            if hotspot.get('function') == function_name and hotspot.get('file') == filename:
                complexity = hotspot.get('complexity', 0)
                if complexity >= 12:
                    if complexity >= 20:
                        self.logger.info(f"High complexity (F-grade): {function_name}={complexity}")
                        return 0.35
                    elif complexity >= 15:
                        return 0.30
                    else:
                        return 0.25
        return 0.0
    
    def _check_type_errors(self, filename: str, line_number: int) -> float:
        ty_data = self.quality_data.get('ty', {})
        all_errors = ty_data.get('all_errors', [])
        
        for error in all_errors:
            if error.get('file') == filename and error.get('line') == line_number:
                return 0.30
        
        for error in all_errors:
            if error.get('file') == filename:
                return 0.20
        
        return 0.0
    
    def _check_security_issues(self, filename: str, line_number: int) -> float:
        semgrep_data = self.quality_data.get('semgrep', {})
        all_findings = semgrep_data.get('all_findings', [])
        
        for finding in all_findings:
            if finding.get('file') == filename and finding.get('line') == line_number:
                severity = finding.get('severity', 'INFO')
                if severity == 'ERROR':
                    return 0.40
                elif severity == 'WARNING':
                    return 0.25
                else:
                    return 0.15
        
        for finding in all_findings:
            if finding.get('file') == filename:
                severity = finding.get('severity', 'INFO')
                if severity == 'ERROR':
                    return 0.30
        
        return 0.0
    
    def _check_dead_code(self, filename: str, function_name: Optional[str]) -> float:
        skylos_data = self.quality_data.get('skylos', {})
        dead_functions = skylos_data.get('dead_functions', [])
        
        for dead_func in dead_functions:
            if dead_func.get('file') == filename and dead_func.get('symbol') == function_name:
                confidence = dead_func.get('confidence', 0)
                if confidence > 80:
                    return 0.25
                elif confidence > 60:
                    return 0.15
        
        return 0.0
    
    def _check_anti_patterns(self, filename: str, function_name: Optional[str]) -> float:
        ruff_data = self.quality_data.get('ruff', {})
        all_issues = ruff_data.get('all_issues', [])
        
        bare_except_found = False
        mutable_default_found = False
        
        for issue in all_issues:
            if issue.get('file') == filename:
                code = issue.get('code', '')
                if code == 'E722':
                    bare_except_found = True
                elif code.startswith('B006'):
                    mutable_default_found = True
        
        score = 0.0
        if bare_except_found:
            score += 0.15
        if mutable_default_found:
            score += 0.10
        
        return score