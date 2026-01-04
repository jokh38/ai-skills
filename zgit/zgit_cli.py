#!/usr/bin/env python3
"""
ZGIT - Context-Preserving Git Commit CLI

Command-line interface for git commits using zagi with
automatic context preservation.
"""

import argparse
import sys
from pathlib import Path
from textwrap import dedent

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from zgit import (
    check_zagi_installed,
    check_git_repo,
    init_git_repo,
    show_status,
    get_changed_files,
    create_commit_with_zagi,
    stage_files,
    suggest_commit_message,
    get_user_context
)


def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser with comprehensive help."""
    parser = argparse.ArgumentParser(
        prog='zgit',
        description=dedent('''
            ZGIT - Context-Preserving Git Commits

            Intelligent git commit wrapper that uses zagi to:
            • Preserve original intent/context with --prompt flag
            • Generate meaningful commit messages
            • Track the "why" behind changes, not just the "what"
            • Enable better code archaeology and AI-assisted reviews

            Requires: zagi (https://zagi.sh)
        '''),
        epilog=dedent('''
            Examples:
              # Interactive commit (prompts for context)
              zgit

              # Non-interactive with context
              zgit --context "Fix authentication bug in login flow"

              # Custom commit message with context
              zgit --context "Add user API" --message "feat: add user CRUD endpoints"

              # Auto-stage all files before commit
              zgit --stage --context "Refactor database layer"

              # Short form
              zgit -c "Fix typo" -m "docs: fix readme typo" -s

            How It Works:
              1. Checks git status and shows pending changes
              2. Prompts for context (the "why" behind changes)
              3. Optionally stages files (with --stage or interactively)
              4. Generates commit message from context
              5. Creates commit via zagi with preserved context

            Context Preservation:
              The context is stored via zagi's --prompt flag, allowing
              future retrieval with: git log --prompts

            Prerequisites:
              • Git repository (will initialize if needed)
              • zagi installed (curl -fsSL zagi.sh/install | sh)

            Exit Codes:
              0: Commit created successfully or no changes
              1: Error or user interruption
        '''),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Optional arguments
    parser.add_argument(
        '--context', '-c',
        type=str,
        metavar='TEXT',
        help='Context/reason for changes (enables non-interactive mode)'
    )

    parser.add_argument(
        '--message', '-m',
        type=str,
        metavar='MSG',
        help='Custom commit message (optional, auto-generated from context if omitted)'
    )

    parser.add_argument(
        '--stage', '-s',
        action='store_true',
        help='Automatically stage all modified files before commit'
    )

    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 0.1.0'
    )

    return parser


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    print("=" * 50)
    print("🚀 Zagi-Assisted Context-Preserving Commit")
    print("=" * 50)
    print()

    # Verify prerequisites - initialize git if needed
    if not check_git_repo():
        print("⚠️  Not in a git repository")
        if not init_git_repo():
            return 1

    if not check_zagi_installed():
        print("❌ Error: zagi is not installed")
        print("   Install with: curl -fsSL zagi.sh/install | sh")
        return 1

    try:
        # Show current status
        show_status()

        # Get changed files
        changed_files = get_changed_files()
        if not changed_files or not any(f.strip() for f in changed_files):
            print("⚠️  No changed files detected")
            print("   Make some changes and try again")
            return 0

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

        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️  Commit cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Commit failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
