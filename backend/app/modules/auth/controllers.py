from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.modules.auth.dependencies import CurrentUser, get_auth_service
from app.modules.auth.schemas import LoginIn, RegisterIn, TokenOut
from app.modules.auth.services import AuthService
from app.modules.users.models import User
from app.modules.users.schemas import UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

Service = Annotated[AuthService, Depends(get_auth_service)]


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a tenant account",
    responses={409: {"description": "Email already registered"}},
)
async def register(data: RegisterIn, service: Service) -> User:
    return await service.register(data)


@router.post(
    "/login",
    response_model=TokenOut,
    summary="Get an access token",
    responses={401: {"description": "Incorrect email or password"}},
)
async def login(data: LoginIn, service: Service) -> TokenOut:
    return await service.login(data)


@router.get("/me", response_model=UserOut, summary="The logged-in user")
async def me(user: CurrentUser) -> User:
    return user
