"""Request validation helpers for common patterns."""

import re
import uuid
from .errors import bad_request, ApiError


# UUID v4 pattern
UUID_PATTERN = re.compile(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$')


def validate_uuid(value: str | None, field_name: str = 'id') -> str:
    """Validate that a string is a valid UUID v4.
    
    Args:
        value: The value to validate
        field_name: Field name for error message
        
    Returns:
        The validated UUID string
        
    Raises:
        ApiError: If validation fails
    """
    if not value:
        raise bad_request('invalid_request', f'{field_name} is required')
    
    if not UUID_PATTERN.match(value.lower()):
        raise bad_request(
            'invalid_uuid_format',
            f'{field_name} must be a valid UUID v4',
            {'field': field_name, 'value': value}
        )
    
    return value


def generate_id() -> str:
    """Generate a new UUID v4."""
    return str(uuid.uuid4())


def validate_string_length(value: str | None, field_name: str, min_len: int = 0, max_len: int = 1000) -> str:
    """Validate string length constraints.
    
    Args:
        value: The string to validate
        field_name: Field name for error message
        min_len: Minimum length (inclusive)
        max_len: Maximum length (inclusive)
        
    Returns:
        The validated string (stripped)
        
    Raises:
        ApiError: If validation fails
    """
    if not value:
        if min_len > 0:
            raise bad_request('validation_error', f'{field_name} is required')
        return ''
    
    stripped = value.strip() if isinstance(value, str) else str(value)
    
    if len(stripped) < min_len:
        raise bad_request(
            'validation_error',
            f'{field_name} must be at least {min_len} characters',
            {'field': field_name, 'min_length': min_len}
        )
    
    if len(stripped) > max_len:
        raise bad_request(
            'validation_error',
            f'{field_name} must not exceed {max_len} characters',
            {'field': field_name, 'max_length': max_len}
        )
    
    return stripped


def validate_priority(value: int | None, field_name: str = 'priority') -> int:
    """Validate priority value (1-5).
    
    Args:
        value: The priority value
        field_name: Field name for error message
        
    Returns:
        The validated priority
        
    Raises:
        ApiError: If validation fails
    """
    if value is None:
        return 2  # Default priority
    
    if not isinstance(value, int) or value < 1 or value > 5:
        raise bad_request(
            'validation_error',
            f'{field_name} must be an integer between 1 and 5',
            {'field': field_name, 'value': value}
        )
    
    return value


def validate_enum(value: str | None, field_name: str, allowed: list[str]) -> str:
    """Validate enum value.
    
    Args:
        value: The value to validate
        field_name: Field name for error message
        allowed: List of allowed values
        
    Returns:
        The validated value
        
    Raises:
        ApiError: If validation fails
    """
    if not value:
        raise bad_request('validation_error', f'{field_name} is required')
    
    if value not in allowed:
        raise bad_request(
            'validation_error',
            f'{field_name} must be one of: {", ".join(allowed)}',
            {'field': field_name, 'allowed': allowed, 'value': value}
        )
    
    return value
