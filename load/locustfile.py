"""Non-claiming smoke/load scaffold for the deployed HTTP safety shell."""

from __future__ import annotations

import os

from locust import HttpUser, between, task


class KisanPathRuntimeUser(HttpUser):
    wait_time = between(0.2, 1.0)

    @task(9)
    def liveness(self) -> None:
        self.client.get("/v1/health", name="GET /v1/health")

    @task(1)
    def readiness(self) -> None:
        self.client.get("/v1/readiness", name="GET /v1/readiness")

    def on_start(self) -> None:
        self.admin_token = os.environ.get("KISANPATH_LOAD_ADMIN_TOKEN")

    @task(1)
    def protected_admin_boundary(self) -> None:
        if not self.admin_token:
            return
        self.client.get(
            "/v1/admin/status",
            name="GET /v1/admin/status",
            headers={"Authorization": f"Bearer {self.admin_token}"},
        )
