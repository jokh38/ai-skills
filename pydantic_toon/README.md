# Pydantic-Guided TOON Formatter

## Overview

This document describes the development of a Pydantic-guided TOON (Token-Oriented Object Notation) formatter that combines the validation power of [Instructor](https://github.com/instructor-ai/instructor) with the token efficiency of [TOON format](https://github.com/toon-format/toon).

## Architecture

```
User Request
     ↓
LLM (Natural Language Response)
     ↓
Instructor (Pydantic Validation + Auto-retry)
     ↓
Pydantic Object (Typed, Validated)
     ↓
TOON Formatter (Custom Serializer)
     ↓
TOON String (Token-efficient Output)
```

### Key Components

1. **Instructor Layer**: LLM response validation with automatic retry
2. **Pydantic Schema**: Type-safe data models with field constraints
3. **TOON Serializer**: Converts Pydantic objects to TOON format
4. **Validation Guardrails**: Ensures TOON structure compliance

## Implementation Steps

### Step 1: Define Pydantic Models for TOON Structure

Create Pydantic classes that mirror TOON's hierarchical structure:

```python
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any

class ToonHeader(BaseModel):
    version: str = Field(description="TOON format version (e.g., '1.0')")
    format_id: str = Field(description="File format identifier")

class ToonMetadata(BaseModel):
    array_length: int = Field(description="Expected number of array elements")
    field_count: int = Field(description="Number of fields per row")
    
    @field_validator('array_length')
    def validate_positive(cls, v):
        if v <= 0:
            raise ValueError('array_length must be positive')
        return v

class ToonFieldDefinition(BaseModel):
    name: str = Field(description="Field name (snake_case)")
    type: str = Field(description="Field type (string, int, float, bool, date)")
    required: bool = Field(default=True, description="Whether field is mandatory")

class ToonArray(BaseModel):
    metadata: ToonMetadata
    fields: List[ToonFieldDefinition]
    data: List[Dict[str, Any]]
    
    @field_validator('data')
    def validate_data_consistency(cls, v, info):
        metadata = info.data.get('metadata')
        if metadata and len(v) != metadata.array_length:
            raise ValueError(
                f'Data length ({len(v)}) does not match metadata.array_length ({metadata.array_length})'
            )
        return v

class ToonDocument(BaseModel):
    header: ToonHeader
    root: Dict[str, Any]
    arrays: Dict[str, ToonArray]
```

### Step 2: Instructor Integration with LLM

Use Instructor to extract structured data from LLM responses:

```python
import instructor
from openai import OpenAI

# Initialize Instructor client
client = instructor.from_provider("openai/gpt-4o-mini")

# Extract structured data from natural language
toon_doc = client.chat.completions.create(
    response_model=ToonDocument,
    messages=[{
        "role": "user",
        "content": """
        Create a TOON document with employee data:
        - 3 employees: Alice (Engineering, 75000), Bob (Sales, 60000), Charlie (Marketing, 65000)
        - Fields: id, name, department, salary
        - Version 1.0
        """
    }],
    max_retries=3,
)
```

### Step 3: TOON Serialization from Pydantic Objects

Implement custom serializer using `toon_format` library:

```python
from toon_format import encode

def pydantic_to_toon(model: BaseModel) -> str:
    """
    Convert Pydantic model to TOON string.
    
    Args:
        model: Pydantic BaseModel instance
        
    Returns:
        TOON formatted string
    """
    # Convert Pydantic model to dictionary
    model_dict = model.model_dump()
    
    # Transform dictionary to TOON-optimized structure
    toon_data = optimize_for_toon(model_dict)
    
    # Encode using toon_format library
    toon_string = encode(toon_data)
    
    return toon_string

def optimize_for_toon(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Optimize dictionary structure for TOON encoding.
    
    This function:
    1. Identifies uniform arrays for tabular format
    2. Adds [N] length declarations
    3. Adds {fields} headers
    4. Converts to TOON-optimized structure
    """
    optimized = {}
    
    # Process header
    if 'header' in data:
        optimized['# version'] = data['header']['version']
        optimized['# format'] = data['header']['format_id']
    
    # Process arrays with tabular optimization
    for key, value in data.items():
        if isinstance(value, dict) and 'data' in value and 'fields' in value:
            # Uniform array - use tabular TOON format
            field_names = [f['name'] for f in value['fields']]
            array_length = len(value['data'])
            
            # TOON format: key[N]{field1,field2,...}:
            optimized_key = f"{key}[{array_length}]{{{','.join(field_names)}}}"
            optimized[optimized_key] = [
                [row.get(f['name']) for f in value['fields']]
                for row in value['data']
            ]
        else:
            optimized[key] = value
    
    return optimized
```

### Step 4: Validation and Error Handling

Implement comprehensive validation:

```python
from pydantic import ValidationError
from typing import TypeVar, Generic

T = TypeVar('T', bound=BaseModel)

class ToonFormatter(Generic[T]):
    def __init__(self, model_class: Type[T], client):
        self.model_class = model_class
        self.client = client
    
    def format_from_llm(self, prompt: str, max_retries: int = 3) -> tuple[T, str]:
        """
        Extract structured data from LLM and convert to TOON.
        
        Returns:
            tuple of (validated_model, toon_string)
        """
        try:
            # Extract with Instructor (includes automatic retry)
            model = self.client.chat.completions.create(
                response_model=self.model_class,
                messages=[{"role": "user", "content": prompt}],
                max_retries=max_retries,
            )
            
            # Validate Pydantic model
            validated_model = self._validate_model(model)
            
            # Serialize to TOON
            toon_string = pydantic_to_toon(validated_model)
            
            return validated_model, toon_string
            
        except ValidationError as e:
            raise ToonFormatError(f"Pydantic validation failed: {e}")
        except Exception as e:
            raise ToonFormatError(f"TOON formatting failed: {e}")
    
    def _validate_model(self, model: T) -> T:
        """Additional validation beyond Pydantic"""
        # Check for duplicate keys
        if hasattr(model, 'arrays'):
            for array_name, array_data in model.arrays.items():
                field_names = [f.name for f in array_data.fields]
                if len(field_names) != len(set(field_names)):
                    raise ValueError(f"Duplicate field names in array '{array_name}'")
        
        return model

class ToonFormatError(Exception):
    """Custom exception for TOON formatting errors"""
    pass
```

### Step 5: Streaming Support (Optional)

Enable streaming for large datasets:

```python
from instructor import Partial

def stream_to_toon(model_class: Type[T], client, prompt: str):
    """
    Stream partial results and update TOON output incrementally.
    """
    toon_formatter = ToonFormatter(model_class, client)
    
    for partial_model in client.chat.completions.create(
        response_model=Partial[model_class],
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    ):
        # Convert partial model to TOON (may be incomplete)
        try:
            toon_string = pydantic_to_toon(partial_model)
            print(toon_string)
            print("---")  # Separator between updates
        except Exception:
            # Skip incomplete models that can't be serialized
            pass
```

## Validation Strategies

### 1. Size Validation
```python
@field_validator('data')
def validate_size_consistency(cls, v, info):
    """Ensure array length matches metadata"""
    metadata = info.data.get('metadata')
    if metadata and len(v) != metadata.array_length:
        raise ValueError(
            f'Size mismatch: metadata says {metadata.array_length}, got {len(v)} elements'
        )
    return v
```

### 2. Field Consistency
```python
@field_validator('data')
def validate_field_count(cls, v, info):
    """Ensure each row has the correct number of fields"""
    metadata = info.data.get('metadata')
    if metadata:
        expected_fields = metadata.field_count
        for i, row in enumerate(v):
            if len(row) != expected_fields:
                raise ValueError(
                    f'Row {i} has {len(row)} fields, expected {expected_fields}'
                )
    return v
```

### 3. Type Constraints
```python
@field_validator('salary')
def validate_salary_range(cls, v):
    """Ensure salary is within reasonable range"""
    if v < 0 or v > 10000000:
        raise ValueError('Salary must be between 0 and 10,000,000')
    return v
```

### 4. Duplicate Prevention
```python
from pydantic import validator

class ToonArray(BaseModel):
    fields: List[ToonFieldDefinition]
    
    @validator('fields')
    def no_duplicate_fields(cls, v):
        field_names = [f.name for f in v]
        if len(field_names) != len(set(field_names)):
            duplicates = [name for name in field_names if field_names.count(name) > 1]
            raise ValueError(f'Duplicate field names: {duplicates}')
        return v
```

## Error Recovery Workflow

Instructor automatically handles validation failures:

```
LLM Response
     ↓
Pydantic Validation
     ↓
     ├─ Success → TOON Serialization
     └─ Failed
          ↓
     Generate Error Message
          ↓
     Send to LLM (Retry 1/N)
          ↓
     LLM Corrects Response
          ↓
     Repeat Validation
          ↓
     Success or Max Retries Reached
```

### Example Error Message Generation

```python
def generate_validation_error(error: ValidationError) -> str:
    """Generate human-readable error message for LLM"""
    errors = error.errors()
    error_messages = []
    
    for err in errors:
        location = " -> ".join(str(loc) for loc in err['loc'])
        message = err['msg']
        error_messages.append(f"Error in '{location}': {message}")
    
    return "Validation failed:\n" + "\n".join(error_messages)

# Example output:
"""
Validation failed:
Error in 'arrays.employees.metadata.array_length': Size field says 5, but you provided 4 elements. Correct this.
Error in 'arrays.employees.data.2.salary': Salary must be positive (got -50000)
"""
```

## Usage Examples

### Example 1: Employee Data

```python
# Define model
class EmployeeArray(ToonArray):
    pass

formatter = ToonFormatter(ToonDocument, client)

# Extract and format
model, toon_string = formatter.format_from_llm("""
    Create employee data for 3 people:
    1. Alice Smith, Engineering, $75,000, 5 years experience
    2. Bob Jones, Sales, $60,000, 3 years experience
    3. Charlie Brown, Marketing, $65,000, 4 years experience
    
    Fields: id, name, department, salary, years_experience
""")

print(toon_string)
```

**Output:**
```
# version: 1.0
# format: toon
employees[3]{id,name,department,salary,years_experience}:
  1,Alice Smith,Engineering,75000,5
  2,Bob Jones,Sales,60000,3
  3,Charlie Brown,Marketing,65000,4
```

### Example 2: Nested Structure

```python
class OrderDocument(ToonDocument):
    pass

model, toon_string = formatter.format_from_llm("""
    Create order data:
    - Order ID: ORD-001, Customer: John Doe (john@example.com), Total: $150.50
    - Items: 2 items (Product A: $100, Product B: $50.50)
""")

print(toon_string)
```

**Output:**
```
# version: 1.0
# format: toon
order:
  id: ORD-001
  customer:
    name: John Doe
    email: john@example.com
  total: 150.50
items[2]{id,name,price}:
  1,Product A,100.00
  2,Product B,50.50
```

### Example 3: Streaming Large Dataset

```python
# Stream as LLM generates data
stream_to_toon(ToonDocument, client, """
    Generate 1000 product records with random data
    Fields: id, name, category, price, stock
""")
```

## Best Practices

### 1. Field Descriptions
```python
# Good: Clear, specific descriptions
class Product(BaseModel):
    name: str = Field(description="Product name (max 100 chars)")
    price: float = Field(description="Price in USD (0-10000 range)")

# Bad: Vague descriptions
class Product(BaseModel):
    name: str = Field(description="name")
    price: float = Field(description="price")
```

### 2. Validation granularity
```python
# Validate at appropriate levels
class ToonArray(BaseModel):
    # Structural validation at array level
    metadata: ToonMetadata
    
    # Data validation at row level
    data: List[Dict[str, Any]]
    
    @field_validator('data')
    def validate_each_row(cls, v):
        for i, row in enumerate(v):
            if not isinstance(row, dict):
                raise ValueError(f'Row {i} must be a dictionary')
        return v
```

### 3. Error context
```python
# Provide helpful error messages
@field_validator('salary')
def validate_salary(cls, v):
    if v < 0:
        raise ValueError(
            f'Salary cannot be negative. Got {v}. '
            f'Please provide a positive value or 0.'
        )
    return v
```

### 4. Token efficiency
```python
# Use tabular format for uniform arrays
def should_use_tabular(data: List[Dict]) -> bool:
    """Check if data is uniform enough for tabular TOON format"""
    if not data:
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
```

## Performance Considerations

### 1. Large Datasets
- Use streaming (`Partial[Model]`) for datasets > 100 rows
- Consider batching for datasets > 1000 rows
- Use `encodeLines()` from `toon_format` for memory efficiency

### 2. Validation Cost
- Pydantic validation is fast (< 1ms per model)
- Instructor retry adds latency (~1-2 seconds per retry)
- Set reasonable `max_retries` (3-5 recommended)

### 3. Token Savings
- TOON typically saves 40% tokens vs JSON for uniform arrays
- Tabular format is optimal for > 5 rows with > 3 fields
- For deeply nested data, JSON compact may be more efficient

## Testing Strategy

### Unit Tests
```python
import pytest
from pydantic import ValidationError

def test_toon_document_validation():
    """Test TOON document structure validation"""
    doc = ToonDocument(
        header=ToonHeader(version="1.0", format_id="toon"),
        root={},
        arrays={}
    )
    assert doc.header.version == "1.0"

def test_array_length_validation():
    """Test array length validation"""
    with pytest.raises(ValidationError):
        ToonArray(
            metadata=ToonMetadata(array_length=5, field_count=3),
            fields=[ToonFieldDefinition(name="id", type="int")],
            data=[{"id": 1}, {"id": 2}]  # Only 2 elements, metadata says 5
        )

def test_duplicate_field_detection():
    """Test duplicate field detection"""
    with pytest.raises(ValidationError):
        ToonArray(
            metadata=ToonMetadata(array_length=3, field_count=2),
            fields=[
                ToonFieldDefinition(name="id", type="int"),
                ToonFieldDefinition(name="id", type="string")  # Duplicate
            ],
            data=[]
        )
```

### Integration Tests
```python
def test_end_to_end_toon_generation():
    """Test complete flow from LLM to TOON"""
    formatter = ToonFormatter(ToonDocument, client)
    
    model, toon_string = formatter.format_from_llm(
        "Create 2 employees with id, name, department fields"
    )
    
    # Verify TOON structure
    assert "[2]" in toon_string  # Array length
    assert "{id,name,department}" in toon_string  # Field headers
    assert "id,name,department" in toon_string.lower()

def test_retry_on_validation_error():
    """Test automatic retry on validation error"""
    formatter = ToonFormatter(ToonDocument, client)
    
    # This should succeed after Instructor retries
    model, toon_string = formatter.format_from_llm(
        "Create 3 employees but make one with negative salary",
        max_retries=3
    )
    
    # All salaries should be positive after retry
    for array in model.arrays.values():
        for row in array.data:
            if 'salary' in row:
                assert row['salary'] >= 0
```

## Dependencies

```toml
[tool.poetry.dependencies]
python = "^3.10"
instructor = "^1.13.0"
pydantic = "^2.0"
toon-format = "^0.1.0"
openai = "^1.0.0"

[tool.poetry.dev-dependencies]
pytest = "^7.0"
pytest-asyncio = "^0.21.0"
ruff = "^0.1.0"
mypy = "^1.0.0"
```

## Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install instructor pydantic toon-format openai

# Or using poetry
poetry install
```

## Configuration

```python
# config.py
import instructor
from openai import OpenAI

# Initialize Instructor client
INSTRUCTOR_CLIENT = instructor.from_provider("openai/gpt-4o-mini")

# Optional: Use different provider
# INSTRUCTOR_CLIENT = instructor.from_provider("anthropic/claude-3-5-sonnet")

# Configuration
MAX_RETRIES = 3
DEFAULT_TOON_VERSION = "1.0"
```

## Troubleshooting

### Issue: Validation fails repeatedly
**Solution:** Check field descriptions are clear and constraints are reasonable

### Issue: TOON output not compact
**Solution:** Ensure data is uniform for tabular format optimization

### Issue: Retry loop never succeeds
**Solution:** Reduce complexity or break into smaller requests

### Issue: Streaming shows incomplete data
**Solution:** This is expected; skip incomplete models in stream handler

## Future Enhancements

1. **Schema Inference**: Auto-detect TOON structure from existing data
2. **Reverse Parser**: Parse TOON back to Pydantic models
3. **Format Migration**: Convert between TOON versions
4. **Validation Reports**: Detailed validation error summaries
5. **Performance Profiling**: Token usage and timing metrics

## References

- [Instructor Documentation](https://python.useinstructor.com)
- [TOON Format Specification](https://github.com/toon-format/spec/blob/main/SPEC.md)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [toon-format Python Library](https://github.com/toon-format/toon-python)

## License

MIT License - See LICENSE file for details
