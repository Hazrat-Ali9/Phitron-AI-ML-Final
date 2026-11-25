from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.core.schemas import PatchModel

BuildingName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)
]
Address = Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=255)]
Area = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=60)]
Floors = Annotated[int, Field(ge=1, le=30)]


class BuildingCreate(BaseModel):
    name: BuildingName
    address: Address
    area: Area = Field(description="Neighbourhood, e.g. Mirpur, Dhanmondi, Uttara")
    total_floors: Floors


class BuildingUpdate(PatchModel):
    name: BuildingName | None = None
    address: Address | None = None
    area: Area | None = None
    total_floors: Floors | None = None


class BuildingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    address: str
    area: str
    total_floors: int
    created_at: datetime
