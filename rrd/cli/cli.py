"""
RRD CLI - Command-line interface for RRD workflow
"""

import click
from pathlib import Path

from orchestrator.rrd_orchestrator import RRDOrchestrator
from orchestrator.session_manager import SessionManager


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """RRD - Recursive Repair Development

    Automated TDD workflow with L1-L4 phases for reliable software development.
    """
    pass


@cli.command()
@click.argument("spec_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--workspace",
    "-w",
    type=click.Path(path_type=Path),
    default=Path.cwd(),
    help="Project workspace (default: current directory)",
)
@click.option(
    "--mode",
    "-m",
    type=click.Choice(["auto", "manual", "interactive"]),
    default="auto",
    help="Execution mode",
)
@click.option(
    "--config", "-c", type=click.Path(exists=True), help="Custom config file path"
)
def execute(spec_file: Path, workspace: Path, mode: str, config: str):
    """Execute full L1-L4 workflow

    Run the complete RRD workflow from specification to commit.
    """
    try:
        orchestrator = RRDOrchestrator(config_path=config, workspace=workspace)
        result = orchestrator.execute_full_workflow(
            spec_file=spec_file, output_dir=workspace, mode=mode
        )
        click.echo(f"\n✅ Workflow complete!")
        click.echo(f"Session ID: {result.session_id}")
        click.echo(f"Phases: {', '.join(result.phases_completed)}")
        click.echo(f"Failures: {len(result.failures)}")
    except Exception as e:
        click.echo(f"\n❌ Workflow failed: {e}", err=True)
        raise click.ClickException(str(e))


@cli.command()
@click.argument("spec_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--workspace",
    "-w",
    type=click.Path(path_type=Path),
    default=Path.cwd(),
    help="Project workspace",
)
@click.option(
    "--config", "-c", type=click.Path(exists=True), help="Custom config file path"
)
def l1_context(spec_file: Path, workspace: Path, config: str):
    """Execute L1: Context & Setup phase

    Load knowledge, analyze codebase, and generate adversarial tests.
    """
    try:
        orchestrator = RRDOrchestrator(config_path=config, workspace=workspace)
        result = orchestrator.execute_l1_context(spec_file)

        click.echo(f"\n✅ L1 complete!")
        click.echo(f"Tests generated: {len(result.tests_generated)}")
        click.echo(f"Knowledge entries: {len(result.knowledge_kernel)}")
        click.echo(
            f"Files analyzed: {len(result.codebase_analysis.file_summary) if result.codebase_analysis else 0}"
        )
    except Exception as e:
        click.echo(f"\n❌ L1 failed: {e}", err=True)
        raise click.ClickException(str(e))


@cli.command()
@click.argument("spec_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--workspace",
    "-w",
    type=click.Path(path_type=Path),
    default=Path.cwd(),
    help="Project workspace",
)
@click.option(
    "--config", "-c", type=click.Path(exists=True), help="Custom config file path"
)
@click.option(
    "--max-attempts", type=int, default=4, help="Max repair attempts in Green phase"
)
def l2_cycle(spec_file: Path, workspace: Path, config: str, max_attempts: int):
    """Execute L2: Red-Green-Blue TDD cycle

    Create skeleton, implement code, and run QA analysis.
    """
    try:
        orchestrator = RRDOrchestrator(config_path=config, workspace=workspace)
        spec_content = spec_file.read_text()
        result = orchestrator.execute_l2_cycle(spec_content)

        click.echo(f"\n✅ L2 complete!")
        click.echo(f"Status: {result.status}")
        click.echo(
            f"Quality score: {result.quality_report.quality_score if result.quality_report else 0}"
        )
        click.echo(f"Cycle count: {result.cycle_count}")
        click.echo(
            f"Quality gates: {'PASSED' if result.gate_results.passed else 'FAILED'}"
        )
    except Exception as e:
        click.echo(f"\n❌ L2 failed: {e}", err=True)
        raise click.ClickException(str(e))


@cli.command()
@click.option(
    "--workspace",
    "-w",
    type=click.Path(path_type=Path),
    default=Path.cwd(),
    help="Project workspace",
)
@click.option(
    "--config", "-c", type=click.Path(exists=True), help="Custom config file path"
)
def l3_harden(workspace: Path, config: str):
    """Execute L3: Hardening phase

    Run strict QA analysis and adversarial security review.
    """
    try:
        orchestrator = RRDOrchestrator(config_path=config, workspace=workspace)
        result = orchestrator.execute_l3_hardening()

        click.echo(f"\n✅ L3 complete!")
        click.echo(f"Quality score: {result.quality_score}")
        click.echo(f"Security findings: {len(result.security_findings)}")
        click.echo(
            f"Quality gates: {'PASSED' if result.gate_results.passed else 'FAILED'}"
        )

        if result.gate_results.failed_gates:
            click.echo("\nFailed gates:")
            for gate in result.gate_results.failed_gates:
                click.echo(f"  - {gate}")
    except Exception as e:
        click.echo(f"\n❌ L3 failed: {e}", err=True)
        raise click.ClickException(str(e))


@cli.command()
@click.argument("spec_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--workspace",
    "-w",
    type=click.Path(path_type=Path),
    default=Path.cwd(),
    help="Project workspace",
)
@click.option(
    "--config", "-c", type=click.Path(exists=True), help="Custom config file path"
)
@click.option(
    "--message",
    "-m",
    required=False,
    help="Custom commit message (auto-generated if not provided)",
)
def l4_finalize(spec_file: Path, workspace: Path, config: str, message: str):
    """Execute L4: Documentation & commit

    Update knowledge kernel, generate documentation, and commit changes.
    """
    try:
        orchestrator = RRDOrchestrator(config_path=config, workspace=workspace)
        result = orchestrator.execute_l4_documentation(spec_file)

        click.echo(f"\n✅ L4 complete!")
        click.echo(f"Commit: {result.commit_hash}")
        click.echo(f"Documentation generated: {result.documentation_generated}")
        click.echo(f"Knowledge updated: {result.knowledge_updated}")
    except Exception as e:
        click.echo(f"\n❌ L4 failed: {e}", err=True)
        raise click.ClickException(str(e))


@cli.command()
@click.argument("session_id")
@click.option(
    "--workspace",
    "-w",
    type=click.Path(path_type=Path),
    default=Path.cwd(),
    help="Project workspace",
)
def status(session_id: str, workspace: Path):
    """Show session status

    Display detailed information about a specific RRD session.
    """
    try:
        session_mgr = SessionManager(workspace)
        session = session_mgr.load_session(session_id)

        if not session:
            click.echo(f"\n❌ Session not found: {session_id}", err=True)
            raise click.ClickException("Session not found")

        click.echo(f"\n📊 Session: {session.session_id}")
        click.echo(f"Status: {session.status}")
        click.echo(f"Workspace: {session.workspace}")
        click.echo(f"Created: {session.created_at}")
        click.echo(f"Updated: {session.updated_at}")
        click.echo(f"Current Phase: {session.current_phase or 'None'}")

        click.echo(f"\nCheckpoints ({len(session.checkpoints)}):")
        for cp in session.checkpoints:
            click.echo(f"  {cp.phase}: {cp.status} ({cp.timestamp})")

        click.echo(f"\nFailures: {len(session.failures)}")
        for failure in session.failures:
            click.echo(f"  - {failure.test_name}: {failure.error_message[:50]}")

        if session.metadata:
            click.echo(f"\nMetadata:")
            for key, value in session.metadata.items():
                click.echo(f"  {key}: {value}")

    except Exception as e:
        click.echo(f"\n❌ Error: {e}", err=True)
        raise click.ClickException(str(e))


@cli.command()
@click.option(
    "--workspace",
    "-w",
    type=click.Path(path_type=Path),
    default=Path.cwd(),
    help="Project workspace",
)
def list_sessions(workspace: Path):
    """List all RRD sessions

    Show all sessions for the current workspace.
    """
    try:
        session_mgr = SessionManager(workspace)
        sessions = session_mgr.list_sessions()

        if not sessions:
            click.echo("\nNo sessions found.")
            return

        click.echo(f"\n📋 RRD Sessions ({len(sessions)}):\n")

        for session in sessions:
            status_icon = {
                "running": "🔄",
                "completed": "✅",
                "failed": "❌",
                "paused": "⏸️",
            }.get(session.status, "❓")

            click.echo(f"{status_icon} {session.session_id}")
            click.echo(f"   Status: {session.status}")
            click.echo(f"   Created: {session.created_at}")
            click.echo(f"   Phase: {session.current_phase or 'None'}")
            click.echo(f"   Failures: {len(session.failures)}")
            click.echo()

    except Exception as e:
        click.echo(f"\n❌ Error: {e}", err=True)
        raise click.ClickException(str(e))


@cli.command()
@click.argument("session_id")
@click.option(
    "--workspace",
    "-w",
    type=click.Path(path_type=Path),
    default=Path.cwd(),
    help="Project workspace",
)
def delete_session(session_id: str, workspace: Path):
    """Delete a session

    Permanently remove a session and its data.
    """
    try:
        session_mgr = SessionManager(workspace)

        if not session_mgr.load_session(session_id):
            click.echo(f"\n❌ Session not found: {session_id}", err=True)
            raise click.ClickException("Session not found")

        if click.confirm(f"\nAre you sure you want to delete session {session_id}?"):
            session_mgr.delete_session(session_id)
            click.echo(f"\n✅ Session deleted: {session_id}")
        else:
            click.echo("\nCancelled.")

    except Exception as e:
        click.echo(f"\n❌ Error: {e}", err=True)
        raise click.ClickException(str(e))


@cli.command()
@click.option(
    "--workspace",
    "-w",
    type=click.Path(path_type=Path),
    default=Path.cwd(),
    help="Project workspace",
)
def init(workspace: Path):
    """Initialize RRD in current workspace

    Create necessary directories and configuration files.
    """
    try:
        # Create directories
        rrd_dir = workspace / "rrd"
        rrd_dir.mkdir(exist_ok=True)
        (rrd_dir / "tests").mkdir(exist_ok=True)
        (rrd_dir / "src").mkdir(exist_ok=True)
        (rrd_dir / "docs").mkdir(exist_ok=True)

        # Create .rrd directory
        rrd_hidden = workspace / ".rrd"
        rrd_hidden.mkdir(exist_ok=True)
        (rrd_hidden / "sessions").mkdir(exist_ok=True)

        # Create config file
        config_file = workspace / ".claude" / "rrd_config.yaml"
        config_file.parent.mkdir(exist_ok=True)

        if not config_file.exists():
            config_content = """# RRD Configuration
llm:
  provider: anthropic
  model: claude-sonnet-4
  timeout_seconds: 300

tools:
  cdqa: cdqa
  cdscan: cdscan
  dbgctxt: dbgctxt
  zgit: zgit

quality:
  drafting:
    max_critical: 5
    max_type_errors: 10
    min_quality_score: 70
  hardening:
    max_critical: 0
    max_type_errors: 0
    min_quality_score: 85
"""
            config_file.write_text(config_content)

        click.echo("\n✅ RRD initialized successfully!")
        click.echo(f"Workspace: {workspace}")
        click.echo(f"Config: {config_file}")
        click.echo(f"\nNext steps:")
        click.echo("  1. Create a specification file (e.g., spec.md)")
        click.echo("  2. Run: rrd execute spec.md")

    except Exception as e:
        click.echo(f"\n❌ Error: {e}", err=True)
        raise click.ClickException(str(e))


if __name__ == "__main__":
    cli()
