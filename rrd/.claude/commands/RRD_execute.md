---
description: "Execute tasks using RRD pipeline with cdqa, cdscan, dbgctxt, and zgit"
---

# RRD Execution Protocol

execution_engine: RRD
base_cycle: L2 (Red-Green-Blue)
tools_required: [cdqa, cdscan, dbgctxt, zgit]

You are now the **RRD Engine**. Follow the L2 Cycle strictly.

---

## Phase 1: Context & Setup (L1)

l1_phase:
  objectives:
    [3] {task, tool, command}
    Load_Knowledge | manual | "Read .specify/memory/knowledge_kernel.toon"
    Analyze_Codebase | cdscan | "Use pathlib to locate cdscan tool: (Path.home() / '.claude' / 'skills' / 'cdscan' / 'run_code_review.py')"
    Write_Adversarial_Tests | manual | "Create pytest tests focusing on edge cases BEFORE implementation"

  steps:
    1_load_knowledge:
      action: "Read knowledge_kernel.toon"
      purpose: "Check for similar past failures"
      file: ".specify/memory/knowledge_kernel.toon"

    2_understand_codebase:
      action: "Run cdscan for structure analysis"
      command: |
        # Use pathlib for cross-platform paths
        from pathlib import Path
        import os

        skills_path = Path(os.getenv("RRD_TOOLS_PATH", Path.home() / ".claude" / "skills"))
        cdscan_dir = skills_path / "cdscan"
        project_path = Path("<project_path>")

        # Run cdscan (works on all OS)
        cd {cdscan_dir}
        python run_code_review.py --workspace {project_path} --output codebase_structure.toon
      output_parse:
        format: TOON
        sections: [codebase_summary, structure_analysis, pattern_findings]

    3_write_tests:
      action: "Write adversarial test cases based on spec.md"
      framework: pytest
      focus: "Edge cases, failure modes, boundary conditions"
      example: |
        def test_edge_case_empty_input():
            """What happens with empty input?"""
            assert handle_input("") == expected_behavior

        def test_edge_case_overflow():
            """What happens with extremely large input?"""
            assert handle_input("x" * 10000) == expected_behavior

---

## Phase 2: The Intelligent Cycle (L2)

l2_cycle:
  pattern: Red-Green-Blue
  iterations: "Until all tests pass and QA gates clear"

### A. Red Phase (Skeleton)

red_phase:
  objective: "Create failing test infrastructure"

  tasks:
    [3] {step, action, verification}
    1 | "Define interfaces and function signatures only" | "No implementation"
    2 | "Verify AST structure with cdscan" | "python cdscan/run_code_review.py --workspace ."
    3 | "Run tests, ensure they fail as expected" | "pytest -v"

  example_code: |
    def process_data(input_data: str) -> dict:
        """Process input data and return structured output."""
        raise NotImplementedError("TODO: Implement in Green Phase")

### B. Green Phase (Implementation)

green_phase:
  objective: "Make tests pass with minimal code"

  workflow:
    [4] {step, action, tool}
    1 | "Implement minimal code to pass tests" | manual
    2 | "Run pytest" | pytest
    3 | "On FAILURE: Generate context with dbgctxt" | dbgctxt
    4 | "On SUCCESS: Proceed to Blue Phase" | -

  on_failure:
    action: "Generate failure context for repair"
    command: |
      # Use pathlib for cross-platform paths
      from pathlib import Path
      import os

      skills_path = Path(os.getenv("RRD_TOOLS_PATH", Path.home() / ".claude" / "skills"))
      dbgctxt_dir = skills_path / "dbgctxt"
      project_path = Path("<project_path>")

      # Run dbgctxt (works on all OS)
      cd {dbgctxt_dir}
      python -m dbgctxt {project_path}
    output: fix_payload.toon
    next_steps:
      [3] {step, action}
      1 | "Parse fix_payload.toon for error signatures"
      2 | "Check if signature exists in knowledge_kernel"
      3 | "If recurring: Apply known solution, else: Manual fix and record"

  cycle_prevention:
    strategy: "Progressive Backoff"
    tracking: "Record in knowledge_kernel.toon with attempt count"

    rules:
      [4] {attempt, action, rationale}
      1-2 | "Apply fixes based on dbgctxt payload" | "Try automatic repair with context"
      3 | "Rollback to skeleton (L2_Red) and simplify implementation" | "Current approach may be too complex"
      4 | "Mark feature as BLOCKED, log to knowledge_kernel, skip to next task" | "Prevent infinite loops, maintain overall progress"

    implementation: |
      from core.cycle_detector import CycleDetector

      detector = CycleDetector(window_size=4)
      attempt_count = get_attempt_count_for_signature(error_signature)

      if attempt_count <= 2:
          # Attempt 1-2: Apply fixes from dbgctxt
          fix = generate_fix_from_context(fix_payload)
          apply_patch(fix)
      elif attempt_count == 3:
          # Attempt 3: Simplify approach
          rollback_to_skeleton()
          simplify_implementation()
      else:
          # Attempt 4+: Block and continue
          mark_as_blocked(error_signature, reason="Exceeded retry limit")
          log_to_knowledge_kernel(error_signature, status="BLOCKED")
          skip_to_next_task()

    blocked_task_format:
      signature: "src/module.py::function::ErrorType"
      status: "BLOCKED"
      attempts: 4
      last_error: "Description of final error"
      recommendation: "Requires human intervention or alternative approach"

### C. Blue Phase (Gradual Strictness: L2 Drafting → L3 Hardening)

blue_phase:
  mode: CRITIC_ACTIVATED
  persona: "Hostile security auditor who wants to REJECT this code"
  strategy: "Progressive quality enforcement"

  cycle_types:
    [2] {cycle, purpose, qa_threshold}
    L2_Blue | "Drafting - Basic functional validation" | relaxed_thresholds
    L3_Blue | "Hardening - Full security and quality audit" | strict_thresholds

  ## L2 Blue Phase (Drafting)
  l2_drafting:
    trigger: "After first successful Green Phase (tests pass)"
    objective: "Ensure basic code quality and essential security"

    quality_gates_relaxed:
      [5] {gate, l2_threshold, action_if_fail}
      linting_errors | <100 | "Fix critical errors only, warnings allowed"
      type_coverage | >60% | "Add types to public APIs only"
      security_critical | 0 | "Fix CRITICAL vulnerabilities only"
      cognitive_complexity | <15 | "Refactor only if extremely complex"
      dead_code | <10 | "Remove obvious dead code only"

    tasks:
      [4] {step, action, tool}
      1 | "Run QA with relaxed thresholds" | cdqa
      2 | "Fix blocking issues (security critical, major bugs)" | manual
      3 | "Verify tests still pass" | pytest
      4 | "Proceed to next feature OR enter L3 if all features done" | manual

    static_analysis_command: |
      # Use pathlib for cross-platform paths
      from pathlib import Path
      import os

      skills_path = Path(os.getenv("RRD_TOOLS_PATH", Path.home() / ".claude" / "skills"))
      cdqa_dir = skills_path / "cdqa"
      project_path = Path("<project_path>")

      # Run cdqa in drafting mode (works on all OS)
      cd {cdqa_dir}
      python run_QA.py --workspace {project_path} --mode drafting --output quality_report.toon

  ## L3 Blue Phase (Hardening)
  l3_hardening:
    trigger: "After ALL features implemented successfully"
    objective: "Full security audit, performance optimization, production readiness"

    quality_gates_strict:
      [5] {gate, l3_threshold, action_if_fail}
      linting_errors | <50 | "Fix ALL errors, minimize warnings"
      type_coverage | >80% | "Add comprehensive type annotations"
      security_critical | 0 | "Fix ALL security issues (critical + high)"
      cognitive_complexity | <12 | "Refactor all complex functions"
      dead_code | <5 | "Remove ALL unused code"

    tasks:
      [7] {step, action, tool}
      1 | "Run comprehensive QA analysis" | cdqa
      2 | "Review TOON report for ALL violations" | manual
      3 | "Fix ALL issues (lint, type, security, complexity)" | manual
      4 | "Run performance profiling" | manual
      5 | "Adversarial review - attack edge cases" | manual
      6 | "Re-run QA until all gates PASS" | cdqa
      7 | "Create new adversarial tests for found issues" | pytest

    static_analysis_command: |
      # Use pathlib for cross-platform paths
      from pathlib import Path
      import os

      skills_path = Path(os.getenv("RRD_TOOLS_PATH", Path.home() / ".claude" / "skills"))
      cdqa_dir = skills_path / "cdqa"
      project_path = Path("<project_path>")

      # Run cdqa in hardening mode (works on all OS)
      cd {cdqa_dir}
      python run_QA.py --workspace {project_path} --mode hardening --output quality_report.toon

  adversarial_questions:
    [6] {question, focus_area}
    "What edge cases did I miss?" | test_coverage
    "Where could this code fail in production?" | reliability
    "What assumptions am I making?" | robustness
    "How could malicious input break this?" | security
    "Is this code maintainable in 6 months?" | maintainability
    "What are the performance bottlenecks?" | performance

  refactor_criteria:
    - Reduce cognitive complexity
    - Add defensive programming
    - Enhance error handling
    - Remove code duplication
    - Improve type safety
    - Optimize critical paths

---

## Phase 3: Documentation (L4)

l4_phase:
  objective: "Update knowledge kernel and commit with context"

  tasks:
    [3] {step, action, tool}
    1 | "Update knowledge_kernel.toon with session data" | manual
    2 | "Generate inline documentation" | manual
    3 | "Commit with context preservation" | zgit

  knowledge_kernel_update:
    file: ".specify/memory/knowledge_kernel.toon"
    structure:
      failures:
        [N] {signature, count, first_seen, last_seen, solution, tags}
        <sig> | <N> | <ISO8601> | <ISO8601> | <description> | [tags]
      patterns:
        [N] {pattern, occurrences, fix}
        <description> | <N> | <solution>

    example_entry:
      signature: "src/auth.py::validate_token::TypeError"
      count: 3
      first_seen: "2026-01-02T10:00:00"
      last_seen: "2026-01-02T11:30:00"
      solution: "Add null check before accessing token attributes"
      tags: [authentication, type_error, null_safety]

  commit_workflow:
    command: |
      # Use pathlib for cross-platform paths
      from pathlib import Path
      import os

      skills_path = Path(os.getenv("RRD_TOOLS_PATH", Path.home() / ".claude" / "skills"))
      zgit_dir = skills_path / "zgit"

      # Run zgit (works on all OS)
      cd {zgit_dir}
      python zgit.py --context "<user intent from L1>" --stage

    context_format: "<Feature/Fix>: <Brief description of what and why>"
    example: "Feature: Implement user authentication with RRD protocol and adversarial testing"

---

## Quality Gates (All Must Pass)

quality_gates:
  enforcement: "BLOCKING - Cannot proceed without passing"

  gates:
    [6] {gate, verification, tool}
    All_Tests_Pass | "pytest exit code 0" | pytest
    Linting_Clean | "ruff errors <50" | cdqa
    Type_Coverage | "ty coverage >80%" | cdqa
    No_Security_Issues | "semgrep critical = 0" | cdqa
    Complexity_Acceptable | "complexipy <12" | cdqa
    No_Dead_Code | "skylos unused <5" | cdqa

  verification_command: |
    # Use pathlib for cross-platform paths
    from pathlib import Path
    import os

    skills_path = Path(os.getenv("RRD_TOOLS_PATH", Path.home() / ".claude" / "skills"))
    cdqa_dir = skills_path / "cdqa"
    project_path = Path("<project_path>")

    # Run full QA gate check (works on all OS)
    cd {cdqa_dir}
    python run_QA.py --workspace {project_path}

    # Parse TOON output for gate status
    grep "quality_gates:" -A 10 quality_report.toon

    # All gates must show "PASS"

---

## Emergency Protocols

emergency_protocols:
  infinite_loop_detection:
    trigger: "Error signature appears >3 times in knowledge_kernel"
    actions:
      [4] {step, action}
      1 | "STOP current cycle"
      2 | "Generate error report with dbgctxt"
      3 | "Document blocker in knowledge_kernel"
      4 | "Request human intervention"

  qa_repeated_failures:
    trigger: "QA gates fail >5 times consecutively"
    actions:
      [4] {step, action}
      1 | "Re-read specification from spec.md"
      2 | "Run cdscan to review architecture assumptions"
      3 | "Consider alternative implementation approach"
      4 | "Consult external documentation or request guidance"

---

## RRD Cycle Summary (TOON)

rrd_cycle_summary:
  phases:
    [4] {phase, key_actions, tools, output}
    L1_Context | "Load knowledge, analyze codebase, write adversarial tests" | cdscan,manual | tests/*.py
    L2_Red | "Create skeleton interfaces, verify AST, run tests (should fail)" | cdscan,pytest | skeleton_code
    L2_Green | "Implement minimal code, run tests, handle failures with context" | pytest,dbgctxt | working_code
    L2_Blue | "QA analysis, fix all issues, adversarial review, refactor" | cdqa,cdscan | clean_code

  loop_until:
    - All tests pass
    - All QA gates clear
    - No recurring error patterns

  then_proceed_to: L4_Documentation

**Remember**: RRD is systematic improvement through adversarial testing, memory retention, and strict quality gates. Every failure is a learning opportunity stored in the knowledge kernel.
