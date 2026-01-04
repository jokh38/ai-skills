# LLM Client CLI

CLI tool for interacting with OpenAI, Anthropic, Ollama, and Z.AI with TOON format support and **agentic file operations**.

## Features

- Multi-provider support (OpenAI, Anthropic, Ollama, Z.AI GLM 4.7)
- Agentic Mode: Autonomous file creation, editing, deletion via tool calling
- Modular architecture with specialized managers
- TOON format support (~40% fewer tokens than JSON)
- GLM 4.7 thinking mode with preserved reasoning
- Configurable parameters (temperature, max tokens, model)
- Context injection from files

## Architecture

Modular design with specialized components:
- **llm_client.py**: Main orchestrator + CLI
- **src/providers.py**: Provider implementations (OpenAI, Anthropic, Ollama, ZAI)
- **src/tools.py**: File operation tools
- **src/agent_engine.py**: Agentic loop orchestration

`LLMClient` delegates to `ProviderManager`, `ToolManager`, and `AgentEngine` for clean separation of concerns.

## Installation

```bash
pip install openai anthropic ollama python-dotenv
```

### Configuration

Create `.env` file:

```bash
# API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
ZAI_API_KEY=...

# Defaults
DEFAULT_PROVIDER=ollama
DEFAULT_MODEL=GLM4.7
DEFAULT_TEMPERATURE=0.7
DEFAULT_MAX_TOKENS=4096

# Provider-specific models (optional)
OPENAI_MODEL=gpt-4-turbo
ANTHROPIC_MODEL=claude-3-opus-20240229
OLLAMA_MODEL=GLM4.7
ZAI_MODEL=glm-4.7
```

**Priority:** CLI args > `.env` > built-in defaults

Ollama (local): No API key needed. Run `ollama serve` first.

## Usage

```bash
python llm_client.py --prompt "Your prompt" [OPTIONS]
```

### Arguments

**Required:**
- `--prompt`: Prompt/question for the model

**Optional:**
- `--provider`: `openai` | `anthropic` | `ollama` | `zai`
- `--model`: Model name
- `--context`: Path to TOON/JSON context file
- `--temperature`: 0.0-2.0 (default: 0.7)
- `--max-tokens`: Max tokens to generate

**Agentic Mode:**
- `--agentic`: Enable file operations (create/edit/remove)
- `--max-iterations`: Max tool calls (default: 10)
- `--verbose`: Detailed tool execution logs
- `--enable-thinking/--disable-thinking`: GLM 4.7 thinking mode

## Examples

```bash
# Basic usage
python llm_client.py --prompt "Explain Python decorators"

# With context file
python llm_client.py --context "data.toon" --prompt "Analyze this"

# Specific provider
python llm_client.py --provider openai --model gpt-4 --prompt "Review this code"

# High temperature for creativity
python llm_client.py --temperature 1.2 --prompt "Generate function names"
```

## Agentic Mode

Enables LLMs to autonomously create, edit, and remove files via tool calling.

**File Tools:**
- `create_file` - Create new file
- `edit_file` - Edit existing file
- `remove_file` - Delete file
- `read_file` - Read file contents

```bash
# Create file
python llm_client.py --prompt "Create calculator.py" --agentic

# With verbose logging
python llm_client.py --prompt "Create project structure" --agentic --verbose

# Custom iteration limit
python llm_client.py --prompt "Complex multi-file setup" --agentic --max-iterations 20
```

**Provider Support:**
| Provider | Status | Thinking Mode |
|----------|--------|---------------|
| ZAI (GLM 4.7) | ✅ Recommended | ✅ Preserved Thinking |
| OpenAI | ✅ Supported | ❌ |
| Anthropic | 🚧 Planned | ❌ |
| Ollama | ⚠️ Limited | ❌ |

**Python API:**
```python
from tools.LLM_api import LLMClient

# Basic usage
client = LLMClient()
response = client.generate(prompt="Explain decorators", provider="openai")

# Agentic mode
result = client.generate_agentic(
    prompt="Create calculator.py", provider="zai", verbose=True
)
print(result['response'])

# Advanced: Direct manager access
from tools.LLM_api import ProviderManager, ToolManager, AgentEngine
provider_mgr = ProviderManager(client.config)
response = provider_mgr.generate("openai", [{"role": "user", "content": "Hello"}])
```

**Security:** Agentic mode has write access. Use in trusted environments.

## TOON Format Support

TOON (Token-Oriented Object Notation) uses ~40% fewer tokens than JSON.

**Example:**
```toon
[3] {id, name, status, error}
1 | AuthService | failed | Connection timeout
2 | DatabasePool | degraded | High latency
3 | CacheLayer | failed | Redis connection lost
```

**Usage:**
```bash
python llm_client.py --context "data.toon" --prompt "Analyze this data"
```

## Common Models

| Provider | Models | Context |
|----------|--------|---------|
| Z.AI | glm-4.7 (358B MoE) | 200K tokens, thinking mode |
| OpenAI | gpt-4, gpt-4-turbo, gpt-3.5-turbo | Standard |
| Anthropic | claude-3-opus, claude-3-sonnet, claude-3-haiku | Standard |
| Ollama | llama2, codellama, mistral, GLM4.7 | Varies |
## Troubleshooting

**Model not found (Ollama):**
```bash
ollama pull GLM4.7
```

**API key not set:**
```bash
echo $OPENAI_API_KEY  # Check environment variables
```

**Context file not found:** Use absolute paths: `--context "/full/path/to/file.toon"`

**Scripting:**
```bash
# Batch process files
for file in data/*.toon; do
  python llm_client.py --context "$file" --prompt "Summarize" > "output/$(basename $file .toon).txt"
done

# Pipeline
cat error.log | python llm_client.py --prompt "Analyze errors" --context /dev/stdin
```

