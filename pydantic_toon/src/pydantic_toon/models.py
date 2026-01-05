from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional, Union
from enum import Enum


class FieldType(str, Enum):
    """Allowed field types for TOON arrays."""

    INT = "int"
    FLOAT = "float"
    STRING = "string"
    BOOL = "bool"
    DATE = "date"


class ToonHeader(BaseModel):
    """TOON document header with version and format identification."""

    version: str = Field(default="1.0", description="TOON format version (e.g., '1.0')")
    format_id: str = Field(default="toon", description="File format identifier")


class ToonMetadata(BaseModel):
    """Metadata for TOON arrays including length and field count."""

    array_length: int = Field(description="Expected number of array elements")
    field_count: int = Field(description="Number of fields per row")

    @field_validator("array_length")
    def validate_array_length_positive(cls, v):
        if v <= 0:
            raise ValueError("array_length must be positive")
        return v

    @field_validator("field_count")
    def validate_field_count_positive(cls, v):
        if v <= 0:
            raise ValueError("field_count must be positive")
        return v


class ToonFieldDefinition(BaseModel):
    """Definition of a single field in TOON array."""

    name: str = Field(description="Field name (snake_case)")
    type: FieldType = Field(description="Field type")
    required: bool = Field(default=True, description="Whether field is mandatory")

    @field_validator("name")
    def validate_snake_case(cls, v):
        if not v.replace("_", "").isalnum():
            raise ValueError(f'Field name "{v}" must be alphanumeric with underscores only')
        return v


class ToonArray(BaseModel):
    """TOON array with metadata, field definitions, and data."""

    metadata: ToonMetadata
    fields: List[ToonFieldDefinition]
    data: List[Dict[str, Any]]

    @field_validator("fields")
    def no_duplicate_fields(cls, v):
        field_names = [f.name for f in v]
        if len(field_names) != len(set(field_names)):
            duplicates = [name for name in field_names if field_names.count(name) > 1]
            raise ValueError(f"Duplicate field names: {duplicates}")
        return v

    @field_validator("data")
    def validate_data_consistency(cls, v, info):
        metadata = info.data.get("metadata")
        if metadata and len(v) != metadata.array_length:
            raise ValueError(
                f"Data length ({len(v)}) does not match metadata.array_length ({metadata.array_length})"
            )
        return v

    @field_validator("data")
    def validate_field_count(cls, v, info):
        metadata = info.data.get("metadata")
        if metadata:
            expected_fields = metadata.field_count
            for i, row in enumerate(v):
                if not isinstance(row, dict):
                    raise ValueError(f"Row {i} must be a dictionary")
                if len(row) != expected_fields:
                    raise ValueError(f"Row {i} has {len(row)} fields, expected {expected_fields}")
        return v

    @field_validator("data")
    def validate_field_types(cls, v, info):
        """Validate that actual data types match declared field types."""
        fields = info.data.get("fields")

        if not fields:
            return v

        # Type mapping for validation
        type_map = {
            FieldType.INT: int,
            FieldType.FLOAT: (float, int),
            FieldType.STRING: str,
            FieldType.BOOL: bool,
            FieldType.DATE: str,  # Date is stored as string
        }

        for row_idx, row in enumerate(v):
            for field in fields:
                val = row.get(field.name)
                expected_type = type_map.get(field.type)

                # Skip validation if value is None or no type mapping
                if val is None or expected_type is None:
                    continue

                # Check type
                if not isinstance(val, expected_type):
                    raise ValueError(
                        f"Row {row_idx}, Field '{field.name}': "
                        f"Expected {field.type.value}, got {type(val).__name__}"
                    )
        return v

    def to_toon_dict(self) -> Dict[str, Any]:
        """
        Convert ToonArray to TOON-optimized dictionary.

        Returns:
            Dictionary with TOON format structure
        """
        field_names = [f.name for f in self.fields]
        array_length = len(self.data)

        # TOON format: key[N]{field1,field2,...}:
        toon_key = f"array[{array_length}]{{{','.join(field_names)}}}"

        # Convert data to list of lists for tabular format
        toon_data = [[row.get(f.name) for f in self.fields] for row in self.data]

        return {toon_key: toon_data}


class ToonDocument(BaseModel):
    """Complete TOON document with header, root objects, and arrays."""

    header: ToonHeader
    root: Dict[str, Any] = Field(default_factory=dict, description="Root-level key-value pairs")
    arrays: Dict[str, ToonArray] = Field(default_factory=dict, description="Named TOON arrays")

    @field_validator("arrays")
    def validate_array_names(cls, v):
        for name in v.keys():
            if not name.replace("_", "").isalnum():
                raise ValueError(f'Array name "{name}" must be snake_case')
        return v

    def to_toon_dict(self) -> Dict[str, Any]:
        """
        Convert ToonDocument to TOON-optimized dictionary.

        Returns:
            Dictionary with TOON format structure
        """
        toon_dict = {}

        # Add header as comments
        toon_dict["# version"] = self.header.version
        toon_dict["# format"] = self.header.format_id

        # Add root-level key-value pairs
        toon_dict.update(self.root)

        # Add arrays in TOON format
        for array_name, array_data in self.arrays.items():
            toon_dict.update(array_data.to_toon_dict())

        return toon_dict


class ToonFormatError(Exception):
    """Custom exception for TOON formatting errors."""

    pass
