"""
Dead Code Safety Analyzer for dbgctxt v2.0

Verifies if dead code can be safely removed without breaking tests or dependencies.
"""

from typing import Any, Dict, List, Optional
import logging

from utils.data_structures import DeadCodeAnalysis

logger = logging.getLogger(__name__)


class DeadCodeAnalyzer:
    
    def __init__(self, quality_data: Dict[str, Any], structure_data: Dict[str, Any]):
        self.quality_data = quality_data
        self.structure_data = structure_data
        self.logger = logging.getLogger(__name__)
    
    def analyze_dead_code(self, function_name: str, filename: str) -> Optional[DeadCodeAnalysis]:
        skylos_data = self.quality_data.get('skylos', {})
        dead_functions = skylos_data.get('dead_functions', [])
        
        for dead_func in dead_functions:
            if dead_func.get('file') == filename and dead_func.get('symbol') == function_name:
                confidence = dead_func.get('confidence', 0)
                
                if confidence < 80:
                    return DeadCodeAnalysis(
                        function_name=function_name,
                        file=filename,
                        line=0,
                        safe_to_remove=False,
                        confidence=confidence,
                        checks={},
                        removal_steps=["Verify function is actually unused before removal"]
                    )
                
                checks = self._run_safety_checks(function_name, filename)
                safe_to_remove = all(checks.values())
                
                removal_steps = self._generate_removal_steps(function_name, filename, safe_to_remove)
                
                return DeadCodeAnalysis(
                    function_name=function_name,
                    file=filename,
                    line=0,
                    safe_to_remove=safe_to_remove,
                    confidence=confidence,
                    checks=checks,
                    removal_steps=removal_steps
                )
        
        return None
    
    def _run_safety_checks(self, function_name: str, filename: str) -> Dict[str, bool]:
        checks = {}
        
        checks['no_references'] = self._check_no_references(function_name, filename)
        checks['not_in_imports'] = self._check_not_in_imports(filename)
        checks['no_security_impact'] = self._check_security_impact(filename)
        checks['no_todos'] = self._check_no_todos(filename)
        checks['not_hot_path'] = self._check_not_hot_path(function_name, filename)
        
        return checks
    
    def _check_no_references(self, function_name: str, filename: str) -> bool:
        import_graph = self.structure_data.get('import_graph', {})
        external_deps = import_graph.get('external_dependencies', [])
        
        module_name = filename.replace('/', '.').replace('.py', '')
        
        for dep in external_deps:
            if module_name in dep.lower():
                return False
        
        call_graph = self.structure_data.get('call_graph', [])
        for call in call_graph:
            if function_name in str(call):
                return False
        
        return True
    
    def _check_not_in_imports(self, filename: str) -> bool:
        import_graph = self.structure_data.get('import_graph', {})
        external_deps = import_graph.get('external_dependencies', [])
        
        module_name = filename.replace('/', '.').replace('.py', '')
        
        for dep in external_deps:
            if module_name in dep:
                return False
        
        return True
    
    def _check_security_impact(self, filename: str) -> bool:
        semgrep_data = self.quality_data.get('semgrep', {})
        all_findings = semgrep_data.get('all_findings', [])
        
        for finding in all_findings:
            if finding.get('file') == filename:
                return False
        
        return True
    
    def _check_no_todos(self, filename: str) -> bool:
        pattern_findings = self.structure_data.get('pattern_findings', {})
        technical_debt = pattern_findings.get('technical_debt', {})
        
        if technical_debt.get('total_count', 0) == 0:
            return True
        
        return False
    
    def _check_not_hot_path(self, function_name: str, filename: str) -> bool:
        complexipy_data = self.quality_data.get('complexipy', {})
        hotspots = complexipy_data.get('complexity_hotspots', [])
        
        for hotspot in hotspots:
            if hotspot.get('function') == function_name and hotspot.get('file') == filename:
                return False
        
        return True
    
    def _generate_removal_steps(self, function_name: str, filename: str, safe_to_remove: bool) -> List[str]:
        steps = []
        
        if safe_to_remove:
            steps.append(f"Remove function definition: {function_name}")
            steps.append(f"Remove from __all__ if present in {filename}")
            steps.append("Run tests to verify no breakage")
            steps.append("Commit changes with descriptive message")
        else:
            steps.append(f"Review function: {function_name} in {filename}")
            steps.append("Check for indirect references or dynamic imports")
            steps.append("Verify test coverage exists for dependent code")
            steps.append("Consider adding deprecation notice instead of removal")
        
        return steps
    
    def get_all_dead_code_analysis(self) -> List[DeadCodeAnalysis]:
        analyses = []
        
        skylos_data = self.quality_data.get('skylos', {})
        dead_functions = skylos_data.get('dead_functions', [])
        
        for dead_func in dead_functions:
            function_name = dead_func.get('symbol')
            filename = dead_func.get('file')
            
            if function_name and filename:
                analysis = self.analyze_dead_code(function_name, filename)
                if analysis:
                    analyses.append(analysis)
        
        return analyses