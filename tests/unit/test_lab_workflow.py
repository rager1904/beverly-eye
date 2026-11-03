from src.backend.security.rbac.permissions import PermissionSet


def test_doctor_can_order_but_cannot_process_lab_work() -> None:
    permissions = PermissionSet.from_roles(["doctor"])

    assert permissions.has_permission("lab:order")
    assert not permissions.has_permission("lab:collect")
    assert not permissions.has_permission("lab:result")
    assert not permissions.has_permission("lab:verify")


def test_lab_technician_can_process_and_verify_but_not_order() -> None:
    permissions = PermissionSet.from_roles(["lab_technician"])

    assert not permissions.has_permission("lab:order")
    assert permissions.has_permission("lab:collect")
    assert permissions.has_permission("lab:result")
    assert permissions.has_permission("lab:verify")
