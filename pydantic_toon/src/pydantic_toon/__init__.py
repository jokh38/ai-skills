"""Pydantic-guided TOON formatter.

This package combines Instructor's LLM validation with TOON's token efficiency.
"""

from .models import (
    ToonHeader,
    ToonMetadata,
    ToonFieldDefinition,
    ToonArray,
    ToonDocument,
    ToonFormatError,
    FieldType,
)

from .serializer import pydantic_to_toon, estimate_token_savings
from .formatter import ToonFormatter, create_formatter, stream_to_toon

__all__ = [
    # Models
    "ToonHeader",
    "ToonMetadata",
    "ToonFieldDefinition",
    "ToonArray",
    "ToonDocument",
    "ToonFormatError",
    "FieldType",
    # Serializer
    "pydantic_to_toon",
    "estimate_token_savings",
    # Formatter
    "ToonFormatter",
    "create_formatter",
    "stream_to_toon",
]

__version__ = "0.1.0"
