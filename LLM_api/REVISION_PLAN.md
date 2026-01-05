# LLM_api Revision Plan

## Issue 1: Self-Correction in AgentEngine

### Problem
When tool execution fails (e.g., file edit failure due to old_content not found), the AgentEngine currently just returns the error message to the LLM. This doesn't provide the LLM with sufficient guidance to recover from the error.

### Solution
Modify the tool execution logic in `src/agent_engine.py` to detect tool execution failures and automatically inject a self-correction system prompt that instructs the LLM to:
1. Read the file content using `read_file` tool
2. Verify the current state
3. Retry the operation with corrected parameters

### Implementation Steps

#### Step 1: Detect Tool Execution Failures
- **File**: `src/agent_engine.py`
- **Location**: Lines 110-140 (tool execution loop)
- **Changes**:
  - Check if tool result contains error indicators (starts with "Error:", contains "Error:")
  - Track which tools failed and why

#### Step 2: Inject Self-Correction Prompt
- **File**: `src/agent_engine.py`
- **Location**: After tool execution (around line 140)
- **Changes**:
  - For file operation failures, insert a system message with self-correction instructions
  - Instructions should be context-specific based on the error type
  - Example prompts:
    - For edit_file failures: "The file edit failed because the old content was not found. Please use read_file to check the current file content, then retry the edit with the correct old_content."
    - For create_file failures: "File creation failed. The path may be invalid or permissions issue. Please verify and retry."
    - For remove_file failures: "File removal failed. The file may not exist or be locked. Please verify and retry."

#### Step 3: Add Configuration Option
- **File**: `src/agent_engine.py`
- **Location**: `__init__` method and `generate_agentic` signature
- **Changes**:
  - Add `enable_self_correction: bool = True` parameter
  - Allow disabling this feature if needed

### Code Changes

```python
# In tool execution loop (around line 122)
result = self.tool_manager.execute_tool(tool_name, arguments)

# Check for errors
if result.startswith("Error:") and enable_self_correction:
    # Generate context-specific correction prompt
    correction_prompt = self._generate_correction_prompt(tool_name, result, arguments)
    
    # Inject as system message
    messages.append({
        "role": "system",
        "content": correction_prompt
    })
    
    if verbose:
        print(f"Self-correction injected: {correction_prompt}")

# Add tool result to messages
messages.append({
    "role": "tool",
    "tool_call_id": tool_call["id"],
    "name": tool_name,
    "content": result
})
```

### Testing
- Test file edit with wrong old_content → should trigger self-correction
- Test file creation on invalid path → should trigger self-correction
- Test with `enable_self_correction=False` → should not inject prompts
- Verify LLM successfully recovers after reading file content

---

## Issue 2: Lazy Loading in providers.py

### Problem
Currently, `src/providers.py` imports all provider libraries (OpenAI, Anthropic) at the module level (lines 4-5). This means users must have all provider libraries installed even if they only use one.

### Solution
Remove top-level imports and move them into each provider client getter method (`_get_openai_client`, `_get_anthropic_client`, etc.) so only the selected provider's library needs to be installed.

### Implementation Steps

#### Step 1: Remove Top-Level Imports
- **File**: `src/providers.py`
- **Location**: Lines 4-5
- **Changes**:
  - Remove `from openai import OpenAI`
  - Remove `from anthropic import Anthropic`

#### Step 2: Update Type Hints
- **File**: `src/providers.py`
- **Location**: Lines 13-15 (client instance variables)
- **Changes**:
  - Change type hints to `Optional[Any]` or use string literals: `Optional['OpenAI']`
  - Or use `TYPE_CHECKING` import for type hints only

#### Step 3: Lazy Import in Client Getters
- **File**: `src/providers.py`
- **Location**: Client getter methods (lines 44-64)
- **Changes**:
  - Add import statements inside `_get_openai_client()`
  - Add import statements inside `_get_anthropic_client()`
  - Maintain error handling for missing imports

#### Step 4: Update Type Annotations
- **File**: `src/providers.py`
- **Location**: Lines 126, 150 (return type annotations)
- **Changes**:
  - Update method return types to use string literals or `Any`

### Code Changes

```python
# Remove top-level imports (lines 4-5)
# Delete these lines:
# from openai import OpenAI
# from anthropic import Anthropic

# Add TYPE_CHECKING import for type hints (optional)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from openai import OpenAI
    from anthropic import Anthropic

# Update instance variables (lines 13-15)
self._openai_client: Optional[Any] = None  # or Optional['OpenAI']
self._anthropic_client: Optional[Any] = None  # or Optional['Anthropic']
self._zai_client: Optional[Any] = None  # or Optional['OpenAI']

# Update _get_openai_client (lines 44-50)
def _get_openai_client(self) -> Any:  # or -> 'OpenAI'
    if self._openai_client is None:
        from openai import OpenAI  # Lazy import
        provider_config = self._get_provider_config('openai')
        api_key = os.getenv('OPENAI_API_KEY')
        base_url = provider_config.get('api_base') if provider_config else None
        self._openai_client = OpenAI(api_key=api_key, base_url=base_url)
    return self._openai_client

# Update _get_anthropic_client (lines 52-56)
def _get_anthropic_client(self) -> Any:  # or -> 'Anthropic'
    if self._anthropic_client is None:
        from anthropic import Anthropic  # Lazy import
        api_key = os.getenv('ANTHROPIC_API_KEY')
        self._anthropic_client = Anthropic(api_key=api_key)
    return self._anthropic_client

# Update _get_zai_client (lines 58-64)
def _get_zai_client(self) -> Any:  # or -> 'OpenAI'
    if self._zai_client is None:
        from openai import OpenAI  # Lazy import
        provider_config = self._get_provider_config('zai')
        api_key = os.getenv('ZAI_API_KEY')
        base_url = provider_config.get('api_base') if provider_config else None
        self._zai_client = OpenAI(api_key=api_key, base_url=base_url)
    return self._zai_client
```

### Testing
- Test with only OpenAI library installed → should work, no Anthropic import error
- Test with only Anthropic library installed → should work, no OpenAI import error
- Test with only Ollama library installed → should work, no other imports
- Test all providers together → should work as before
- Verify type hints still work correctly in IDEs

### Benefits
- Reduced dependencies for users who only use specific providers
- Faster import time (only imports what's needed)
- Better error messages (only see missing library errors for the provider you're trying to use)
- More flexible deployment in constrained environments

---

## Implementation Order

1. **Issue 2 first** (Lazy Loading) - Lower risk, independent changes
   - Modify `src/providers.py`
   - Test with individual providers

2. **Issue 1 second** (Self-Correction) - Requires careful testing
   - Modify `src/agent_engine.py`
   - Test various failure scenarios
   - Verify self-correction prompts work correctly

---

## Summary

| Issue | File | Lines | Priority | Risk |
|-------|------|-------|----------|------|
| Self-Correction | `src/agent_engine.py` | 110-140 | Medium | Medium |
| Lazy Loading | `src/providers.py` | 4-5, 13-15, 44-64 | High | Low |

Both issues improve robustness and user experience of the LLM_api system.
