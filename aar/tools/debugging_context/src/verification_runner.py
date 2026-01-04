import hashlib
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List
import logging
import subprocess
import tempfile

sys.path.insert(0, str(Path(__file__).parent))

from utils.data_structures import ExecutionResult, FailureData
from utils.path_utils import normalize_path

logger = logging.getLogger(__name__)


class TestSuiteExecutor:
    
    def __init__(self):
        self.workspace_dir: Path | None = None
    
    def trigger_verification(self, target_dir: Path, test_case: str | None = None) -> ExecutionResult:
        self.workspace_dir = normalize_path(target_dir)
        normalized_dir = normalize_path(target_dir)
        
        with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as tmp:
            report_path = Path(tmp.name)
        
        try:
            cmd = ['pytest', '--junitxml', str(report_path)]
            if test_case:
                cmd.append(test_case)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=normalized_dir
            )
            
            tree = ET.parse(report_path)
            root = tree.getroot()
            
            testsuite = root.find('testsuite')
            if testsuite is None:
                total_tests = int(root.attrib.get('tests', 0))
                failed_tests = int(root.attrib.get('failures', 0))
                failed_tests += int(root.attrib.get('errors', 0))
            else:
                total_tests = int(testsuite.attrib.get('tests', 0))
                failed_tests = int(testsuite.attrib.get('failures', 0))
                failed_tests += int(testsuite.attrib.get('errors', 0))
            
            return ExecutionResult(
                exit_code=result.returncode,
                total_tests=total_tests,
                failed_tests=failed_tests,
                report_path=report_path
            )
        except Exception as e:
            logger.error(f"Failed to execute tests: {e}")
            return ExecutionResult(
                exit_code=1,
                total_tests=0,
                failed_tests=0,
                report_path=report_path
            )
    
    def extract_failure_metadata(self, report_path: Path) -> List[FailureData]:
        normalized_path = normalize_path(report_path)
        
        if not normalized_path.exists():
            logger.warning(f"Report file not found: {normalized_path}")
            return []
        
        failures = []
        
        try:
            tree = ET.parse(normalized_path)
            root = tree.getroot()
            
            for test_case in root.iter('testcase'):
                failure_elem = test_case.find('failure')
                error_elem = test_case.find('error')
                
                if failure_elem is not None or error_elem is not None:
                    elem = failure_elem if failure_elem is not None else error_elem
                    
                    if elem is None:
                        continue
                    
                    test_id = test_case.attrib.get('name', 'unknown')
                    class_name = test_case.attrib.get('classname', '')
                    file_path = test_case.attrib.get('file', '')
                    line_number = int(test_case.attrib.get('line', 0))
                    
                    error_type = elem.attrib.get('type', 'UnknownError')
                    error_message = elem.attrib.get('message', 'No message')
                    traceback = elem.text or ''
                    
                    if error_message == 'collection failure':
                        error_type = 'CollectionError'
                    
                    if error_type == 'UnknownError':
                        import re
                        match = re.search(r'^([A-Z]\w+Error):', traceback, re.MULTILINE)
                        if match:
                            error_type = match.group(1)
                        else:
                            match = re.search(r'^([A-Z]\w+Error):', error_message)
                            if match:
                                error_type = match.group(1)
                    
                    if line_number == 0 and traceback:
                        import re
                        lines = traceback.split('\n')
                        for i, line in enumerate(lines):
                            if '.py:' in line and 'test_' not in line.lower():
                                match = re.search(r'([^/\\]+\.py):(\d+)', line)
                                if match:
                                    file_path = match.group(1)
                                    line_number = int(match.group(2))
                                    break
                    
                    if not file_path and traceback and error_type == 'CollectionError':
                        import re
                        match = re.search(r"'([^']+\.py)':(\d+)", traceback)
                        if match:
                            file_path = match.group(1)
                            line_number = int(match.group(2))
                    
                    if not file_path and class_name:
                        file_path = f"{class_name.replace('.', '/')}.py"
                    
                    if not file_path and error_type == 'CollectionError' and test_id:
                        file_path = f"{test_id.replace('.', '/')}.py"
                    
                    if not file_path and traceback:
                        import re
                        match = re.search(r'File "([^"]+)", line (\d+)', traceback)
                        if match:
                            file_path = match.group(1)
                            line_number = int(match.group(2))
                    
                    if not file_path:
                        file_path = f"{class_name.replace('.', '/')}.py"
                    
                    if self.workspace_dir and not Path(file_path).is_absolute():
                        file_path = str(self.workspace_dir / file_path)
                    
                    signature = self._generate_signature(error_type, error_message, traceback)
                    
                    failure = FailureData(
                        test_id=f"{class_name}::{test_id}",
                        source_file=file_path,
                        line_number=line_number,
                        error_type=error_type,
                        error_message=error_message,
                        traceback=traceback,
                        signature=signature
                    )
                    failures.append(failure)
        except Exception as e:
            logger.error(f"Failed to parse report file: {e}")
        
        return failures
    
    def _generate_signature(self, error_type: str, error_message: str, traceback: str) -> str:
        normalized_traceback = self._normalize_traceback(traceback)
        signature_string = f"{error_type}:{error_message}:{normalized_traceback}"
        return hashlib.sha256(signature_string.encode()).hexdigest()
    
    def _normalize_traceback(self, traceback: str) -> str:
        import re
        normalized = re.sub(r'0x[0-9a-fA-F]+', '0xXXXX', traceback)
        normalized = re.sub(r'\[.*?\]', '[XXX]', normalized)
        return normalized
