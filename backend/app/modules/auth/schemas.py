from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, EmailStr, Field, StringConstraints

from app.core.validators import OptionalBDPhone

LowerEmail = Annotated[EmailStr, AfterValidator(str.lower)]
FullName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]


class RegisterIn(BaseModel):
    full_name: FullName
    email: LowerEmail
    phone: OptionalBDPhone = None
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: LowerEmail
    password: str = Field(min_length=1, max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(description="Seconds until the token expires")
