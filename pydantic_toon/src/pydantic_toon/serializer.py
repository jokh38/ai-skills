from typing import Dict, Any, List

try:
    from toon_format import encode
except ImportError:
    toon_available = False
else:
    toon_available = True

from .models import ToonDocument


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
            "toon_format library is not installed. Install it with: pip install toon-format"
        )

    try:
        # Use model's to_toon_dict() method for TOON-optimized structure
        toon_data = model.to_toon_dict()

        # Encode using toon_format library
        toon_string = encode(toon_data)

        return toon_string

    except Exception as e:
        from models import ToonFormatError

        raise ToonFormatError(f"TOON serialization failed: {e}")


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
    savings_percentage = (savings / original_json_tokens * 100) if original_json_tokens > 0 else 0

    return {
        "original_json_tokens": original_json_tokens,
        "estimated_toon_tokens": estimated_toon_tokens,
        "tokens_saved": savings,
        "savings_percentage": round(savings_percentage, 2),
    }
