"""
Pydantic v1 to v2 compatibility layer
"""
from pydantic import field_validator, model_validator
from functools import wraps


# Re-export with v1 names for backward compatibility
validator = field_validator
root_validator = model_validator


def make_v2_validator(func):
    """Wrapper to make v1-style validators work with v2"""
    @wraps(func)
    def wrapper(cls, v, info=None):
        # v2 passes ValidationInfo, v1 expected values dict
        return func(cls, v)
    return wrapper
