"""Configuration loader for RRD"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict
from core.data_types import Config


class RRDConfig:
    """Manages RRD configuration with environment variable support"""

    DEFAULT_CONFIG_PATH = ".claude/rrd_config.yaml"
    DEFAULT_TOOLS_PATH = Path.home() / ".claude" / "skills"

    def __init__(self, config_path: str | None = None):
        """Load RRD configuration from YAML file with environment variable resolution

        Args:
            config_path: Path to config file (default: .claude/rrd_config.yaml or RRD_CONFIG_PATH env var)
        """
        self.config_path = Path(
            config_path or os.getenv("RRD_CONFIG_PATH", self.DEFAULT_CONFIG_PATH)
        )
        self._config = self._load_config()
        self._resolve_tool_paths()

    def _load_config(self) -> Dict[str, Any]:
        """Load and parse YAML configuration file"""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"RRD config file not found: {self.config_path}\n"
                f"Set RRD_CONFIG_PATH environment variable or create {self.DEFAULT_CONFIG_PATH}"
            )

        with open(self.config_path) as f:
            return yaml.safe_load(f) or {}

    def _resolve_tool_paths(self) -> None:
        """Resolve ${RRD_TOOLS_PATH} placeholders in tool paths"""
        tools_path = Path(os.getenv("RRD_TOOLS_PATH", str(self.DEFAULT_TOOLS_PATH)))
        self._resolve_tools_section(tools_path)
        self._resolve_paths_section()

    def _resolve_tools_section(self, tools_path: Path) -> None:
        """Resolve tool path templates to absolute paths

        Args:
            tools_path: Base path for tool directory
        """
        if "tools" not in self._config:
            self._config["tools"] = {}

        for tool, path_template in self._config["tools"].items():
            self._config["tools"][tool] = self._resolve_path_template(
                path_template, tools_path
            )

    def _resolve_paths_section(self) -> None:
        """Convert paths section to Path objects"""
        if "paths" not in self._config:
            self._config["paths"] = {}

        for key in ["workspace", "knowledge_kernel", "session_logs", "backup_dir"]:
            if key in self._config["paths"]:
                self._config["paths"][key] = self._to_path(self._config["paths"][key])

    def _resolve_path_template(
        self, path_template: str | Path, tools_path: Path
    ) -> Path:
        """
        Resolve path template, expanding ${RRD_TOOLS_PATH} placeholder

        Args:
            path_template: Path template (may contain ${RRD_TOOLS_PATH})
            tools_path: Base path for RRD tools

        Returns:
            Resolved Path object
        """
        if isinstance(path_template, str):
            path_str = path_template.replace("${RRD_TOOLS_PATH}", str(tools_path))
            return Path(path_str)
        return Path(path_template)

    def _to_path(self, path_value: str | Path) -> Path:
        """
        Convert string or Path value to Path object

        Args:
            path_value: Path value to convert

        Returns:
            Path object
        """
        if isinstance(path_value, str):
            return Path(path_value)
        return path_value

    @property
    def tools(self) -> Dict[str, Path]:
        """Get tool paths"""
        return self._config.get("tools", {})

    @property
    def paths(self) -> Dict[str, Path]:
        """Get project paths"""
        return self._config.get("paths", {})

    @property
    def analysis(self) -> Dict[str, Any]:
        """Get analysis settings"""
        return self._config.get("analysis", {})

    @property
    def knowledge_kernel(self) -> Dict[str, Any]:
        """Get knowledge kernel settings"""
        return self._config.get("knowledge_kernel", {})

    @property
    def quality_gates(self) -> Dict[str, Any]:
        """Get quality gates settings"""
        return self._config.get("quality_gates", {})

    @property
    def cycle_detection(self) -> Dict[str, Any]:
        """Get cycle detection settings"""
        return self._config.get("cycle_detection", {})

    @property
    def patch_management(self) -> Dict[str, Any]:
        """Get patch management settings"""
        return self._config.get("patch_management", {})

    @property
    def llm(self) -> Dict[str, Any]:
        """Get LLM settings"""
        return self._config.get("llm", {})

    def get_tool_path(self, tool_name: str) -> Path:
        """Get path for a specific tool

        Args:
            tool_name: Name of the tool (cdqa, cdscan, dbgctxt, zgit)

        Returns:
            Path to the tool directory
        """
        tool_path = self.tools.get(tool_name)
        if tool_path is None:
            raise KeyError(f"Tool '{tool_name}' not found in configuration")
        return tool_path

    def get_path(self, path_name: str) -> Path:
        """Get path for a specific project path

        Args:
            path_name: Name of the path (workspace, knowledge_kernel, etc.)

        Returns:
            Path to the project directory
        """
        project_path = self.paths.get(path_name)
        if project_path is None:
            raise KeyError(f"Path '{path_name}' not found in configuration")
        return project_path

    def is_incremental_mode(self) -> bool:
        """Check if incremental analysis mode is enabled"""
        return self.analysis.get("incremental_mode", False)

    def get_quality_gates(self, mode: str = "l2") -> Dict[str, Any]:
        """Get quality gate thresholds for a specific mode

        Args:
            mode: Quality gate mode (l2 for drafting, l3 for hardening)

        Returns:
            Dictionary of threshold values
        """
        return self.quality_gates.get(f"{mode}_thresholds", {})

    def to_config(self) -> Config:
        """Convert RRDConfig to core.data_types.Config

        Returns:
            Config object with settings
        """
        config = Config.from_env()

        # Override with RRD-specific settings
        if "cycle_detection" in self._config:
            config.cycle_window = self.cycle_detection.get("window_size", 4)

        if "llm" in self._config:
            config.llm_timeout_seconds = self.llm.get("timeout_seconds", 300)
            config.max_toon_retries = self.llm.get("max_retries", 3)

        if "patch_management" in self._config:
            config.atomic_write_enabled = self.patch_management.get(
                "atomic_write_enabled", True
            )
            config.backup_before_patch = self.patch_management.get(
                "backup_before_patch", True
            )

        return config

    def are_paths_equal(self, path1: str | Path, path2: str | Path) -> bool:
        """Cross-platform path comparison using os.path.samefile()

        This handles different path separators, symbolic links, relative vs absolute paths,
        and case sensitivity differences across OS.

        Args:
            path1: First path to compare
            path2: Second path to compare

        Returns:
            True if paths refer to the same file/directory
        """
        p1 = Path(path1).resolve()
        p2 = Path(path2).resolve()

        if p1.exists() and p2.exists():
            return p1.samefile(p2)
        else:
            return p1 == p2


def load_rrd_config(config_path: str | None = None) -> RRDConfig:
    """Convenience function to load RRD configuration

    Args:
        config_path: Path to config file (default: .claude/rrd_config.yaml or RRD_CONFIG_PATH env var)

    Returns:
        RRDConfig instance
    """
    return RRDConfig(config_path)
