"""Adaptive Recursive Repair Agent - Auditable & Context-Aware Auto-Repair System"""

__version__ = "2.1"
__author__ = "Repair Agent Team"
__license__ = "MIT"


def run_repair_session(target_file, max_retries=5):
    """
    Convenience function to run a repair session

    Args:
        target_file: Path to file to repair
        max_retries: Maximum retry attempts

    Returns:
        Status code: SUCCESS, MAX_RETRIES_EXCEEDED, CYCLE_DETECTED
    """
    from agent_orchestrator import AgentOrchestrator

    orchestrator = AgentOrchestrator()
    return orchestrator.run_repair_session(target_file, max_retries)


__all__ = ["run_repair_session"]
