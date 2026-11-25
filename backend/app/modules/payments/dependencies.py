from typing import Annotated

from fastapi import Depends

from app.modules.leases.dependencies import get_lease_repository
from app.modules.leases.repositories import LeaseRepository
from app.modules.payments.repositories import PaymentRepository
from app.modules.payments.services import PaymentService
from app.modules.users.dependencies import DbSession


def get_payment_repository(db: DbSession) -> PaymentRepository:
    return PaymentRepository(db)


def get_payment_service(
    payments: Annotated[PaymentRepository, Depends(get_payment_repository)],
    leases: Annotated[LeaseRepository, Depends(get_lease_repository)],
) -> PaymentService:
    return PaymentService(payments, leases)
