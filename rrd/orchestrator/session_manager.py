"""Session Manager for RRD workflow"""

import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from datetime import datetime
import uuid

from core.toon_utils import dumps, parse_toon
from core.data_types import SessionSummary, FailureSignature


@dataclass
class Checkpoint:
    """Workflow phase checkpoint for resume capability"""

    phase: str
    timestamp: str
    status: str
    data: Dict[str, Any]


@dataclass
class Session:
    """RRD workflow session"""

    session_id: str
    workspace: Path
    created_at: str
    updated_at: str
    status: str  # running, paused, completed, failed
    current_phase: Optional[str] = None
    checkpoints: List[Checkpoint] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    failures: List[FailureSignature] = field(default_factory=list)


class SessionManager:
    """Manages RRD session lifecycle"""

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.sessions_dir = workspace / ".rrd" / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.current_session: Optional[Session] = None

    def create_session(self, metadata: Optional[Dict[str, Any]] = None) -> Session:
        """Initialize new RRD session

        Args:
            metadata: Optional metadata for the session

        Returns:
            New Session object
        """
        session_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()

        session = Session(
            session_id=session_id,
            workspace=self.workspace,
            created_at=now,
            updated_at=now,
            status="running",
            metadata=metadata or {},
        )

        self.current_session = session
        self._save_session(session)

        return session

    def load_session(self, session_id: str) -> Optional[Session]:
        """Load existing session

        Args:
            session_id: Session identifier

        Returns:
            Session object or None if not found
        """
        session_file = self.sessions_dir / f"{session_id}.toon"

        if not session_file.exists():
            return None

        try:
            toon_data = session_file.read_text()
            parsed = parse_toon(toon_data)

            if isinstance(parsed, list) and len(parsed) > 0:
                session_data = parsed[0]
            else:
                session_data = parsed if isinstance(parsed, dict) else {}

            checkpoints = [Checkpoint(**cp) for cp in session_data.get("checkpoints", [])]
            failures = [FailureSignature(**fs) for fs in session_data.get("failures", [])]

            session = Session(
                session_id=session_data.get("session_id", ""),
                workspace=Path(session_data.get("workspace", "")),
                created_at=session_data.get("created_at", ""),
                updated_at=session_data.get("updated_at", ""),
                status=session_data.get("status", "unknown"),
                current_phase=session_data.get("current_phase"),
                checkpoints=checkpoints,
                metadata=session_data.get("metadata", {}),
                failures=failures,
            )

            self.current_session = session
            return session

        except Exception as e:
            print(f"Error loading session {session_id}: {e}")
            return None

    def save_checkpoint(self, phase: str, status: str, data: Dict[str, Any]) -> Checkpoint:
        """Save phase checkpoint for resume

        Args:
            phase: Phase identifier (L1, L2, L3, L4)
            status: Phase status (in_progress, completed, failed)
            data: Phase-specific data to persist

        Returns:
            Checkpoint object
        """
        if not self.current_session:
            raise RuntimeError("No active session")

        now = datetime.now().isoformat()
        checkpoint = Checkpoint(phase=phase, timestamp=now, status=status, data=data)

        self.current_session.checkpoints.append(checkpoint)
        self.current_session.current_phase = phase
        self.current_session.updated_at = now
        self.current_session.status = "running" if status == "in_progress" else "completed"

        self._save_session(self.current_session)

        return checkpoint

    def load_checkpoint(self, session_id: str, phase: str) -> Optional[Checkpoint]:
        """Load specific checkpoint from session

        Args:
            session_id: Session identifier
            phase: Phase identifier

        Returns:
            Checkpoint object or None if not found
        """
        session = self.load_session(session_id)
        if not session:
            return None

        for cp in session.checkpoints:
            if cp.phase == phase:
                return cp

        return None

    def record_failure(self, failure: FailureSignature):
        """Record a failure signature for learning

        Args:
            failure: FailureSignature to record
        """
        if not self.current_session:
            raise RuntimeError("No active session")

        self.current_session.failures.append(failure)
        self._save_session(self.current_session)

    def get_failures(self, session_id: Optional[str] = None) -> List[FailureSignature]:
        """Get failures from session

        Args:
            session_id: Session ID (uses current if None)

        Returns:
            List of FailureSignature objects
        """
        if session_id:
            session = self.load_session(session_id)
        else:
            session = self.current_session

        if not session:
            return []

        return session.failures

    def finalize_session(self, status: str, metadata: Optional[Dict[str, Any]] = None) -> Session:
        """Save final session summary

        Args:
            status: Final session status (completed, failed)
            metadata: Optional additional metadata

        Returns:
            Finalized Session object
        """
        if not self.current_session:
            raise RuntimeError("No active session")

        self.current_session.status = status
        self.current_session.updated_at = datetime.now().isoformat()

        if metadata:
            self.current_session.metadata.update(metadata)

        self._save_session(self.current_session)

        return self.current_session

    def list_sessions(self) -> List[Session]:
        """List all RRD sessions

        Returns:
            List of Session objects sorted by creation time
        """
        sessions = []

        for session_file in self.sessions_dir.glob("*.toon"):
            try:
                toon_data = session_file.read_text()
                parsed = parse_toon(toon_data)

                if isinstance(parsed, list) and len(parsed) > 0:
                    session_data = parsed[0]
                else:
                    session_data = parsed if isinstance(parsed, dict) else {}

                session = Session(
                    session_id=session_data.get("session_id", ""),
                    workspace=Path(session_data.get("workspace", "")),
                    created_at=session_data.get("created_at", ""),
                    updated_at=session_data.get("updated_at", ""),
                    status=session_data.get("status", "unknown"),
                    current_phase=session_data.get("current_phase"),
                    metadata=session_data.get("metadata", {}),
                )

                sessions.append(session)
            except Exception:
                continue

        return sorted(sessions, key=lambda s: s.created_at, reverse=True)

    def get_session_summary(self, session_id: Optional[str] = None) -> Optional[SessionSummary]:
        """Get session summary for knowledge kernel

        Args:
            session_id: Session ID (uses current if None)

        Returns:
            SessionSummary object or None
        """
        if session_id:
            session = self.load_session(session_id)
        else:
            session = self.current_session

        if not session:
            return None

        return SessionSummary(
            session_id=session.session_id,
            timestamp=session.updated_at,
            total_iterations=len(session.checkpoints),
            status=session.status,
            success_rate=1.0 if session.status == "completed" else 0.0,
            workspace=str(session.workspace),
            phases_completed=[cp.phase for cp in session.checkpoints if cp.status == "completed"],
            failures=session.failures,
        )

    def delete_session(self, session_id: str) -> bool:
        """Delete a session

        Args:
            session_id: Session identifier

        Returns:
            True if deleted successfully
        """
        session_file = self.sessions_dir / f"{session_id}.toon"

        if session_file.exists():
            session_file.unlink()

            if self.current_session and self.current_session.session_id == session_id:
                self.current_session = None

            return True

        return False

    def _save_session(self, session: Session):
        """Save session to file

        Args:
            session: Session object to save
        """
        session_file = self.sessions_dir / f"{session.session_id}.toon"

        session_dict = asdict(session)
        session_dict["workspace"] = str(session.workspace)
        session_dict["checkpoints"] = [asdict(cp) for cp in session.checkpoints]
        session_dict["failures"] = [asdict(fs) for fs in session.failures]

        toon_data = dumps([session_dict])
        session_file.write_text(toon_data)

    def get_checkpoint_data(self, checkpoint: Checkpoint, key: str) -> Any:
        """Get specific data from checkpoint

        Args:
            checkpoint: Checkpoint object
            key: Data key to retrieve

        Returns:
            Data value or None if not found
        """
        return checkpoint.data.get(key)

    def resume_from_checkpoint(self, session_id: str, phase: str) -> Optional[Session]:
        """Resume session from specific checkpoint

        Args:
            session_id: Session identifier
            phase: Phase to resume from

        Returns:
            Session object or None if checkpoint not found
        """
        session = self.load_session(session_id)
        if not session:
            return None

        checkpoint = self.load_checkpoint(session_id, phase)
        if not checkpoint:
            return None

        session.current_phase = phase
        session.status = "running"
        self.current_session = session
        self._save_session(session)

        return session
