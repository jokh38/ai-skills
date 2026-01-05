#!/usr/bin/env python3
"""
TOON Format Serializer

Converts Python data structures to TOON (Token-Oriented Object Notation) format,
optimized for LLM consumption with ~40% fewer tokens than JSON.

TOON Specification v3.0 Compliance:
- Array headers: key[N]: or key[N]{fields}: (colon required)
- Delimiters: default comma, declare pipe as [N|] if needed
- Key quoting: ^[A-Za-z_][A-Za-z0-9_.]*$ or quoted
- Escaping: only \\, \", \n, \r, \t
- Numbers: canonical decimal form, no exponents
"""

from typing import Any, Dict, List
from datetime import datetime
import re


class ToonSerializer:
    """Serializes Python data structures to TOON format (spec v3.0 compliant)."""

    def __init__(self, indent_size: int = 2):
        """
        Initialize TOON serializer.

        Args:
            indent_size: Number of spaces per indentation level (default: 2)
        """
        self.indent_size = indent_size

    def _quote_key(self, key: str) -> str:
        """
        Quote key if needed per TOON spec §7.3.

        Unquoted keys must match: ^[A-Za-z_][A-Za-z0-9_.]*$

        Args:
            key: Key string to potentially quote

        Returns:
            Quoted or unquoted key
        """
        if re.match(r"^[A-Za-z_][A-Za-z0-9_.]*$", key):
            return key
        return f'"{key}"'

    def _escape_string(self, value: str) -> str:
        """
        Escape string per TOON spec §7.1.

        Valid escapes: \\, \", \n, \r, \t

        Args:
            value: String to escape

        Returns:
            Escaped string
        """
        return (
            value.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t")
        )

    def _should_quote_string(self, value: str, is_delimited: bool = False) -> bool:
        """
        Determine if string needs quoting per TOON spec §7.2.

        Args:
            value: String value
            is_delimited: True if value is in a delimited context (array cell)

        Returns:
            True if quoting required
        """
        # Must quote if:
        # - Empty
        # - Has leading/trailing whitespace
        # - Equals reserved literals (true, false, null)
        # - Numeric-like
        # - Contains colon, quote, backslash
        # - Contains brackets/braces
        # - Contains control chars
        # - Contains delimiter (if in delimited context)
        # - Equals "-" or starts with "-"

        if not value:
            return True

        if value != value.strip():
            return True

        lower_val = value.lower()
        if lower_val in ("true", "false", "null"):
            return True

        # Numeric-like patterns
        if re.match(r"^-?\d+(?:\.\d+)?(?:e[+-]?\d+)?$", lower_val):
            return True
        if re.match(r"^0\d+$", value):
            return True

        if any(char in value for char in [":", '"', "\\", "[", "]", "{", "}"]):
            return True

        if any(char in value for char in ["\n", "\r", "\t"]):
            return True

        # Delimiter checking (comma is default)
        if is_delimited:
            if "," in value:
                return True

        # Hyphen patterns
        if value == "-" or value.startswith("-"):
            return True

        return False

    def _format_number(self, value: float) -> str:
        """
        Format number in canonical form per TOON spec §2.

        - No exponent notation
        - No leading zeros (except "0")
        - No trailing zeros in fractional part
        - -0 → 0

        Args:
            value: Number to format

        Returns:
            Canonical number string
        """
        # Handle -0
        if value == -0:
            return "0"

        # Convert to string
        num_str = str(value)

        # Remove exponent notation (simple case)
        if "e" in num_str.lower():
            # Use Python's format to remove exponent
            num_str = f"{value:f}"

        # Remove trailing zeros after decimal point
        if "." in num_str:
            num_str = num_str.rstrip("0").rstrip(".")

        return num_str

    def serialize(self, data: Any, indent_level: int = 0) -> str:
        """
        Serialize data to TOON format.

        Args:
            data: Data structure to serialize
            indent_level: Current indentation level

        Returns:
            TOON-formatted string
        """
        if isinstance(data, dict):
            return self._serialize_dict(data, indent_level)
        elif isinstance(data, list):
            return self._serialize_list(data, indent_level)
        elif isinstance(data, (str, int, float, bool, type(None))):
            return self._serialize_primitive(data)
        else:
            # Fallback for other types
            return str(data)

    def _serialize_dict(self, data: Dict, indent_level: int) -> str:
        """Serialize dictionary to TOON format."""
        lines = []
        indent = " " * (indent_level * self.indent_size)

        for key, value in data.items():
            if (
                isinstance(value, list)
                and len(value) >= 5
                and self._is_uniform_list(value)
            ):
                # Use tabular TOON format for uniform lists
                lines.append(self._serialize_uniform_list(value, indent_level, key))
            elif isinstance(value, list):
                # Use regular format for small/non-uniform lists
                lines.append(self._serialize_list(value, indent_level, key))
            elif isinstance(value, dict):
                # Nested dictionary
                lines.append(f"{indent}{self._quote_key(key)}:")
                lines.append(self._serialize_dict(value, indent_level + 1))
            else:
                # Simple key-value pair
                lines.append(
                    f"{indent}{self._quote_key(key)}: {self._serialize_primitive(value)}"
                )

        return "\n".join(lines)

    def _serialize_list(self, data: List, indent_level: int, key: str = "") -> str:
        """
        Serialize list to TOON format.

        Args:
            data: List to serialize
            indent_level: Current indentation level
            key: Key name for array (optional)
        """
        if not data:
            return " " * (indent_level * self.indent_size) + "[]"

        indent = " " * (indent_level * self.indent_size)

        # If all items are strings, use simplified format
        if all(isinstance(item, str) for item in data):
            key_prefix = f"{self._quote_key(key)}" if key else ""
            header_line = f"{indent}{key_prefix}[{len(data)}]:"
            return (
                header_line
                + "\n"
                + "\n".join(
                    [f"{indent}{self._serialize_primitive(item)}" for item in data]
                )
            )

        # Check if this is a uniform list suitable for tabular format
        if len(data) >= 5 and self._is_uniform_list(data):
            return self._serialize_uniform_list(data, indent_level, key)

        # Otherwise, serialize as regular list
        lines = []
        key_prefix = f"{self._quote_key(key)}" if key else ""
        header_line = f"{indent}{key_prefix}[{len(data)}]:"
        lines.append(header_line)

        for item in data:
            if isinstance(item, dict):
                # Multi-line dict item
                lines.append(f"{indent}-")
                lines.append(self._serialize_dict(item, indent_level + 1))
            elif isinstance(item, list):
                lines.append(
                    f"{indent}- {self._serialize_list(item, indent_level + 1)}"
                )
            else:
                lines.append(f"{indent}- {self._serialize_primitive(item)}")

        return "\n".join(lines)

    def _is_uniform_list(self, data: List) -> bool:
        """
        Check if list is uniform (all items are dicts with same keys).

        Args:
            data: List to check

        Returns:
            True if uniform, False otherwise
        """
        if not data or not isinstance(data[0], dict):
            return False

        first_keys = set(data[0].keys())
        return all(
            isinstance(item, dict) and set(item.keys()) == first_keys for item in data
        )

    def _serialize_uniform_list(
        self, data: List[Dict], indent_level: int, key: str = ""
    ) -> str:
        """
        Serialize uniform list using TOON tabular format.

        Args:
            data: List of dictionaries with identical keys
            indent_level: Current indentation level
            key: Key name for array (optional for root arrays)

        Returns:
            TOON tabular format string
        """
        if not data:
            return ""

        lines = []
        indent = " " * (indent_level * self.indent_size)

        # Get column headers from first item
        headers = list(data[0].keys())

        # Write header: key[N] {field1, field2, ...}:
        key_prefix = f"{self._quote_key(key)}" if key else ""
        header_line = f"{indent}{key_prefix}[{len(data)}] {{{', '.join(headers)}}}:"
        lines.append(header_line)

        # Write data rows using comma delimiter (default) at depth + 1
        row_indent = " " * ((indent_level + 1) * self.indent_size)
        for item in data:
            values = [self._serialize_cell_value(item[key]) for key in headers]
            row = ", ".join(values)
            lines.append(f"{row_indent}{row}")

        return "\n".join(lines)

    def _serialize_cell_value(self, value: Any) -> str:
        """
        Serialize a cell value for TOON table format.
        Handles nested lists/dicts with compact inline notation.

        Args:
            value: Cell value (can be primitive, list, or dict)

        Returns:
            Compact string representation for table cell
        """
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, str):
            escaped = self._escape_string(value)
            # Quote if needed (using comma delimiter)
            if self._should_quote_string(escaped, is_delimited=True):
                return f'"{escaped}"'
            return escaped
        elif isinstance(value, int):
            return str(value)
        elif isinstance(value, float):
            return self._format_number(value)
        elif isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, list):
            return self._serialize_inline_list(value)
        elif isinstance(value, dict):
            return self._serialize_inline_dict(value)
        else:
            return str(value)

    def _serialize_inline_list(self, data: List) -> str:
        """
        Serialize list as compact inline format for table cells.

        Examples:
            [a, b, c] -> "a,b,c"
            [{name: foo}, {name: bar}] -> "foo,bar" (extracts key values)
        """
        if not data:
            return "-"

        # If list of dicts with 'name' key, extract names
        if all(isinstance(item, dict) and "name" in item for item in data):
            names = [str(item["name"]) for item in data]
            if len(names) <= 5:
                return ",".join(names)
            return f"{','.join(names[:3])}...(+{len(names) - 3})"

        # If list of primitives, join with commas
        if all(isinstance(item, (str, int, float, bool)) for item in data):
            items = [str(self._serialize_primitive(item)) for item in data]
            if len(items) <= 5:
                return ",".join(items)
            return f"{','.join(items[:3])}...(+{len(items) - 3})"

        # Complex nested structure - show count only
        return f"[{len(data)} items]"

    def _serialize_inline_dict(self, data: Dict) -> str:
        """
        Serialize dict as compact inline format for table cells.

        Examples:
            {name: foo, line: 10} -> "foo@10"
            {type: class, methods: [...]} -> "class(3 methods)"
        """
        if not data:
            return "-"

        # Common patterns for function/class info
        if "name" in data:
            name = data["name"]
            if "line" in data:
                result = f"{name}@{data['line']}"
                # Add params count if present
                if "params" in data and isinstance(data["params"], list):
                    result += f"({len(data['params'])}p)"
                return result
            return str(name)

        # For statement/line pattern (imports)
        if "statement" in data:
            stmt = data["statement"]
            # Extract module name from import statement
            if stmt.startswith("import "):
                return stmt[7:].split()[0]
            elif stmt.startswith("from "):
                parts = stmt.split()
                if len(parts) >= 2:
                    return parts[1]
            return stmt[:30] + "..." if len(stmt) > 30 else stmt

        # Generic: show key count
        return f"{{{len(data)} keys}}"

    def _serialize_primitive(self, value: Any) -> str:
        """
        Serialize primitive value to string.

        Args:
            value: Primitive value to serialize

        Returns:
            String representation
        """
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, str):
            escaped = self._escape_string(value)
            # Quote if needed
            if self._should_quote_string(escaped, is_delimited=False):
                return f'"{escaped}"'
            return escaped
        elif isinstance(value, int):
            return str(value)
        elif isinstance(value, float):
            return self._format_number(value)
        elif isinstance(value, datetime):
            return value.isoformat()
        else:
            return str(value)

    def dumps(self, data: Any) -> str:
        """
        Serialize data to TOON format string.

        Args:
            data: Data to serialize

        Returns:
            TOON-formatted string
        """
        return self.serialize(data, indent_level=0)

    def dump(self, data: Any, file_path: str):
        """
        Serialize data to TOON format and write to file.

        Args:
            data: Data to serialize
            file_path: Output file path
        """
        toon_str = self.dumps(data)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(toon_str)


def dumps(data: Any, indent: int = 2) -> str:
    """
    Convenience function to serialize data to TOON format.

    Args:
        data: Data to serialize
        indent: Indentation size (default: 2)

    Returns:
        TOON-formatted string
    """
    serializer = ToonSerializer(indent_size=indent)
    return serializer.dumps(data)


def dump(data: Any, file_path: str, indent: int = 2):
    """
    Convenience function to serialize data to TOON format file.

    Args:
        data: Data to serialize
        file_path: Output file path
        indent: Indentation size (default: 2)
    """
    serializer = ToonSerializer(indent_size=indent)
    serializer.dump(data, file_path)
