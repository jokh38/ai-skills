"""TOON (Token-Oriented Object Notation) parser and encoder"""

import re
from typing import Any, Dict, List
from core.data_types import (
    FailureSignature,
    PatchToon,
    ActiveContext,
    SessionSummary,
)


class ToonParser:
    """Parser for TOON format"""

    def __init__(self, delimiter: str = "|"):
        self.delimiter = delimiter

    def parse(self, toon_str: str) -> Any:
        """Parse TOON string into Python objects"""
        lines = toon_str.strip().split("\n")
        return self._parse_lines(lines)

    def _parse_lines(self, lines: List[str]) -> Any:
        if not lines:
            return None

        result = {}
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            if not line:
                i += 1
                continue

            if line.startswith("["):
                arr_data, i = self._parse_array_section(lines, i)
                return self._handle_array_result(arr_data, result)

            if "{" in line and "}" in line:
                key, value = self._parse_dict_line(line)
                result[key] = value
                i += 1
                continue

            i += 1

        return result

    def _handle_array_result(self, arr_data: Any, result: Dict[str, Any]) -> Any:
        """
        Handle array parsing result

        Args:
            arr_data: Parsed array data
            result: Current result dictionary

        Returns:
            Final parsed data (either arr_data or updated result)
        """
        if not arr_data and not result:
            return None

        if isinstance(arr_data, list):
            return arr_data

        result.update(arr_data)
        return result

    def _parse_array_section(self, lines: List[str], i: int) -> tuple[Any, int]:
        """
        Parse array section and return data with updated index

        Args:
            lines: All lines to parse from
            i: Current line index

        Returns:
            Tuple of (parsed_data, next_index)
        """
        arr_len, rest = self._extract_array_size(lines[i].strip())
        headers = self._extract_headers(rest) if rest else None
        arr_data = self._parse_array(lines[i + 1 :], arr_len, headers)

        if headers:
            return {"array_0": arr_data}, i + arr_len + 1
        else:
            return arr_data, i + arr_len + 1

    def _extract_array_size(self, line: str) -> tuple[int, str]:
        match = re.match(r"\[(\d+)\](.*)", line)
        if match:
            return int(match.group(1)), match.group(2).strip()
        return 0, ""

    def _extract_headers(self, line: str) -> List[str]:
        match = re.match(r"\{([^}]+)\}", line)
        if match:
            return [h.strip() for h in match.group(1).split(",")]
        return []

    def _parse_array(
        self, lines: List[str], size: int, headers: List[str] | None
    ) -> List[Any]:
        arr = []
        for i in range(min(size, len(lines))):
            line = lines[i].strip()
            if headers:
                values = [v.strip() for v in line.split(self.delimiter)]
                if len(values) == len(headers):
                    row = {headers[j]: values[j] for j in range(len(headers))}
                    arr.append(row)
            else:
                arr.append(line)
        return arr

    def _parse_dict_line(self, line: str) -> tuple[str, Any]:
        match = re.match(r"([^{]+)\{([^}]+)\}", line)
        if match:
            key = match.group(1).strip()
            value = match.group(2).strip()
            return key, value
        return "", ""

    def parse_failure_payload(self, toon_str: str) -> Dict[str, Any]:
        """Parse failure payload TOON"""
        result = self.parse(toon_str)
        if "failure_payload" in result:
            return result["failure_payload"]
        return result


class ToonEncoder:
    """Encoder for TOON format"""

    def __init__(self, delimiter: str = "|"):
        self.delimiter = delimiter

    def encode(self, obj: Any) -> str:
        """Encode Python object to TOON string"""
        if isinstance(obj, dict):
            return self._encode_dict(obj)
        elif isinstance(obj, list):
            return self._encode_list(obj)
        elif isinstance(obj, str):
            return obj
        else:
            return str(obj)

    def _encode_dict(self, obj: Dict[str, Any]) -> str:
        lines = []
        for key, value in obj.items():
            if isinstance(value, dict):
                items = [f"{k}:{self._escape_value(v)}" for k, v in value.items()]
                lines.append(f"{key} {{{','.join(items)}}}")
            elif isinstance(value, list):
                encoded_list = self._encode_list(value)
                lines.append(f"{key}\n  {encoded_list}")
            else:
                lines.append(f"{key}{{{self._escape_value(value)}}}")
        return "\n".join(lines)

    def _encode_list(self, obj: List[Any]) -> str:
        if not obj:
            return "[0]"

        if all(isinstance(item, dict) for item in obj):
            first_keys = list(obj[0].keys())
            if all(set(item.keys()) == set(first_keys) for item in obj):
                return self._encode_table(obj, first_keys)

        lines = [f"[{len(obj)}]"]
        for item in obj:
            lines.append(self.encode(item))
        return "\n".join(lines)

    def _encode_table(self, obj: List[Dict[str, Any]], headers: List[str]) -> str:
        lines = [f"[{len(obj)}] {{{','.join(headers)}}}"]
        for item in obj:
            values = [self._escape_value(item.get(h, "")) for h in headers]
            lines.append(f"{self.delimiter.join(values)}")
        return "\n".join(lines)

    def _escape_value(self, value: Any) -> str:
        """Escape special characters in values"""
        if value is None:
            return ""
        str_val = str(value)
        return str_val.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")

    def encode_failure_signature(self, sig: FailureSignature) -> str:
        """Encode failure signature to TOON"""
        return f"failure{{{sig.file_path}::{sig.function_name}::{sig.error_type}}}"

    def encode_patch_toon(self, patch: PatchToon) -> str:
        """Encode patch to TOON format"""
        lines = [
            "patch[1]",
            "{",
            f'  file_path:"{patch.file_path}",',
            f"  line_range:({patch.line_range[0]},{patch.line_range[1]}),",
            f'  old_code:"{self._escape_value(patch.old_code)}",',
            f'  new_code:"{self._escape_value(patch.new_code)}"',
            "}",
        ]
        return "\n".join(lines)

    def encode_active_context(self, ctx: ActiveContext) -> str:
        """Encode active context to TOON format"""
        lines = [
            "active_context",
            f"  {{iteration:{ctx.iteration}}}",
            f"  active_history[{len(ctx.active_history)}]",
        ]

        for item in ctx.active_history:
            lines.append(f"    {item}")

        lines.append(f"  current_failures[{len(ctx.current_failures)}]")
        for sig in ctx.current_failures:
            lines.append(f"    {self.encode_failure_signature(sig)}")

        return "\n".join(lines)

    def encode_session_summary(self, summary: SessionSummary) -> str:
        """Encode session summary to TOON format"""
        lines = [
            "summary",
            f'  {{session_id:"{summary.session_id}",total_iterations:{summary.total_iterations},status:{summary.status},success_rate:{summary.success_rate}}}',
        ]
        return "\n".join(lines)


class ToonSerializer:
    """Serializes Python data structures to TOON format.

    This class provides a more feature-rich serialization compared to ToonEncoder,
    including automatic tabular format detection for uniform lists.
    """

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
                lines.append(f"{indent}{key}:")
                lines.append(self._serialize_uniform_list(value, indent_level + 1))
            elif isinstance(value, list):
                lines.append(f"{indent}{key}:")
                lines.append(self._serialize_list(value, indent_level + 1))
            elif isinstance(value, dict):
                lines.append(f"{indent}{key}:")
                lines.append(self._serialize_dict(value, indent_level + 1))
            else:
                lines.append(f"{indent}{key}: {self._serialize_primitive(value)}")

        return "\n".join(lines)

    def _serialize_list(self, data: List, indent_level: int) -> str:
        """Serialize list to TOON format."""
        if not data:
            return " " * (indent_level * self.indent_size) + "[]"

        indent = " " * (indent_level * self.indent_size)

        # If all items are strings, use simplified format
        if all(isinstance(item, str) for item in data):
            header_line = f"{indent}[{len(data)}]"
            return header_line + "\n" + "\n".join([f"{indent}{item}" for item in data])

        # Check if this is a uniform list suitable for tabular format
        if len(data) >= 5 and self._is_uniform_list(data):
            return self._serialize_uniform_list(data, indent_level)

        # Otherwise, serialize as regular list
        lines = []
        for item in data:
            if isinstance(item, dict):
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
        """Check if list is uniform (all items are dicts with same keys)."""
        if not data or not isinstance(data[0], dict):
            return False
        first_keys = set(data[0].keys())
        return all(
            isinstance(item, dict) and set(item.keys()) == first_keys for item in data
        )

    def _serialize_uniform_list(self, data: List[Dict], indent_level: int) -> str:
        """Serialize uniform list using TOON tabular format."""
        if not data:
            return ""

        lines = []
        indent = " " * (indent_level * self.indent_size)
        headers = list(data[0].keys())

        # Write header: [N] {field1, field2, ...}
        header_line = f"{indent}[{len(data)}] {{{', '.join(headers)}}}"
        lines.append(header_line)

        # Write data rows
        for item in data:
            values = [self._serialize_primitive(item[key]) for key in headers]
            row = " | ".join(values)
            lines.append(f"{indent}{row}")

        return "\n".join(lines)

    def _serialize_primitive(self, value: Any) -> str:
        """Serialize primitive value to string."""
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, str):
            escaped = value.replace("|", "\\|").replace("\n", " ")
            if " " in escaped or "|" in value or ":" in escaped:
                return f'"{escaped}"'
            return escaped
        elif isinstance(value, (int, float)):
            return str(value)
        else:
            return str(value)

    def dumps(self, data: Any) -> str:
        """Serialize data to TOON format string."""
        return self.serialize(data, indent_level=0)

    def dump(self, data: Any, file_path: str):
        """Serialize data to TOON format and write to file."""
        toon_str = self.dumps(data)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(toon_str)

    def serialize_to_file(self, data: Any, file_path: str):
        """Alias for dump method for compatibility."""
        self.dump(data, file_path)


def encode_toon(obj: Any, delimiter: str = "|") -> str:
    """Convenience function to encode object to TOON"""
    encoder = ToonEncoder(delimiter)
    return encoder.encode(obj)


def parse_toon(toon_str: str, delimiter: str = "|") -> Any:
    """Convenience function to parse TOON string"""
    parser = ToonParser(delimiter)
    return parser.parse(toon_str)


def dumps(data: Any, indent: int = 2) -> str:
    """Convenience function to serialize data to TOON format."""
    serializer = ToonSerializer(indent_size=indent)
    return serializer.dumps(data)


def dump(data: Any, file_path: str, indent: int = 2):
    """Convenience function to serialize data to TOON format file."""
    serializer = ToonSerializer(indent_size=indent)
    serializer.dump(data, file_path)


def parse_toon_file(path) -> Dict[str, Any]:
    """Parse a TOON file from disk.

    Args:
        path: Path to the TOON file (str or Path)

    Returns:
        Parsed dictionary
    """
    from pathlib import Path as PathLib

    file_path = PathLib(path)

    if not file_path.exists():
        return {}

    content = file_path.read_text(encoding="utf-8")
    parser = ToonParser()
    return parser.parse(content) or {}


def write_toon_file(path, data: Dict[str, Any]):
    """Write data to a TOON file.

    Args:
        path: Path to write to (str or Path)
        data: Dictionary to serialize
    """
    from pathlib import Path as PathLib

    file_path = PathLib(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    encoder = ToonEncoder()
    content = encoder.encode(data)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
