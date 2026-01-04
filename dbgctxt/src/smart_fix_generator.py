"""
Smart Fix Suggestion Generator for dbgctxt v2.0

Generates contextually relevant fix suggestions based on quality metrics findings.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import logging

from utils.data_structures import FailureData, RootCauseCorrelation, FixSuggestion

logger = logging.getLogger(__name__)


class SmartFixGenerator:
    
    def __init__(self, quality_data: Dict[str, Any], structure_data: Dict[str, Any]):
        self.quality_data = quality_data
        self.structure_data = structure_data
        self.logger = logging.getLogger(__name__)
    
    def generate_fixes(self, failure: FailureData, correlation: RootCauseCorrelation) -> List[FixSuggestion]:
        suggestions = []
        priority = 1
        filename = failure.source_file
        function_name = self._extract_function_name(failure)
        
        if correlation.primary_cause == 'security':
            security_fix = self._generate_security_fix(filename, failure.line_number)
            if security_fix:
                suggestions.append(security_fix)
                priority += 1
        
        if correlation.primary_cause == 'complexity' or self._has_high_complexity(filename, function_name):
            complexity_fix = self._generate_complexity_fix(filename, function_name)
            if complexity_fix:
                suggestions.append(FixSuggestion(
                    failure_id=failure.signature,
                    priority=priority,
                    action=complexity_fix['action'],
                    effort=complexity_fix['effort'],
                    confidence='HIGH',
                    evidence=complexity_fix.get('evidence', [])
                ))
                priority += 1
        
        if correlation.primary_cause == 'type_errors' or self._has_type_errors(filename):
            type_fix = self._generate_type_fix(filename, failure.line_number)
            if type_fix:
                suggestions.append(type_fix)
                priority += 1
        
        if self._has_bare_except(filename):
            suggestions.append(FixSuggestion(
                failure_id=failure.signature,
                priority=priority,
                action="Specify exception types instead of bare except",
                effort="10min",
                confidence="MEDIUM",
                evidence=["Found bare except clause in file"]
            ))
            priority += 1
        
        if self._has_dead_code(filename, function_name):
            suggestions.append(FixSuggestion(
                failure_id=failure.signature,
                priority=priority,
                action="Review and remove dead code or add documentation",
                effort="5min",
                confidence="MEDIUM",
                evidence=["Function marked as unused by skylos"]
            ))
        
        return suggestions
    
    def _extract_function_name(self, failure: FailureData) -> Optional[str]:
        for line in failure.traceback.split('\n'):
            if 'in ' in line and '.py' in line:
                parts = line.split('in ')
                if len(parts) > 1:
                    func_name = parts[1].split('(')[0].strip()
                    return func_name
        return None
    
    def _generate_security_fix(self, filename: str, line_number: int) -> Optional[FixSuggestion]:
        semgrep_data = self.quality_data.get('semgrep', {})
        all_findings = semgrep_data.get('all_findings', [])
        
        for finding in all_findings:
            if finding.get('file') == filename and finding.get('line') == line_number:
                rule_id = finding.get('rule_id', '')
                message = finding.get('message', '')
                
                if 'shell=True' in rule_id:
                    return FixSuggestion(
                        failure_id=f"security_{filename}_{line_number}",
                        priority=1,
                        action="Replace shell=True with shell=False and use subprocess list arguments",
                        effort="10min",
                        confidence="HIGH",
                        evidence=[message]
                    )
                elif 'sql' in rule_id.lower() or 'injection' in message.lower():
                    return FixSuggestion(
                        failure_id=f"security_{filename}_{line_number}",
                        priority=1,
                        action="Use parameterized queries or an ORM to prevent SQL injection",
                        effort="15min",
                        confidence="HIGH",
                        evidence=[message]
                    )
                else:
                    return FixSuggestion(
                        failure_id=f"security_{filename}_{line_number}",
                        priority=1,
                        action=f"Fix security issue: {message}",
                        effort="15min",
                        confidence="HIGH",
                        evidence=[message]
                    )
        return None
    
    def _generate_complexity_fix(self, filename: str, function_name: Optional[str]) -> Optional[Dict[str, Any]]:
        if not function_name:
            return None
        
        complexipy_data = self.quality_data.get('complexipy', {})
        hotspots = complexipy_data.get('complexity_hotspots', [])
        
        for hotspot in hotspots:
            if hotspot.get('function') == function_name and hotspot.get('file') == filename:
                complexity = hotspot.get('complexity', 0)
                grade = self._get_complexity_grade(complexity)
                
                if grade in ['D', 'F']:
                    return {
                        'action': f'Extract complex logic into smaller functions (cognitive complexity {complexity} → <12)',
                        'effort': '2hrs',
                        'evidence': [f'Cognitive complexity: {complexity} ({grade}-grade)']
                    }
        return None
    
    def _generate_type_fix(self, filename: str, line_number: int) -> Optional[FixSuggestion]:
        ty_data = self.quality_data.get('ty', {})
        all_errors = ty_data.get('all_errors', [])
        
        for error in all_errors:
            if error.get('file') == filename and error.get('line') == line_number:
                code = error.get('code', '')
                message = error.get('message', '')
                
                if code == 'attr-defined':
                    return FixSuggestion(
                        failure_id=f"type_{filename}_{line_number}",
                        priority=1,
                        action="Add missing attribute or verify data structure initialization",
                        effort="15min",
                        confidence="HIGH",
                        evidence=[message]
                    )
                elif code == 'arg-type':
                    return FixSuggestion(
                        failure_id=f"type_{filename}_{line_number}",
                        priority=1,
                        action="Fix type mismatch in function arguments",
                        effort="10min",
                        confidence="HIGH",
                        evidence=[message]
                    )
                else:
                    return FixSuggestion(
                        failure_id=f"type_{filename}_{line_number}",
                        priority=1,
                        action=f"Add type annotations or fix type error: {message}",
                        effort="10min",
                        confidence="MEDIUM",
                        evidence=[message]
                    )
        return None
    
    def _has_high_complexity(self, filename: str, function_name: Optional[str]) -> bool:
        if not function_name:
            return False
        
        complexipy_data = self.quality_data.get('complexipy', {})
        hotspots = complexipy_data.get('complexity_hotspots', [])
        
        for hotspot in hotspots:
            if hotspot.get('function') == function_name and hotspot.get('file') == filename:
                return hotspot.get('complexity', 0) >= 12
        return False
    
    def _has_type_errors(self, filename: str) -> bool:
        ty_data = self.quality_data.get('ty', {})
        all_errors = ty_data.get('all_errors', [])
        
        return any(error.get('file') == filename for error in all_errors)
    
    def _has_bare_except(self, filename: str) -> bool:
        ruff_data = self.quality_data.get('ruff', {})
        all_issues = ruff_data.get('all_issues', [])
        
        return any(
            error.get('file') == filename and error.get('code') == 'E722'
            for error in all_issues
        )
    
    def _has_dead_code(self, filename: str, function_name: Optional[str]) -> bool:
        if not function_name:
            return False
        
        skylos_data = self.quality_data.get('skylos', {})
        dead_functions = skylos_data.get('dead_functions', [])
        
        return any(
            dead_func.get('file') == filename and dead_func.get('symbol') == function_name
            for dead_func in dead_functions
        )
    
    def _get_complexity_grade(self, complexity: int) -> str:
        if complexity <= 5:
            return 'A'
        elif complexity <= 10:
            return 'B'
        elif complexity <= 15:
            return 'C'
        elif complexity <= 20:
            return 'D'
        else:
            return 'F'