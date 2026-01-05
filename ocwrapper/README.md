# OpenCode Python Wrapper Examples

Examples of using OpenCode in agentic mode from Python subprocess to create files autonomously.

## Overview

OpenCode's **agentic mode** is the default behavior where the AI agent autonomously uses tools (file operations, bash commands, etc.) to complete tasks. Instead of just returning text, it creates, edits, and modifies files directly in your workspace.

## Files

- `basic_usage.py` - Simple examples of using OpenCode from Python
- `advanced_usage.py` - Advanced examples with error handling and batch processing

## Key Command and Flags

- **`opencode run [message..]`**: Run OpenCode with a message/prompt non-interactively
- **`--agent`**: Agent to use (e.g., "plan", "build")
- **`-m, --model`**: Model to use in format provider/model (e.g., "anthropic/claude-sonnet-4.5")
- **`-f, --file`**: Attach file(s) to provide context (can be specified multiple times)
- **`-s, --session`**: Continue from a specific session ID
- **`--print-logs`**: Print verbose logs to stderr
- **`--format`**: Output format: "default" (formatted) or "json" (raw JSON events)

## Common Tools

- `Write` - Create new files
- `Edit` - Modify existing files
- `Read` - Read file contents
- `Bash` - Execute shell commands
- `Glob` - File pattern matching
- `Grep` - Search file contents
- `WebFetch` - Fetch web content
- `WebSearch` - Search the web

## Usage Examples

### Basic Usage

```python
import subprocess

subprocess.run([
    "opencode", "run",
    "Create a hello.py file with a simple hello world function"
], check=True)
```

### With Custom Agent

```python
# Use the plan agent for planning tasks
subprocess.run([
    "opencode", "run",
    "--agent", "plan",
    "Create an implementation plan for the authentication module"
], check=True)
```

### With Specific Model

```python
# Use a specific model
subprocess.run([
    "opencode", "run",
    "--model", "anthropic/claude-sonnet-4.5",
    "Refactor the authentication module"
], check=True)
```

### With File Attachments

```python
# Attach files for context
subprocess.run([
    "opencode", "run",
    "--file", "api_schema.yaml",
    "--file", "README.md",
    "Generate API client code based on the schema"
], check=True)
```

### With Error Handling

```python
from advanced_usage import run_opencode_task

success = run_opencode_task(
    "Create a FastAPI app in main.py with a health check endpoint",
    agent="build"
)

if success:
    print("Task completed successfully!")
else:
    print("Task failed!")
```

### Batch Processing

```python
from advanced_usage import batch_tasks

tasks = [
    {"prompt": "Create a README.md"},
    {"prompt": "Create a .gitignore for Python"},
    {"prompt": "Create requirements.txt with common dependencies"}
]

results = batch_tasks(tasks)
print(f"Completed: {results['success']}/{len(tasks)}")
```

## Important Notes

1. **Command Syntax**: Use `opencode run "prompt"` for non-interactive execution
2. **Argument Order**: Options/flags should come before the prompt message
3. **Working Directory**: OpenCode creates files in the current working directory unless specified
4. **Error Handling**: Always use try/except or check return codes when running from Python
5. **Tool Restrictions**: Configure via agent config files in `.opencode/agents/`, not CLI flags
6. **Agents**: Use `--agent` to select different agents (e.g., "plan" for planning, "build" for coding)

## References

- [OpenCode Agents Documentation](https://opencode.ai/docs/agents/)
- [OpenCode CLI Documentation](https://opencode.ai/docs/cli/)
- [OpenCode GitHub](https://github.com/opencode-ai/opencode)
