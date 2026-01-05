#!/usr/bin/env python3
"""
Advanced examples with error handling and output capture for OpenCode subprocess usage.
"""

import subprocess
import sys
from pathlib import Path
from typing import Optional, List


def run_opencode_task(
    prompt: str,
    agent: Optional[str] = None,
    model: Optional[str] = None,
    files: Optional[List[str]] = None,
    session: Optional[str] = None,
    verbose: bool = False,
    working_dir: Optional[Path] = None
) -> bool:
    """
    Run OpenCode task with comprehensive error handling.

    Args:
        prompt: The task prompt for OpenCode
        agent: Agent to use (e.g., "plan", "build")
        model: Model to use in format provider/model (e.g., "anthropic/claude-sonnet-4.5")
        files: List of files to attach for context
        session: Session ID to continue from previous session
        verbose: Enable verbose logging to stderr
        working_dir: Directory to run OpenCode in (defaults to current dir)

    Returns:
        True if successful, False otherwise
    """
    cmd = ["opencode", "run"]

    if agent:
        cmd.extend(["--agent", agent])

    if model:
        cmd.extend(["--model", model])

    if files:
        for file in files:
            cmd.extend(["--file", file])

    if session:
        cmd.extend(["--session", session])

    if verbose:
        cmd.append("--print-logs")

    # Prompt comes last
    cmd.append(prompt)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            cwd=working_dir
        )
        print(f"✓ Task completed successfully")
        if result.stdout:
            print(f"Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error executing OpenCode task:", file=sys.stderr)
        print(f"  Return code: {e.returncode}", file=sys.stderr)
        if e.stderr:
            print(f"  Error output: {e.stderr}", file=sys.stderr)
        return False
    except FileNotFoundError:
        print("✗ OpenCode not found. Please install it first.", file=sys.stderr)
        return False


def batch_tasks(tasks: List[dict]) -> dict:
    """
    Run multiple OpenCode tasks in sequence.

    Args:
        tasks: List of task dictionaries with 'prompt' and optional 'allowed_tools'

    Returns:
        Dictionary with success/failure counts and results
    """
    results = {"success": 0, "failed": 0, "details": []}

    for i, task in enumerate(tasks, 1):
        print(f"\n[{i}/{len(tasks)}] Running: {task['prompt'][:60]}...")

        success = run_opencode_task(
            prompt=task["prompt"],
            agent=task.get("agent"),
            model=task.get("model")
        )

        if success:
            results["success"] += 1
        else:
            results["failed"] += 1

        results["details"].append({
            "task": task["prompt"],
            "success": success
        })

    return results


# Example usage
if __name__ == "__main__":
    # Example 1: Single task with error handling
    print("Example 1: Create a FastAPI application")
    print("=" * 60)
    run_opencode_task(
        "Create a FastAPI app in main.py with a health check endpoint"
    )

    # Example 2: Batch processing multiple tasks
    print("\n\nExample 2: Batch create project files")
    print("=" * 60)
    tasks = [
        {
            "prompt": "Create a README.md with project overview"
        },
        {
            "prompt": "Create a requirements.txt with common dependencies"
        },
        {
            "prompt": "Create a .gitignore for Python projects"
        }
    ]

    results = batch_tasks(tasks)
    print(f"\n\nBatch Results: {results['success']} succeeded, {results['failed']} failed")

    # Example 3: Using plan agent for planning tasks
    print("\n\nExample 3: Use plan agent for implementation planning")
    print("=" * 60)
    run_opencode_task(
        "Create an implementation plan for adding user authentication",
        agent="plan",
        verbose=True
    )

    # Example 4: Attach files for context
    print("\n\nExample 4: Generate code with file context")
    print("=" * 60)
    run_opencode_task(
        "Generate test cases based on the API schema",
        files=["api_schema.yaml", "existing_tests.py"]
    )
