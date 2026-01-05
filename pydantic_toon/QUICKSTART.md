# Pydantic-Guided TOON Formatter

Pydantic-guided TOON formatter combining [Instructor](https://github.com/instructor-ai/instructor) validation with [TOON](https://github.com/toon-format/toon) token efficiency.

## Quick Start

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Or using poetry
poetry install
```

### Basic Usage

```python
from formatter import create_formatter
from models import ToonDocument

# Create formatter
formatter = create_formatter(
    model_class=ToonDocument,
    provider="openai/gpt-4o-mini"
)

# Extract from LLM and convert to TOON
model, toon_string = formatter.format_from_llm("""
    Create 3 employees with id, name, department, salary fields
""")

print(toon_string)
```

**Output:**
```
# version: 1.0
# format: toon
employees[3]{id,name,department,salary}:
  1,Alice,Engineering,75000
  2,Bob,Sales,60000
  3,Charlie,Marketing,65000
```

### Convert Existing Data

```python
# Convert dictionary to TOON without LLM
data_dict = {
    "header": {"version": "1.0", "format_id": "toon"},
    "arrays": {
        "employees": {
            "metadata": {"array_length": 2, "field_count": 2},
            "fields": [
                {"name": "id", "type": "int"},
                {"name": "name", "type": "string"}
            ],
            "data": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        }
    }
}

model, toon_string = formatter.format_from_dict(data_dict)
print(toon_string)
```

## Features

- **Automatic Validation**: Pydantic ensures data integrity
- **Auto-Retry**: Instructor retries on validation failures
- **Token Efficient**: TOON saves ~40% tokens vs JSON
- **Type Safe**: Full IDE support with Pydantic
- **Multi-Provider**: Works with OpenAI, Anthropic, Google, etc.

## Documentation

See [README.md](README.md) for comprehensive documentation.

## Examples

- [Basic LLM Extraction](examples/example_1_basic.py)
- [Dictionary Conversion](examples/example_2_dict.py)

## Testing

```bash
# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=.

# Lint code
ruff check .
```

## License

MIT License - See [LICENSE](LICENSE) file.
