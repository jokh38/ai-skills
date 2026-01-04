import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging
import re

sys.path.insert(0, str(Path(__file__).parent))

from utils.data_structures import FailureData, RichContext
from utils.path_utils import normalize_path

logger = logging.getLogger(__name__)


class FailureContextMapper:
    
    def deduplicate_failures(self, failures: List[FailureData]) -> List[FailureData]:
        signature_groups: Dict[str, List[FailureData]] = {}
        
        for failure in failures:
            if failure.signature not in signature_groups:
                signature_groups[failure.signature] = []
            signature_groups[failure.signature].append(failure)
        
        deduplicated: List[FailureData] = []
        
        for signature, group in signature_groups.items():
            representative = group[0]
            
            if len(group) > 1:
                representative.error_message = f"{representative.error_message} (...and {len(group) - 1} other similar failures)"
            
            deduplicated.append(representative)
        
        logger.info(f"Deduplicated {len(failures)} failures to {len(deduplicated)} unique failures")
        return deduplicated
    
    def enrich_failure_data(
        self, 
        failures: List[FailureData], 
        structure_map: Dict[Path, List[Any]], 
        quality_map: Dict[Path, List[Any]]
    ) -> List[RichContext]:
        enriched: List[RichContext] = []
        
        for failure in failures:
            source_file = normalize_path(failure.source_file)
            
            error_class = self._classify_error(failure)
            
            related_code, ast_scope = self._resolve_structure_context(
                source_file, 
                failure.line_number, 
                structure_map
            )
            
            static_errors = self._resolve_quality_errors(
                source_file, 
                failure.line_number, 
                quality_map
            )
            
            stack_trace = self._extract_stack_trace(failure.traceback)
            import_chain = self._extract_import_chain(failure.traceback, failure.error_type)
            search_paths = self._extract_search_paths(failure.error_type, failure.source_file)
            expected_vs_actual = self._extract_expected_actual(failure.error_message)
            call_context = self._extract_call_context(failure.traceback)
            test_context = self._extract_test_context(failure.test_id, str(source_file))
            missing_resources = self._extract_missing_resources(failure.error_type, failure.error_message, str(source_file))
            config_state = self._extract_config_state(failure.error_type, failure.error_message)
            missing_vars = self._extract_missing_vars(failure.error_message)
            rule_info = self._extract_rule_info(failure.error_type, failure.error_message)
            suggested_fix = self._extract_suggested_fix(failure.error_type, failure.error_message)
            
            dedup_note = ""
            if "...and" in failure.error_message:
                import re
                match = re.search(r'\((\d+) other similar failures\)', failure.error_message)
                if match:
                    dedup_note = match.group(0)
            
            context = RichContext(
                failure=failure,
                related_code=related_code,
                ast_scope=ast_scope,
                static_errors=static_errors,
                deduplication_note=dedup_note,
                error_class=error_class,
                stack_trace=stack_trace,
                import_chain=import_chain,
                search_paths=search_paths,
                expected_vs_actual=expected_vs_actual,
                call_context=call_context,
                test_context=test_context,
                missing_resources=missing_resources,
                config_state=config_state,
                missing_vars=missing_vars,
                rule_info=rule_info,
                suggested_fix=suggested_fix
            )
            enriched.append(context)
        
        return enriched
    
    def _resolve_structure_context(
        self, 
        file_path: Path, 
        line_number: int, 
        structure_map: Dict[Path, List[Any]]
    ) -> tuple[str, str]:
        if file_path not in structure_map:
            return self._load_full_file_code(file_path), "Unknown"
        
        nodes = structure_map[file_path]
        enclosing_node = None
        enclosing_node_type = "Unknown"
        
        for node in nodes:
            if isinstance(node, dict):
                node_start = node.get('start_line', 0)
                node_end = node.get('end_line', float('inf'))
                
                if node_start <= line_number <= node_end:
                    if enclosing_node is None or node_start > enclosing_node.get('start_line', 0):
                        enclosing_node = node
                        enclosing_node_type = node.get('type', 'Unknown')
        
        related_code = self._load_full_file_code(file_path)
        
        return related_code, enclosing_node_type
    
    def _resolve_quality_errors(
        self, 
        file_path: Path, 
        line_number: int, 
        quality_map: Dict[Path, List[Any]]
    ) -> List[str]:
        if file_path not in quality_map:
            return []
        
        issues = quality_map[file_path]
        relevant_issues = []
        
        for issue in issues:
            if isinstance(issue, dict):
                issue_line = issue.get('line', -1)
                issue_code = issue.get('code', '')
                issue_msg = issue.get('message', '')
                
                if abs(issue_line - line_number) <= 5:
                    relevant_issues.append(f"{issue_code}: {issue_msg}")
        
        return relevant_issues
    
    def _load_full_file_code(self, file_path: Path) -> str:
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            return f"Could not load file: {file_path}"
        except Exception as e:
            logger.error(f"Failed to load file {file_path}: {e}")
            return f"Error loading file: {e}"
    
    def _classify_error(self, failure: FailureData) -> str:
        """Classify error type into tier for targeted context."""
        error_type = failure.error_type
        error_message = failure.error_message.lower()
        
        if error_type in ['ImportError', 'ModuleNotFoundError']:
            return 'import'
        elif error_type == 'AssertionError':
            return 'assertion'
        elif error_type in ['FileNotFoundError', 'CollectionError']:
            return 'test_infra'
        elif (error_type == 'AuthenticationError' or 
              'authentication' in error_message or 
              'anthropic' in error_message and 'error' in error_message):
            return 'config'
        elif 'ruff' in error_message or 'semgrep' in error_message or error_type == 'LintError':
            return 'lint'
        elif error_type in ['TypeError', 'AttributeError', 'KeyError', 'NameError', 'ValueError', 'NotImplementedError']:
            return 'runtime'
        else:
            return 'runtime'
    
    def _extract_stack_trace(self, traceback: str) -> List[Dict[str, Any]]:
        """Extract structured stack trace from traceback string."""
        frames: List[Dict[str, Any]] = []
        if not traceback:
            return frames
        
        for line in traceback.split('\n'):
            if '.py:' in line and 'line' in line:
                match = re.search(r'File "([^"]+)", line (\d+), in ([^\s]+)', line)
                if match:
                    file_path = match.group(1)
                    line_num = int(match.group(2))
                    func_name = match.group(3)
                    frames.append({
                        'file': file_path,
                        'line': line_num,
                        'function': func_name,
                        'code_snippet': line.strip()
                    })
        
        return frames
    
    def _extract_import_chain(self, traceback: str, error_type: str) -> List[Dict[str, Any]]:
        """Extract import chain for import errors."""
        if error_type not in ['ImportError', 'ModuleNotFoundError']:
            return []
        
        chain = []
        import_errors = []
        
        if traceback:
            for line in traceback.split('\n'):
                if 'import' in line.lower() or 'module' in line.lower():
                    match = re.search(r"'([^']+)'", line)
                    if match:
                        module = match.group(1)
                        import_errors.append(module)
        
        for module in import_errors[:5]:
            resolved = Path(f"{module.replace('.', '/')}.py").exists() or Path(f"{module.replace('.', '/')}/__init__.py").exists()
            chain.append({
                'module': module,
                'import_file': f"{module.replace('.', '/')}.py",
                'resolved': resolved,
                'error': 'Module not found' if not resolved else None
            })
        
        return chain
    
    def _extract_search_paths(self, error_type: str, source_file: str) -> List[Dict[str, Any]]:
        """Extract module search paths."""
        if error_type not in ['ImportError', 'ModuleNotFoundError']:
            return []
        
        paths = []
        sys_paths = sys.path[:5]
        for path in sys_paths:
            path_exists = Path(path).exists()
            paths.append({
                'path': path,
                'exists': path_exists
            })
        
        return paths
    
    def _extract_expected_actual(self, error_message: str) -> Optional[Dict[str, Any]]:
        """Extract expected vs actual from assertion errors."""
        if 'assert' not in error_message.lower():
            return None
        
        expected_match = re.search(r'expected[:\s]+([^\n]+)', error_message, re.IGNORECASE)
        actual_match = re.search(r'actual[:\s]+([^\n]+)', error_message, re.IGNORECASE)
        
        if expected_match or actual_match:
            return {
                'expected': expected_match.group(1) if expected_match else None,
                'actual': actual_match.group(1) if actual_match else None,
                'diff': error_message
            }
        
        return None
    
    def _extract_call_context(self, traceback: str) -> Optional[Dict[str, Any]]:
        """Extract call context from traceback."""
        if not traceback:
            return None
        
        lines = traceback.split('\n')
        for i, line in enumerate(lines):
            if 'Error:' in line and i > 0:
                func_line = lines[i-1]
                match = re.search(r'([^\s]+)\((.*?)\)', func_line)
                if match:
                    return {
                        'function': match.group(1),
                        'parameters': match.group(2)
                    }
        
        return None
    
    def _extract_test_context(self, test_id: str, source_file: str) -> Optional[Dict[str, Any]]:
        """Extract test context for test infrastructure errors."""
        try:
            if source_file and Path(source_file).exists():
                with open(source_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    fixtures = re.findall(r'@pytest\.fixture|def ([a-z_]+)\(.*?\):', content)
                    return {
                        'test_function': test_id.split('::')[-1],
                        'fixtures_used': fixtures[:5]
                    }
        except Exception:
            pass
        
        return None
    
    def _extract_missing_resources(self, error_type: str, error_message: str, source_file: str) -> List[Dict[str, str]]:
        """Extract missing resources for test infrastructure errors."""
        resources = []
        
        if error_type == 'FileNotFoundError':
            match = re.search(r"'([^']+)'", error_message)
            if match:
                resources.append({
                    'path': match.group(1),
                    'expected_usage': 'Test file or fixture'
                })
        
        return resources
    
    def _extract_config_state(self, error_type: str, error_message: str) -> Optional[Dict[str, Any]]:
        """Extract config state for configuration errors."""
        if 'anthropic' in error_message.lower() or 'authentication' in error_message.lower():
            return {
                'provider': 'anthropic',
                'model': 'unknown',
                'error': 'Invalid or missing API key'
            }
        
        if 'openai' in error_message.lower():
            return {
                'provider': 'openai',
                'model': 'unknown',
                'error': 'Invalid or missing API key'
            }
        
        return None
    
    def _extract_missing_vars(self, error_message: str) -> List[str]:
        """Extract missing environment variables."""
        vars_found = []
        if 'api_key' in error_message.lower() or 'api key' in error_message.lower():
            vars_found.append('API_KEY')
        
        return vars_found
    
    def _extract_rule_info(self, error_type: str, error_message: str) -> Optional[Dict[str, Any]]:
        """Extract rule info for linting errors."""
        if 'ruff' in error_message.lower() or 'semgrep' in error_message.lower():
            rule_match = re.search(r'[A-Z]{1,2}\d{3,4}', error_message)
            if rule_match:
                return {
                    'rule_id': rule_match.group(0),
                    'severity': 'error',
                    'description': error_message[:200]
                }
        
        return None
    
    def _extract_suggested_fix(self, error_type: str, error_message: str) -> Optional[Dict[str, str]]:
        """Extract suggested fix for linting errors."""
        return None
    
    def enrich_failures_with_correlation(
        self,
        failures: List[FailureData],
        structure_data: Dict[str, Any],
        quality_data: Dict[str, Any]
    ) -> tuple[List[RichContext], List[Any], List[Any]]:
        """Enrich failures with root cause analysis and smart fixes."""
        
        from src.root_cause_analyzer import RootCauseAnalyzer
        from src.smart_fix_generator import SmartFixGenerator
        
        root_cause_analyzer = RootCauseAnalyzer(quality_data, structure_data)
        fix_generator = SmartFixGenerator(quality_data, structure_data)
        
        enriched_contexts = []
        all_correlations = []
        all_fixes = []
        
        for failure in failures:
            correlation = root_cause_analyzer.analyze_failure(failure)
            all_correlations.append(correlation)
            
            fixes = fix_generator.generate_fixes(failure, correlation)
            all_fixes.extend(fixes)
            
            context = RichContext(
                failure=failure,
                related_code=self._load_full_file_code(Path(failure.source_file)),
                ast_scope="unknown",
                static_errors=[],
                deduplication_note="",
                error_class=self._classify_error(failure)
            )
            
            enriched_contexts.append(context)
        
        return enriched_contexts, all_correlations, all_fixes
