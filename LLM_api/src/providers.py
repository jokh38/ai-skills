"""Provider management for LLM API - handles multiple LLM providers"""
import os
from typing import Dict, Any, Optional, List, Union
from openai import OpenAI
from anthropic import Anthropic


class ProviderManager:
    """Manages LLM provider clients and generation methods"""

    def __init__(self, config):
        self.config = config
        self._openai_client: Optional[OpenAI] = None
        self._anthropic_client: Optional[Anthropic] = None
        self._zai_client: Optional[OpenAI] = None

    # ==================== Helper Methods ====================

    def _get_provider_config(self, provider_name: str) -> dict:
        return self.config.get_llm_provider(provider_name) or {}

    def _resolve_model_params(
        self,
        model: Optional[str],
        max_tokens: Optional[int],
        provider_config: dict,
        default_model: str,
        default_max_tokens: int
    ) -> tuple[str, int]:
        resolved_model = model or provider_config.get('model', default_model)
        resolved_max_tokens = max_tokens or provider_config.get('max_tokens', default_max_tokens)
        return resolved_model, resolved_max_tokens

    def _prepend_system_message(self, messages: List[Dict[str, str]], system_message: Optional[str]) -> List[Dict[str, str]]:
        if system_message:
            return [{"role": "system", "content": system_message}] + messages
        return messages

    def _get_timeout(self) -> int:
        return self.config.llm_settings.get('timeout_seconds', 120)

    # ==================== Provider Client Getters ====================

    def _get_openai_client(self) -> OpenAI:
        if self._openai_client is None:
            provider_config = self._get_provider_config('openai')
            api_key = os.getenv('OPENAI_API_KEY')
            base_url = provider_config.get('api_base') if provider_config else None
            self._openai_client = OpenAI(api_key=api_key, base_url=base_url)
        return self._openai_client

    def _get_anthropic_client(self) -> Anthropic:
        if self._anthropic_client is None:
            api_key = os.getenv('ANTHROPIC_API_KEY')
            self._anthropic_client = Anthropic(api_key=api_key)
        return self._anthropic_client

    def _get_zai_client(self) -> OpenAI:
        if self._zai_client is None:
            provider_config = self._get_provider_config('zai')
            api_key = os.getenv('ZAI_API_KEY')
            base_url = provider_config.get('api_base') if provider_config else None
            self._zai_client = OpenAI(api_key=api_key, base_url=base_url)
        return self._zai_client

    def _get_ollama_client(self):
        try:
            import ollama
            return ollama
        except ImportError:
            raise ImportError("Ollama library not installed. Install with: pip install ollama")

    # ==================== Main Generation Method ====================

    def generate(
        self,
        provider: str,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        system_message: Optional[str] = None,
        tools: Optional[List[Dict]] = None
    ) -> Union[str, Dict[str, Any]]:
        """
        Route generation request to appropriate provider

        Args:
            provider: Provider name (openai, anthropic, ollama, zai)
            messages: Conversation messages
            model: Optional model override
            max_tokens: Optional max tokens override
            temperature: Temperature for generation
            system_message: Optional system message
            tools: Optional tools for tool calling

        Returns:
            Generated text or dict with tool calls
        """
        if provider == 'openai':
            if tools:
                return self._generate_openai_with_tools(messages, model, max_tokens, temperature, tools)
            return self._generate_openai(messages, model, max_tokens, temperature, system_message)
        elif provider == 'anthropic':
            return self._generate_anthropic(messages, model, max_tokens, temperature, system_message)
        elif provider == 'ollama':
            return self._generate_ollama(messages, model, max_tokens, temperature, system_message)
        elif provider == 'zai':
            if tools:
                enable_thinking = self._get_provider_config('zai').get('thinking', True)
                return self._generate_zai_with_tools(messages, model, max_tokens, temperature, tools, enable_thinking)
            return self._generate_zai(messages, model, max_tokens, temperature, system_message)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    # ==================== Provider-Specific Generation ====================

    def _generate_openai(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        system_message: Optional[str] = None
    ) -> str:
        client = self._get_openai_client()
        provider_config = self._get_provider_config('openai')
        model, max_tokens = self._resolve_model_params(model, max_tokens, provider_config, 'gpt-4-turbo', 4096)
        timeout = self._get_timeout()

        messages = self._prepend_system_message(messages, system_message)

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout
        )
        return response.choices[0].message.content

    def _generate_anthropic(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        system_message: Optional[str] = None
    ) -> str:
        client = self._get_anthropic_client()
        provider_config = self._get_provider_config('anthropic')
        model, max_tokens = self._resolve_model_params(model, max_tokens, provider_config, 'claude-3-opus-20240229', 4096)
        timeout = self._get_timeout()

        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=messages,
            temperature=temperature,
            timeout=timeout,
            system=system_message
        )
        for block in response.content:
            if hasattr(block, 'text'):
                return block.text
        return ""

    def _generate_ollama(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        system_message: Optional[str] = None
    ) -> str:
        ollama = self._get_ollama_client()
        provider_config = self._get_provider_config('ollama')
        model, max_tokens = self._resolve_model_params(model, max_tokens, provider_config, 'GLM4.7', 2048)

        messages = self._prepend_system_message(messages, system_message)

        response = ollama.chat(
            model=model,
            messages=messages,
            options={
                "num_predict": max_tokens,
                "temperature": temperature
            }
        )
        return response['message']['content']

    def _generate_zai(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 1.0,
        system_message: Optional[str] = None,
        thinking: Optional[bool] = None
    ) -> str:
        client = self._get_zai_client()
        provider_config = self._get_provider_config('zai')
        model, max_tokens = self._resolve_model_params(model, max_tokens, provider_config, 'glm-4.7', 4096)
        timeout = self._get_timeout()

        messages = self._prepend_system_message(messages, system_message)

        params = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "timeout": timeout
        }

        enable_thinking = thinking if thinking is not None else provider_config.get('thinking', True)
        if enable_thinking:
            params["extra_body"] = {"thinking": {"type": "enabled"}}
        else:
            params["extra_body"] = {"thinking": {"type": "disabled"}}

        response = client.chat.completions.create(**params)
        
        # Handle thinking responses that might have different structure
        if hasattr(response.choices[0].message, 'content') and response.choices[0].message.content:
            return response.choices[0].message.content
        elif hasattr(response, 'model_dump'):
            # Debug: log full response if content is None
            import sys
            print(f"[DEBUG] Full response: {response.model_dump()}", file=sys.stderr)
            return response.model_dump_json()
        else:
            return str(response)

    # ==================== Schema-Based Generation ====================

    def generate_with_schema(
        self,
        prompt: str,
        schema: Dict[str, Any],
        provider: str,
        model: Optional[str] = None
    ) -> str:
        """Generate response following a JSON schema"""
        if provider == 'openai':
            return self._generate_openai_schema(prompt, schema, model)
        else:
            import json
            json_prompt = f"{prompt}\n\nRespond with valid JSON that follows this schema:\n{json.dumps(schema, indent=2)}"
            messages = [{"role": "user", "content": json_prompt}]
            return self.generate(provider, messages, model=model)

    def _generate_openai_schema(
        self,
        prompt: str,
        schema: Dict[str, Any],
        model: Optional[str] = None
    ) -> str:
        client = self._get_openai_client()
        provider_config = self._get_provider_config('openai')
        model, _ = self._resolve_model_params(model, None, provider_config, 'gpt-4-turbo', 4096)

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content

    # ==================== Tool Calling Methods ====================

    def _generate_zai_with_tools(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 1.0,
        tools: Optional[List[Dict[str, Any]]] = None,
        enable_thinking: bool = True
    ) -> Dict[str, Any]:
        """Generate response with ZAI provider supporting tool calls."""
        client = self._get_zai_client()
        provider_config = self._get_provider_config('zai')
        model, max_tokens = self._resolve_model_params(model, max_tokens, provider_config, 'glm-4.7', 4096)
        timeout = self._get_timeout()

        params = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "timeout": timeout
        }

        # Add tools if provided
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"

        # Enable preserved thinking for agentic tasks
        if enable_thinking:
            params["extra_body"] = {
                "thinking": {"type": "enabled"},
                "chat_template_kwargs": {
                    "enable_thinking": True,
                    "clear_thinking": False  # Preserve thinking across turns
                }
            }

        response = client.chat.completions.create(**params)

        # Parse response
        choice = response.choices[0]
        message = choice.message

        result = {
            "message": message.content or "",
            "tool_calls": []
        }

        # Extract tool calls if present
        if hasattr(message, 'tool_calls') and message.tool_calls:
            result["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in message.tool_calls
            ]

        return result

    def _generate_openai_with_tools(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Generate response with OpenAI provider supporting tool calls."""
        client = self._get_openai_client()
        provider_config = self._get_provider_config('openai')
        model, max_tokens = self._resolve_model_params(model, max_tokens, provider_config, 'gpt-4-turbo', 4096)
        timeout = self._get_timeout()

        params = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "timeout": timeout
        }

        # Add tools if provided
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"

        response = client.chat.completions.create(**params)

        # Parse response
        choice = response.choices[0]
        message = choice.message

        result = {
            "message": message.content or "",
            "tool_calls": []
        }

        # Extract tool calls if present
        if hasattr(message, 'tool_calls') and message.tool_calls:
            result["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in message.tool_calls
            ]

        return result
