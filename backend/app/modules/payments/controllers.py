from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.pagination import PageDep
from app.modules.auth.dependencies import AdminUser, TenantOrAdminUser
from app.modules.payments.dependencies import get_payment_service
from app.modules.payments.models import PaymentStatus, RentPayment
from app.modules.payments.repositories import PaymentFilters
from app.modules.payments.schemas import PaymentCreate, PaymentOut, PaymentUpdate
from app.modules.payments.services import PaymentService

router = APIRouter(prefix="/payments", tags=["payments"])

Service = Annotated[PaymentService, Depends(get_payment_service)]


@router.get(
    "",
    response_model=list[PaymentOut],
    summary="Rent ledger, newest month first (admin: all, tenant: own)",
)
async def list_payments(
    user: TenantOrAdminUser,
    service: Service,
    page: PageDep,
    month: Annotated[str | None, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")] = None,
    status: Annotated[PaymentStatus | None, Query()] = None,
    lease_id: Annotated[int | None, Query(ge=1)] = None,
) -> list[RentPayment]:
    filters = PaymentFilters(month=month, status=status, lease_id=lease_id)
    return await service.search(user, filters, page)


@router.get("/{payment_id}", response_model=PaymentOut, summary="Get one rent record")
async def get_payment(payment_id: int, user: TenantOrAdminUser, service: Service) -> RentPayment:
    return await service.get(user, payment_id)


@router.post(
    "",
    response_model=PaymentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a month's rent record (admin); status is computed",
    responses={409: {"description": "Record for this lease and month already exists"}},
)
async def create_payment(data: PaymentCreate, _: AdminUser, service: Service) -> RentPayment:
    return await service.create(data)


@router.patch(
    "/{payment_id}",
    response_model=PaymentOut,
    summary="Record a payment / edit a rent record (admin)",
)
async def update_payment(
    payment_id: int, data: PaymentUpdate, _: AdminUser, service: Service
) -> RentPayment:
    return await service.update(payment_id, data)


@router.delete(
    "/{payment_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a rent record"
)
async def delete_payment(payment_id: int, _: AdminUser, service: Service) -> None:
    await service.delete(payment_id)
