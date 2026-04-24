from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, HTTPException, status

from app.core.config import settings


@dataclass(frozen=True, slots=True)
class AdminPrincipal:
    email: str


def require_admin(
    x_admin_email: str | None = Header(default=None),
    x_admin_token: str | None = Header(default=None),
) -> AdminPrincipal:
    if not x_admin_email or not x_admin_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing admin credentials",
        )

    if x_admin_token != settings.admin_api_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin token",
        )

    allowed = {email.lower() for email in settings.admin_allowed_emails}
    if allowed and x_admin_email.lower() not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin email not authorized",
        )

    return AdminPrincipal(email=x_admin_email)
