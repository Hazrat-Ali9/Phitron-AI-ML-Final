"""Fill the database with realistic demo data (Dhaka buildings, tenants, rent, repairs).

Idempotent: every row is looked up by its natural key first, so running it twice creates
nothing new. Demo logins match the frontend's login page:

    owner      rahman@baribhara.app    / admin123
    caretaker  karim@baribhara.app     / staff123
    tenant     tanvir.hasan@gmail.com  / tenant123   (and the other tenants below)

Run from backend/:  uv run python -m scripts.seed
"""

import asyncio
import hashlib
from collections import Counter
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models  # noqa: F401  (register all models)
from app.core.database import SessionLocal, engine
from app.core.security import hash_password
from app.core.validators import normalize_bd_phone
from app.modules.buildings.models import Building
from app.modules.flats.models import Flat, FlatStatus
from app.modules.leases.models import Lease
from app.modules.maintenance.models import (
    MaintenanceCategory,
    MaintenancePriority,
    MaintenanceRequest,
    MaintenanceStatus,
)
from app.modules.payments.models import PaymentMethod, RentPayment
from app.modules.payments.services import compute_status
from app.modules.users.models import Role, RoleName, User

# ---- data ---------------------------------------------------------------------------------

# email, full name, phone, role, password
USERS = [
    ("rahman@baribhara.app", "Abdur Rahman", "01711-482913", RoleName.ADMIN, "admin123"),
    ("karim@baribhara.app", "Md. Karim Uddin", "01819-205577", RoleName.STAFF, "staff123"),
    ("tanvir.hasan@gmail.com", "Tanvir Hasan", "01712-334455", RoleName.TENANT, "tenant123"),
    ("nusrat.jahan@gmail.com", "Nusrat Jahan", "01915-667788", RoleName.TENANT, "tenant123"),
    ("farhana.akter@yahoo.com", "Farhana Akter", "01633-901122", RoleName.TENANT, "tenant123"),
    ("mahmud.islam@gmail.com", "Mahmudul Islam", "01556-778899", RoleName.TENANT, "tenant123"),
    ("shirin.sultana@gmail.com", "Shirin Sultana", "01799-110022", RoleName.TENANT, "tenant123"),
    ("rafiq.alam@outlook.com", "Rafiqul Alam", "01711-908070", RoleName.TENANT, "tenant123"),
    ("sabbir.ahmed@gmail.com", "Sabbir Ahmed", "01844-556677", RoleName.TENANT, "tenant123"),
    ("ayesha.s@gmail.com", "Ayesha Siddiqua", "01977-223344", RoleName.TENANT, "tenant123"),
    ("imran.hossain@gmail.com", "Imran Hossain", "01722-889900", RoleName.TENANT, "tenant123"),
]

# name, address, area, total floors
BUILDINGS = [
    ("Rahman Villa", "House 12, Road 5, Section 10, Mirpur, Dhaka 1216", "Mirpur", 6),
    ("Nur Manzil", "House 34/A, Road 9/A, Dhanmondi, Dhaka 1209", "Dhanmondi", 7),
    ("Shanti Neer", "House 7, Road 14, Sector 11, Uttara, Dhaka 1230", "Uttara", 5),
]

# building, flat_no, floor, beds, baths, sqft, rent, service charge, status, description
FLATS = [
    ("Rahman Villa", "2A", 2, 3, 2, 1250, 22000, 2000, "occupied", "South-facing, 2 balconies"),
    ("Rahman Villa", "2B", 2, 2, 2, 950, 18000, 2000, "occupied", None),
    ("Rahman Villa", "3A", 3, 3, 2, 1250, 22000, 2000, "occupied", "South-facing, 2 balconies"),
    (
        "Rahman Villa",
        "3B",
        3,
        2,
        2,
        950,
        18000,
        2000,
        "vacant",
        "Newly painted, gas line connected",
    ),
    ("Rahman Villa", "4A", 4, 3, 2, 1250, 22500, 2000, "occupied", None),
    (
        "Rahman Villa",
        "4B",
        4,
        2,
        2,
        950,
        18500,
        2000,
        "maintenance",
        "Bathroom tiles being replaced",
    ),
    ("Rahman Villa", "5A", 5, 3, 3, 1300, 23500, 2000, "vacant", "Top floor, roof access"),
    ("Rahman Villa", "5B", 5, 2, 2, 950, 19000, 2000, "occupied", None),
    (
        "Nur Manzil",
        "3A",
        3,
        3,
        3,
        1800,
        45000,
        5000,
        "vacant",
        "Lake-view, servant room, 1 car parking",
    ),
    ("Nur Manzil", "4A", 4, 3, 3, 1800, 46000, 5000, "occupied", "1 car parking"),
    ("Nur Manzil", "5A", 5, 3, 3, 1800, 47000, 5000, "occupied", "1 car parking"),
    ("Nur Manzil", "6A", 6, 4, 3, 2100, 55000, 5000, "vacant", "Duplex-style, 2 car parking"),
    ("Shanti Neer", "2A", 2, 3, 2, 1350, 26000, 3000, "occupied", "Near Sector 11 market"),
    ("Shanti Neer", "2B", 2, 3, 2, 1350, 25000, 3000, "vacant", None),
    ("Shanti Neer", "3A", 3, 3, 2, 1350, 26500, 3000, "vacant", "Generator backup"),
    ("Shanti Neer", "3B", 3, 3, 2, 1350, 26000, 3000, "occupied", "Generator backup"),
]

# tenant email, (building, flat_no), months ago the lease started, NID, family members
LEASES = [
    ("tanvir.hasan@gmail.com", ("Rahman Villa", "2A"), 14, "1992384756", 4),
    ("nusrat.jahan@gmail.com", ("Rahman Villa", "2B"), 10, "1995472831", 2),
    ("farhana.akter@yahoo.com", ("Rahman Villa", "3A"), 8, "1988726351423", 3),
    ("mahmud.islam@gmail.com", ("Rahman Villa", "4A"), 7, "1990183746", 5),
    ("shirin.sultana@gmail.com", ("Rahman Villa", "5B"), 5, "1987364521", 3),
    ("rafiq.alam@outlook.com", ("Nur Manzil", "4A"), 11, "1979283746", 4),
    ("sabbir.ahmed@gmail.com", ("Nur Manzil", "5A"), 4, "1993746152", 2),
    ("ayesha.s@gmail.com", ("Shanti Neer", "2A"), 3, "1996152837", 3),
    ("imran.hossain@gmail.com", ("Shanti Neer", "3B"), 2, "1991827364", 4),
]

# Amount paid that differs from "paid in full": (tenant email, months from now) -> taka
PAYMENT_EXCEPTIONS = {
    ("tanvir.hasan@gmail.com", 0): 0,
    ("shirin.sultana@gmail.com", 0): 0,
    ("ayesha.s@gmail.com", 0): 0,
    ("mahmud.islam@gmail.com", 0): 15000,
    ("shirin.sultana@gmail.com", -1): 10000,
}
METHODS = [
    PaymentMethod.BKASH,
    PaymentMethod.NAGAD,
    PaymentMethod.BANK,
    PaymentMethod.CASH,
    PaymentMethod.BKASH,
]

# (building, flat_no), reporter email, title, description, category, priority, status,
# days ago created, days ago resolved, assigned to caretaker?
MAINTENANCE = [
    (("Rahman Villa", "2A"), "tanvir.hasan@gmail.com", "Kitchen sink leaking",
     "Water is leaking under the kitchen sink since last night. The cabinet below is getting wet.",
     "plumbing", "high", "open", 1, None, False),
    (("Rahman Villa", "4A"), "mahmud.islam@gmail.com", "Bedroom fan regulator not working",
     "Fan only runs at full speed, regulator seems burnt.",
     "electrical", "medium", "in_progress", 3, None, True),
    (("Nur Manzil", "4A"), "rafiq.alam@outlook.com", "Lift stops between 3rd and 4th floor",
     "Lift stopped twice this week between floors. Elderly parents live with us, please check urgently.",
     "lift", "urgent", "in_progress", 2, None, True),
    (("Shanti Neer", "2A"), "ayesha.s@gmail.com", "Low gas pressure in the morning",
     "Gas burner flame is very low between 7am and 10am.",
     "gas", "medium", "open", 5, None, False),
    (("Rahman Villa", "3A"), "farhana.akter@yahoo.com", "Damp patch on bedroom wall",
     "Seepage on the north wall after the rain, paint is peeling.",
     "painting", "low", "resolved", 20, 12, True),
    (("Rahman Villa", "5B"), "shirin.sultana@gmail.com", "Bathroom flush broken",
     "The flush handle broke off, water keeps running.",
     "plumbing", "high", "resolved", 9, 8, True),
]  # fmt: skip


# ---- helpers ------------------------------------------------------------------------------


def month_start(months_from_now: int, today: date | None = None) -> date:
    today = today or date.today()
    index = today.year * 12 + (today.month - 1) + months_from_now
    return date(index // 12, index % 12 + 1, 1)


def trx_id(method: PaymentMethod, lease_id: int, month: str) -> str | None:
    if method == PaymentMethod.CASH:
        return None
    digest = hashlib.sha1(f"{lease_id}-{month}".encode()).hexdigest().upper()
    prefix = {"bkash": "BK", "nagad": "NG", "bank": "BT"}[method.value]
    return prefix + digest[:8]


class Seeder:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.created: Counter[str] = Counter()

    async def roles(self) -> dict[str, Role]:
        roles = {}
        for name in RoleName:
            role = await self.session.scalar(select(Role).where(Role.name == name.value))
            if role is None:
                role = Role(name=name.value)
                self.session.add(role)
                self.created["roles"] += 1
            roles[name.value] = role
        await self.session.flush()
        return roles

    async def users(self, roles: dict[str, Role]) -> dict[str, User]:
        users = {}
        for email, full_name, phone, role, password in USERS:
            user = await self.session.scalar(select(User).where(User.email == email))
            if user is None:
                user = User(
                    email=email,
                    full_name=full_name,
                    phone=normalize_bd_phone(phone),
                    password_hash=hash_password(password),
                    role=roles[role.value],
                )
                self.session.add(user)
                self.created["users"] += 1
            users[email] = user
        await self.session.flush()
        return users

    async def buildings(self, owner: User) -> dict[str, Building]:
        buildings = {}
        for name, address, area, floors in BUILDINGS:
            building = await self.session.scalar(select(Building).where(Building.name == name))
            if building is None:
                building = Building(
                    name=name, address=address, area=area, total_floors=floors, owner_id=owner.id
                )
                self.session.add(building)
                self.created["buildings"] += 1
            buildings[name] = building
        await self.session.flush()
        return buildings

    async def flats(self, buildings: dict[str, Building]) -> dict[tuple[str, str], Flat]:
        flats = {}
        for bname, flat_no, floor, beds, baths, sqft, rent, service, status, desc in FLATS:
            building = buildings[bname]
            flat = await self.session.scalar(
                select(Flat).where(Flat.building_id == building.id, Flat.flat_no == flat_no)
            )
            if flat is None:
                flat = Flat(
                    building_id=building.id,
                    flat_no=flat_no,
                    floor=floor,
                    bedrooms=beds,
                    bathrooms=baths,
                    size_sqft=sqft,
                    monthly_rent=rent,
                    service_charge=service,
                    status=FlatStatus(status),
                    description=desc,
                )
                self.session.add(flat)
                self.created["flats"] += 1
            flats[(bname, flat_no)] = flat
        await self.session.flush()
        return flats

    async def leases(
        self, users: dict[str, User], flats: dict[tuple[str, str], Flat]
    ) -> dict[str, Lease]:
        leases = {}
        for email, flat_key, months_ago, nid, family in LEASES:
            tenant, flat = users[email], flats[flat_key]
            lease = await self.session.scalar(
                select(Lease).where(Lease.flat_id == flat.id, Lease.tenant_id == tenant.id)
            )
            if lease is None:
                lease = Lease(
                    flat_id=flat.id,
                    tenant_id=tenant.id,
                    start_date=month_start(-months_ago),
                    monthly_rent=flat.monthly_rent + flat.service_charge,
                    advance_amount=flat.monthly_rent * 2,
                    nid_number=nid,
                    family_members=family,
                    is_active=True,
                )
                self.session.add(lease)
                self.created["leases"] += 1
            leases[email] = lease
        await self.session.flush()
        return leases

    async def payments(self, leases: dict[str, Lease]) -> None:
        """Rent records for the last 3 months; this month is a mix of paid, partial and due."""
        for offset in (-2, -1, 0):
            month_date = month_start(offset)
            month = month_date.strftime("%Y-%m")
            for email, lease in leases.items():
                if lease.start_date > month_date:
                    continue
                exists = await self.session.scalar(
                    select(RentPayment.id).where(
                        RentPayment.lease_id == lease.id, RentPayment.month == month
                    )
                )
                if exists:
                    continue
                paid = PAYMENT_EXCEPTIONS.get((email, offset), lease.monthly_rent)
                method = METHODS[(lease.id + offset + 3) % len(METHODS)] if paid else None
                paid_at = (
                    datetime(
                        month_date.year, month_date.month, 3 + lease.id % 6, 10, 30, tzinfo=UTC
                    )
                    if paid
                    else None
                )
                self.session.add(
                    RentPayment(
                        lease_id=lease.id,
                        month=month,
                        amount_due=lease.monthly_rent,
                        amount_paid=paid,
                        method=method,
                        trx_id=trx_id(method, lease.id, month) if method else None,
                        paid_at=paid_at,
                        status=compute_status(lease.monthly_rent, paid),
                    )
                )
                self.created["rent records"] += 1
        await self.session.flush()

    async def maintenance(
        self, users: dict[str, User], flats: dict[tuple[str, str], Flat], caretaker: User
    ) -> None:
        now = datetime.now(UTC)
        for (
            flat_key, email, title, description, category, priority, status,
            created_days_ago, resolved_days_ago, assigned,
        ) in MAINTENANCE:  # fmt: skip
            flat = flats[flat_key]
            exists = await self.session.scalar(
                select(MaintenanceRequest.id).where(
                    MaintenanceRequest.flat_id == flat.id, MaintenanceRequest.title == title
                )
            )
            if exists:
                continue
            self.session.add(
                MaintenanceRequest(
                    flat_id=flat.id,
                    reported_by_id=users[email].id,
                    assigned_to_id=caretaker.id if assigned else None,
                    title=title,
                    description=description,
                    category=MaintenanceCategory(category),
                    priority=MaintenancePriority(priority),
                    status=MaintenanceStatus(status),
                    created_at=now - timedelta(days=created_days_ago, hours=3),
                    resolved_at=(
                        now - timedelta(days=resolved_days_ago) if resolved_days_ago else None
                    ),
                )
            )
            self.created["maintenance requests"] += 1
        await self.session.flush()

    async def run(self) -> None:
        roles = await self.roles()
        users = await self.users(roles)
        owner = users["rahman@baribhara.app"]
        caretaker = users["karim@baribhara.app"]
        buildings = await self.buildings(owner)
        flats = await self.flats(buildings)
        leases = await self.leases(users, flats)
        await self.payments(leases)
        await self.maintenance(users, flats, caretaker)
        await self.session.commit()


async def main() -> None:
    async with SessionLocal() as session:
        seeder = Seeder(session)
        await seeder.run()
    await engine.dispose()

    if seeder.created:
        print("Seed complete. Created:")
        for what, count in seeder.created.items():
            print(f"  {count:>3} {what}")
    else:
        print("Seed complete. Nothing new to create (database already seeded).")
    print("\nDemo logins:")
    print("  owner      rahman@baribhara.app   / admin123")
    print("  caretaker  karim@baribhara.app    / staff123")
    print("  tenant     tanvir.hasan@gmail.com / tenant123")


if __name__ == "__main__":
    asyncio.run(main())
