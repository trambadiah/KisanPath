from __future__ import annotations

import json

import pytest

from kisanpath.security.auth import (
    AdminAction,
    AdminAuthenticationError,
    AdminAuthenticator,
    AdminAuthorizationError,
    AdminRole,
)


def authenticator() -> AdminAuthenticator:
    return AdminAuthenticator.from_json(
        json.dumps(
            [
                {
                    "token": "synthetic-admin-token-000001",
                    "subject": "synthetic-reviewer",
                    "roles": ["reviewer", "auditor"],
                }
            ]
        )
    )


def test_authentication_and_role_boundaries_fail_closed() -> None:
    auth = authenticator()
    principal = auth.authenticate("Bearer synthetic-admin-token-000001")

    auth.authorize(principal, frozenset({AdminRole.REVIEWER}))
    with pytest.raises(AdminAuthorizationError):
        auth.authorize(principal, frozenset({AdminRole.PUBLISHER}))
    auth.authorize_action(principal, AdminAction.REVIEW_CORPUS)
    with pytest.raises(AdminAuthorizationError):
        auth.authorize_action(principal, AdminAction.PUBLISH_CORPUS)
    with pytest.raises(AdminAuthenticationError):
        auth.authenticate("Bearer invalid-synthetic-token-000")
    with pytest.raises(AdminAuthenticationError):
        AdminAuthenticator.from_json(None).authenticate(None)
