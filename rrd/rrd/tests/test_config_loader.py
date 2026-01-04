"""Tests for config_loader module"""

import os
import tempfile
from pathlib import Path
import pytest
import yaml

from core.config_loader import load_rrd_config


@pytest.fixture
def temp_dir():
    """Create temporary directory for test config files"""
    temp = Path(tempfile.mkdtemp())
    yield temp


@pytest.fixture
def config_file(temp_dir):
    """Create a test config file"""
    config = {
        "version": "1.0",
        "tools_path": str(temp_dir / "tools"),
        "knowledge_kernel": {"path": str(temp_dir / "kernel.toon"), "max_size": 100},
        "quality_gates": {"l2": {"max_complexity": 15, "min_type_coverage": 80}},
    }

    config_file = temp_dir / "rrd_config.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config, f)

    return config_file


def test_load_rrd_config(config_file):
    """Test loading RRD config from file"""
    config = load_rrd_config(str(config_file))

    assert config["version"] == "1.0"
    assert "tools_path" in config
    assert "knowledge_kernel" in config


def test_load_rrd_config_with_env_override(config_file, monkeypatch):
    """Test loading config with environment variable override"""
    monkeypatch.setenv("RRD_TOOLS_PATH", "/custom/tools")

    config = load_rrd_config(str(config_file))

    assert config["tools_path"] == "/custom/tools"


def test_load_rrd_config_no_env_override(config_file):
    """Test loading config without environment override"""
    config = load_rrd_config(str(config_file))

    assert config["tools_path"] == str(config_file.parent / "tools")


def test_load_rrd_config_invalid_file():
    """Test loading config from invalid file"""
    with pytest.raises(FileNotFoundError):
        load_rrd_config("/nonexistent/config.yaml")


def test_load_rrd_config_invalid_yaml(temp_dir):
    """Test loading config with invalid YAML"""
    invalid_file = temp_dir / "invalid.yaml"
    invalid_file.write_text("invalid: yaml: content: [")

    with pytest.raises(yaml.YAMLError):
        load_rrd_config(str(invalid_file))


def test_load_rrd_config_missing_fields(temp_dir):
    """Test loading config with missing required fields"""
    incomplete_file = temp_dir / "incomplete.yaml"
    incomplete_file.write_text("tools_path: /tools")

    # Should still work, just missing version
    config = load_rrd_config(str(incomplete_file))
    assert "tools_path" in config
