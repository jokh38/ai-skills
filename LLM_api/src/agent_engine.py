"""Agentic engine for LLM API - orchestrates tool calling loops"""
import json
from typing import Dict, Any, Optional, List


class AgentEngine:
    """Manages agentic loop orchestration with tool calling"""

    def __init__(self, provider_manager, tool_manager, config):
        self.provider_manager = provider_manager
        self.tool_manager = tool_manager
        self.config = config

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
        """
        Generate response with agentic tool calling support.

        Args:
            prompt: User prompt
            provider: LLM provider (openai, anthropic, ollama, zai)
            model: Model name
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation
            max_iterations: Maximum number of tool calling iterations
            tools: List of tool schemas (uses file tools if None)
            enable_thinking: Enable thinking mode for ZAI provider
            verbose: Print detailed execution logs

        Returns:
            Dictionary containing final response, tool calls, and conversation history
        """
        provider = provider or self.config.llm_settings.get('default_provider', 'ollama')
        tools = tools or self.tool_manager.get_file_tools_schema()

        messages = [{"role": "user", "content": prompt}]
        all_tool_calls = []
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            if verbose:
                print(f"\n=== Iteration {iteration} ===")
                print(f"Messages: {len(messages)}")

            # Generate response with tools
            if provider == 'zai':
                response_data = self.provider_manager._generate_zai_with_tools(
                    messages, model, max_tokens, temperature, tools, enable_thinking
                )
            elif provider == 'openai':
                response_data = self.provider_manager._generate_openai_with_tools(
                    messages, model, max_tokens, temperature, tools
                )
            else:
                # Fallback: generate without tools and try to parse JSON tool calls
                response_text = self.provider_manager.generate(
                    provider=provider,
                    messages=messages,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                return {
                    "response": response_text,
                    "tool_calls": all_tool_calls,
                    "messages": messages,
                    "iterations": iteration
                }

            # Check if there are tool calls
            if not response_data.get("tool_calls"):
                # No more tool calls, return final response
                final_message = response_data.get("message", "")
                messages.append({"role": "assistant", "content": final_message})

                if verbose:
                    print(f"Final response: {final_message}")

                return {
                    "response": final_message,
                    "tool_calls": all_tool_calls,
                    "messages": messages,
                    "iterations": iteration
                }

            # Execute tool calls
            tool_calls = response_data["tool_calls"]
            assistant_message = response_data.get("message", "")

            # Add assistant message with tool calls
            messages.append({
                "role": "assistant",
                "content": assistant_message or "Using tools...",
                "tool_calls": tool_calls
            })

            # Execute each tool call
            for tool_call in tool_calls:
                tool_name = tool_call["function"]["name"]
                try:
                    arguments = json.loads(tool_call["function"]["arguments"])
                except json.JSONDecodeError:
                    arguments = {}

                if verbose:
                    print(f"\nExecuting tool: {tool_name}")
                    print(f"Arguments: {arguments}")

                # Execute the tool
                result = self.tool_manager.execute_tool(tool_name, arguments)

                if verbose:
                    print(f"Result: {result}")

                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": tool_name,
                    "content": result
                })

                # Track tool calls
                all_tool_calls.append({
                    "name": tool_name,
                    "arguments": arguments,
                    "result": result
                })

        # Max iterations reached
        return {
            "response": "Maximum iterations reached",
            "tool_calls": all_tool_calls,
            "messages": messages,
            "iterations": iteration,
            "max_iterations_reached": True
        }
