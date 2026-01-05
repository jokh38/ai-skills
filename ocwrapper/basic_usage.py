#!/usr/bin/env python3
"""
Basic examples of using OpenCode in agentic mode from Python subprocess.
OpenCode will autonomously create/modify files instead of just returning text.
"""

import subprocess

def basic_file_creation():
    """Basic usage - agent will create files autonomously"""
    subprocess.run([
        "opencode", "run",
        "Create a hello.py file with a simple hello world function"
    ], check=True)


def with_custom_agent():
    """Use OpenCode with a specific agent (e.g., plan agent)"""
    # Use a specific agent configured in .opencode/agents/
    subprocess.run([
        "opencode", "run",
        "--agent", "plan",
        "Create an implementation plan for the authentication module"
    ], check=True)


def with_model_selection():
    """Use OpenCode with a specific model"""
    # Specify which model to use
    subprocess.run([
        "opencode", "run",
        "--model", "anthropic/claude-sonnet-4.5",
        "Add error handling to database.py"
    ], check=True)


def create_fastapi_app():
    """Create a complete FastAPI application"""
    subprocess.run([
        "opencode", "run",
        "Create a FastAPI app in main.py with a health check endpoint and user CRUD operations"
    ], check=True)


def attach_files():
    """Attach files to provide context to OpenCode"""
    subprocess.run([
        "opencode", "run",
        "--file", "config.yaml",
        "--file", "schema.sql",
        "Generate Python models based on the database schema"
    ], check=True)


if __name__ == "__main__":
    # Example: Create a hello world file
    print("Creating hello.py file...")
    basic_file_creation()
    print("Done!")
