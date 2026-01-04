"""Cycle detector module for infinite loop prevention"""

from typing import Optional, Set
import logging

from core.data_types import PatchToon, CycleDetectionState


logger = logging.getLogger(__name__)


class CycleDetector:
    """Infinite loop prevention through patch and signature tracking"""

    def __init__(self, window_size: int = 4):
        """
        Initialize cycle detector

        Args:
            window_size: Number of signature sets to track for cycle detection
        """
        self.state = CycleDetectionState()
        self.window_size = window_size

    def check_duplicate_patch(self, patch: PatchToon) -> bool:
        """
        Check if same patch occurred consecutively

        Uses semantic comparison to distinguish between:
        - Actual duplicates (same new_code)
        - Different approaches (different new_code at same location)
        - Refinements (slight modifications to previous new_code)

        Args:
            patch: Current patch to check

        Returns:
            True if duplicate, False otherwise
        """
        current_hash = hash(str(patch))

        if self.state.last_patch is None:
            self._update_patch_state(patch, current_hash)
            return False

        if self._is_exact_duplicate(patch):
            logger.warning(
                f"Exact duplicate patch detected at {patch.file_path}:{patch.line_range}"
            )
            self._update_patch_state(patch, current_hash)
            return True

        if self._is_same_location(patch):
            similarity = self._calculate_code_similarity(
                self.state.last_patch.new_code, patch.new_code
            )

            if similarity > 0.9:
                logger.info(
                    f"Semantic refinement detected (similarity: {similarity:.2f})"
                )
                self._update_patch_state(patch, current_hash)
                return False

            if similarity > 0.5:
                logger.info(
                    f"Different approach detected (similarity: {similarity:.2f})"
                )
                self._update_patch_state(patch, current_hash)
                return False

        self._update_patch_state(patch, current_hash)
        return False

    def _is_exact_duplicate(self, patch: PatchToon) -> bool:
        """
        Check if patch is an exact duplicate of last patch

        Args:
            patch: Current patch to check

        Returns:
            True if exact duplicate, False otherwise
        """
        return (
            self.state.last_patch.file_path == patch.file_path
            and self.state.last_patch.line_range == patch.line_range
            and self.state.last_patch.new_code.strip() == patch.new_code.strip()
        )

    def _is_same_location(self, patch: PatchToon) -> bool:
        """
        Check if patch targets same file and line range as last patch

        Args:
            patch: Current patch to check

        Returns:
            True if same location, False otherwise
        """
        return (
            self.state.last_patch.file_path == patch.file_path
            and self.state.last_patch.line_range == patch.line_range
        )

    def _update_patch_state(self, patch: PatchToon, patch_hash: int) -> None:
        """
        Update state with new patch information

        Args:
            patch: New patch
            patch_hash: Hash of patch
        """
        self.state.last_patch = patch
        self.state.last_patch_hash = patch_hash

    def _calculate_code_similarity(self, code1: str, code2: str) -> float:
        """
        Calculate similarity between two code snippets

        Args:
            code1: First code snippet
            code2: Second code snippet

        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Normalize code
        norm1 = code1.strip().replace(" ", "")
        norm2 = code2.strip().replace(" ", "")

        # Quick check for exact match
        if norm1 == norm2:
            return 1.0

        # Use simple token overlap for similarity
        tokens1 = set(norm1.split("(")[0].split("=")[0].split(")")[0].split())
        tokens2 = set(norm2.split("(")[0].split("=")[0].split(")")[0].split())

        # Calculate Jaccard similarity
        if not tokens1 and not tokens2:
            return 1.0

        if not tokens1 or not tokens2:
            return 0.0

        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)

        return intersection / union if union > 0 else 0.0

    def check_signature_cycle(self, signatures: Set[str]) -> bool:
        """
        Check for signature cycles (e.g., A → B → A patterns)

        Args:
            signatures: Current set of failure signatures

        Returns:
            True if cycle detected, False otherwise
        """
        frozen = frozenset(signatures)

        if frozen in self.state.signature_history:
            logger.warning(f"Signature cycle detected: {frozen}")
            return True

        self.state.signature_history.append(frozen)

        if len(self.state.signature_history) > self.window_size:
            self.state.signature_history = self.state.signature_history[
                -self.window_size :
            ]

        return False

    def update_history(self, patch: PatchToon, signatures: Set[str]) -> None:
        """
        Update detection state with new patch and signatures

        Args:
            patch: Applied patch
            signatures: Current failure signatures
        """
        patch_hash = hash(str(patch))
        self.state.patch_hash_history.append(patch_hash)
        self.state.last_patch = patch

        frozen = frozenset(signatures)
        self.state.signature_history.append(frozen)

        if len(self.state.signature_history) > self.window_size:
            self.state.signature_history = self.state.signature_history[
                -self.window_size :
            ]

        self.state.last_patch_hash = patch_hash

    def reset(self) -> None:
        """Reset detection state"""
        self.state.reset()

    def get_state(self) -> CycleDetectionState:
        """
        Get current detection state

        Returns:
            Current CycleDetectionState
        """
        return self.state

    def detect_pattern(self, pattern_length: int = 2) -> Optional[list[str]]:
        """
        Detect repeating patterns in signature history

        Args:
            pattern_length: Length of pattern to look for

        Returns:
            Detected pattern as list of signature sets, or None
        """
        if len(self.state.signature_history) < pattern_length * 2:
            return None

        history = list(self.state.signature_history)
        for i in range(len(history) - pattern_length * 2 + 1):
            pattern = history[i : i + pattern_length]
            next_pattern = history[i + pattern_length : i + pattern_length * 2]

            if pattern == next_pattern:
                return [str(s) for s in pattern]

        return None
