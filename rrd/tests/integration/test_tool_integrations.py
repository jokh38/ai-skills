"""Tests for tool integrations"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from integrations.cdqa_integration import CdqaIntegration, QualityReport, GateResults, AutoFix
from integrations.cdscan_integration import CdscanIntegration, CodebaseAnalysis, ComplexityHotspot
from integrations.dbgctxt_integration import DbgctxtIntegration, DebugContext
from integrations.zgit_integration import ZgitIntegration, CommitResult


class TestCdqaIntegration:
    """Test suite for CdqaIntegration"""

    @pytest.fixture
    def config(self):
        """Create mock config"""
        config = Mock()
        config.get_tool_path = Mock(side_effect=KeyError("Tool not found"))
        return config

    @pytest.fixture
    def cdqa(self, config):
        """Create CdqaIntegration instance"""
        return CdqaIntegration(config)

    def test_initialization(self, cdqa):
        """Test cdqa integration initializes"""
        assert cdqa.config is not None
        assert cdqa.parser is not None
        assert cdqa.tool_path == "cdqa"

    @patch("subprocess.run")
    def test_run_quality_check_success(self, mock_run, cdqa, tmp_path):
        """Test running quality check successfully"""
        # Mock subprocess result
        mock_run.return_value = Mock(returncode=0, stdout="[1] {quality_score}\n85")

        # Run quality check
        report = cdqa.run_quality_check(workspace=tmp_path, mode="drafting")

        # Verify
        assert report is not None
        assert report.quality_score == 85.0

    @patch("subprocess.run")
    def test_run_quality_check_failure(self, mock_run, cdqa, tmp_path):
        """Test handling quality check failure"""
        # Mock subprocess result
        mock_run.return_value = Mock(returncode=1, stderr="cdqa: error")

        # Run quality check should raise error
        with pytest.raises(RuntimeError):
            cdqa.run_quality_check(workspace=tmp_path)

    def test_check_quality_gates_pass(self, cdqa):
        """Test quality gates passing"""
        report = QualityReport(
            lint_issues=[],
            type_errors=[],
            security_issues=[],
            complexity_metrics={},
            quality_score=90.0,
            raw_output="",
        )

        thresholds = {
            "max_critical": 0,
            "max_type_errors": 0,
            "max_security_high": 0,
            "min_quality_score": 85.0,
        }

        results = cdqa.check_quality_gates(report, thresholds)

        assert results.passed is True
        assert len(results.failed_gates) == 0

    def test_check_quality_gates_fail(self, cdqa):
        """Test quality gates failing"""
        report = QualityReport(
            lint_issues=[{"severity": "critical", "code": "E001"}],
            type_errors=[{"code": "type-error"}],
            security_issues=[],
            complexity_metrics={},
            quality_score=70.0,
            raw_output="",
        )

        thresholds = {
            "max_critical": 0,
            "max_type_errors": 0,
            "max_security_high": 0,
            "min_quality_score": 85.0,
        }

        results = cdqa.check_quality_gates(report, thresholds)

        assert results.passed is False
        assert len(results.failed_gates) > 0


class TestCdscanIntegration:
    """Test suite for CdscanIntegration"""

    @pytest.fixture
    def config(self):
        """Create mock config"""
        config = Mock()
        config.get_tool_path = Mock(side_effect=KeyError("Tool not found"))
        return config

    @pytest.fixture
    def cdscan(self, config):
        """Create CdscanIntegration instance"""
        return CdscanIntegration(config)

    def test_initialization(self, cdscan):
        """Test cdscan integration initializes"""
        assert cdscan.config is not None
        assert cdscan.parser is not None
        assert cdscan.tool_path == "cdscan"

    @patch("subprocess.run")
    def test_analyze_codebase_success(self, mock_run, cdscan, tmp_path):
        """Test analyzing codebase successfully"""
        # Mock subprocess result
        mock_run.return_value = Mock(returncode=0, stdout="[1] {file_count}\n5")

        # Run analysis
        analysis = cdscan.analyze_codebase(workspace=tmp_path, pattern="**/*.py")

        # Verify
        assert analysis is not None
        assert isinstance(analysis, CodebaseAnalysis)

    def test_get_complexity_hotspots(self, cdscan):
        """Test extracting complexity hotspots"""
        analysis = CodebaseAnalysis(
            structure={},
            file_summary=[
                {"path": "test.py", "complexity": 15},
                {"path": "simple.py", "complexity": 5},
            ],
            function_summary=[
                {
                    "name": "complex_func",
                    "file": "test.py",
                    "cognitive_complexity": 15,
                    "start_line": 1,
                    "end_line": 100,
                    "lines_of_code": 150,
                    "parameter_count": 8,
                },
                {
                    "name": "simple_func",
                    "file": "simple.py",
                    "cognitive_complexity": 5,
                    "start_line": 1,
                    "end_line": 10,
                    "lines_of_code": 20,
                    "parameter_count": 2,
                },
            ],
            imports={},
            hotspots=[],
            raw_output="",
        )

        hotspots = cdscan.get_complexity_hotspots(analysis, threshold=12)

        assert len(hotspots) == 1
        assert hotspots[0].function_name == "complex_func"
        assert hotspots[0].complexity == 15

    def test_get_test_files(self, cdscan):
        """Test finding test files"""
        analysis = CodebaseAnalysis(
            structure={},
            file_summary=[
                {"path": "test_calculator.py"},
                {"path": "calculator.py"},
                {"path": "test_utils.py"},
            ],
            function_summary=[],
            imports={},
            hotspots=[],
            raw_output="",
        )

        test_files = cdscan.get_test_files(analysis)

        assert len(test_files) == 2
        assert any("test_calculator.py" in str(f) for f in test_files)
        assert any("test_utils.py" in str(f) for f in test_files)


class TestZgitIntegration:
    """Test suite for ZgitIntegration"""

    @pytest.fixture
    def config(self):
        """Create mock config"""
        config = Mock()
        config.get_tool_path = Mock(side_effect=KeyError("Tool not found"))
        return config

    @pytest.fixture
    def zgit(self, config):
        """Create ZgitIntegration instance"""
        return ZgitIntegration(config)

    def test_initialization(self, zgit):
        """Test zgit integration initializes"""
        assert zgit.config is not None
        assert zgit.tool_path == "zgit"

    @patch("subprocess.run")
    def test_commit_with_context_success(self, mock_run, zgit):
        """Test committing with context successfully"""
        # Mock subprocess result
        mock_run.return_value = Mock(returncode=0, stdout="Committed: abc123def456")

        # Commit
        result = zgit.commit_with_context(
            message="Test commit", context={"session_id": "test123"}, stage_all=True
        )

        # Verify
        assert result.success is True
        assert "abc123" in result.commit_hash

    @patch("subprocess.run")
    def test_check_repo_status(self, mock_run, zgit):
        """Test checking repository status"""
        # Mock subprocess result
        mock_run.return_value = Mock(returncode=0, stdout="M calculator.py\nA new_file.py")

        # Check status
        status = zgit.check_repo_status()

        # Verify
        assert status["has_changes"] is True

    @patch("subprocess.run")
    def test_stage_files(self, mock_run, zgit):
        """Test staging files"""
        # Mock subprocess result
        mock_run.return_value = Mock(returncode=0)

        # Stage files
        success = zgit.stage_files(["calculator.py", "new_file.py"])

        # Verify
        assert success is True
