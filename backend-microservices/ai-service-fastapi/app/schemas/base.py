"""
Base Pydantic model with automatic snake_case → camelCase conversion.
All API response/request schemas should inherit from CamelModel.
"""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Base model that auto-converts snake_case fields to camelCase in JSON output."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
