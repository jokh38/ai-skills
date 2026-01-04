"""
RRD LLM Integration

Unified LLM interface for code generation, test generation, and fix proposals
Uses the existing LLM_api tool as a backend
"""

import sys
from pathlib import Path
from typing import Optional, Dict, Any, List

# Add LLM_api to path
llm_api_path = Path(__file__).parent.parent.parent.parent / "skills" / "LLM_api"
if llm_api_path.exists():
    sys.path.insert(0, str(llm_api_path))

try:
    from llm_client import LLMClient as BaseLLMClient
except ImportError:
    # Fallback if LLM_api not available
    BaseLLMClient = None

from core.config_loader import RRDConfig
from core.toon_utils import ToonParser, parse_toon
from core.data_types import PatchToon, ActiveContext
from integrations.cdscan_integration import CodebaseAnalysis
from integrations.cdqa_integration import QualityReport


# RRD-specific prompt templates
ADVERSARIAL_TEST_TEMPLATE = """
You are a test-focused AI. Generate comprehensive pytest tests from this specification.

Specification:
{spec}

Codebase Structure:
{codebase_summary}

Requirements:
1. Cover ALL edge cases and boundary conditions
2. Test failure modes - try to break the implementation
3. Include tests for error conditions (None, empty, invalid types)
4. Use pytest fixtures where appropriate
5. Include parametrized tests for multiple inputs
6. Mock external dependencies

Output ONLY valid Python code with pytest tests.
No explanations, just the code.
"""

SKELETON_TEMPLATE = """
Create a skeleton implementation based on this specification.

Specification:
{spec}

Existing Code (if any):
{existing_code}

Requirements:
1. Create ALL function signatures from the spec
2. Add type hints
3. Add docstrings
4. Each function should raise NotImplementedError("TODO: Implement in Green Phase")
5. Include necessary imports
6. Follow PEP 8 style

Output ONLY valid Python code.
"""

IMPLEMENTATION_TEMPLATE = """
Implement this code to pass the provided tests.

Test Code:
{test_code}

Skeleton Code:
{skkeleton}

Context from previous attempts:
{context}

Requirements:
1. Implement all functions marked with NotImplementedError
2. Follow the existing code style
3. Handle edge cases shown in tests
4. Ensure all tests pass
5. Use defensive programming

Output ONLY valid Python code with the complete implementation.
"""

FIX_GENERATION_TEMPLATE = """
Generate a code fix for this test failure.

Test Failure Context:
{failure_context}

Failing Code:
{failing_code}

Past Similar Failures (for learning):
{knowledge_kernel}

Output format (TOON):
patch[1]
{{
  file_path: "path/to/file.py",
  line_range: (start, end),
  old_code: "exact code to replace",
  new_code: "replacement code"
}}

Learn from past solutions if available.
"""

ADVERSARIAL_REVIEW_TEMPLATE = """
You are a security-focused code reviewer. Critically analyze this code for vulnerabilities.

Code to Review:
{code}

Quality Report:
{quality_report}

Focus Areas:
1. Input validation and sanitization
2. SQL injection, XSS, CSRF vulnerabilities
3. Authentication and authorization issues
4. Data exposure and privacy concerns
5. Error handling and information disclosure
6. Resource management (memory, file handles)
7. Race conditions and concurrency issues

Output findings in this TOON format:
[1] {severity, category, description, line_number, recommendation}
CRITICAL | SQL Injection | User input not sanitized | 42 | "Use parameterized queries"
"""

QUALITY_REVIEW_TEMPLATE = """
Review this code for quality issues.

Code:
{code}

Quality Metrics:
{quality_metrics}

Check for:
1. Code complexity > 12
2. Dead code or unreachable code
3. Duplicate code
4. Poor naming conventions
5. Missing type hints
6. Missing docstrings
7. Long functions (>100 lines)
8. Too many parameters (>7)

Output findings in TOON format:
[1] {severity, issue_type, description, line_number, suggestion}
"""

DOCUMENTATION_UPDATE_TEMPLATE = """
Generate documentation for this feature.

Implementation:
{implementation}

Tests:
{tests}

Quality Report:
{quality_report}

Generate:
1. Module docstring
2. Function docstrings
3. Usage examples
4. Edge case documentation

Output in Markdown format.
"""


class LLMClient:
    """Unified LLM interface for RRD workflow tasks"""

    def __init__(self, config: Optional[RRDConfig] = None):
        self.config = config
        self.parser = ToonParser()

        # Initialize base LLM client if available
        if BaseLLMClient:
            try:
                self.client = BaseLLMClient()
            except Exception:
                self.client = None
        else:
            self.client = None

    def generate_adversarial_tests(
        self, spec: str, codebase_analysis: Optional[CodebaseAnalysis] = None
    ) -> str:
        """Generate pytest tests from specification

        Args:
            spec: Feature specification
            codebase_analysis: Optional codebase structure for context

        Returns:
            Python test code as string
        """
        codebase_summary = ""
        if codebase_analysis:
            codebase_summary = str(codebase_analysis.structure)

        prompt = ADVERSARIAL_TEST_TEMPLATE.format(spec=spec, codebase_summary=codebase_summary)

        return self._call_llm(prompt)

    def generate_skeleton(self, spec: str, existing_code: Optional[str] = None) -> str:
        """Generate interface definitions only

        Args:
            spec: Feature specification
            existing_code: Optional existing code to extend

        Returns:
            Python skeleton code as string
        """
        existing = existing_code or ""
        prompt = SKELETON_TEMPLATE.format(spec=spec, existing_code=existing)

        return self._call_llm(prompt)

    def generate_implementation(
        self, test_code: str, skeleton: str, context: Optional[ActiveContext] = None
    ) -> str:
        """Generate implementation to pass tests

        Args:
            test_code: Test code to satisfy
            skeleton: Skeleton code with signatures
            context: Active context from previous attempts

        Returns:
            Python implementation code as string
        """
        context_str = ""
        if context:
            context_str = f"""
Previous attempts: {len(context.history)}
Recent failures: {[f.signature for f in context.history[-5:]]}
"""

        prompt = IMPLEMENTATION_TEMPLATE.format(
            test_code=test_code, skkeleton=skeleton, context=context_str
        )

        return self._call_llm(prompt)

    def generate_fix(
        self,
        failure_context: str,
        failing_code: str,
        knowledge_kernel: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[PatchToon]:
        """Generate code fix from test failure context

        Args:
            failure_context: Debug context from test failure
            failing_code: The code that is failing
            knowledge_kernel: Past similar failures for learning

        Returns:
            PatchToon object or None if no fix generated
        """
        kernel_str = ""
        if knowledge_kernel:
            kernel_str = "\n".join(
                [
                    f"- {k.get('signature', 'unknown')}: {k.get('solution', 'no solution')}"
                    for k in knowledge_kernel[-10:]
                ]
            )

        prompt = FIX_GENERATION_TEMPLATE.format(
            failure_context=failure_context,
            failing_code=failing_code,
            knowledge_kernel=kernel_str,
        )

        response = self._call_llm(prompt)

        try:
            parsed = self.parser.parse(response)
            if isinstance(parsed, list) and len(parsed) > 0:
                patch_data = parsed[0]
                return PatchToon(
                    file_path=patch_data.get("file_path", ""),
                    line_range=tuple(patch_data.get("line_range", [0, 0])),
                    old_code=patch_data.get("old_code", ""),
                    new_code=patch_data.get("new_code", ""),
                )
        except Exception:
            pass

        return None

    def adversarial_review(
        self, code: str, qa_report: Optional[QualityReport] = None
    ) -> List[Dict[str, Any]]:
        """Critic mode: find vulnerabilities

        Args:
            code: Code to review
            qa_report: Optional quality analysis

        Returns:
            List of security findings
        """
        qa_str = ""
        if qa_report:
            qa_str = str(qa_report.raw_output)

        prompt = ADVERSARIAL_REVIEW_TEMPLATE.format(code=code, quality_report=qa_str)

        response = self._call_llm(prompt)

        try:
            findings = self.parser.parse(response)
            if isinstance(findings, list):
                return findings
        except Exception:
            pass

        return []

    def quality_review(
        self, code: str, quality_metrics: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Review code for quality issues

        Args:
            code: Code to review
            quality_metrics: Optional complexity metrics

        Returns:
            List of quality issues
        """
        metrics_str = ""
        if quality_metrics:
            metrics_str = str(quality_metrics)

        prompt = QUALITY_REVIEW_TEMPLATE.format(code=code, quality_metrics=metrics_str)

        response = self._call_llm(prompt)

        try:
            issues = self.parser.parse(response)
            if isinstance(issues, list):
                return issues
        except Exception:
            pass

        return []

    def generate_documentation(
        self, implementation: str, tests: str, qa_report: Optional[QualityReport] = None
    ) -> str:
        """Generate documentation for feature

        Args:
            implementation: Implementation code
            tests: Test code
            qa_report: Optional quality analysis

        Returns:
            Markdown documentation
        """
        qa_str = ""
        if qa_report:
            qa_str = str(qa_report.raw_output)

        prompt = DOCUMENTATION_UPDATE_TEMPLATE.format(
            implementation=implementation, tests=tests, quality_report=qa_str
        )

        return self._call_llm(prompt)

    def _call_llm(self, prompt: str) -> str:
        """Call LLM and return response

        Args:
            prompt: Prompt to send to LLM

        Returns:
            LLM response as string
        """
        if self.client:
            try:
                return self.client.generate(prompt=prompt)
            except Exception as e:
                return f"Error calling LLM: {e}"
        else:
            # Mock response for testing
            return "# Mock LLM response\n# LLM client not configured"

    def generate(self, prompt: str, **kwargs) -> str:
        """Generic generate method

        Args:
            prompt: Prompt to send
            **kwargs: Additional arguments

        Returns:
            LLM response
        """
        return self._call_llm(prompt)
