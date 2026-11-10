"""Hospital directory tests: admin-only department/staff management.

These run without a database by mocking the small slice of the async session
that the service layer touches (``execute`` for lookups, ``flush`` for writes).
"""

import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from src.backend.services.hospital_management import schemas, services
from src.backend.services.hospital_management import dependencies
from src.backend.services.hospital_management.routers import hospitals as hospitals_router
from src.backend.services.hospital_management.routers import staff as staff_router


def _request(roles=None, permissions=None, hospital_id=None, user_id="clerk-1"):
    state = SimpleNamespace(
        roles=roles or [],
        permissions=permissions,
        hospital_id=hospital_id,
        user_id=user_id,
        username="Clerk",
    )
    return SimpleNamespace(state=state)


def _perms(*allowed):
    return SimpleNamespace(has_permission=lambda permission: permission in allowed)


def _db():
    return SimpleNamespace(add=Mock(), flush=AsyncMock())


class DepartmentServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_update_applies_only_supplied_fields(self):
        db = _db()
        service = services.HospitalService(db, uuid.uuid4(), "admin-1")
        department = SimpleNamespace(
            id=uuid.uuid4(),
            name="Outpatient",
            code="OPD",
            location=None,
            is_active=True,
            updated_by=None,
        )
        service.get_department = AsyncMock(return_value=department)

        result = await service.update_department(
            department.id,
            schemas.DepartmentUpdate(name="Outpatient Department", location="Block B"),
        )

        self.assertIs(result, department)
        self.assertEqual(department.name, "Outpatient Department")
        self.assertEqual(department.location, "Block B")
        # Untouched fields survive a partial update.
        self.assertEqual(department.code, "OPD")
        self.assertEqual(department.updated_by, "admin-1")
        db.flush.assert_awaited_once()

    async def test_update_missing_department_raises_lookup_error(self):
        service = services.HospitalService(_db(), uuid.uuid4(), "admin-1")
        service.get_department = AsyncMock(return_value=None)

        with pytest.raises(LookupError):
            await service.update_department(
                uuid.uuid4(), schemas.DepartmentUpdate(name="Cardiology")
            )

    async def test_deactivate_keeps_row_and_flags_inactive(self):
        db = _db()
        service = services.HospitalService(db, uuid.uuid4(), "admin-1")
        department = SimpleNamespace(id=uuid.uuid4(), is_active=True, updated_by=None)
        service.get_department = AsyncMock(return_value=department)

        result = await service.deactivate_department(department.id)

        self.assertFalse(result.is_active)
        self.assertEqual(result.updated_by, "admin-1")
        db.flush.assert_awaited_once()

    async def test_list_departments_can_include_inactive(self):
        db = SimpleNamespace(execute=AsyncMock())
        db.execute.return_value = SimpleNamespace(
            scalars=lambda: SimpleNamespace(all=lambda: [])
        )
        service = services.HospitalService(db, uuid.uuid4(), "admin-1")

        await service.get_departments(include_inactive=True)
        everything = str(db.execute.await_args.args[0].whereclause)
        await service.get_departments(include_inactive=False)
        active_only = str(db.execute.await_args.args[0].whereclause)

        # The is_active filter is only applied for the default listing.
        self.assertNotIn("is_active", everything)
        self.assertIn("is_active", active_only)


class StaffServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_update_staff_can_reassign_department_and_role(self):
        db = _db()
        service = services.StaffService(db, uuid.uuid4(), "admin-1")
        staff = SimpleNamespace(
            id=uuid.uuid4(),
            first_name="John",
            last_name="Mwamba",
            role="doctor",
            department_id=None,
            is_active=True,
            updated_by=None,
        )
        service.get_staff = AsyncMock(return_value=staff)
        department_id = uuid.uuid4()
        db.scalar = AsyncMock(return_value=department_id)

        result = await service.update_staff(
            staff.id,
            schemas.StaffUpdate(department_id=department_id, role=schemas.StaffRole.nurse),
        )

        self.assertIs(result, staff)
        self.assertEqual(staff.department_id, department_id)
        self.assertEqual(staff.role, "nurse")
        self.assertEqual(staff.last_name, "Mwamba")
        self.assertEqual(staff.updated_by, "admin-1")
        db.flush.assert_awaited_once()

    async def test_create_staff_rejects_unavailable_department(self):
        db = _db()
        db.scalar = AsyncMock(return_value=None)
        service = services.StaffService(db, uuid.uuid4(), "admin-1")
        data = schemas.StaffCreate(
            first_name="Jane", last_name="Banda", role="doctor", department_id=uuid.uuid4()
        )
        with self.assertRaisesRegex(ValueError, "active department"):
            await service.create_staff(data)
        db.flush.assert_not_awaited()

    async def test_deactivate_staff_soft_deletes(self):
        db = _db()
        service = services.StaffService(db, uuid.uuid4(), "admin-1")
        staff = SimpleNamespace(id=uuid.uuid4(), is_active=True, updated_by=None)
        service.get_staff = AsyncMock(return_value=staff)

        result = await service.deactivate_staff(staff.id)

        self.assertFalse(result.is_active)
        db.flush.assert_awaited_once()

    async def test_update_missing_staff_raises_lookup_error(self):
        service = services.StaffService(_db(), uuid.uuid4(), "admin-1")
        service.get_staff = AsyncMock(return_value=None)

        with pytest.raises(LookupError):
            await service.update_staff(uuid.uuid4(), schemas.StaffUpdate(phone="+260970000000"))


class DirectorySchemaTests(unittest.TestCase):
    def test_department_update_rejects_blank_name(self):
        with pytest.raises(ValidationError):
            schemas.DepartmentUpdate(name="")

    def test_staff_update_rejects_unknown_role(self):
        with pytest.raises(ValidationError):
            schemas.StaffUpdate(role="witch_doctor")

    def test_staff_update_rejects_impossible_hours(self):
        with pytest.raises(ValidationError):
            schemas.StaffUpdate(max_hours_per_week=0)


class DirectoryAdminGuardTests(unittest.IsolatedAsyncioTestCase):
    async def test_admin_role_is_allowed(self):
        await hospitals_router._require_admin(_request(roles=["admin"]))
        await staff_router._require_admin(_request(roles=["admin"]))

    async def test_admin_permission_is_allowed(self):
        await hospitals_router._require_admin(_request(permissions=_perms("admin:*")))
        await staff_router._require_admin(_request(permissions=_perms("admin:*")))

    async def test_other_roles_are_rejected(self):
        for router in (hospitals_router, staff_router):
            with pytest.raises(HTTPException) as excinfo:
                await router._require_admin(
                    _request(roles=["doctor"], permissions=_perms("patient_flow:write"))
                )
            self.assertEqual(excinfo.value.status_code, 403)


class HospitalIdFallbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_platform_admin_without_claim_uses_seeded_hospital(self):
        hospital_id = await dependencies.get_hospital_id_header(
            _request(roles=["admin"]), x_hospital_id=None
        )
        self.assertEqual(hospital_id, dependencies.DEFAULT_HOSPITAL_ID)

    async def test_non_admin_without_claim_is_rejected(self):
        with pytest.raises(HTTPException) as excinfo:
            await dependencies.get_hospital_id_header(
                _request(roles=["doctor"]), x_hospital_id=None
            )
        self.assertEqual(excinfo.value.status_code, 400)

    async def test_explicit_header_wins(self):
        explicit = uuid.uuid4()
        hospital_id = await dependencies.get_hospital_id_header(
            _request(roles=["doctor"]), x_hospital_id=str(explicit)
        )
        self.assertEqual(hospital_id, explicit)

    async def test_malformed_header_is_rejected(self):
        with pytest.raises(HTTPException) as excinfo:
            await dependencies.get_hospital_id_header(
                _request(roles=["admin"]), x_hospital_id="not-a-uuid"
            )
        self.assertEqual(excinfo.value.status_code, 400)

class EMRFacilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_unassigned_platform_admin_uses_directory_default(self):
        from src.backend.services.emr.dependencies import get_hospital_id

        self.assertEqual(
            await get_hospital_id(_request(roles=["admin"]), None),
            dependencies.DEFAULT_HOSPITAL_ID,
        )

    async def test_staff_without_assignment_has_no_default_facility(self):
        from src.backend.services.emr.dependencies import get_hospital_id

        self.assertIsNone(await get_hospital_id(_request(roles=["doctor"]), None))

class SelectedFacilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_only_admin_can_override_facility(self):
        db = _db()
        with self.assertRaises(HTTPException) as error:
            await dependencies.get_selected_facility(_request(roles=["doctor"]), uuid.uuid4(), db)
        self.assertEqual(error.exception.status_code, 403)

    async def test_admin_cannot_select_unavailable_facility(self):
        db = _db()
        db.scalar = AsyncMock(return_value=None)
        with self.assertRaises(HTTPException) as error:
            await dependencies.get_selected_facility(_request(roles=["admin"]), uuid.uuid4(), db)
        self.assertEqual(error.exception.status_code, 404)

    async def test_admin_can_select_active_facility(self):
        facility_id = uuid.uuid4()
        db = _db()
        db.scalar = AsyncMock(return_value=facility_id)
        result = await dependencies.get_selected_facility(_request(roles=["admin"]), facility_id, db)
        self.assertEqual(result, facility_id)
