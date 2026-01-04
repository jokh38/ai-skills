"""Configuration loader for LLM API"""
import os
from pathlib import Path
from typing import Dict, Any


class ConfigLoader:
    """Load configuration for LLM providers"""
    
    def __init__(self):
        self.llm_settings = {
            'default_provider': os.getenv('DEFAULT_PROVIDER', 'openai'),
            'timeout_seconds': 120,
        }
    
    def get_llm_provider(self, provider_name: str) -> Dict[str, Any]:
        """Get provider configuration
        
        Args:
            provider_name: Name of the provider (openai, anthropic, ollama, zai)
        
        Returns:
            Dictionary with provider configuration
        """
        if provider_name == 'openai':
            return {
                'model': os.getenv('OPENAI_MODEL', 'gpt-4-turbo'),
                'api_base': os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1'),
                'max_tokens': 4096,
            }
        elif provider_name == 'anthropic':
            return {
                'model': os.getenv('ANTHROPIC_MODEL', 'claude-3-opus-20240229'),
                'max_tokens': 4096,
            }
        elif provider_name == 'ollama':
            return {
                'model': os.getenv('OLLAMA_MODEL', 'GLM4.7'),
                'max_tokens': 2048,
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
        """Path to prompts file"""
        return str(Path(__file__).parent / "prompts.toon")
