from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.modules.users.models import RoleName


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: EmailStr
    phone: str | None
    # The ORM `User.role` is a Role row; the API exposes just its name.
    role: RoleName = Field(validation_alias="role_name")
    is_active: bool
    created_at: datetime
