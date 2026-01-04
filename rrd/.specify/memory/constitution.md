# RRD Project Constitution

This document defines the core principles and protocols that all agents must follow when working on RRD projects.

---

## Article 1: Spec Kit Integration

This project follows Spec Kit methodology for spec-driven development.

principles:
  - All development must be driven by specifications
  - Specifications must be clear, testable, and complete
  - Implementation follows specification, not reverse

---

## Article 2: RRD Protocol (Implementation Standards)

implementation_protocol:
  name: "Recursive Repair Development (RRD)"
  enforcement: mandatory

phases:
  [4] {phase, description, tools}
  L1_Context | "Load knowledge kernel and write adversarial tests first" | dbgctxt,cdscan
  L2_Red | "Create skeleton with interfaces only" | cdscan
  L2_Green | "Implement to pass tests, track failures" | pytest,dbgctxt
  L2_Blue | "Critic mode - attack your own code" | cdqa,cdscan

principles:
  dual_loop_architecture:
    inner_loop: "TDD (Test-Driven Development)"
    outer_loop: "Architecture Evolution"

  critic_intervention:
    trigger: "After Green Phase completion"
    mode: "Adversarial code review"
    requirement: "MUST attack and validate own code"
    tools: "cdqa for static analysis, cdscan for patterns"

  strict_qa_gates:
    enforcement: "Code that fails QA cannot be committed"
    gates:
      [5] {gate, tool, threshold}
      linting | ruff | <50 errors
      type_coverage | ty | >80%
      security | semgrep | 0 critical
      complexity | complexipy | <12 cognitive
      dead_code | skylos | <5 functions

  memory_access:
    on_error:
      [3] {step, action}
      1 | "DO NOT immediately fix"
      2 | "FIRST consult knowledge_kernel (past failures)"
      3 | "Check for recurring patterns and apply solutions"
    knowledge_file: ".specify/memory/knowledge_kernel.toon"

---

## Article 3: Cross-Platform Compatibility

All code must work across Windows, Linux, and macOS without modifications.

requirements:
  - Use pathlib.Path instead of os.path for all path operations
  - Use Path.samefile() for path comparison (handles symlinks, relative paths, etc.)
  - Use pathlib with subprocess for cross-platform command execution
  - Never hardcode path separators (/ or \)

example_good_practice:
  |
  from pathlib import Path
  import os

  skills_path = Path(os.getenv("RRD_TOOLS_PATH", Path.home() / ".claude" / "skills"))
  cdqa_path = skills_path / "cdqa" / "run_QA.py"

  # Works on Windows, Linux, macOS
  subprocess.run(["python", str(cdqa_path)], cwd=skills_path)

example_bad_practice:
  |
  # DON'T do this - fails on Windows
  cdqa_path = "~/.claude/skills/cdqa/run_QA.py"

  # DON'T do this - fails on Windows
  if path1 == path2:
      print("Same file")

---

## Article 4: TOON Format

All tool outputs and structured data MUST use TOON (Token-Oriented Object Notation) format.

benefits:
  - "40% fewer tokens than JSON"
  - "Optimized for LLM consumption"
  - "Human-readable structure"

syntax:
  array_size: "[N]"
  column_headers: "{field1, field2, field3}"
  value_separator: "|"
  nesting: "Use indentation"

example:
  description: "Quality gate results"
  toon: |
    quality_gates:
      [5] {gate, threshold, actual, status}
      linting_errors | <50 | 12 | PASS
      type_coverage | >80% | 92% | PASS
      security_critical | 0 | 0 | PASS
      cognitive_complexity | <12 | 8 | PASS
      dead_code | <5 | 2 | PASS

---

## Article 5: Incremental Analysis

When git repository exists, prefer incremental analysis over full codebase scans.

benefits:
  - 10x speedup for small changes
  - 84% token savings for small changes
  - Focus on recent work

triggers:
  condition: "git repository exists and has commits"
  fallback: "Full codebase scan if no git history"

workflow:
  [3] {step, action}
  1 | "Get changed files via git diff --name-only"
  2 | "Run analysis only on changed files"
  3 | "Include dependencies if configured"

---

## Governance

This constitution supersedes all other development practices.

enforcement:
  - All agents must verify compliance before making changes
  - Complexity deviations must be justified in comments
  - Use /RRD_execute command for runtime development guidance

amendments:
  - Changes require documentation, approval, and migration plan
  - Version tracking mandatory for all amendments

**Version**: 1.0.0 | **Ratified**: 2026-01-02 | **Last Amended**: 2026-01-02
