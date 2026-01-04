#!/usr/bin/env python3
"""
Zagi-Assisted Context-Preserving Commit Skill

Creates a git commit using zagi with automatic context preservation.
The --prompt flag captures the original user intent for future reference.
"""

import subprocess
import sys
import os
import argparse


def run_command(cmd, capture=False):
    """Execute a shell command and optionally capture output."""
    try:
        if capture:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        else:
            subprocess.run(cmd, shell=True, check=True)
            return None
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if e.stderr:
            print(f"Details: {e.stderr}")
        sys.exit(1)


def check_zagi_installed():
    """Check if zagi is installed."""
    try:
        run_command("which zagi", capture=True)
        return True
    except:
        return False


def check_git_repo():
    """Check if we're in a git repository."""
    try:
        run_command("git rev-parse --git-dir", capture=True)
        return True
    except:
        return False


def init_git_repo():
    """Initialize a new git repository."""
    print("📦 Initializing git repository...")
    try:
        run_command("git init")
        print("✅ Git repository initialized successfully!")
        print()
        return True
    except Exception as e:
        print(f"❌ Failed to initialize git repository: {e}")
        return False


def show_status():
    """Display git status using zagi."""
    print("📝 Current Git Status:")
    print("-" * 40)
    run_command("zagi status")
    print()


def get_user_context(non_interactive_context=None):
    """Prompt user for the context/reason for changes."""
    if non_interactive_context:
        return non_interactive_context

    print("🤔 Describe the context for these changes:")
    print("   (What are you trying to accomplish?)")
    try:
        context = input("→ ").strip()
    except EOFError:
        print("❌ Running in non-interactive mode but no context provided")
        print("   Use: --context 'your context here'")
        sys.exit(1)

    if not context:
        print("❌ Context cannot be empty")
        sys.exit(1)

    return context


def get_changed_files():
    """Get list of changed files."""
    # First try to get staged changes (--cached shows staged files)
    try:
        output = run_command("git diff --cached --name-only", capture=True)
        if output:
            return output.split('\n')
    except:
        pass

    # Then try to get unstaged changes
    try:
        output = run_command("git diff --name-only", capture=True)
        if output:
            return output.split('\n')
    except:
        pass

    return []


def suggest_commit_message(context, changed_files):
    """Suggest a commit message based on context and files."""
    # Simple heuristic: use the context as-is if it's reasonable length
    if len(context) <= 72:  # Conventional commit message length
        return context

    # Otherwise, truncate to first 72 characters
    return context[:69] + "..."


def stage_files(auto_stage=False):
    """Optionally stage files."""
    if auto_stage:
        print("Staging files...")
        run_command("git add -A")
        print("✅ Files staged")
        print()
        return

    print("📋 Would you like to stage all modified files? (y/n)")
    try:
        response = input("→ ").strip().lower()
    except EOFError:
        print("⚠️  Running in non-interactive mode, skipping staging")
        print()
        return

    if response == 'y':
        print("Staging files...")
        run_command("git add -A")
        print("✅ Files staged")
    elif response != 'n':
        print("❌ Invalid response, skipping staging")

    print()


def create_commit_with_zagi(message, context):
    """Create commit using zagi with context preservation."""
    print(f"✨ Commit Message: {message}")
    print(f"📌 Context: {context}")
    print()

    print("💾 Creating commit with zagi...")

    # Check if ZAGI_AGENT is set
    agent = os.environ.get('ZAGI_AGENT', '')
    if agent:
        print(f"   (Agent mode enabled: {agent})")

    # Create commit with zagi using --prompt flag to preserve context
    cmd = f'zagi commit -m "{message}" --prompt "{context}"'

    try:
        run_command(cmd)
        print()
        print("✅ Commit created successfully!")
        print("📖 View context later with: git log --prompts")
        print()

        # Show the commit that was just created
        print("📝 Commit details:")
        run_command("zagi log -1")

    except Exception as e:
        print(f"❌ Failed to create commit: {e}")
        sys.exit(1)


def main():
    """Main workflow for zagi-assisted commit."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Zagi-Assisted Context-Preserving Commit')
    parser.add_argument('--context', '-c', type=str, help='Context/reason for changes (non-interactive mode)')
    parser.add_argument('--message', '-m', type=str, help='Custom commit message (optional)')
    parser.add_argument('--stage', '-s', action='store_true', help='Automatically stage all files')
    args = parser.parse_args()

    print("=" * 50)
    print("🚀 Zagi-Assisted Context-Preserving Commit")
    print("=" * 50)
    print()

    # Verify prerequisites - initialize git if needed
    if not check_git_repo():
        print("⚠️  Not in a git repository")
        if not init_git_repo():
            sys.exit(1)

    if not check_zagi_installed():
        print("❌ Error: zagi is not installed")
        print("   Install with: curl -fsSL zagi.sh/install | sh")
        sys.exit(1)

    # Show current status
    show_status()

    # Get changed files
    changed_files = get_changed_files()
    if not changed_files or not any(f.strip() for f in changed_files):
        print("⚠️  No changed files detected")
        print("   Make some changes and try again")
        sys.exit(0)

    print(f"📂 Changed files: {len([f for f in changed_files if f.strip()])} file(s)")
    print()

    # Get context from user (or command line)
    context = get_user_context(args.context)
    print()

    # Optionally stage files
    stage_files(args.stage)

    # Generate and suggest commit message
    message = args.message if args.message else suggest_commit_message(context, changed_files)

    # Create commit with zagi
    create_commit_with_zagi(message, context)

    print("=" * 50)
    print("✨ Done!")
    print("=" * 50)


if __name__ == "__main__":
    main()
