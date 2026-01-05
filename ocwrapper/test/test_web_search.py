#!/usr/bin/env python3
"""
Test script demonstrating OpenCode's agentic web search capability.

This script uses OpenCode to:
1. Search the web for "Find medical physics journal url"
2. Save the correct URL to url.txt

This demonstrates OpenCode's ability to autonomously:
- Use the WebSearch tool
- Process search results
- Write output to a file
"""

import subprocess
import sys
from pathlib import Path


def test_web_search_and_save():
    """
    Use OpenCode to search the web and save the medical physics journal URL.

    OpenCode will autonomously:
    - Execute a web search
    - Identify the correct medical physics journal URL
    - Create url.txt with the result
    """

    # Get the test directory path
    test_dir = Path(__file__).parent

    # Construct the prompt for OpenCode
    prompt = (
        "Search the web for 'medical physics journal' and find the official "
        "journal URL. Save the main journal website URL (not a specific article) "
        "to a file named 'url.txt'. The URL should be for the primary Medical Physics journal."
    )

    print("=" * 70)
    print("OpenCode Agentic Web Search Test")
    print("=" * 70)
    print(f"Task: Find Medical Physics journal URL and save to url.txt")
    print(f"Working directory: {test_dir}")
    print("-" * 70)

    try:
        # Run OpenCode (tool restrictions configured via agent config, not CLI flags)
        # Note: Not capturing output so we can see OpenCode working in real-time
        result = subprocess.run(
            [
                "opencode", "run",
                prompt
            ],
            cwd=test_dir,  # Run in test directory
            check=True,
            timeout=180  # 3 minutes timeout
        )

        print("\n✓ OpenCode completed successfully!")

        # Check if url.txt was created
        url_file = test_dir / "url.txt"
        if url_file.exists():
            print(f"\n✓ File created: {url_file}")
            with open(url_file, 'r') as f:
                content = f.read().strip()
                print(f"\nContent of url.txt:")
                print("-" * 70)
                print(content)
                print("-" * 70)
            return True
        else:
            print(f"\n✗ Expected file not found: {url_file}")
            return False

    except subprocess.TimeoutExpired:
        print("\n✗ Error: OpenCode timed out after 3 minutes")
        return False
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Error: OpenCode failed with exit code {e.returncode}")
        if e.stderr:
            print(f"\nError output:\n{e.stderr}")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    print("\nStarting OpenCode agentic web search test...")
    print("This will use OpenCode to autonomously search the web and save results.\n")

    success = test_web_search_and_save()

    print("\n" + "=" * 70)
    if success:
        print("TEST PASSED: OpenCode successfully found and saved the URL")
        sys.exit(0)
    else:
        print("TEST FAILED: Check the output above for details")
        sys.exit(1)
