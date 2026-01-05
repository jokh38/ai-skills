from typing import TypeVar, Generic, Type, Optional, Tuple, Generator
from pydantic import BaseModel, ValidationError

try:
    import instructor

    instructor_available = True
except ImportError:
    instructor_available = False

from .models import ToonDocument, ToonFormatError
from .serializer import pydantic_to_toon

T = TypeVar("T", bound=BaseModel)


class ToonFormatter(Generic[T]):
    """
    Main formatter class that combines Instructor and TOON serialization.

    This class provides a unified interface for:
    1. Extracting structured data from LLM using Instructor
    2. Validating with Pydantic
    3. Serializing to TOON format
    """

    def __init__(self, model_class: Type[T], client, max_retries: int = 3):
        """
        Initialize ToonFormatter.

        Args:
            model_class: Pydantic BaseModel class (e.g., ToonDocument)
            client: Instructor client instance
            max_retries: Maximum number of validation retries

        Raises:
            ImportError: If instructor is not installed
        """
        if not instructor_available:
            raise ImportError(
                "Instructor is not installed. Install it with: pip install instructor"
            )

        self.model_class = model_class
        self.client = client
        self.max_retries = max_retries

    def format_from_llm(
        self, prompt: str, max_retries: Optional[int] = None, **kwargs
    ) -> Tuple[T, str]:
        """
        Extract structured data from LLM and convert to TOON.

        Args:
            prompt: Natural language prompt for LLM
            max_retries: Override default max_retries
            **kwargs: Additional arguments passed to Instructor client

        Returns:
            Tuple of (validated_model, toon_string)

        Raises:
            ToonFormatError: If validation or serialization fails
        """
        retries = max_retries if max_retries is not None else self.max_retries

        try:
            # Extract with Instructor (includes automatic retry)
            model = self._extract_from_llm(prompt, retries, **kwargs)

            # Pydantic model is already validated, no additional checks needed
            # (Type checking and structural validation are in models.py)

            # Serialize to TOON
            toon_string = pydantic_to_toon(model)

            return model, toon_string

        except ValidationError as e:
            error_msg = self._generate_validation_error(e)
            raise ToonFormatError(f"Pydantic validation failed:\n{error_msg}")
        except ToonFormatError:
            raise
        except Exception as e:
            raise ToonFormatError(f"TOON formatting failed: {e}")

    def _extract_from_llm(self, prompt: str, max_retries: int, **kwargs) -> T:
        """
        Extract structured data using Instructor.

        Args:
            prompt: Natural language prompt
            max_retries: Maximum retries
            **kwargs: Additional arguments

        Returns:
            Validated Pydantic model
        """
        return self.client.chat.completions.create(
            response_model=self.model_class,
            messages=[{"role": "user", "content": prompt}],
            max_retries=max_retries,
            **kwargs,
        )

    def _generate_validation_error(self, error: ValidationError) -> str:
        """
        Generate human-readable error message for LLM.

        Args:
            error: Pydantic ValidationError instance

        Returns:
            Formatted error message
        """
        errors = error.errors()
        error_messages = []

        for err in errors:
            location = " -> ".join(str(loc) for loc in err["loc"])
            message = err["msg"]
            error_messages.append(f"Error in '{location}': {message}")

        return "\n".join(error_messages)

    def format_from_dict(self, data_dict: dict) -> Tuple[T, str]:
        """
        Convert dictionary to Pydantic model and then to TOON.

        This bypasses LLM and directly serializes existing data.

        Args:
            data_dict: Dictionary representation of data

        Returns:
            Tuple of (validated_model, toon_string)

        Raises:
            ToonFormatError: If validation or serialization fails
        """
        try:
            # Parse dictionary to Pydantic model (validates automatically)
            model = self.model_class.model_validate(data_dict)

            # Serialize to TOON
            toon_string = pydantic_to_toon(model)

            return model, toon_string

        except ValidationError as e:
            error_msg = self._generate_validation_error(e)
            raise ToonFormatError(f"Pydantic validation failed:\n{error_msg}")
        except Exception as e:
            raise ToonFormatError(f"TOON formatting failed: {e}")


def stream_to_toon(
    model_class: Type[T], client, prompt: str, max_retries: int = 3
) -> Generator[str, None, None]:
    """
    Stream partial results and update TOON output incrementally.

    This function uses Instructor's Partial[Model] support to show
    progress as LLM generates data.

    Args:
        model_class: Pydantic BaseModel class
        client: Instructor client instance
        prompt: Natural language prompt
        max_retries: Maximum retries

    Yields:
        TOON strings as they are generated

    Raises:
        ImportError: If instructor is not installed
        ToonFormatError: If streaming fails

    Example:
        >>> for toon_chunk in stream_to_toon(ToonDocument, client, "Create 3 employees"):
        ...     print(toon_chunk)
    """
    if not instructor_available:
        raise ImportError("Instructor is not installed. Install it with: pip install instructor")

    try:
        from instructor import Partial

        last_toon_string = ""

        for partial_model in client.chat.completions.create(
            response_model=Partial[model_class],
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        ):
            # Convert partial model to TOON (may be incomplete)
            try:
                current_toon_string = pydantic_to_toon(partial_model)

                # Only yield if content has changed
                if current_toon_string != last_toon_string:
                    yield current_toon_string
                    last_toon_string = current_toon_string
            except Exception:
                # Skip incomplete models that can't be serialized
                pass

    except Exception as e:
        raise ToonFormatError(f"Streaming failed: {e}")


def create_formatter(
    model_class: Type[T],
    provider: str = "openai/gpt-4o-mini",
    api_key: Optional[str] = None,
    max_retries: int = 3,
    **kwargs,
) -> ToonFormatter[T]:
    """
    Convenience function to create a ToonFormatter instance.

    Args:
        model_class: Pydantic BaseModel class
        provider: LLM provider (e.g., "openai/gpt-4o-mini", "anthropic/claude-3-5-sonnet")
        api_key: Optional API key (if not using environment variable)
        max_retries: Maximum number of retries
        **kwargs: Additional arguments for Instructor client

    Returns:
        Configured ToonFormatter instance

    Raises:
        ImportError: If instructor is not installed

    Example:
        >>> formatter = create_formatter(ToonDocument, "openai/gpt-4o-mini")
        >>> model, toon_string = formatter.format_from_llm("Create 3 employees")
    """
    if not instructor_available:
        raise ImportError("Instructor is not installed. Install it with: pip install instructor")

    # Initialize Instructor client
    if api_key:
        client = instructor.from_provider(provider, api_key=api_key, **kwargs)
    else:
        client = instructor.from_provider(provider, **kwargs)

    # Create formatter
    return ToonFormatter(model_class, client, max_retries)
