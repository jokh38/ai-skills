import os
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from .config import ConfigLoader
    from .src import ProviderManager, ToolManager, AgentEngine
else:
    try:
        from .config import ConfigLoader
        from .src import ProviderManager, ToolManager, AgentEngine
    except ImportError:
        # Fallback to simple ConfigLoader definition
        class ConfigLoader:
            def __init__(self):
                self.llm_settings = {
                    'default_provider': os.getenv('DEFAULT_PROVIDER', 'openai'),
                    'timeout_seconds': int(os.getenv('TIMEOUT_SECONDS', '120')),
                }

            def get_llm_provider(self, provider_name: str) -> dict:
                if provider_name == 'openai':
                    return {
                        'model': os.getenv('OPENAI_MODEL', 'gpt-4-turbo'),
                        'api_base': os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1'),
                        'max_tokens': int(os.getenv('OPENAI_MAX_TOKENS', '4096')),
                    }
                elif provider_name == 'anthropic':
                    return {
                        'model': os.getenv('ANTHROPIC_MODEL', 'claude-3-opus-20240229'),
                        'max_tokens': int(os.getenv('ANTHROPIC_MAX_TOKENS', '4096')),
                    }
                elif provider_name == 'ollama':
                    return {
                        'model': os.getenv('OLLAMA_MODEL', 'GLM4.7'),
                        'api_base': os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'),
                        'max_tokens': int(os.getenv('OLLAMA_MAX_TOKENS', '2048')),
                    }
                elif provider_name == 'zai':
                    return {
                        'model': os.getenv('ZAI_MODEL', 'glm-4.7'),
                        'api_base': os.getenv('ZAI_BASE_URL', 'https://api.z.ai/api/coding/paas/v4'),
                        'max_tokens': int(os.getenv('ZAI_MAX_TOKENS', '4096')),
                        'thinking': os.getenv('ZAI_THINKING', 'true').lower() == 'true',
                    }
                return {}

            @property
            def prompts_file(self) -> str:
                return str(Path(__file__).parent / "prompts.toon")
        
        # Try to import from src as absolute import
        try:
            from src import ProviderManager, ToolManager, AgentEngine
        except ImportError:
            ProviderManager, ToolManager, AgentEngine = None, None, None


class LLMClient:
    """Main LLM client orchestrator - delegates to specialized managers"""

    def __init__(self, config: Optional[ConfigLoader] = None):
        self.config = config or ConfigLoader()
        self._prompts_file: Optional[str] = None

        # Initialize managers
        self.provider_manager = ProviderManager(self.config)
        self.tool_manager = ToolManager()
        self.agent_engine = AgentEngine(
            self.provider_manager,
            self.tool_manager,
            self.config
        )

    @property
    def prompts_file(self) -> str:
        if self._prompts_file:
            return self._prompts_file
        return self.config.prompts_file

    @prompts_file.setter
    def prompts_file(self, value: str):
        self._prompts_file = value

    # ==================== Delegation Methods ====================

    def generate(
        self,
        prompt: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        system_message: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """Generate text using specified provider"""
        provider = provider or self.config.llm_settings.get('default_provider', 'openai')
        messages = messages or [{"role": "user", "content": prompt}]

        return self.provider_manager.generate(
            provider=provider,
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system_message=system_message
        )

    def generate_with_schema(
        self,
        prompt: str,
        schema: Dict[str, Any],
        provider: Optional[str] = None,
        model: Optional[str] = None
    ) -> str:
        """Generate response following a JSON schema"""
        provider = provider or self.config.llm_settings.get('default_provider', 'openai')
        return self.provider_manager.generate_with_schema(prompt, schema, provider, model)

    def generate_agentic(
        self,
        prompt: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        max_iterations: int = 10,
        tools: Optional[List[Dict[str, Any]]] = None,
        enable_thinking: bool = True,
        verbose: bool = False
    ) -> Dict[str, Any]:
        """Generate response with agentic tool calling"""
        return self.agent_engine.generate_agentic(
            prompt=prompt,
            provider=provider,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            max_iterations=max_iterations,
            tools=tools,
            enable_thinking=enable_thinking,
            verbose=verbose
        )

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool by name"""
        return self.tool_manager.execute_tool(tool_name, arguments)

    def get_file_tools_schema(self) -> List[Dict[str, Any]]:
        """Get file operation tool schemas"""
        return self.tool_manager.get_file_tools_schema()

    # ==================== Prompt Management Methods ====================

    def load_prompt(self, prompt_id: str) -> str:
        """Load a prompt template from the prompts file"""
        prompts_file = Path(self.prompts_file)
        if not prompts_file.exists():
            raise FileNotFoundError(f"Prompts file not found: {prompts_file}")

        content = prompts_file.read_text()
        prompts = self._parse_toon_prompts(content)

        if prompt_id not in prompts:
            raise ValueError(f"Prompt ID not found: {prompt_id}")

        return prompts[prompt_id]

    def _parse_toon_prompts(self, content: Optional[str] = None) -> Dict[str, str]:
        """Parse TOON format prompts file."""
        if content is None:
            prompts_file = Path(self.prompts_file)
            if not prompts_file.exists():
                return {}
            content = prompts_file.read_text()

        prompts = {}
        current_section = None
        in_user_template = False
        parsing_row = False
        current_template_id = None
        current_template_parts = []

        for line in content.split('\n'):
            stripped = line.strip()

            if stripped.startswith('#') or not stripped:
                continue

            # Check for TOON format [N] {headers}
            if stripped.startswith('[') and ']' in stripped and '{' in stripped:
                parts = stripped.split(']')
                header_part = parts[0].replace('[', '')
                if header_part.isdigit():
                    headers = parts[1].strip('{}').split(',')
                    in_user_template = True
                    parsing_row = False
                    continue

            if stripped.endswith(':'):
                current_section = stripped[:-1]
                in_user_template = False
                parsing_row = False
                continue

            if in_user_template and '|' in stripped:
                parts = [p.strip() for p in stripped.split('|')]

                if len(parts) >= 2:
                    template_id = parts[0]
                    template_content = parts[1] if len(parts) > 1 else ''

                    if template_content and template_content.startswith('"'):
                        template_content = template_content.strip('"')
                    elif template_content and template_content.endswith('"'):
                        template_content = template_content.strip('"')

                    if template_content and template_content not in ['phase', 'user_template', 'required_vars', 'output_schema', 'notes']:
                        prompts[template_id] = template_content

        return prompts

    def render_prompt(self, prompt_id_or_template: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Render a prompt template with context variables"""
        context = context or {}

        try:
            prompt_template = self.load_prompt(prompt_id_or_template)
        except (FileNotFoundError, ValueError):
            prompt_template = prompt_id_or_template

        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"
            prompt_template = prompt_template.replace(placeholder, str(value))

        return prompt_template


# ==================== CLI Interface ====================

def main():
    import argparse

    # Load environment variables from .env file
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).parent / '.env'
        load_dotenv(dotenv_path=env_path)
    except ImportError:
        print("Warning: python-dotenv not installed. Install with: pip install python-dotenv")
    except Exception as e:
        print(f"Warning: Could not load .env file: {e}")

    # Get defaults from environment variables
    default_provider = os.getenv('DEFAULT_PROVIDER', 'ollama')
    default_model = os.getenv('DEFAULT_MODEL', None)
    default_temperature = float(os.getenv('DEFAULT_TEMPERATURE', '0.7'))
    default_max_tokens = os.getenv('DEFAULT_MAX_TOKENS', None)
    if default_max_tokens:
        default_max_tokens = int(default_max_tokens)

    parser = argparse.ArgumentParser(description='LLM Client CLI with Agentic Mode')
    parser.add_argument('--model', type=str, default=default_model,
                        help=f'Model name to use (default: {default_model or "from config"})')
    parser.add_argument('--context', type=str, help='Path to TOON context file')
    parser.add_argument('--prompt', type=str, required=True, help='Prompt to send to the model')
    parser.add_argument('--provider', type=str, default=default_provider,
                        help=f'LLM provider (openai, anthropic, ollama, zai) (default: {default_provider})')
    parser.add_argument('--temperature', type=float, default=default_temperature,
                        help=f'Temperature for generation (default: {default_temperature})')
    parser.add_argument('--max-tokens', type=int, default=default_max_tokens,
                        help=f'Maximum tokens to generate (default: {default_max_tokens or "from config"})')

    # Agentic mode arguments
    parser.add_argument('--agentic', action='store_true',
                        help='Enable agentic mode with tool calling (file operations)')
    parser.add_argument('--max-iterations', type=int, default=10,
                        help='Maximum iterations for agentic mode (default: 10)')
    parser.add_argument('--verbose', action='store_true',
                        help='Print detailed execution logs in agentic mode')
    parser.add_argument('--enable-thinking', action='store_true', default=True,
                        help='Enable thinking mode for ZAI provider (default: True)')
    parser.add_argument('--disable-thinking', action='store_true',
                        help='Disable thinking mode for ZAI provider')

    args = parser.parse_args()

    # Initialize client
    try:
        client = LLMClient()
    except Exception:
        # If config fails, create without config
        client = LLMClient.__new__(LLMClient)
        client.config = ConfigLoader()
        client._prompts_file = None
        client.provider_manager = ProviderManager(client.config)
        client.tool_manager = ToolManager()
        client.agent_engine = AgentEngine(
            client.provider_manager,
            client.tool_manager,
            client.config
        )

    # Read context file if provided
    context_content = ""
    if args.context:
        context_path = Path(args.context)
        if not context_path.exists():
            print(f"Error: Context file not found: {args.context}")
            return 1
        context_content = context_path.read_text()

    # Construct the full prompt
    full_prompt = args.prompt
    if context_content:
        full_prompt = f"{args.prompt}\n\nContext:\n{context_content}"

    # Determine if thinking should be enabled
    enable_thinking = args.enable_thinking and not args.disable_thinking

    # Generate response
    try:
        if args.agentic:
            # Agentic mode with tool calling
            result = client.generate_agentic(
                prompt=full_prompt,
                provider=args.provider,
                model=args.model,
                temperature=args.temperature,
                max_tokens=args.max_tokens,
                max_iterations=args.max_iterations,
                enable_thinking=enable_thinking,
                verbose=args.verbose
            )

            # Print results
            print("\n" + "="*60)
            print("AGENTIC MODE RESULTS")
            print("="*60)
            print(f"\nFinal Response:\n{result['response']}")
            print(f"\nIterations: {result['iterations']}")

            if result.get('tool_calls'):
                print(f"\nTool Calls Made: {len(result['tool_calls'])}")
                for i, tool_call in enumerate(result['tool_calls'], 1):
                    print(f"\n  {i}. {tool_call['name']}")
                    print(f"     Arguments: {tool_call['arguments']}")
                    print(f"     Result: {tool_call['result']}")

            if result.get('max_iterations_reached'):
                print("\n⚠️  Warning: Maximum iterations reached")

            return 0
        else:
            # Standard mode (text-only)
            response = client.generate(
                prompt=full_prompt,
                provider=args.provider,
                model=args.model,
                temperature=args.temperature,
                max_tokens=args.max_tokens
            )
            print(response)
            return 0
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
