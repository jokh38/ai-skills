from typing import Dict, Any, List
from models import ToonDocument, ToonArray

try:
    from toon_format import encode
except ImportError:
    toon_available = False
else:
    toon_available = True


def pydantic_to_toon(model: ToonDocument) -> str:
    """
    Convert Pydantic model to TOON string.

    Args:
        model: Pydantic BaseModel instance (ToonDocument)

    Returns:
        TOON formatted string

    Raises:
        ImportError: If toon_format library is not installed
        ToonFormatError: If serialization fails
    """
    if not toon_available:
        raise ImportError(
            "toon_format library is not installed. "
            "Install it with: pip install toon-format"
        )

    try:
        # Convert Pydantic model to dictionary
        model_dict = model.model_dump()

        # Transform dictionary to TOON-optimized structure
        toon_data = optimize_for_toon(model_dict)

        # Encode using toon_format library
        toon_string = encode(toon_data)

        return toon_string

    except Exception as e:
        from models import ToonFormatError

        raise ToonFormatError(f"TOON serialization failed: {e}")


def optimize_for_toon(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Optimize dictionary structure for TOON encoding.

    This function:
    1. Identifies uniform arrays for tabular format
    2. Adds [N] length declarations
    3. Adds {fields} headers
    4. Converts to TOON-optimized structure

    Args:
        data: Dictionary representation of Pydantic model

    Returns:
        TOON-optimized dictionary
    """
    optimized = {}

    # Process header
    if "header" in data:
        header = data["header"]
        optimized["# version"] = header.get("version", "1.0")
        optimized["# format"] = header.get("format_id", "toon")

    # Process root-level key-value pairs
    if "root" in data and data["root"]:
        for key, value in data["root"].items():
            optimized[key] = value

    # Process arrays with tabular optimization
    if "arrays" in data:
        for key, array_data in data["arrays"].items():
            if isinstance(array_data, dict):
                # Check if it's a ToonArray structure
                if (
                    "data" in array_data
                    and "fields" in array_data
                    and "metadata" in array_data
                ):
                    # Uniform array - use tabular TOON format
                    field_names = [f["name"] for f in array_data["fields"]]
                    array_length = len(array_data["data"])

                    # TOON format: key[N]{field1,field2,...}:
                    optimized_key = f"{key}[{array_length}]{{{','.join(field_names)}}}"
                    optimized[optimized_key] = [
                        [row.get(f["name"]) for f in array_data["fields"]]
                        for row in array_data["data"]
                    ]
                else:
                    # Non-uniform array - keep as-is
                    optimized[key] = array_data

    return optimized


def should_use_tabular(data: List[Dict[str, Any]]) -> bool:
    """
    Check if data is uniform enough for tabular TOON format.

    Tabular format is optimal when:
    - All rows have identical keys
    - All values are primitive types (no nested objects/arrays)
    - At least 2 rows

    Args:
        data: List of dictionaries to check

    Returns:
        True if data should use tabular format, False otherwise
    """
    if not data or len(data) < 2:
        return False

    # All rows must have same keys
    first_keys = set(data[0].keys())
    for row in data:
        if set(row.keys()) != first_keys:
            return False

    # All values must be primitive (no nested objects)
    for row in data:
        for value in row.values():
            if isinstance(value, (dict, list)):
                return False

    return True


def estimate_token_savings(original_json_tokens: int) -> Dict[str, Any]:
    """
    Estimate token savings when using TOON format.

    Based on TOON benchmarks, TOON typically saves ~40% tokens
    compared to JSON for uniform arrays of objects.

    Args:
        original_json_tokens: Estimated token count for JSON

    Returns:
        Dictionary with savings information
    """
    estimated_toon_tokens = int(original_json_tokens * 0.6)
    savings = original_json_tokens - estimated_toon_tokens
    savings_percentage = (
        (savings / original_json_tokens * 100) if original_json_tokens > 0 else 0
    )

    return {
        "original_json_tokens": original_json_tokens,
        "estimated_toon_tokens": estimated_toon_tokens,
        "tokens_saved": savings,
        "savings_percentage": round(savings_percentage, 2),
    }


def validate_toon_structure(data: Dict[str, Any]) -> List[str]:
    """
    Validate TOON structure before serialization.

    Args:
        data: Dictionary to validate

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Check header
    if "header" in data:
        header = data["header"]
        if "version" not in header:
            errors.append("Header missing 'version' field")
        if "format_id" not in header:
            errors.append("Header missing 'format_id' field")

    # Check arrays
    if "arrays" in data:
        for array_name, array_data in data["arrays"].items():
            if isinstance(array_data, dict):
                # Check metadata consistency
                if "metadata" in array_data and "data" in array_data:
                    metadata = array_data["metadata"]
                    data_rows = array_data["data"]
                    if metadata.get("array_length") != len(data_rows):
                        errors.append(
                            f"Array '{array_name}': metadata.array_length "
                            f"({metadata.get('array_length')}) != data length ({len(data_rows)})"
                        )

    return errors
