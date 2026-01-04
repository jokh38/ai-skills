---
name: zgit
description: Context-preserving git commits using zagi with automatic context storage via --prompt flag
supported-languages: all
interactive: true
stream-output: true
allowed-tools: Bash(zagi:*), Bash(git:*), Bash(python:*)
---

# Zagi-Assisted Context-Preserving Commit

Creates a git commit using zagi with automatic context preservation via the `--prompt` flag.

## How to Invoke This Skill

When the user requests a commit (e.g., "commit the changes", "create a commit", "/zgit"):

### 1. Navigate to Skill Directory
```bash
cd /home/vscode/.claude/skills/zgit
```

### 2. Run the Zgit Commit Script
```bash
python zgit.py [OPTIONS]
```

**Command Options:**
- `--context "text"` or `-c "text"`: Context/reason for changes (non-interactive mode)
- `--message "text"` or `-m "text"`: Custom commit message (optional, defaults to context)
- `--stage` or `-s`: Automatically stage all files without prompting

**Examples:**
```bash
# Interactive mode (prompts for context)
python zgit.py

# Non-interactive mode with context
python zgit.py --context "Add error handling for network timeouts" --stage

# Custom message and context
python zgit.py --context "Refactor auth module" --message "Refactor: simplify authentication flow"
```

## Description

This skill provides an interactive workflow for creating git commits with zagi that preserve the original context and reasoning behind code changes. It:

1. **Checks git repository** - Auto-initializes if not already a git repository
2. **Displays current git status** - Shows what files have been modified
3. **Prompts for context** - Asks you to describe what you're trying to accomplish (the user's intent/request)
4. **Stages changes** - Optionally stages unstaged files
5. **Generates commit message** - Suggests an appropriate message based on the changes
6. **Creates commit with context** - Uses zagi's `--prompt` flag to preserve the original context for future reference

## Requirements

- **zagi** must be installed and initialized (`curl -fsSL zagi.sh/install | sh`)
- Git repository (auto-initializes if not present)
- Environment variable `ZAGI_AGENT=claude-code` should be set for agent mode

## Features

- **Auto Git Init**: Automatically initializes git repository if not present
- **Context Preservation**: The original user request is stored with `git log --prompts`
- **Guardrails**: Zagi prevents destructive operations when in agent mode
- **AI-Optimized**: Zagi's output is designed to fit in AI context windows efficiently
- **Co-author Stripping**: Automatically removes Co-Authored-By lines (optional via `ZAGI_STRIP_COAUTHORS=1`)

## Example Workflow

```bash
$ cd /home/vscode/.claude/skills/zgit
$ python zgit.py

==================================================
🚀 Zagi-Assisted Context-Preserving Commit
==================================================

📝 Current Git Status:
----------------------------------------
  M  src/main.py
  M  README.md

🤔 Describe the context for these changes:
   (What are you trying to accomplish?)
→ Add error handling for network timeouts

📋 Changed files: 2 file(s)

✨ Commit Message: Add error handling for network timeouts
📌 Context: Add error handling for network timeouts

💾 Creating commit with zagi...
[main abc1234] Add error handling for network timeouts
 2 files changed, 24 insertions(+), 5 deletions(-)

✅ Commit created successfully!
📖 View context later with: git log --prompts

📝 Commit details:
abc1234 Add error handling for network timeouts

==================================================
✨ Done!
==================================================
```

## Environment Setup

To enable agent-specific features (including the `--prompt` requirement):

```bash
export ZAGI_AGENT=claude-code
readonly ZAGI_AGENT
```

To automatically strip Co-Authored-By lines:

```bash
export ZAGI_STRIP_COAUTHORS=1
```

## When to Use This Skill

Use when you need to:
- ✅ **Create git commits** - Standard commit workflow with context preservation
- ✅ **Preserve user intent** - Store the original request/context with the commit
- ✅ **Agent-friendly commits** - Optimized for AI agents with guardrails
- ✅ **Review context later** - Use `git log --prompts` to see original context

**Don't use for:**
- ❌ Emergency rollbacks (use git directly)
- ❌ Amending commits (use git directly)
- ❌ Interactive rebases (use git directly)

## Implementation Files

```
zgit/
├── SKILL.md              # This file (skill documentation and configuration)
└── zgit.py               # Main entry point (interactive commit workflow)
```

## More Information

- [Zagi GitHub Repository](https://github.com/mattzcarey/zagi)
- Zagi is optimized for AI agents with 121 git-compatible commands
- Output is ~50% smaller to fit better in AI context windows
- Performance is 1.5-2x faster than traditional git
