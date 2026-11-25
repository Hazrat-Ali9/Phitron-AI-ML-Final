from datetime import datetime
from typing import Annotated

from pydantic import AliasPath, BaseModel, ConfigDict, Field, StringConstraints

from app.core.schemas import PatchModel
from app.modules.maintenance.models import (
    MaintenanceCategory,
    MaintenancePriority,
    MaintenanceStatus,
)

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=120)]
Details = Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=2000)]


class MaintenanceCreate(BaseModel):
    flat_id: int | None = Field(
        default=None, description="Required for admin/staff. Tenants: their active lease's flat."
    )
    title: Title
    description: Details
    category: MaintenanceCategory
    priority: MaintenancePriority = MaintenancePriority.MEDIUM


class MaintenanceUpdate(PatchModel):
    nullable_fields = frozenset({"assigned_to_id"})

    status: MaintenanceStatus | None = None
    priority: MaintenancePriority | None = None
    assigned_to_id: int | None = None


class MaintenanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    flat_id: int
    flat_no: str = Field(validation_alias=AliasPath("flat", "flat_no"))
    building_name: str = Field(validation_alias=AliasPath("flat", "building", "name"))
    reported_by_id: int
    reported_by_name: str = Field(validation_alias=AliasPath("reported_by", "full_name"))
    title: str
    description: str
    category: MaintenanceCategory
    priority: MaintenancePriority
    status: MaintenanceStatus
    assigned_to_id: int | None
    assigned_to_name: str | None = Field(
        default=None, validation_alias=AliasPath("assigned_to", "full_name")
    )
    created_at: datetime
    resolved_at: datetime | None
