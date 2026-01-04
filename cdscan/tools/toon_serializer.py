#!/usr/bin/env python3
"""
TOON Format Serializer

Converts Python data structures to TOON (Token-Oriented Object Notation) format,
optimized for LLM consumption with ~40% fewer tokens than JSON.

TOON Syntax:
- [N] - Array size declaration
- {field1, field2} - Column headers (declared once, not per row)
- | - Value separator
- Indentation shows nesting

Example:
    [3] {file, functions, complexity}
    auth.py | 12 | medium
    database.py | 8 | low
    api.py | 25 | high
"""

from typing import Any, Dict, List
from datetime import datetime


class ToonSerializer:
    """Serializes Python data structures to TOON format."""

    def __init__(self, indent_size: int = 2):
        """
        Initialize TOON serializer.

        Args:
            indent_size: Number of spaces per indentation level
        """
        self.indent_size = indent_size

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
        indent = ' ' * (indent_level * self.indent_size)

        for key, value in data.items():
            if isinstance(value, list) and len(value) >= 5 and self._is_uniform_list(value):
                # Use tabular TOON format for uniform lists
                lines.append(f"{indent}{key}:")
                lines.append(self._serialize_uniform_list(value, indent_level + 1))
            elif isinstance(value, list):
                # Use regular format for small/non-uniform lists
                lines.append(f"{indent}{key}:")
                lines.append(self._serialize_list(value, indent_level + 1))
            elif isinstance(value, dict):
                # Nested dictionary
                lines.append(f"{indent}{key}:")
                lines.append(self._serialize_dict(value, indent_level + 1))
            else:
                # Simple key-value pair
                lines.append(f"{indent}{key}: {self._serialize_primitive(value)}")

        return '\n'.join(lines)

    def _serialize_list(self, data: List, indent_level: int) -> str:
        """Serialize list to TOON format."""
        if not data:
            return ' ' * (indent_level * self.indent_size) + "[]"

        indent = ' ' * (indent_level * self.indent_size)

        # If all items are strings, use simplified format
        if all(isinstance(item, str) for item in data):
            header_line = f"{indent}[{len(data)}]"
            return header_line + '\n' + '\n'.join([f"{indent}{item}" for item in data])

        # Check if this is a uniform list suitable for tabular format
        if len(data) >= 5 and self._is_uniform_list(data):
            return self._serialize_uniform_list(data, indent_level)

        # Otherwise, serialize as regular list
        lines = []

        for item in data:
            if isinstance(item, dict):
                # Multi-line dict item
                lines.append(f"{indent}-")
                lines.append(self._serialize_dict(item, indent_level + 1))
            elif isinstance(item, list):
                lines.append(f"{indent}- {self._serialize_list(item, indent_level + 1)}")
            else:
                lines.append(f"{indent}- {self._serialize_primitive(item)}")

        return '\n'.join(lines)

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
        return all(isinstance(item, dict) and set(item.keys()) == first_keys for item in data)

    def _serialize_uniform_list(self, data: List[Dict], indent_level: int) -> str:
        """
        Serialize uniform list using TOON tabular format.

        Args:
            data: List of dictionaries with identical keys
            indent_level: Current indentation level

        Returns:
            TOON tabular format string
        """
        if not data:
            return ""

        lines = []
        indent = ' ' * (indent_level * self.indent_size)

        # Get column headers from first item
        headers = list(data[0].keys())

        # Write header: [N] {field1, field2, ...}
        header_line = f"{indent}[{len(data)}] {{{', '.join(headers)}}}"
        lines.append(header_line)

        # Write data rows
        for item in data:
            values = [self._serialize_cell_value(item[key]) for key in headers]
            row = ' | '.join(values)
            lines.append(f"{indent}{row}")

        return '\n'.join(lines)

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
            escaped = value.replace('|', '\\|').replace('\n', ' ')
            if ' ' in escaped or '|' in value or ':' in escaped:
                return f'"{escaped}"'
            return escaped
        elif isinstance(value, (int, float)):
            return str(value)
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
            [a, b, c] -> "a;b;c"
            [{name: foo}, {name: bar}] -> "foo;bar" (extracts key values)
        """
        if not data:
            return "-"

        # If list of dicts with 'name' key, extract names
        if all(isinstance(item, dict) and 'name' in item for item in data):
            names = [str(item['name']) for item in data]
            if len(names) <= 5:
                return ';'.join(names)
            return f"{';'.join(names[:3])}...(+{len(names)-3})"

        # If list of primitives, join with semicolons
        if all(isinstance(item, (str, int, float, bool)) for item in data):
            items = [self._serialize_primitive(item) for item in data]
            if len(items) <= 5:
                return ';'.join(items)
            return f"{';'.join(items[:3])}...(+{len(items)-3})"

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
        if 'name' in data:
            name = data['name']
            if 'line' in data:
                result = f"{name}@{data['line']}"
                # Add params count if present
                if 'params' in data and isinstance(data['params'], list):
                    result += f"({len(data['params'])}p)"
                return result
            return str(name)

        # For statement/line pattern (imports)
        if 'statement' in data:
            stmt = data['statement']
            # Extract module name from import statement
            if stmt.startswith('import '):
                return stmt[7:].split()[0]
            elif stmt.startswith('from '):
                parts = stmt.split()
                if len(parts) >= 2:
                    return parts[1]
            return stmt[:30] + '...' if len(stmt) > 30 else stmt

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
            # Escape pipes and newlines in strings
            escaped = value.replace('|', '\\|').replace('\n', ' ')
            # Only quote if contains spaces or special chars
            if ' ' in escaped or '|' in value or ':' in escaped:
                return f'"{escaped}"'
            return escaped
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, list):
            return self._serialize_inline_list(value)
        elif isinstance(value, dict):
            return self._serialize_inline_dict(value)
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
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(toon_str)

    def serialize_to_file(self, data: Any, file_path: str):
        """
        Alias for dump method for test compatibility.

        Args:
            data: Data to serialize
            file_path: Output file path
        """
        self.dump(data, file_path)

    def _get_indent(self, level: int) -> str:
        """
        Get indentation string for given level.

        Args:
            level: Indentation level

        Returns:
            Indentation string
        """
        return ' ' * (level * self.indent_size)


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
