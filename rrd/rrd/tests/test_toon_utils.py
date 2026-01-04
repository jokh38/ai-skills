"""Tests for toon_utils module"""

import pytest
import json

from core.toon_utils import ToonParser, ToonEncoder


class TestToonParser:
    """Test suite for ToonParser class"""

    def test_parse_simple_array(self):
        """Test parsing simple TOON array"""
        toon_text = "[3] {id, name}\n1 | Alice\n2 | Bob\n3 | Charlie"
        parser = ToonParser()
        result = parser.parse(toon_text)

        assert len(result) == 3
        assert result[0] == {"id": "1", "name": "Alice"}
        assert result[1] == {"id": "2", "name": "Bob"}
        assert result[2] == {"id": "3", "name": "Charlie"}

    def test_parse_with_quotes(self):
        """Test parsing TOON with quoted values"""
        toon_text = '[2] {id, message}\n1 | "Hello, World!"\n2 | "Test message"'
        parser = ToonParser()
        result = parser.parse(toon_text)

        assert result[0]["message"] == "Hello, World!"
        assert result[1]["message"] == "Test message"

    def test_parse_nested_toon(self):
        """Test parsing nested TOON structure"""
        toon_text = '[1] {user}\n{"name": "Alice", "age": 30}'
        parser = ToonParser()
        result = parser.parse(toon_text)

        assert len(result) == 1
        assert isinstance(result[0]["user"], dict)
        assert result[0]["user"]["name"] == "Alice"

    def test_parse_empty_array(self):
        """Test parsing empty TOON array"""
        toon_text = "[0] {id, name}"
        parser = ToonParser()
        result = parser.parse(toon_text)

        assert result == []

    def test_parse_dict_format(self):
        """Test parsing TOON dictionary format"""
        toon_text = "{name, age}\nAlice | 30"
        parser = ToonParser()
        result = parser.parse(toon_text)

        assert result == {"name": "Alice", "age": "30"}


class TestToonEncoder:
    """Test suite for ToonEncoder class"""

    def test_encode_simple_list(self):
        """Test encoding simple list to TOON"""
        data = [{"id": "1", "name": "Alice"}, {"id": "2", "name": "Bob"}]
        encoder = ToonEncoder()
        toon_text = encoder.encode(data)

        assert "[2]" in toon_text
        assert "{id, name}" in toon_text
        assert "1 | Alice" in toon_text
        assert "2 | Bob" in toon_text

    def test_encode_with_special_chars(self):
        """Test encoding values with special characters"""
        data = [{"id": "1", "message": "Hello | World"}]
        encoder = ToonEncoder()
        toon_text = encoder.encode(data)

        assert "Hello | World" in toon_text

    def test_encode_empty_list(self):
        """Test encoding empty list"""
        data = []
        encoder = ToonEncoder()
        toon_text = encoder.encode(data)

        assert toon_text == "[]"

    def test_encode_preserve_order(self):
        """Test that encoding preserves key order"""
        data = [{"b": "2", "a": "1", "c": "3"}]
        encoder = ToonEncoder()
        toon_text = encoder.encode(data)

        assert "{b, a, c}" in toon_text

    def test_encode_with_lists(self):
        """Test encoding values that are lists"""
        data = [{"id": "1", "items": '["a", "b", "c"]'}]
        encoder = ToonEncoder()
        toon_text = encoder.encode(data)

        assert '["a", "b", "c"]' in toon_text

    def test_roundtrip(self):
        """Test that parse(encode(data)) == data"""
        original = [
            {"id": "1", "name": "Alice", "age": "30"},
            {"id": "2", "name": "Bob", "age": "25"},
        ]

        encoder = ToonEncoder()
        parser = ToonParser()

        toon_text = encoder.encode(original)
        parsed = parser.parse(toon_text)

        assert parsed == original
