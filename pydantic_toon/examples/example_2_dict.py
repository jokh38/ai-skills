"""
Example: Converting dictionary to TOON

This example shows how to bypass the LLM and directly convert
existing structured data to TOON format.
"""

from formatter import create_formatter
from models import (
    ToonDocument,
    ToonArray,
    ToonMetadata,
    ToonFieldDefinition,
    ToonHeader,
)


def main():
    """Convert dictionary data to TOON without LLM."""

    # Create formatter
    formatter = create_formatter(
        model_class=ToonDocument,
        provider="openai/gpt-4o-mini",  # Provider doesn't matter for dict conversion
    )

    # Define data as dictionary
    data_dict = {
        "header": {"version": "1.0", "format_id": "toon"},
        "root": {"total_employees": 3, "company": "Tech Corp"},
        "arrays": {
            "employees": {
                "metadata": {"array_length": 3, "field_count": 4},
                "fields": [
                    {"name": "id", "type": "int", "required": True},
                    {"name": "name", "type": "string", "required": True},
                    {"name": "department", "type": "string", "required": True},
                    {"name": "salary", "type": "int", "required": True},
                ],
                "data": [
                    {
                        "id": 1,
                        "name": "Alice",
                        "department": "Engineering",
                        "salary": 75000,
                    },
                    {"id": 2, "name": "Bob", "department": "Sales", "salary": 60000},
                    {
                        "id": 3,
                        "name": "Charlie",
                        "department": "Marketing",
                        "salary": 65000,
                    },
                ],
            }
        },
    }

    try:
        # Convert dictionary to TOON
        model, toon_string = formatter.format_from_dict(data_dict)

        # Print results
        print("=" * 60)
        print("TOON Output from Dictionary:")
        print("=" * 60)
        print(toon_string)
        print("=" * 60)
        print("\nConversion successful!")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
