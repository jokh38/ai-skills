"""
Unit tests for pydantic_toon models.

Run with: pytest tests/test_models.py -v
"""

import pytest
from pydantic import ValidationError

from models import (
    ToonHeader,
    ToonMetadata,
    ToonFieldDefinition,
    ToonArray,
    ToonDocument,
    ToonFormatError,
)


class TestToonHeader:
    """Test ToonHeader model."""

    def test_valid_header(self):
        """Test creating a valid TOON header."""
        header = ToonHeader(version="1.0", format_id="toon")
        assert header.version == "1.0"
        assert header.format_id == "toon"

    def test_header_defaults(self):
        """Test header with default values."""
        header = ToonHeader()
        assert header.version == "1.0"
        assert header.format_id == "toon"


class TestToonMetadata:
    """Test ToonMetadata model."""

    def test_valid_metadata(self):
        """Test creating valid metadata."""
        metadata = ToonMetadata(array_length=5, field_count=3)
        assert metadata.array_length == 5
        assert metadata.field_count == 3

    def test_negative_array_length(self):
        """Test that negative array_length fails validation."""
        with pytest.raises(ValidationError, match="array_length must be positive"):
            ToonMetadata(array_length=-1, field_count=3)

    def test_zero_array_length(self):
        """Test that zero array_length fails validation."""
        with pytest.raises(ValidationError, match="array_length must be positive"):
            ToonMetadata(array_length=0, field_count=3)

    def test_negative_field_count(self):
        """Test that negative field_count fails validation."""
        with pytest.raises(ValidationError, match="field_count must be positive"):
            ToonMetadata(array_length=5, field_count=-1)


class TestToonFieldDefinition:
    """Test ToonFieldDefinition model."""

    def test_valid_field(self):
        """Test creating a valid field definition."""
        field = ToonFieldDefinition(name="employee_id", type="int", required=True)
        assert field.name == "employee_id"
        assert field.type == "int"
        assert field.required is True

    def test_field_defaults(self):
        """Test field with default required value."""
        field = ToonFieldDefinition(name="name", type="string")
        assert field.required is True

    def test_invalid_field_name(self):
        """Test that invalid field names fail validation."""
        with pytest.raises(ValidationError, match="must be alphanumeric"):
            ToonFieldDefinition(name="name@123", type="string")


class TestToonArray:
    """Test ToonArray model."""

    def test_valid_array(self):
        """Test creating a valid TOON array."""
        array = ToonArray(
            metadata=ToonMetadata(array_length=3, field_count=2),
            fields=[
                ToonFieldDefinition(name="id", type="int"),
                ToonFieldDefinition(name="name", type="string"),
            ],
            data=[
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"},
                {"id": 3, "name": "Charlie"},
            ],
        )
        assert len(array.data) == 3

    def test_array_length_mismatch(self):
        """Test that array length mismatch fails validation."""
        with pytest.raises(
            ValidationError, match="does not match metadata.array_length"
        ):
            ToonArray(
                metadata=ToonMetadata(array_length=5, field_count=2),
                fields=[
                    ToonFieldDefinition(name="id", type="int"),
                    ToonFieldDefinition(name="name", type="string"),
                ],
                data=[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
            )

    def test_duplicate_field_names(self):
        """Test that duplicate field names fail validation."""
        with pytest.raises(ValidationError, match="Duplicate field names"):
            ToonArray(
                metadata=ToonMetadata(array_length=3, field_count=3),
                fields=[
                    ToonFieldDefinition(name="id", type="int"),
                    ToonFieldDefinition(name="name", type="string"),
                    ToonFieldDefinition(name="id", type="string"),
                ],
                data=[],
            )

    def test_field_count_mismatch(self):
        """Test that field count mismatch fails validation."""
        with pytest.raises(ValidationError, match="expected .* fields"):
            ToonArray(
                metadata=ToonMetadata(array_length=3, field_count=3),
                fields=[
                    ToonFieldDefinition(name="id", type="int"),
                    ToonFieldDefinition(name="name", type="string"),
                    ToonFieldDefinition(name="department", type="string"),
                ],
                data=[
                    {"id": 1, "name": "Alice"},
                    {"id": 2, "name": "Bob", "department": "Sales"},
                    {"id": 3, "name": "Charlie", "department": "Marketing"},
                ],
            )


class TestToonDocument:
    """Test ToonDocument model."""

    def test_valid_document(self):
        """Test creating a valid TOON document."""
        doc = ToonDocument(
            header=ToonHeader(version="1.0", format_id="toon"),
            root={"total": 10},
            arrays={},
        )
        assert doc.header.version == "1.0"
        assert doc.root["total"] == 10

    def test_document_with_arrays(self):
        """Test document with arrays."""
        doc = ToonDocument(
            header=ToonHeader(version="1.0", format_id="toon"),
            root={},
            arrays={
                "employees": ToonArray(
                    metadata=ToonMetadata(array_length=2, field_count=2),
                    fields=[
                        ToonFieldDefinition(name="id", type="int"),
                        ToonFieldDefinition(name="name", type="string"),
                    ],
                    data=[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
                )
            },
        )
        assert "employees" in doc.arrays
        assert len(doc.arrays["employees"].data) == 2

    def test_invalid_array_name(self):
        """Test that invalid array names fail validation."""
        with pytest.raises(ValidationError, match="must be snake_case"):
            ToonDocument(
                header=ToonHeader(version="1.0", format_id="toon"),
                arrays={
                    "Employee-Data": ToonArray(
                        metadata=ToonMetadata(array_length=2, field_count=1),
                        fields=[ToonFieldDefinition(name="id", type="int")],
                        data=[{"id": 1}, {"id": 2}],
                    )
                },
            )


class TestToonFormatError:
    """Test ToonFormatError exception."""

    def test_exception_creation(self):
        """Test creating a ToonFormatError."""
        error = ToonFormatError("Test error message")
        assert str(error) == "Test error message"

    def test_exception_raising(self):
        """Test raising a ToonFormatError."""
        with pytest.raises(ToonFormatError):
            raise ToonFormatError("Test error")
