from typing import Annotated

from pydantic import AliasPath, BaseModel, ConfigDict, Field, StringConstraints

from app.core.schemas import PatchModel
from app.modules.flats.models import FlatStatus

FlatNo = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        to_upper=True,
        min_length=1,
        max_length=10,
        pattern=r"^[A-Za-z0-9/-]+$",
    ),
]
Floor = Annotated[int, Field(ge=0, le=30)]
Rooms = Annotated[int, Field(ge=1, le=10)]
Sqft = Annotated[int, Field(gt=0, le=20000)]
Taka = Annotated[int, Field(ge=0, le=10_000_000, description="Whole taka")]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]


class FlatCreate(BaseModel):
    building_id: int
    flat_no: FlatNo = Field(examples=["3B"])
    floor: Floor
    bedrooms: Rooms
    bathrooms: Rooms
    size_sqft: Sqft
    monthly_rent: Taka
    service_charge: Taka = 0
    status: FlatStatus = FlatStatus.VACANT
    description: Description | None = None


class FlatUpdate(PatchModel):
    nullable_fields = frozenset({"description"})

    building_id: int | None = None
    flat_no: FlatNo | None = None
    floor: Floor | None = None
    bedrooms: Rooms | None = None
    bathrooms: Rooms | None = None
    size_sqft: Sqft | None = None
    monthly_rent: Taka | None = None
    service_charge: Taka | None = None
    status: FlatStatus | None = None
    description: Description | None = None


class FlatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    building_id: int
    building_name: str = Field(validation_alias=AliasPath("building", "name"))
    area: str = Field(validation_alias=AliasPath("building", "area"))
    flat_no: str
    floor: int
    bedrooms: int
    bathrooms: int
    size_sqft: int
    monthly_rent: int
    service_charge: int
    status: FlatStatus
    description: str | None
