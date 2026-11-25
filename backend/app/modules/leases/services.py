from datetime import date

from app.core.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.core.pagination import Page
from app.modules.flats.models import Flat, FlatStatus
from app.modules.flats.repositories import FlatRepository
from app.modules.leases.models import Lease
from app.modules.leases.repositories import LeaseFilters, LeaseRepository
from app.modules.leases.schemas import LeaseCreate, LeaseUpdate
from app.modules.users.models import RoleName, User
from app.modules.users.repositories import UserRepository


class LeaseService:
    def __init__(
        self, leases: LeaseRepository, flats: FlatRepository, users: UserRepository
    ) -> None:
        self.leases = leases
        self.flats = flats
        self.users = users

    # ---- reads ------------------------------------------------------------------------

    async def search(self, user: User, filters: LeaseFilters, page: Page) -> list[Lease]:
        if user.role_name == RoleName.TENANT:
            filters = LeaseFilters(q=filters.q, is_active=filters.is_active, tenant_id=user.id)
        return await self.leases.search(filters, page)

    async def get(self, user: User, lease_id: int) -> Lease:
        lease = await self.leases.get(lease_id)
        # A tenant asking for someone else's lease gets the same 404 as a missing one,
        # so the API does not reveal that the lease exists.
        if lease is None or (user.role_name == RoleName.TENANT and lease.tenant_id != user.id):
            raise NotFoundError("Lease not found")
        return lease

    async def current_for_tenant(self, tenant: User) -> Lease | None:
        return await self.leases.active_for_tenant(tenant.id)

    # ---- writes (admin) ---------------------------------------------------------------

    async def create(self, data: LeaseCreate) -> Lease:
        flat = await self._get_flat(data.flat_id)
        await self._check_tenant(data.tenant_id)
        if data.is_active:
            await self._check_no_active_lease(flat)

        lease = Lease(**data.model_dump())
        await self.leases.add(lease)
        await self._sync_flat_status(flat)
        await self.leases.commit()
        return await self._fresh(lease.id)

    async def update(self, lease_id: int, data: LeaseUpdate) -> Lease:
        lease = await self._get_admin(lease_id)
        changes = data.changes()
        old_flat = lease.flat

        new_flat = old_flat
        if "flat_id" in changes and changes["flat_id"] != lease.flat_id:
            new_flat = await self._get_flat(changes["flat_id"])
        if "tenant_id" in changes and changes["tenant_id"] != lease.tenant_id:
            await self._check_tenant(changes["tenant_id"])

        will_be_active = changes.get("is_active", lease.is_active)
        if will_be_active and (new_flat.id != old_flat.id or not lease.is_active):
            await self._check_no_active_lease(new_flat, exclude_lease_id=lease.id)

        # "End lease": the frontend sends {is_active: false, end_date}. Fill end_date if missing.
        if (
            lease.is_active
            and not will_be_active
            and changes.get("end_date", lease.end_date) is None
        ):
            changes["end_date"] = max(date.today(), changes.get("start_date", lease.start_date))

        start = changes.get("start_date", lease.start_date)
        end = changes.get("end_date", lease.end_date)
        if end is not None and end < start:
            raise UnprocessableError("end_date", "End date must be on or after the start date")

        await self.leases.update(lease, changes)
        await self._sync_flat_status(new_flat)
        if new_flat.id != old_flat.id:
            await self._sync_flat_status(old_flat)
        await self.leases.commit()
        return await self._fresh(lease.id)

    async def delete(self, lease_id: int) -> None:
        lease = await self._get_admin(lease_id)
        flat = lease.flat
        await self.leases.delete(lease)  # rent_payments cascade
        await self._sync_flat_status(flat)
        await self.leases.commit()

    # ---- helpers ----------------------------------------------------------------------

    async def _get_admin(self, lease_id: int) -> Lease:
        lease = await self.leases.get(lease_id)
        if lease is None:
            raise NotFoundError("Lease not found")
        return lease

    async def _fresh(self, lease_id: int) -> Lease:
        lease = await self.leases.get(lease_id, refresh=True)
        if lease is None:
            raise NotFoundError("Lease not found")
        return lease

    async def _get_flat(self, flat_id: int) -> Flat:
        flat = await self.flats.get(flat_id)
        if flat is None:
            raise NotFoundError("Flat not found")
        return flat

    async def _check_tenant(self, tenant_id: int) -> None:
        tenant = await self.users.get(tenant_id)
        if tenant is None or tenant.role_name != RoleName.TENANT:
            raise UnprocessableError("tenant_id", "Choose a user with the tenant role")
        if not tenant.is_active:
            raise UnprocessableError("tenant_id", "This tenant account is deactivated")

    async def _check_no_active_lease(self, flat: Flat, exclude_lease_id: int | None = None) -> None:
        if await self.leases.active_for_flat(flat.id, exclude_id=exclude_lease_id):
            raise ConflictError(
                f"Flat {flat.flat_no} in {flat.building.name} already has an active lease"
            )

    async def _sync_flat_status(self, flat: Flat) -> None:
        """occupied while there is an active lease; back to vacant when there is none.
        A flat under maintenance stays under maintenance when its lease ends."""
        if await self.leases.active_for_flat(flat.id):
            if flat.status != FlatStatus.OCCUPIED:
                await self.flats.set_status(flat, FlatStatus.OCCUPIED)
        elif flat.status == FlatStatus.OCCUPIED:
            await self.flats.set_status(flat, FlatStatus.VACANT)
