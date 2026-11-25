from datetime import UTC, datetime

from app.core.exceptions import ForbiddenError, NotFoundError, UnprocessableError
from app.core.pagination import Page
from app.modules.flats.repositories import FlatRepository
from app.modules.leases.repositories import LeaseRepository
from app.modules.maintenance.models import MaintenanceRequest, MaintenanceStatus
from app.modules.maintenance.repositories import MaintenanceFilters, MaintenanceRepository
from app.modules.maintenance.schemas import MaintenanceCreate, MaintenanceUpdate
from app.modules.users.models import RoleName, User
from app.modules.users.repositories import UserRepository


class MaintenanceService:
    def __init__(
        self,
        requests: MaintenanceRepository,
        flats: FlatRepository,
        leases: LeaseRepository,
        users: UserRepository,
    ) -> None:
        self.requests = requests
        self.flats = flats
        self.leases = leases
        self.users = users

    async def search(
        self, user: User, filters: MaintenanceFilters, page: Page
    ) -> list[MaintenanceRequest]:
        if user.role_name == RoleName.TENANT:
            filters = MaintenanceFilters(
                status=filters.status,
                category=filters.category,
                priority=filters.priority,
                flat_id=filters.flat_id,
                reported_by_id=user.id,
            )
        return await self.requests.search(filters, page)

    async def get(self, user: User, request_id: int) -> MaintenanceRequest:
        request = await self.requests.get(request_id)
        if request is None or (
            user.role_name == RoleName.TENANT and request.reported_by_id != user.id
        ):
            raise NotFoundError("Maintenance request not found")
        return request

    async def create(self, user: User, data: MaintenanceCreate) -> MaintenanceRequest:
        if user.role_name == RoleName.TENANT:
            # Tenants can only report for the flat they currently rent; flat_id is ignored.
            lease = await self.leases.active_for_tenant(user.id)
            if lease is None:
                raise ForbiddenError("You need an active lease to report a repair")
            flat_id = lease.flat_id
        else:
            if data.flat_id is None:
                raise UnprocessableError("flat_id", "Choose the flat that needs the repair")
            if await self.flats.get(data.flat_id) is None:
                raise NotFoundError("Flat not found")
            flat_id = data.flat_id

        request = MaintenanceRequest(
            flat_id=flat_id,
            reported_by_id=user.id,
            title=data.title,
            description=data.description,
            category=data.category,
            priority=data.priority,
        )
        await self.requests.add(request)
        await self.requests.commit()
        return await self._fresh(request.id)

    async def update(self, request_id: int, data: MaintenanceUpdate) -> MaintenanceRequest:
        request = await self._get_any(request_id)
        changes = data.changes()

        assignee_id = changes.get("assigned_to_id")
        if assignee_id is not None:
            assignee = await self.users.get(assignee_id)
            if assignee is None or assignee.role_name not in (RoleName.ADMIN, RoleName.STAFF):
                raise UnprocessableError(
                    "assigned_to_id", "Repairs can only be assigned to staff or the owner"
                )

        new_status = changes.get("status")
        if new_status is not None and new_status != request.status:
            changes["resolved_at"] = (
                datetime.now(UTC) if new_status == MaintenanceStatus.RESOLVED else None
            )

        await self.requests.update(request, changes)
        await self.requests.commit()
        return await self._fresh(request.id)

    async def delete(self, request_id: int) -> None:
        request = await self._get_any(request_id)
        await self.requests.delete(request)
        await self.requests.commit()

    async def open_count_for_building(self, building_id: int) -> int:
        return await self.requests.count_open_by_building(building_id)

    async def _get_any(self, request_id: int) -> MaintenanceRequest:
        request = await self.requests.get(request_id)
        if request is None:
            raise NotFoundError("Maintenance request not found")
        return request

    async def _fresh(self, request_id: int) -> MaintenanceRequest:
        request = await self.requests.get(request_id, refresh=True)
        if request is None:
            raise NotFoundError("Maintenance request not found")
        return request
