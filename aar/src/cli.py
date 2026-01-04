#!/usr/bin/env python3
"""CLI entry point for Adaptive Recursive Repair Agent"""

import sys
import argparse
from pathlib import Path


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Adaptive Recursive Repair Agent - Auditable & Context-Aware Auto-Repair System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Repair a specific test file
  arr repair tests/test_example.py

  # Repair with custom retries
  arr repair tests/test_example.py --max-retries 10

  # Repair with verbose logging
  arr repair tests/test_example.py --log-level DEBUG

  # Run from specific project directory
  arr repair tests/test_example.py --project-dir /path/to/project
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Repair command
    repair_parser = subparsers.add_parser(
        "repair",
        help="Run repair session on target file"
    )
    repair_parser.add_argument(
        "target",
        type=Path,
        help="Path to test file to repair"
    )
    repair_parser.add_argument(
        "--max-retries",
        type=int,
        default=5,
        help="Maximum repair iterations (default: 5)"
    )
    repair_parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging verbosity (default: INFO)"
    )
    repair_parser.add_argument(
        "--log-dir",
        type=Path,
        default=None,
        help="Base directory for session logs (default: ./repair_logs)"
    )
    repair_parser.add_argument(
        "--project-dir",
        type=Path,
        default=None,
        help="Project root directory (default: current directory)"
    )
    repair_parser.add_argument(
        "--disable-ruff",
        action="store_true",
        help="Disable Ruff auto-fix"
    )

    # Status command
    status_parser = subparsers.add_parser(
        "status",
        help="Show status of last repair session"
    )
    status_parser.add_argument(
        "session_id",
        type=str,
        nargs="?",
        help="Session ID (default: latest)"
    )

    # List command
    list_parser = subparsers.add_parser(
        "list",
        help="List all repair sessions"
    )
    list_parser.add_argument(
        "--log-dir",
        type=Path,
        default=Path("./repair_logs"),
        help="Base directory for session logs (default: ./repair_logs)"
    )

    args = parser.parse_args()

    if args.command == "repair":
        return run_repair(args)
    elif args.command == "status":
        return show_status(args)
    elif args.command == "list":
        return list_sessions(args)
    else:
        parser.print_help()
        return 1


def run_repair(args):
    """Execute repair session"""
    import os
    import logging
    import sys
    from pathlib import Path

    # Add src to path if needed
    src_dir = Path(__file__).parent
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from agent_orchestrator import AgentOrchestrator
    from modules.data_types import Config

    # Set up logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="[%(levelname)s] %(message)s"
    )

    # Set environment variables
    if args.log_dir:
        os.environ["REPAIR_LOG_DIR"] = str(args.log_dir)
    if args.disable_ruff:
        os.environ["REPAIR_ENABLE_RUFF"] = "false"

    # Validate target file
    if not args.target.exists():
        print(f"Error: Target file not found: {args.target}", file=sys.stderr)
        return 1

    # Initialize orchestrator
    config = Config.from_env()
    config.log_level = args.log_level
    config.max_retries = args.max_retries
    config.ruff_enabled = not args.disable_ruff

    orchestrator = AgentOrchestrator(config)

    # Run repair session
    print(f"Starting repair session for: {args.target}")
    print(f"Max retries: {args.max_retries}")
    print(f"Ruff enabled: {config.ruff_enabled}")
    print("-" * 60)

    try:
        result = orchestrator.run_repair_session(args.target, args.max_retries)

        print("-" * 60)
        if result == "SUCCESS":
            print("✓ Repair completed successfully!")
            return 0
        elif result == "MAX_RETRIES_EXCEEDED":
            print("✗ Repair failed: Max retries exceeded")
            return 1
        elif result == "CYCLE_DETECTED":
            print("✗ Repair failed: Cycle detected")
            return 1
        else:
            print(f"✗ Repair failed: {result}")
            return 1

    except KeyboardInterrupt:
        print("\n✗ Repair interrupted by user")
        return 130
    except Exception as e:
        print(f"✗ Repair failed with error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def show_status(args):
    """Show session status"""
    import os
    import json
    from pathlib import Path

    log_dir = Path(os.getenv("REPAIR_LOG_DIR", "./repair_logs"))

    if args.session_id:
        session_path = log_dir / args.session_id
    else:
        # Find latest session
        sessions = sorted([d for d in log_dir.iterdir() if d.is_dir()])
        if not sessions:
            print("No repair sessions found")
            return 1
        session_path = sessions[-1]

    if not session_path.exists():
        print(f"Session not found: {session_path}")
        return 1

    # Read metadata
    metadata_file = session_path / "session_metadata.json"
    if metadata_file.exists():
        with open(metadata_file) as f:
            metadata = json.load(f)
            print(f"Session: {metadata['session_id']}")
            print(f"Timestamp: {metadata['timestamp']}")
            print(f"Status: {metadata.get('status', 'Unknown')}")

    # Read summary
    summary_file = session_path / "full_session_summary.toon"
    if summary_file.exists():
        print(f"\nSummary:\n{summary_file.read_text()}")
    else:
        print("\nNo summary available")

    return 0


def list_sessions(args):
    """List all sessions"""
    import json

    log_dir = args.log_dir

    if not log_dir.exists():
        print(f"No repair logs directory: {log_dir}")
        return 1

    sessions = sorted([d for d in log_dir.iterdir() if d.is_dir()], reverse=True)

    if not sessions:
        print("No repair sessions found")
        return 0

    print(f"Repair sessions in {log_dir}:")
    print("-" * 60)

    for session in sessions:
        metadata_file = session / "session_metadata.json"
        if metadata_file.exists():
            with open(metadata_file) as f:
                metadata = json.load(f)
                status = metadata.get('status', 'Unknown')
                timestamp = metadata.get('timestamp', '')
                print(f"  {session.name}")
                print(f"    Status: {status}")
                print(f"    Time: {timestamp}")
        else:
            print(f"  {session.name}")

    print("-" * 60)
    print(f"Total: {len(sessions)} sessions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
