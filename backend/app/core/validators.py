"""Reusable Pydantic field types for Bangladesh-specific values."""

import re
from typing import Annotated

from pydantic import AfterValidator, BeforeValidator

_BD_MOBILE = re.compile(r"^01[3-9]\d{8}$")
_MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _blank_to_none(value: object) -> object:
    if isinstance(value, str) and not value.strip():
        return None
    return value


def normalize_bd_phone(value: str) -> str:
    """'01711-482913', '+880 1711 482913' -> '01711482913'."""
    digits = re.sub(r"[\s\-()]", "", value)
    if digits.startswith("+88"):
        digits = digits[3:]
    elif digits.startswith("88") and len(digits) == 13:
        digits = digits[2:]
    if not _BD_MOBILE.match(digits):
        raise ValueError("Enter a valid Bangladeshi mobile number, e.g. 01711-482913")
    return digits


def validate_month(value: str) -> str:
    if not _MONTH.match(value):
        raise ValueError("Month must look like YYYY-MM, e.g. 2026-11")
    return value


BDPhone = Annotated[str, AfterValidator(normalize_bd_phone)]
OptionalBDPhone = Annotated[BDPhone | None, BeforeValidator(_blank_to_none)]
Month = Annotated[str, AfterValidator(validate_month)]
