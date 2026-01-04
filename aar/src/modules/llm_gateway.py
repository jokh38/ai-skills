"""LLM gateway module for LLM communication and response validation

This is consolidated LLM interface that:
- Loads prompts from centralized prompts/ directory
- Supports multiple LLM providers via LLMClient
- Validates TOON format responses
- Handles retry logic with exponential backoff
"""

import logging
import time
import re
import os
from pathlib import Path
from typing import Optional, List

from modules.data_types import PatchToon, ActiveContext
from modules.toon_utils import ToonParser, ToonEncoder


logger = logging.getLogger(__name__)

# Import LLMClient from tools/LLM_api (REQUIRED)
_llm_tools_path = Path(__file__).parent.parent.parent / "tools"
_llm_api_path = _llm_tools_path / "LLM_api"
_env_file = _llm_api_path / ".env"

# Add tools path BEFORE importing
import sys
tools_str = str(_llm_tools_path.resolve())
if tools_str not in sys.path:
    sys.path.insert(0, tools_str)
    logger.debug(f"Added {tools_str} to sys.path")

# Load .env file from tools/LLM_api
try:
    from dotenv import load_dotenv
    if _env_file.exists():
        load_dotenv(dotenv_path=_env_file)
        logger.info(f"Loaded .env from {_env_file}")
except ImportError:
    logger.debug("python-dotenv not installed, .env file not loaded")
except Exception as e:
    logger.warning(f"Could not load .env file: {e}")

# Import LLMClient (REQUIRED - ARR cannot work without it)
try:
    from LLM_api.llm_client import LLMClient
except ImportError as e:
    raise ImportError(
        f"LLMClient is required but could not be imported from {_llm_api_path}. "
        f"Error: {e}\n"
        f"Please install required dependencies and ensure API key is configured."
    )


class LLMGateway:
    """LLM communication interface with TOON format validation

    This consolidated class handles:
    - Prompt template loading from prompts/ directory
    - LLM API communication (via LLMClient)
    - TOON format validation and parsing
    - Retry logic with exponential backoff
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 300,
        max_retries: int = 3,
    ):
        """
        Initialize LLM gateway

        Args:
            api_key: API key for LLM service (from env if None)
            model: Model identifier (from env if None)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts

        Raises:
            RuntimeError: If API key is not available
        """
        # Get credentials from environment if not provided
        self.api_key = api_key or self._get_api_key()

        if not self.api_key or self.api_key in ("mock_key", ""):
            raise RuntimeError(
                "API key is required. Please set ZAI_API_KEY, OPENAI_API_KEY, "
                "ANTHROPIC_API_KEY, or LLM_API_KEY environment variable."
            )

        self.model = model or os.getenv("DEFAULT_MODEL", "gpt-4")
        self.timeout = timeout
        self.max_retries = max_retries
        self.parser = ToonParser()
        self.encoder = ToonEncoder()

        # Prompt template cache
        self._prompt_cache: dict = {}
        self._prompts_dir = Path(__file__).parent.parent.parent / "prompts"

        # Initialize LLMClient (REQUIRED)
        try:
            self.llm_client = LLMClient()
            logger.info(f"Using LLMClient with model: {self.model}")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize LLMClient: {e}")

    def _get_api_key(self) -> str:
        """Get API key from environment variables"""
        return (
            os.getenv("ZAI_API_KEY") or
            os.getenv("OPENAI_API_KEY") or
            os.getenv("ANTHROPIC_API_KEY") or
            os.getenv("LLM_API_KEY") or
            ""
        )

    def load_prompt(self, prompt_id: str) -> str:
        """Load prompt template from prompts/ directory

        Args:
            prompt_id: Prompt identifier (e.g., "fix_request", "format_reminder")

        Returns:
            Prompt template string
        """
        if prompt_id in self._prompt_cache:
            return self._prompt_cache[prompt_id]

        prompt_file = self._prompts_dir / "repair_agent.toon"
        if not prompt_file.exists():
            logger.warning(f"Prompts file not found: {prompt_file}, using default")
            return self._get_default_prompt(prompt_id)

        try:
            content = prompt_file.read_text()
            # Simple TOON parsing for prompts
            prompts = self._parse_prompt_file(content)
            self._prompt_cache.update(prompts)
            return self._prompt_cache.get(prompt_id, self._get_default_prompt(prompt_id))
        except Exception as e:
            logger.warning(f"Failed to load prompt {prompt_id}: {e}")
            return self._get_default_prompt(prompt_id)

    def _parse_prompt_file(self, content: str) -> dict:
        """Parse TOON prompt file into dictionary"""
        prompts = {}
        current_key = None
        current_lines: List[str] = []
        in_multiline = False

        for line in content.split('\n'):
            stripped = line.strip()

            # Skip comments
            if stripped.startswith('#'):
                continue

            # Check for multiline start
            if stripped.endswith('|'):
                current_key = stripped.split(':')[0].strip()
                in_multiline = True
                current_lines = []
                continue

            # Collect multiline content
            if in_multiline:
                if line and not line[0].isspace() and ':' in line:
                    # End of multiline
                    prompts[current_key] = '\n'.join(current_lines)
                    in_multiline = False
                    current_key = None
                else:
                    # Strip common indent
                    current_lines.append(line.lstrip())
                    continue

            # Simple key: value
            if ':' in stripped and not stripped.endswith(':'):
                parts = stripped.split(':', 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip().strip('"')
                    prompts[key] = value

        # Handle last multiline block
        if in_multiline and current_key:
            prompts[current_key] = '\n'.join(current_lines)

        return prompts

    def _get_default_prompt(self, prompt_id: str) -> str:
        """Get default prompt if file not available"""
        defaults = {
            "fix_request": """You are an expert Python code repair agent. Analyze test failures and propose a fix.

Iteration: {{iteration}}

Active History (only unresolved issues):
{{active_history}}

Current Failures:
{{current_failures}}

================================================================================
CRITICAL INDENTATION RULES (PYTHON IS WHITESPACE-SENSITIVE):
================================================================================
1. PRESERVE EXACT indentation of original code
2. Use 4 spaces per indentation level (NOT tabs)
3. If old_code has 4 spaces indent, new_code MUST have 4 spaces indent
4. If old_code has 8 spaces indent, new_code MUST have 8 spaces indent
5. Count the leading spaces in old_code and use EXACTLY the same in new_code
6. DO NOT add extra indentation to new_code
7. DO NOT remove indentation from new_code

Example - CORRECT:
old_code:"    return x * y"      (4 spaces)
new_code:"    return x * y * 0.5" (4 spaces - SAME)

Example - WRONG:
old_code:"    return x * y"      (4 spaces)
new_code:"        return x * y * 0.5" (8 spaces - WRONG!)
================================================================================

IMPORTANT: Respond ONLY with a patch in TOON format. No explanations, no other text.

patch[1]
  {
    file_path:"path/to/file.py",
    line_range:(start_line,end_line),
    old_code:"exact code WITH EXACT INDENTATION",
    new_code:"replacement WITH SAME INDENTATION"
  }

Ensure old_code matches EXACTLY including all leading spaces.
Ensure new_code has SAME leading spaces as old_code.
""",
            "format_reminder": """IMPORTANT: Respond ONLY with a patch in TOON format.
REMEMBER: Preserve EXACT indentation - new_code must have same leading spaces as old_code!
No explanations. No markdown."""
        }
        return defaults.get(prompt_id, "")

    def generate(
        self,
        prompt: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        system_message: Optional[str] = None,
        messages: Optional[list] = None
    ) -> str:
        """Generate text using LLM

        Args:
            prompt: The prompt to send
            provider: LLM provider (openai, anthropic, zai, ollama)
            model: Model to use
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            system_message: Optional system message
            messages: Optional message history

        Returns:
            Generated text response
        """
        if self.llm_client is None:
            raise RuntimeError("LLMClient not available")

        response = self.llm_client.generate(
            prompt=prompt,
            provider=provider or os.getenv('DEFAULT_PROVIDER', 'openai'),
            model=model or self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system_message=system_message,
            messages=messages
        )

        # Handle response that might be a dict (from thinking-enabled models)
        if isinstance(response, dict):
            # Try to extract content from dict response
            if 'content' in response and response['content']:
                return response['content']
            elif 'reasoning_content' in response and response['reasoning_content']:
                return response['reasoning_content']
            else:
                # Last resort: try to find any string content
                for key in ['content', 'reasoning_content', 'message', 'text']:
                    if key in response and isinstance(response[key], str) and response[key]:
                        return response[key]
                return str(response)

        return response

    def request_fix(self, context: ActiveContext) -> PatchToon:
        """
        Request code fix from LLM with active context

        Args:
            context: Active context with filtered history

        Returns:
            PatchToon with proposed fix

        Raises:
            Exception: If request fails after retries
        """
        for attempt in range(self.max_retries):
            try:
                prompt = self._build_prompt(context)

                response = self.generate(
                    prompt=prompt,
                    provider=os.getenv('DEFAULT_PROVIDER', 'openai'),
                    model=self.model,
                    max_tokens=2000,
                    temperature=0.7
                )

                logger.debug(f"LLM Response (first 500 chars): {response[:500]}")
                logger.debug(f"Response length: {len(response)}")

                # Handle thinking-enabled responses (reasoning_content field)
                if isinstance(response, dict) and 'reasoning_content' in response:
                    # Extract actual content from reasoning_content
                    actual_content = response.get('reasoning_content', str(response))
                    logger.debug(f"Extracted content from reasoning_content (first 500 chars): {actual_content[:500]}")

                    if self.validate_toon_format(actual_content):
                        patch = self._parse_patch_response(actual_content)
                        return patch
                    else:
                        logger.warning(
                            f"TOON validation failed on attempt {attempt + 1}"
                        )
                elif self.validate_toon_format(response):
                    patch = self._parse_patch_response(response)
                    return patch
                else:
                    logger.warning(
                        f"TOON validation failed on attempt {attempt + 1}"
                    )
                    if attempt < self.max_retries - 1:
                        context = self._add_format_reminder(context)

            except Exception as e:
                logger.error(f"LLM request failed on attempt {attempt + 1}: {e}")
                if attempt == self.max_retries - 1:
                    raise

        raise RuntimeError(f"Failed to get valid response after {self.max_retries} attempts")

    def _build_prompt(self, context: ActiveContext) -> str:
        """Build LLM prompt from active context"""
        template = self.load_prompt("fix_request")

        # Replace template variables
        prompt = template.replace("{{iteration}}", str(context.iteration))
        prompt = prompt.replace("{{active_history}}", self._format_history(context.active_history))
        prompt = prompt.replace("{{current_failures}}", self._format_failures(context.current_failures))

        return prompt

    def _format_history(self, history: list) -> str:
        """Format history for prompt"""
        if not history:
            return "None"
        lines = []
        for entry in history:
            lines.append(f"  - {entry}")
        return "\n".join(lines)

    def _format_failures(self, failures: list) -> str:
        """Format failures for prompt"""
        if not failures:
            return "None"
        lines = []
        for fail in failures:
            lines.append(f"  - {fail}")
        return "\n".join(lines)

    def validate_toon_format(self, response: str) -> bool:
        """
        Validate TOON format response

        Args:
            response: LLM response text

        Returns:
            True if valid TOON, False otherwise
        """
        required_fields = ["file_path", "line_range", "old_code", "new_code"]

        # Check all required fields are present
        for field in required_fields:
            if field not in response:
                logger.debug(f"Missing required field: {field}")
                return False

        if "patch[" not in response:
            logger.debug("Missing 'patch[' marker")
            return False

        try:
            pattern = r'patch\[\d+\]\s*\{'
            if not re.search(pattern, response):
                logger.debug("Invalid patch structure")
                return False

            # Extract fields using regex to validate format
            file_match = re.search(r'file_path\s*:\s*"([^"]+)"', response)
            range_match = re.search(r'line_range\s*:\s*\((\d+|None)\s*,\s*(\d+|None)\)', response)
            old_match = re.search(r'old_code\s*:\s*"([^"]*(?:\\"[^"]*)*)"', response, re.DOTALL)
            new_match = re.search(r'new_code\s*:\s*"([^"]*(?:\\"[^"]*)*)"', response, re.DOTALL)

            if not all([file_match, range_match, old_match, new_match]):
                logger.debug("Could not extract all patch fields")
                return False

            return True
        except Exception as e:
            logger.debug(f"TOON parsing error: {e}")
            return False

    def _parse_patch_response(self, response: str) -> PatchToon:
        """
        Parse LLM response into PatchToon

        Args:
            response: LLM response text

        Returns:
            PatchToon object

        Raises:
            ValueError: If parsing fails
        """
        try:
            file_match = re.search(r'file_path:"([^"]+)"', response)
            range_match = re.search(r"line_range:\((\d+|None),(\d+|None)\)", response)
            old_match = re.search(r'old_code:"([^"]*)"', response, re.DOTALL)
            new_match = re.search(r'new_code:"([^"]*)"', response, re.DOTALL)

            if not all([file_match, range_match, old_match, new_match]):
                raise ValueError("Missing required patch fields")

            file_path = file_match.group(1) if file_match else ""
            start_line = int(range_match.group(1)) if range_match and range_match.group(1) != "None" else 1
            end_line = int(range_match.group(2)) if range_match and range_match.group(2) != "None" else 1
            old_code = old_match.group(1).replace("\\n", "\n") if old_match else ""
            new_code = new_match.group(1).replace("\\n", "\n") if new_match else ""

            return PatchToon(
                file_path=file_path,
                line_range=(start_line, end_line),
                old_code=old_code,
                new_code=new_code,
            )

        except Exception as e:
            logger.error(f"Failed to parse patch response: {e}")
            raise ValueError(f"Invalid patch format: {e}")

    def _add_format_reminder(self, context: ActiveContext) -> ActiveContext:
        """
        Add format reminder to context for retry

        Args:
            context: Original context

        Returns:
            Context with incremented iteration
        """
        context.iteration += 1
        return context

    def apply_retry_logic(
        self, context: ActiveContext, attempt: int
    ) -> None:
        """
        Apply retry logic with exponential backoff

        Args:
            context: Current context
            attempt: Attempt number
        """
        if attempt > 0:
            backoff = min(2 ** attempt, 60)
            logger.info(f"Retrying after {backoff}s backoff...")
            time.sleep(backoff)
