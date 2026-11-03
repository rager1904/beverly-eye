from __future__ import annotations

import functools
import inspect
import logging
from typing import Any, Callable, Optional, TypeVar

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.backend.security.audit.logger import audit_logger
from src.backend.security.rbac.middleware import verify_hospital_access, verify_permission
from src.backend.security.rbac.permissions import PermissionSet

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

security_scheme = HTTPBearer(auto_error=False)


def require_permission(permission: str):
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            request = _find_request(kwargs)
            if request is None:
                logger.warning("No Request found in kwargs for %s", func.__name__)
                return await func(*args, **kwargs)
            if not await verify_permission(request, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required permission: {permission}",
                )
            return await func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator


def require_role(role: str):
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            request = _find_request(kwargs)
            if request is None:
                return await func(*args, **kwargs)
            roles: list[str] = getattr(request.state, "roles", [])
            if role not in roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Required role: {role}",
                )
            return await func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator


def require_hospital_access():
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            request = _find_request(kwargs)
            if request is None:
                return await func(*args, **kwargs)
            target_hospital_id = kwargs.get("hospital_id")
            if target_hospital_id is None:
                target_hospital_id = request.path_params.get("hospital_id")
            if target_hospital_id and not await verify_hospital_access(request, target_hospital_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: hospital ID mismatch",
                )
            return await func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator


def audit_log(action: str, resource_type: str | None = None):
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            request = _find_request(kwargs)
            if request is None:
                return await func(*args, **kwargs)
            result = await func(*args, **kwargs)
            try:
                user_id = getattr(request.state, "user_id", "unknown")
                username = getattr(request.state, "username", "unknown")
                resource = resource_type or func.__name__
                detail = {
                    "function": func.__name__,
                    "args": str(_sanitize_args(kwargs)),
                }
                await audit_logger.log(
                    actor=username,
                    actor_id=user_id,
                    action=action,
                    resource=resource,
                    detail=detail,
                    ip=request.client.host if request.client else "",
                    user_agent=request.headers.get("user-agent", ""),
                )
            except Exception as e:
                logger.warning("Audit log failed: %s", e)
            return result

        return wrapper  # type: ignore

    return decorator


def _find_request(kwargs: dict) -> Optional[Request]:
    for val in kwargs.values():
        if isinstance(val, Request):
            return val
    return None


def _sanitize_args(kwargs: dict) -> dict:
    sensitive_keys = {"password", "token", "secret", "authorization", "api_key"}
    return {k: ("***" if k.lower() in sensitive_keys else v) for k, v in kwargs.items()}


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> dict:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        from src.backend.security.keycloak.client import keycloak_client
        from src.backend.core.config.settings import settings
        if settings.JWT_PUBLIC_KEY:
            return keycloak_client.decode_token(credentials.credentials)
        return await keycloak_client.validate_token(credentials.credentials)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


async def get_permission_set(
    current_user: dict = Depends(get_current_user),
) -> PermissionSet:
    return PermissionSet.from_token_claims(current_user)
