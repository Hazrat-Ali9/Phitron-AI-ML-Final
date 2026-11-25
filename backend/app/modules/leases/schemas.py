from datetime import date
from typing import Annotated, Self

from pydantic import AliasPath, BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.core.schemas import PatchModel

NID = Annotated[
    str,
    StringConstraints(strip_whitespace=True, pattern=r"^(\d{10}|\d{13}|\d{17})$"),
    Field(description="Bangladesh NID: 10, 13 or 17 digits", examples=["1992384756"]),
]
Taka = Annotated[int, Field(ge=0, le=10_000_000)]
FamilyMembers = Annotated[int, Field(ge=1, le=20)]


class LeaseCreate(BaseModel):
    flat_id: int
    tenant_id: int
    start_date: date
    end_date: date | None = None
    monthly_rent: Taka = Field(description="Agreed rent + service charge")
    advance_amount: Taka = 0
    nid_number: NID
    family_members: FamilyMembers = 1
    is_active: bool = True

    @model_validator(mode="after")
    def _end_after_start(self) -> Self:
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class LeaseUpdate(PatchModel):
    nullable_fields = frozenset({"end_date"})

    flat_id: int | None = None
    tenant_id: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    monthly_rent: Taka | None = None
    advance_amount: Taka | None = None
    nid_number: NID | None = None
    family_members: FamilyMembers | None = None
    is_active: bool | None = None


class LeaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    flat_id: int
    tenant_id: int
    tenant_name: str = Field(validation_alias=AliasPath("tenant", "full_name"))
    tenant_phone: str | None = Field(validation_alias=AliasPath("tenant", "phone"))
    flat_no: str = Field(validation_alias=AliasPath("flat", "flat_no"))
    building_name: str = Field(validation_alias=AliasPath("flat", "building", "name"))
    start_date: date
    end_date: date | None
    monthly_rent: int
    advance_amount: int
    nid_number: str
    family_members: int
    is_active: bool
