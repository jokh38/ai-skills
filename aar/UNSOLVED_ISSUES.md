# ARR Unresolved Issues & Future Enhancements

## Executive Summary

This document documents unresolved issues in the ARR (Adaptive Recursive Repair Agent) system and explores how GLM4.7's agentic mode with file operation tools can address them.

---

## 1. Critical Issues

### 1.1 Path Resolution Bug

**Severity:** High
**Status:** Partially Worked Around

#### Problem Description
When `arr.py repair` is executed from one directory but pytest runs from a different working directory, patch application fails due to path mismatches.

#### Reproduction Steps
```bash
cd ARR/
python arr.py repair sample_test_project/test_calculator.py
# Error: "Target file not found: calculator.py"
```

#### Root Cause Analysis

**Location:** `src/modules/patch_manager.py` line 37-41
```python
def apply_patch(self, patch: PatchToon) -> bool:
    target_path = Path(patch.file_path)
    if not target_path.exists():
        logger.error(f"Target file not found: {target_path}")
        return False
```

**Issue:** The `patch.file_path` is generated with absolute paths in `_call_llm_mock()`, but pytest execution context may have a different CWD, causing the patch manager to fail file existence checks.

**Affected Components:**
- `modules/llm_gateway.py:_call_llm_mock()` - Generates paths
- `modules/patch_manager.py:apply_patch()` - Validates paths
- `modules/agent_orchestrator.py:_run_iteration()` - Orchestrates the flow

#### Current Workaround
Manually ensure file paths are absolute during mock LLM generation.

#### Recommended Solution with Agentic Mode

GLM4.7's agentic mode can use file tools to resolve this:

```python
# Enhanced patch generation using agentic tools
tools = [
    {
        "type": "function",
        "function": {
            "name": "resolve_file_path",
            "description": "Resolve relative to absolute file path based on project context",
            "parameters": {
                "type": "object",
                "properties": {
                    "relative_path": {"type": "string"},
                    "context_dir": {"type": "string"}
                },
                "required": ["relative_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "verify_file_exists",
            "description": "Verify a file exists at the given path",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"}
                },
                "required": ["file_path"]
            }
        }
    }
]

# Usage in repair flow
result = self.llm_client.generate_agentic(
    prompt=f"""
    The target file is: {test_file}
    Current working directory: {os.getcwd()}
    The imported module is: {import_module}

    Use file tools to:
    1. Verify the correct file path
    2. Check if the file exists
    3. Read the file content to generate accurate patches
    """,
    provider='zai',
    model='glm-4.7',
    enable_thinking=True,
    tools=tools,
    verbose=True
)
```

**Benefits:**
- LLM can actively verify file paths before generating patches
- Automatic resolution of relative vs absolute paths
- Self-correcting behavior when path resolution fails

---

### 1.2 Cycle Detection Over-Aggressiveness

**Severity:** Medium
**Status:** Unresolved

#### Problem Description
The cycle detector terminates sessions prematurely when encountering similar patches, even if they might be different approaches to fixing the same issue.

#### Reproduction Steps
```bash
[INFO] Found 6 failures
[WARNING] Duplicate patch detected, terminating session
```

#### Root Cause Analysis

**Location:** `src/modules/cycle_detector.py` line 25-43
```python
def check_duplicate_patch(self, patch: PatchToon) -> bool:
    current_hash = hash(str(patch))
    if self.state.last_patch_hash is not None:
        is_duplicate = current_hash == self.state.last_patch_hash
        self.state.last_patch_hash = current_hash
        return is_duplicate
```

**Issue:** Simple hash comparison doesn't distinguish between:
- Different fixes to the same line with different approaches
- Patches that look similar but have different `new_code` values
- Legitimate retry attempts after partial fixes

#### Recommended Solution with Agentic Mode

Use GLM4.7's semantic understanding to detect actual cycles vs legitimate retries:

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "analyze_patch_diversity",
            "description": "Analyze if patches are semantically different despite being in similar locations",
            "parameters": {
                "type": "object",
                "properties": {
                    "previous_patches": {"type": "array", "items": {"type": "string"}},
                    "current_patch": {"type": "string"}
                },
                "required": ["previous_patches", "current_patch"]
            }
        }
    }
]

# LLM can determine semantic differences
result = self.llm_client.generate_agentic(
    prompt="""
    Previous repair attempts:
    {patch_history}

    Current proposed patch:
    {current_patch}

    Analyze if this represents a new approach or a cycle.
    Consider:
    - Is the new_code semantically different from previous attempts?
    - Does this address a different aspect of the bug?
    - Is this a refinement of a previous approach?

    Return: "NEW_APPROACH" or "CYCLE_DETECTED"
    """,
    enable_thinking=True,
    tools=tools
)
```

---

## 2. Moderate Issues

### 2.1 Type Checking Errors

**Severity:** Low
**Status:** Unresolved

#### Problem Description
Type checker reports errors for optional types in `agent_orchestrator.py`.

#### Errors
```
ERROR [160:34] "recorder" is not a known attribute of "None"
ERROR [179:47] "pruner" is not a known attribute of "None"
ERROR [183:24] Operator "/" not supported for "None"
```

#### Root Cause Analysis

**Location:** `src/agent_orchestrator.py` lines 159-263

The `history_manager` is typed as `HistoryManager | None` but used without null checks:

```python
self.history_manager: HistoryManager | None = None
# Later used without check:
self.history_manager.recorder.append_log(...)  # Error: None has no 'recorder'
```

#### Recommended Solution

Add proper type guards or use early initialization:

```python
# Option 1: Type guards
if self.history_manager is None:
    raise RuntimeError("History manager not initialized")

# Option 2: Use assert
assert self.history_manager is not None, "History manager must be initialized"

# Option 3: Early initialization in __init__
self.history_manager = HistoryManager(None)  # Placeholder, replaced in _init_session
```

---

### 2.2 Mock LLM Pattern Matching Limitations

**Severity:** Medium
**Status:** Unresolved

#### Problem Description
The mock LLM only handles hardcoded patterns for specific function names. It cannot generalize to new codebases.

#### Current Implementation

**Location:** `src/modules/llm_gateway.py` lines 456-490

```python
# Hardcoded patterns
calculator_patterns = [
    ('add', ('    a + b', '    return a + b')),
    ('subtract', ('    return b - a', '    return a - b')),
    # ... more patterns
]
```

#### Recommended Solution with Agentic Mode

Replace mock LLM with actual GLM4.7 agentic mode using file tools:

```python
def request_fix_with_agentic_mode(self, context: ActiveContext) -> PatchToon:
    """Generate fixes using GLM4.7 agentic mode with file tools"""

    tools = self.llm_client.tool_manager.get_file_tools_schema()

    result = self.llm_client.generate_agentic(
        prompt=f"""
        You are an expert code repair agent.

        Test failures:
        {context.current_failures}

        History of attempted fixes:
        {context.active_history}

        Use available file tools to:
        1. Read the source files mentioned in test failures
        2. Analyze the code to identify bugs
        3. Propose and apply fixes using appropriate tools

        Constraint: Respond with a TOON-formatted patch:
        patch[1]
          {{
            file_path:"path/to/file.py",
            line_range:(start_line,end_line),
            old_code:"exact code WITH EXACT INDENTATION",
            new_code:"replacement WITH SAME INDENTATION"
          }}
        """,
        provider='zai',
        model='glm-4.7',
        max_iterations=10,
        tools=tools,
        enable_thinking=True,
        verbose=True
    )

    # Extract patch from agentic result
    return self._extract_patch_from_agentic_result(result)
```

**Benefits:**
- No hardcoded patterns needed
- LLM can read actual source code
- Self-correcting based on test results
- Works for any codebase, not just calculator examples

---

## 3. File Operation Tools for Agentic Mode

GLM4.7's agentic mode can use the following tools to enhance repair capabilities:

### 3.1 Read File Tool
```python
{
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read the complete content of a file",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to read"
                }
            },
            "required": ["file_path"]
        }
    }
}
```

### 3.2 Create File Tool
```python
{
    "type": "function",
    "function": {
        "name": "create_file",
        "description": "Create a new file with given content",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path where to create the file"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file"
                }
            },
            "required": ["file_path", "content"]
        }
    }
}
```

### 3.3 Edit File Tool
```python
{
    "type": "function",
    "function": {
        "name": "edit_file",
        "description": "Replace specific lines in a file",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to edit"
                },
                "start_line": {
                    "type": "integer",
                    "description": "Starting line number (1-indexed)"
                },
                "end_line": {
                    "type": "integer",
                    "description": "Ending line number (1-indexed)"
                },
                "old_code": {
                    "type": "string",
                    "description": "Exact code to replace (must match including indentation)"
                },
                "new_code": {
                    "type": "string",
                    "description": "Replacement code (must preserve indentation)"
                }
            },
            "required": ["file_path", "start_line", "end_line", "old_code", "new_code"]
        }
    }
}
```

### 3.4 Delete File Tool
```python
{
    "type": "function",
    "function": {
        "name": "delete_file",
        "description": "Delete a file from the filesystem",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to delete"
                }
            },
            "required": ["file_path"]
        }
    }
}
```

### 3.5 List Files Tool
```python
{
    "type": "function",
    "function": {
        "name": "list_files",
        "description": "List files in a directory",
        "parameters": {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Directory path to list"
                },
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern to filter files (e.g., '*.py')"
                }
            },
            "required": ["directory"]
        }
    }
}
```

---

## 4. Enhanced Repair Workflow with Agentic Mode

### 4.1 Proposed Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  1. Agent Orchestrator Starts Repair Session         │
│     ↓                                              │
│  2. Run Tests → Get Failures                        │
│     ↓                                              │
│  3. Initialize Agentic LLM with File Tools           │
│     ↓                                              │
│  4. Agentic Loop (max 10 iterations):               │
│     ├─ 4a. LLM reads source files                  │
│     ├─ 4b. LLM analyzes failures                 │
│     ├─ 4c. LLM uses edit_file to apply fix        │
│     ├─ 4d. LLM runs tests                       │
│     ├─ 4e. If failures: repeat from 4a            │
│     └─ 4f. If success: return                    │
│     ↓                                              │
│  5. Success: All Tests Pass                        │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Implementation Plan

#### Phase 1: Enable Agentic Mode in LLM Gateway
```python
class LLMGateway:
    def request_fix_agentic(self, context: ActiveContext) -> PatchToon:
        """Generate fix using GLM4.7 agentic mode with file tools"""

        if self._use_mock:
            return self._call_llm_mock(context)

        tools = self.llm_client.tool_manager.get_file_tools_schema()

        result = self.llm_client.generate_agentic(
            prompt=self._build_agentic_prompt(context),
            provider='zai',
            model=self.model or 'glm-4.7',
            max_iterations=15,
            tools=tools,
            enable_thinking=True,
            verbose=True
        )

        return self._parse_agentic_result(result)
```

#### Phase 2: Update Agent Orchestrator
```python
def _run_iteration_agentic(self, target_file: Path, iteration: int) -> str:
    """Run iteration using agentic mode"""

    test_payload = self.debugging_context.get_current_context(target_file)

    if not test_payload.failures:
        return "SUCCESS"

    active_context = self.history_manager.pruner.get_active_context(
        test_payload.failures, iteration
    )

    # Use agentic mode instead of simple patch generation
    result = self.llm_gateway.request_fix_agentic(active_context)

    # The agentic LLM will have already applied fixes and run tests
    if result.get("success"):
        return "SUCCESS"
    else:
        return "CONTINUE"
```

#### Phase 3: Add File Tools to Tool Manager
```python
class ToolManager:
    def __init__(self):
        self.file_operations = FileOperations()

    def get_file_tools_schema(self) -> List[Dict]:
        """Get schema for all file operation tools"""
        return [
            self._create_tool_schema("read_file", "Read file content"),
            self._create_tool_schema("create_file", "Create new file"),
            self._create_tool_schema("edit_file", "Edit existing file"),
            self._create_tool_schema("delete_file", "Delete file"),
            self._create_tool_schema("list_files", "List directory"),
            self._create_tool_schema("run_tests", "Run pytest"),
        ]

    def execute_tool(self, tool_name: str, arguments: Dict) -> str:
        """Execute a file operation tool"""
        if tool_name == "read_file":
            return self.file_operations.read_file(arguments["file_path"])
        elif tool_name == "create_file":
            return self.file_operations.create_file(
                arguments["file_path"],
                arguments["content"]
            )
        elif tool_name == "edit_file":
            return self.file_operations.edit_file(
                arguments["file_path"],
                arguments["start_line"],
                arguments["end_line"],
                arguments["old_code"],
                arguments["new_code"]
            )
        # ... etc
```

---

## 5. Expected Benefits

### 5.1 Automatic Bug Discovery
- LLM can read multiple source files to understand dependencies
- Identifies bugs that span multiple files
- Discovers missing files or incorrect imports

### 5.2 Self-Correction
- If a fix breaks tests, LLM can:
  - Read the error message
  - Analyze what went wrong
  - Apply a different fix
  - Without requiring a new iteration

### 5.3 Reduced Iterations
- Agentic mode can apply multiple fixes in one iteration
- No waiting for orchestrator to re-run tests between patches
- LLM can chain fixes together intelligently

### 5.4 Better Context Understanding
- File tools give LLM direct access to codebase
- No need to include all source code in prompts
- Token-efficient for large projects

---

## 6. Priority Matrix

| Issue | Severity | Effort | Impact | Priority |
|--------|----------|---------|---------|----------|
| Path Resolution Bug | High | Medium | High | P0 |
| Enable Agentic Mode | High | High | Very High | P0 |
| Cycle Detection Refinement | Medium | Medium | Medium | P1 |
| Type Checking Errors | Low | Low | Low | P2 |
| Mock LLM Limitations | Medium | High | Medium | P2 |

---

## 7. Implementation Roadmap

### Sprint 1: Critical Path Resolution (Week 1)
1. Implement `resolve_file_path` tool
2. Update `_call_llm_mock` to use file tools
3. Add path resolution tests

### Sprint 2: Agentic Mode Integration (Week 2-3)
1. Implement file operation tools in ToolManager
2. Create `request_fix_agentic` method
3. Update agent orchestrator to use agentic mode optionally

### Sprint 3: Cycle Detection Enhancement (Week 4)
1. Implement semantic cycle detection
2. Add LLM-based patch diversity analysis
3. Update cycle detector to use semantic comparison

### Sprint 4: Type Safety & Testing (Week 5)
1. Fix all type checking errors
2. Add unit tests for edge cases
3. Integration tests with real LLM API

---

## 8. Risk Mitigation

### 8.1 Agentic Mode Risks
- **Risk:** LLM may create or modify files unintentionally
  - **Mitigation:** Require explicit confirmation for destructive operations
  - **Mitigation:** Create backups before any modifications

- **Risk:** Infinite loops in agentic mode
  - **Mitigation:** Enforce `max_iterations=10`
  - **Mitigation:** Timeout protection at 5 minutes per repair

- **Risk:** Token cost explosion
  - **Mitigation:** Cache file contents locally
  - **Mitigation:** Limit context window to essential files

### 8.2 Tool Execution Risks
- **Risk:** Malicious file paths
  - **Mitigation:** Validate paths are within project directory
  - **Mitigation:** Reject paths with `../` or absolute paths outside project

- **Risk:** Large file operations
  - **Mitigation:** Enforce file size limits (10MB max)
  - **Mitigation:** Limit number of files read per iteration

---

## 9. Conclusion

By leveraging GLM4.7's agentic mode with file operation tools, ARR can significantly improve its repair capabilities:

1. **Automatic path resolution** - Eliminates the #1 bug
2. **Direct file access** - Removes need for hardcoded patterns
3. **Self-correcting behavior** - Reduces iteration count
4. **Better context** - Handles complex, multi-file bugs

The highest priority is implementing file operation tools and enabling agentic mode, which addresses multiple critical issues simultaneously.

---

**Document Version:** 1.0
**Last Updated:** 2025-12-31
**Next Review:** After Sprint 1 completion
