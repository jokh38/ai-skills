#!/usr/bin/env python3
"""Simple demo script showing how to use ARR programmatically"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agent_orchestrator import AgentOrchestrator
from modules.data_types import Config

def main():
    """Demo repair session"""

    # Set environment variables (in production, set these externally)
    import os
    if not os.getenv("LLM_API_KEY"):
        print("Warning: LLM_API_KEY not set. Using mock mode.")
        os.environ["LLM_API_KEY"] = "mock_key"
    if not os.getenv("LLM_MODEL"):
        os.environ["LLM_MODEL"] = "gpt-4"

    # Create configuration
    config = Config.from_env()
    config.max_retries = 5
    config.log_level = "INFO"

    # Initialize orchestrator
    orchestrator = AgentOrchestrator(config)

    # Run repair session
    target_file = Path("sample_project/tests/test_math.py")

    if not target_file.exists():
        print(f"Error: Target file not found: {target_file}")
        return 1

    print(f"Starting repair session for: {target_file}")
    print("-" * 60)

    result = orchestrator.run_repair_session(target_file)

    print("-" * 60)
    print(f"Result: {result}")

    if result == "SUCCESS":
        print("✓ Repair completed successfully!")
        return 0
    else:
        print("✗ Repair did not complete successfully")
        return 1

if __name__ == "__main__":
    sys.exit(main())
