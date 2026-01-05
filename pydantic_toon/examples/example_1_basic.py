"""
Example: Generating TOON from LLM response

This example demonstrates how to use the ToonFormatter to extract
structured data from an LLM and convert it to TOON format.
"""

from formatter import create_formatter
from models import ToonDocument


def main():
    """Generate employee TOON data from natural language."""

    # Create formatter (requires OPENAI_API_KEY environment variable)
    formatter = create_formatter(
        model_class=ToonDocument, provider="openai/gpt-4o-mini", max_retries=3
    )

    # Define prompt
    prompt = """
    Create a TOON document with employee data:
    - 3 employees: Alice (Engineering, $75,000, 5 years), Bob (Sales, $60,000, 3 years), Charlie (Marketing, $65,000, 4 years)
    - Fields: id, name, department, salary, years_experience
    - Use TOON version 1.0
    """

    try:
        # Extract and format
        model, toon_string = formatter.format_from_llm(prompt)

        # Print results
        print("=" * 60)
        print("TOON Output:")
        print("=" * 60)
        print(toon_string)
        print("=" * 60)
        print("\nValidation successful!")

        # Print metadata
        print(f"\nDocument version: {model.header.version}")
        print(f"Arrays: {list(model.arrays.keys())}")

        if "employees" in model.arrays:
            emp_array = model.arrays["employees"]
            print(f"Employee count: {len(emp_array.data)}")
            print(f"Field count: {len(emp_array.fields)}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
