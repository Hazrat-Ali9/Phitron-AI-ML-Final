from typing import Any, ClassVar

from pydantic import BaseModel, ValidationInfo, field_validator


class PatchModel(BaseModel):
    """Base for PATCH bodies: every field is optional, but `null` is only accepted
    for fields listed in `nullable_fields` (columns that are nullable in the DB)."""

    nullable_fields: ClassVar[frozenset[str]] = frozenset()

    # Field validators only run for values the client sent (defaults are not validated),
    # so an omitted field is fine while an explicit null is rejected with the field's loc.
    @field_validator("*")
    @classmethod
    def _reject_null_for_required(cls, value: Any, info: ValidationInfo) -> Any:
        if value is None and info.field_name not in cls.nullable_fields:
            raise ValueError("This field cannot be null")
        return value

    def changes(self) -> dict[str, Any]:
        """Only the fields the client actually sent."""
        return self.model_dump(exclude_unset=True)
