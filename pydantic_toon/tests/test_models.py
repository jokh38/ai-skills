"""
Unit tests for pydantic_toon models.

Run with: pytest tests/test_models.py -v
"""

import pytest
from pydantic import ValidationError

from pydantic_toon.models import (
    ToonHeader,
    ToonMetadata,
    ToonFieldDefinition,
    ToonArray,
    ToonDocument,
    ToonFormatError,
    FieldType,
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
        field = ToonFieldDefinition(name="employee_id", type=FieldType.INT, required=True)
        assert field.name == "employee_id"
        assert field.type == FieldType.INT
        assert field.required is True

    def test_field_with_string_type(self):
        """Test field with string type."""
        field = ToonFieldDefinition(name="name", type="string", required=True)
        assert field.type == FieldType.STRING

    def test_field_defaults(self):
        """Test field with default required value."""
        field = ToonFieldDefinition(name="name", type=FieldType.STRING)
        assert field.required is True

    def test_invalid_field_name(self):
        """Test that invalid field names fail validation."""
        with pytest.raises(ValidationError, match="must be alphanumeric"):
            ToonFieldDefinition(name="name@123", type=FieldType.STRING)

    def test_invalid_field_type(self):
        """Test that invalid type fails validation."""
        with pytest.raises(ValidationError):
            ToonFieldDefinition(name="name", type="unknown_type")


class TestToonArray:
    """Test ToonArray model."""

    def test_valid_array(self):
        """Test creating a valid TOON array."""
        array = ToonArray(
            metadata=ToonMetadata(array_length=3, field_count=2),
            fields=[
                ToonFieldDefinition(name="id", type=FieldType.INT),
                ToonFieldDefinition(name="name", type=FieldType.STRING),
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
        with pytest.raises(ValidationError, match="does not match metadata.array_length"):
            ToonArray(
                metadata=ToonMetadata(array_length=5, field_count=2),
                fields=[
                    ToonFieldDefinition(name="id", type=FieldType.INT),
                    ToonFieldDefinition(name="name", type=FieldType.STRING),
                ],
                data=[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
            )

    def test_duplicate_field_names(self):
        """Test that duplicate field names fail validation."""
        with pytest.raises(ValidationError, match="Duplicate field names"):
            ToonArray(
                metadata=ToonMetadata(array_length=3, field_count=3),
                fields=[
                    ToonFieldDefinition(name="id", type=FieldType.INT),
                    ToonFieldDefinition(name="name", type=FieldType.STRING),
                    ToonFieldDefinition(name="id", type=FieldType.STRING),
                ],
                data=[],
            )

    def test_field_count_mismatch(self):
        """Test that field count mismatch fails validation."""
        with pytest.raises(ValidationError, match="has 2 fields, expected 3"):
            ToonArray(
                metadata=ToonMetadata(array_length=3, field_count=3),
                fields=[
                    ToonFieldDefinition(name="id", type=FieldType.INT),
                    ToonFieldDefinition(name="name", type=FieldType.STRING),
                    ToonFieldDefinition(name="department", type=FieldType.STRING),
                ],
                data=[
                    {"id": 1, "name": "Alice"},
                    {"id": 2, "name": "Bob", "department": "Sales"},
                    {"id": 3, "name": "Charlie", "department": "Marketing"},
                ],
            )

    def test_field_type_mismatch(self):
        """Test that field type mismatch fails validation."""
        with pytest.raises(ValidationError, match="Expected int, got str"):
            ToonArray(
                metadata=ToonMetadata(array_length=2, field_count=2),
                fields=[
                    ToonFieldDefinition(name="id", type=FieldType.INT),
                    ToonFieldDefinition(name="name", type=FieldType.STRING),
                ],
                data=[
                    {"id": "not_an_int", "name": "Alice"},  # Invalid type
                    {"id": 2, "name": "Bob"},
                ],
            )

    def test_valid_float_field(self):
        """Test that float type accepts both float and int."""
        array = ToonArray(
            metadata=ToonMetadata(array_length=2, field_count=1),
            fields=[ToonFieldDefinition(name="price", type=FieldType.FLOAT)],
            data=[
                {"price": 99.99},
                {"price": 100},  # int should be accepted for float field
            ],
        )
        assert len(array.data) == 2

    def test_to_toon_dict(self):
        """Test to_toon_dict method."""
        array = ToonArray(
            metadata=ToonMetadata(array_length=2, field_count=2),
            fields=[
                ToonFieldDefinition(name="id", type=FieldType.INT),
                ToonFieldDefinition(name="name", type=FieldType.STRING),
            ],
            data=[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
        )

        toon_dict = array.to_toon_dict()

        assert "array[2]{id,name}" in toon_dict
        assert toon_dict["array[2]{id,name}"] == [[1, "Alice"], [2, "Bob"]]


class TestToonDocument:
    """Test ToonDocument model."""

    def test_valid_document(self):
        """Test creating a valid TOON document."""
        doc = ToonDocument(
            header=ToonHeader(version="1.0", format_id="toon"), root={"total": 10}, arrays={}
        )
        assert doc.header.version == "1.0"
        assert doc.root["total"] == 10

    def test_document_with_arrays(self):
        """Test document with arrays."""
        doc = ToonDocument(
            header=ToonHeader(),
            root={},
            arrays={
                "employees": ToonArray(
                    metadata=ToonMetadata(array_length=2, field_count=2),
                    fields=[
                        ToonFieldDefinition(name="id", type=FieldType.INT),
                        ToonFieldDefinition(name="name", type=FieldType.STRING),
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
                header=ToonHeader(),
                arrays={
                    "Employee-Data": ToonArray(
                        metadata=ToonMetadata(array_length=2, field_count=1),
                        fields=[ToonFieldDefinition(name="id", type=FieldType.INT)],
                        data=[{"id": 1}, {"id": 2}],
                    )
                },
            )

    def test_to_toon_dict(self):
        """Test to_toon_dict method."""
        doc = ToonDocument(
            header=ToonHeader(version="1.0", format_id="toon"),
            root={"total": 10},
            arrays={
                "employees": ToonArray(
                    metadata=ToonMetadata(array_length=2, field_count=2),
                    fields=[
                        ToonFieldDefinition(name="id", type=FieldType.INT),
                        ToonFieldDefinition(name="name", type=FieldType.STRING),
                    ],
                    data=[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
                )
            },
        )

        toon_dict = doc.to_toon_dict()

        assert toon_dict["# version"] == "1.0"
        assert toon_dict["# format"] == "toon"
        assert toon_dict["total"] == 10
        assert "array[2]{id,name}" in toon_dict


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


class TestFieldType:
    """Test FieldType enum."""

    def test_field_types(self):
        """Test all field type enum values."""
        assert FieldType.INT.value == "int"
        assert FieldType.FLOAT.value == "float"
        assert FieldType.STRING.value == "string"
        assert FieldType.BOOL.value == "bool"
        assert FieldType.DATE.value == "date"

    def test_field_type_comparison(self):
        """Test field type comparison."""
        assert FieldType.INT == "int"
        assert FieldType.INT == FieldType.INT
        assert FieldType.INT != FieldType.STRING
