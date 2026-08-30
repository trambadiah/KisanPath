"""Environment-backed admin authentication and explicit role checks."""

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Mapping
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class AdminRole(StrEnum):
    AUDITOR = "auditor"
    REVIEWER = "reviewer"
    PUBLISHER = "publisher"
    OPERATOR = "operator"


class AdminAction(StrEnum):
    VIEW_AUDIT = "view_audit"
    REVIEW_CORPUS = "review_corpus"
    PUBLISH_CORPUS = "publish_corpus"
    RETIRE_PUBLICATION = "retire_publication"
    OPERATE_RUNTIME = "operate_runtime"


_ACTION_ROLES: dict[AdminAction, frozenset[AdminRole]] = {
    AdminAction.VIEW_AUDIT: frozenset({AdminRole.AUDITOR}),
    AdminAction.REVIEW_CORPUS: frozenset({AdminRole.REVIEWER}),
    AdminAction.PUBLISH_CORPUS: frozenset({AdminRole.PUBLISHER}),
    AdminAction.RETIRE_PUBLICATION: frozenset({AdminRole.PUBLISHER}),
    AdminAction.OPERATE_RUNTIME: frozenset({AdminRole.OPERATOR}),
}


class AdminPrincipal(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    subject: str = Field(min_length=1, max_length=200)
    roles: frozenset[AdminRole] = Field(min_length=1)


class AdminAuthenticationError(Exception):
    pass


class AdminAuthorizationError(Exception):
    pass


class AdminAuthenticator:
    """Validates opaque bearer tokens supplied only through runtime environment."""

    def __init__(self, token_hashes: Mapping[str, AdminPrincipal]) -> None:
        self._token_hashes = dict(token_hashes)

    @classmethod
    def from_json(cls, raw: str | None) -> AdminAuthenticator:
        if not raw:
            return cls({})
        try:
            entries = json.loads(raw)
            if not isinstance(entries, list):
                raise ValueError("admin token configuration must be a list")
            hashes: dict[str, AdminPrincipal] = {}
            for entry in entries:
                token = entry.pop("token", None) if isinstance(entry, dict) else None
                if not isinstance(token, str) or len(token) < 24:
                    raise ValueError("admin tokens must contain at least 24 characters")
                principal = AdminPrincipal.model_validate(entry)
                hashes[cls._digest(token)] = principal
            return cls(hashes)
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            raise ValueError("invalid KISANPATH_ADMIN_TOKENS_JSON") from exc

    @staticmethod
    def _digest(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def authenticate(self, authorization: str | None) -> AdminPrincipal:
        if not authorization or not authorization.startswith("Bearer "):
            raise AdminAuthenticationError("admin bearer token required")
        digest = self._digest(authorization[7:])
        for expected, principal in self._token_hashes.items():
            if hmac.compare_digest(digest, expected):
                return principal
        raise AdminAuthenticationError("invalid admin bearer token")

    @staticmethod
    def authorize(principal: AdminPrincipal, required: frozenset[AdminRole]) -> None:
        if not required.issubset(principal.roles):
            raise AdminAuthorizationError("admin role is not authorized for this operation")

    @staticmethod
    def authorize_any(principal: AdminPrincipal, allowed: frozenset[AdminRole]) -> None:
        if principal.roles.isdisjoint(allowed):
            raise AdminAuthorizationError("admin role is not authorized for this operation")

    @staticmethod
    def authorize_action(principal: AdminPrincipal, action: AdminAction) -> None:
        AdminAuthenticator.authorize_any(principal, _ACTION_ROLES[action])
