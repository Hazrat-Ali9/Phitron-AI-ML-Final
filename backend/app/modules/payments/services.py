from collections import defaultdict
from datetime import UTC, date, datetime
from typing import Any

from app.core.exceptions import ConflictError, NotFoundError
from app.core.pagination import Page
from app.modules.leases.repositories import LeaseRepository
from app.modules.payments.models import PaymentStatus, RentPayment
from app.modules.payments.repositories import PaymentFilters, PaymentRepository
from app.modules.payments.schemas import (
    BuildingCollectionOut,
    CollectionSummaryOut,
    PaymentCreate,
    PaymentUpdate,
    PendingTenantOut,
    RentMonthOut,
    RentStatusOut,
)
from app.modules.users.models import RoleName, User


def compute_status(amount_due: int, amount_paid: int) -> PaymentStatus:
    if amount_paid <= 0:
        return PaymentStatus.DUE
    if amount_paid < amount_due:
        return PaymentStatus.PARTIAL
    return PaymentStatus.PAID


class PaymentService:
    def __init__(self, payments: PaymentRepository, leases: LeaseRepository) -> None:
        self.payments = payments
        self.leases = leases

    async def search(self, user: User, filters: PaymentFilters, page: Page) -> list[RentPayment]:
        if user.role_name == RoleName.TENANT:
            filters = PaymentFilters(
                month=filters.month,
                status=filters.status,
                lease_id=filters.lease_id,
                tenant_id=user.id,
            )
        return await self.payments.search(filters, page)

    async def get(self, user: User, payment_id: int) -> RentPayment:
        payment = await self.payments.get(payment_id)
        if payment is None or (
            user.role_name == RoleName.TENANT and payment.lease.tenant_id != user.id
        ):
            raise NotFoundError("Payment record not found")
        return payment

    async def create(self, data: PaymentCreate) -> RentPayment:
        lease = await self.leases.get(data.lease_id)
        if lease is None:
            raise NotFoundError("Lease not found")
        if await self.payments.exists_for_month(lease.id, data.month):
            raise ConflictError(
                f"A rent record for {data.month} already exists for {lease.tenant.full_name}"
            )

        values = data.model_dump()
        values["amount_due"] = data.amount_due or lease.monthly_rent
        self._apply_rules(values)
        payment = RentPayment(**values)
        await self.payments.add(payment)
        await self.payments.commit()
        return await self._fresh(payment.id)

    async def update(self, payment_id: int, data: PaymentUpdate) -> RentPayment:
        payment = await self._get_admin(payment_id)
        changes = data.changes()
        if "month" in changes and await self.payments.exists_for_month(
            payment.lease_id, changes["month"], exclude_id=payment.id
        ):
            raise ConflictError(f"A rent record for {changes['month']} already exists")

        merged = {
            "amount_due": payment.amount_due,
            "amount_paid": payment.amount_paid,
            "paid_at": payment.paid_at,
            **changes,
        }
        self._apply_rules(merged)
        changes["status"] = merged["status"]
        changes["paid_at"] = merged["paid_at"]
        await self.payments.update(payment, changes)
        await self.payments.commit()
        return await self._fresh(payment.id)

    async def delete(self, payment_id: int) -> None:
        payment = await self._get_admin(payment_id)
        await self.payments.delete(payment)
        await self.payments.commit()

    # ---- reports -------------------------------------------------------------------------

    async def rent_status_for_tenant(self, tenant: User) -> RentStatusOut:
        """The tenant's current lease and every rent record on it, newest month first."""
        lease = await self.leases.active_for_tenant(tenant.id)
        if lease is None:
            return RentStatusOut(has_active_lease=False)
        records = await self.payments.search(PaymentFilters(lease_id=lease.id))
        months = [
            RentMonthOut(
                month=p.month,
                amount_due=p.amount_due,
                amount_paid=p.amount_paid,
                outstanding=max(p.amount_due - p.amount_paid, 0),
                status=p.status,
                method=p.method,
                paid_at=p.paid_at,
            )
            for p in records
        ]
        return RentStatusOut(
            has_active_lease=True,
            building=lease.flat.building.name,
            flat_no=lease.flat.flat_no,
            monthly_rent=lease.monthly_rent,
            lease_start=lease.start_date.isoformat(),
            months=months,
            total_outstanding=sum(m.outstanding for m in months),
        )

    async def collection_summary(self, month: str | None = None) -> CollectionSummaryOut:
        """Expected vs collected rent for one month across all buildings.

        An active lease with no rent record for the month counts as fully due.
        """
        month = month or date.today().strftime("%Y-%m")
        records = await self.payments.search(PaymentFilters(month=month))
        recorded_leases = {p.lease_id for p in records}

        rows: list[PendingTenantOut] = []
        for p in records:
            lease = p.lease
            rows.append(
                PendingTenantOut(
                    tenant_name=lease.tenant.full_name,
                    tenant_phone=lease.tenant.phone,
                    building=lease.flat.building.name,
                    flat_no=lease.flat.flat_no,
                    amount_due=p.amount_due,
                    amount_paid=p.amount_paid,
                    outstanding=max(p.amount_due - p.amount_paid, 0),
                    status=p.status.value,
                )
            )
        for lease in await self.leases.list_active():
            if lease.id in recorded_leases or lease.start_date.strftime("%Y-%m") > month:
                continue
            rows.append(
                PendingTenantOut(
                    tenant_name=lease.tenant.full_name,
                    tenant_phone=lease.tenant.phone,
                    building=lease.flat.building.name,
                    flat_no=lease.flat.flat_no,
                    amount_due=lease.monthly_rent,
                    amount_paid=0,
                    outstanding=lease.monthly_rent,
                    status="no_record",
                )
            )

        per_building: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for row in rows:
            per_building[row.building][0] += row.amount_due
            per_building[row.building][1] += row.amount_paid
        expected = sum(row.amount_due for row in rows)
        collected = sum(row.amount_paid for row in rows)
        outstanding = sum(row.outstanding for row in rows)
        return CollectionSummaryOut(
            month=month,
            expected=expected,
            collected=collected,
            outstanding=outstanding,
            collection_rate_percent=round(100 * collected / expected, 1) if expected else 0.0,
            by_building=[
                BuildingCollectionOut(
                    building=name,
                    expected=due,
                    collected=paid,
                    outstanding=max(due - paid, 0),
                )
                for name, (due, paid) in sorted(per_building.items())
            ],
            pending_tenants=sorted(
                (row for row in rows if row.outstanding > 0),
                key=lambda row: (row.building, row.flat_no),
            ),
        )

    @staticmethod
    def _apply_rules(values: dict[str, Any]) -> None:
        """status is always derived from the amounts; a payment gets a paid_at timestamp."""
        values["status"] = compute_status(values["amount_due"], values["amount_paid"])
        if values["amount_paid"] > 0 and values.get("paid_at") is None:
            values["paid_at"] = datetime.now(UTC)
        if values["amount_paid"] == 0:
            values["paid_at"] = None

    async def _get_admin(self, payment_id: int) -> RentPayment:
        payment = await self.payments.get(payment_id)
        if payment is None:
            raise NotFoundError("Payment record not found")
        return payment

    async def _fresh(self, payment_id: int) -> RentPayment:
        payment = await self.payments.get(payment_id, refresh=True)
        if payment is None:
            raise NotFoundError("Payment record not found")
        return payment
