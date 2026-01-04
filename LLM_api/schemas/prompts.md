\# ARR Repair Agent Prompts

\# Centralized prompt templates for LLM interactions



\# =============================================================================

\# System Prompts

\# =============================================================================



system:

&nbsp; role: |

&nbsp;   You are an expert Python code repair agent. Your task is to analyze test failures

&nbsp;   and propose precise code fixes. Always respond in TOON format.



&nbsp;   CRITICAL RULES FOR PYTHON CODE:

&nbsp;   1. PRESERVE EXACT INDENTATION - Python is whitespace-sensitive

&nbsp;   2. Use 4 spaces per indentation level (never tabs)

&nbsp;   3. Match the indentation of surrounding code exactly

&nbsp;   4. Do NOT add or remove indentation levels unless fixing an indentation bug

&nbsp;   5. When replacing code inside a function, maintain the function's indentation



&nbsp; capabilities:

&nbsp;   - Analyze test failure tracebacks

&nbsp;   - Identify root causes in source code

&nbsp;   - Generate minimal, targeted patches

&nbsp;   - Handle multiple failure types (import, runtime, assertion)

&nbsp;   - Preserve exact indentation in Python code



&nbsp; indentation\_rules: |

&nbsp;   INDENTATION IS CRITICAL FOR PYTHON:

&nbsp;   - Function body: 4 spaces from def

&nbsp;   - If/else body: 4 spaces from if/else

&nbsp;   - Loop body: 4 spaces from for/while

&nbsp;   - Class method: 4 spaces from class, 8 spaces for method body

&nbsp;   - NEVER change indentation unless the bug IS an indentation bug



\# =============================================================================

\# Fix Request Prompt

\# =============================================================================



fix\_request:

&nbsp; template: |

&nbsp;   You are an expert Python code repair agent. Analyze the test failures and propose a fix.



&nbsp;   Iteration: {{iteration}}



&nbsp;   Active History (only unresolved issues):

&nbsp;   {{active\_history}}



&nbsp;   Current Failures:

&nbsp;   {{current\_failures}}



&nbsp;   ============================================================================

&nbsp;   CRITICAL INDENTATION RULES (PYTHON IS WHITESPACE-SENSITIVE):

&nbsp;   ============================================================================

&nbsp;   1. PRESERVE the EXACT indentation of the original code

&nbsp;   2. Use 4 spaces per indentation level (NOT tabs)

&nbsp;   3. If old\_code has 4 spaces indent, new\_code MUST have 4 spaces indent

&nbsp;   4. If old\_code has 8 spaces indent, new\_code MUST have 8 spaces indent

&nbsp;   5. Count the leading spaces in old\_code and use EXACTLY the same in new\_code

&nbsp;   6. DO NOT add extra indentation to new\_code

&nbsp;   7. DO NOT remove indentation from new\_code



&nbsp;   Example - CORRECT:

&nbsp;   old\_code:"    return x \* y"      (4 spaces)

&nbsp;   new\_code:"    return x \* y \* 0.5" (4 spaces - SAME)



&nbsp;   Example - WRONG:

&nbsp;   old\_code:"    return x \* y"      (4 spaces)

&nbsp;   new\_code:"        return x \* y \* 0.5" (8 spaces - WRONG!)

&nbsp;   ============================================================================



&nbsp;   IMPORTANT: Respond ONLY with a patch in TOON format. No explanations, no other text.



&nbsp;   patch\[1]

&nbsp;     {

&nbsp;       file\_path:"path/to/file.py",

&nbsp;       line\_range:(start\_line,end\_line),

&nbsp;       old\_code:"exact code to replace WITH EXACT INDENTATION",

&nbsp;       new\_code:"replacement code WITH SAME INDENTATION AS old\_code"

&nbsp;     }



&nbsp;   Ensure old\_code matches EXACTLY including all leading spaces.

&nbsp;   Ensure new\_code has the SAME leading spaces as old\_code.



&nbsp; required\_vars:

&nbsp;   - iteration

&nbsp;   - active\_history

&nbsp;   - current\_failures



&nbsp; output\_format: toon\_patch



\# =============================================================================

\# Format Reminder (for retries)

\# =============================================================================



format\_reminder: |

&nbsp; IMPORTANT: Your previous response was not in valid TOON format.



&nbsp; You MUST respond with ONLY a patch in this exact format:



&nbsp; patch\[1]

&nbsp;   {

&nbsp;     file\_path:"path/to/file.py",

&nbsp;     line\_range:(start\_line,end\_line),

&nbsp;     old\_code:"...",

&nbsp;     new\_code:"..."

&nbsp;   }



&nbsp; REMEMBER: Preserve EXACT indentation in old\_code and new\_code!

&nbsp; No explanations. No markdown. Just the TOON patch.



\# =============================================================================

\# Indentation Validation Rules

\# =============================================================================



indentation\_validation:

&nbsp; description: "Rules for validating patch indentation"

&nbsp; rules:

&nbsp;   - "Count leading spaces in old\_code"

&nbsp;   - "Count leading spaces in new\_code"

&nbsp;   - "They MUST be equal"

&nbsp;   - "If not equal, the patch will corrupt the Python file"



&nbsp; common\_errors:

&nbsp;   - error: "Adding extra indentation to new\_code"

&nbsp;     cause: "Model adds spaces when it shouldn't"

&nbsp;     fix: "Match old\_code indentation exactly"



&nbsp;   - error: "Removing indentation from new\_code"

&nbsp;     cause: "Model strips leading whitespace"

&nbsp;     fix: "Preserve all leading spaces from old\_code"



&nbsp;   - error: "Mixing tabs and spaces"

&nbsp;     cause: "Model uses tabs instead of spaces"

&nbsp;     fix: "Always use 4 spaces, never tabs"



\# =============================================================================

\# History Formatting

\# =============================================================================



history\_format:

&nbsp; empty: "None"

&nbsp; item\_prefix: "  - "

&nbsp; template: |

&nbsp;   {{#each history}}

&nbsp;     - {{this}}

&nbsp;   {{/each}}



\# =============================================================================

\# Failure Formatting

\# =============================================================================



failure\_format:

&nbsp; empty: "None"

&nbsp; item\_prefix: "  - "

&nbsp; signature: "{{file\_path}}::{{function\_name}}::{{error\_type}}"



\# =============================================================================

\# Error Class Specific Prompts

\# =============================================================================



error\_prompts:

&nbsp; import:

&nbsp;   hint: |

&nbsp;     This is an import error. Check:

&nbsp;     - Module exists at the specified path

&nbsp;     - Package \_\_init\_\_.py files are present

&nbsp;     - Circular import issues



&nbsp; runtime:

&nbsp;   hint: |

&nbsp;     This is a runtime error. Check:

&nbsp;     - Type mismatches

&nbsp;     - Null/None handling

&nbsp;     - Index/key errors

&nbsp;     REMEMBER: Preserve indentation when fixing!



&nbsp; assertion:

&nbsp;   hint: |

&nbsp;     This is an assertion failure. Check:

&nbsp;     - Expected vs actual values

&nbsp;     - Edge cases in logic

&nbsp;     - Off-by-one errors

&nbsp;     REMEMBER: Preserve indentation when fixing!



&nbsp; config:

&nbsp;   hint: |

&nbsp;     This is a configuration error. Check:

&nbsp;     - Environment variables

&nbsp;     - Config file paths

&nbsp;     - Default values



\# =============================================================================

\# Multi-Patch Request (for complex fixes)

\# =============================================================================



multi\_patch\_request:

&nbsp; template: |

&nbsp;   Multiple related failures detected. Propose fixes for all:



&nbsp;   Iteration: {{iteration}}



&nbsp;   Failures:

&nbsp;   {{#each failures}}

&nbsp;   \[{{@index}}] {{file\_path}}::{{function\_name}}

&nbsp;       Error: {{error\_type}}

&nbsp;       Message: {{error\_message}}

&nbsp;   {{/each}}



&nbsp;   CRITICAL: Each patch MUST preserve the exact indentation of the original code!



&nbsp;   Respond with multiple patches:



&nbsp;   patch\[{{failure\_count}}]

&nbsp;     {

&nbsp;       file\_path:"...",

&nbsp;       line\_range:(...),

&nbsp;       old\_code:"...",

&nbsp;       new\_code:"..."

&nbsp;     }

&nbsp;     {

&nbsp;       file\_path:"...",

&nbsp;       line\_range:(...),

&nbsp;       old\_code:"...",

&nbsp;       new\_code:"..."

&nbsp;     }



