from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional


class ToonHeader(BaseModel):
    """TOON document header with version and format identification."""

    version: str = Field(description="TOON format version (e.g., '1.0')")
    format_id: str = Field(description="File format identifier")


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
    type: str = Field(description="Field type (string, int, float, bool, date)")
    required: bool = Field(default=True, description="Whether field is mandatory")

    @field_validator("name")
    def validate_snake_case(cls, v):
        if not v.replace("_", "").isalnum():
            raise ValueError(
                f'Field name "{v}" must be alphanumeric with underscores only'
            )
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
                    raise ValueError(
                        f"Row {i} has {len(row)} fields, expected {expected_fields}"
                    )
        return v


class ToonDocument(BaseModel):
    """Complete TOON document with header, root objects, and arrays."""

    header: ToonHeader
    root: Dict[str, Any] = Field(
        default_factory=dict, description="Root-level key-value pairs"
    )
    arrays: Dict[str, ToonArray] = Field(
        default_factory=dict, description="Named TOON arrays"
    )

    @field_validator("arrays")
    def validate_array_names(cls, v):
        for name in v.keys():
            if not name.replace("_", "").isalnum():
                raise ValueError(f'Array name "{name}" must be snake_case')
        return v


class ToonFormatError(Exception):
    """Custom exception for TOON formatting errors."""

    pass
