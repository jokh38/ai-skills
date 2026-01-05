# Pydantic-Guided TOON Formatter

Combines [Instructor](https://github.com/instructor-ai/instructor) validation with [TOON](https://github.com/toon-format/toon) token efficiency for LLM data extraction.

## Architecture

```
LLM → Instructor (validation + retry) → Pydantic → TOON Serializer → TOON output
```

**Key Components:**
- Instructor: LLM response validation with auto-retry
- Pydantic: Type-safe models with field constraints
- TOON Serializer: Converts to token-efficient format

## Core Implementation

### Define Models

```python
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any

class ToonHeader(BaseModel):
    version: str = Field(description="TOON format version")
    format_id: str = Field(description="File format identifier")

class ToonMetadata(BaseModel):
    array_length: int = Field(description="Expected number of elements")
    
    @field_validator('array_length')
    def validate_positive(cls, v):
        if v <= 0:
            raise ValueError('array_length must be positive')
        return v

class ToonFieldDefinition(BaseModel):
    name: str = Field(description="Field name (snake_case)")
    type: str = Field(description="Field type")

class ToonArray(BaseModel):
    metadata: ToonMetadata
    fields: List[ToonFieldDefinition]
    data: List[Dict[str, Any]]
    
    @field_validator('data')
    def validate_data_consistency(cls, v, info):
        metadata = info.data.get('metadata')
        if metadata and len(v) != metadata.array_length:
            raise ValueError(f'Data length mismatch: {len(v)} != {metadata.array_length}')
        return v

class ToonDocument(BaseModel):
    header: ToonHeader
    root: Dict[str, Any]
    arrays: Dict[str, ToonArray]
```

### Instructor Integration

```python
import instructor

client = instructor.from_provider("openai/gpt-4o-mini")

toon_doc = client.chat.completions.create(
    response_model=ToonDocument,
    messages=[{
        "role": "user",
        "content": "Create 3 employees with id, name, department, salary fields"
    }],
    max_retries=3,
)
```

### TOON Serialization

```python
from toon_format import encode

def pydantic_to_toon(model: BaseModel) -> str:
    model_dict = model.model_dump()
    toon_data = optimize_for_toon(model_dict)
    return encode(toon_data)

def optimize_for_toon(data: Dict[str, Any]) -> Dict[str, Any]:
    optimized = {}
    
    # Process header
    if 'header' in data:
        optimized['# version'] = data['header']['version']
        optimized['# format'] = data['header']['format_id']
    
    # Process arrays with tabular optimization
    for key, value in data.items():
        if isinstance(value, dict) and 'data' in value and 'fields' in value:
            field_names = [f['name'] for f in value['fields']]
            array_length = len(value['data'])
            optimized_key = f"{key}[{array_length}]{{{','.join(field_names)}}}"
            optimized[optimized_key] = [
                [row.get(f['name']) for f in value['fields']]
                for row in value['data']
            ]
        else:
            optimized[key] = value
    
    return optimized
```

### Formatter Class

```python
from pydantic import ValidationError
from typing import TypeVar, Generic

T = TypeVar('T', bound=BaseModel)

class ToonFormatter(Generic[T]):
    def __init__(self, model_class: Type[T], client):
        self.model_class = model_class
        self.client = client
    
    def format_from_llm(self, prompt: str, max_retries: int = 3) -> tuple[T, str]:
        try:
            model = self.client.chat.completions.create(
                response_model=self.model_class,
                messages=[{"role": "user", "content": prompt}],
                max_retries=max_retries,
            )
            toon_string = pydantic_to_toon(model)
            return model, toon_string
        except ValidationError as e:
            raise ToonFormatError(f"Validation failed: {e}")

class ToonFormatError(Exception):
    pass
```

## Error Handling

Instructor automatically retries on validation failures. Provide clear field descriptions to minimize retries.

## Streaming

For large datasets, use streaming to process data incrementally:

```python
from instructor import Partial

for partial_model in client.chat.completions.create(
    response_model=Partial[ToonDocument],
    messages=[{"role": "user", "content": "Generate 1000 records"}],
    stream=True,
):
    try:
        toon_string = pydantic_to_toon(partial_model)
        print(toon_string)
    except Exception:
        pass  # Skip incomplete models
```

## Performance

- **Large datasets**: Use `Partial[Model]` for streaming (>100 rows)
- **Validation**: Pydantic is fast (<1ms), Instructor retry adds ~1-2s per retry
- **Token savings**: TOON saves ~40% vs JSON for uniform arrays
- **Max retries**: 3-5 recommended

## Testing

```bash
# Run tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=.

# Lint
ruff check .
mypy .
```

## Installation

```bash
pip install instructor pydantic toon-format openai
# or
poetry install
```

## Configuration

```python
import instructor

client = instructor.from_provider("openai/gpt-4o-mini")
```

## Troubleshooting

- **Validation fails**: Check field descriptions are clear
- **TOON not compact**: Ensure data is uniform for tabular format
- **Retry loop**: Reduce complexity or break into smaller requests

## References

- [Instructor](https://python.useinstructor.com)
- [TOON Format](https://github.com/toon-format/toon)
- [Pydantic](https://docs.pydantic.dev/)
