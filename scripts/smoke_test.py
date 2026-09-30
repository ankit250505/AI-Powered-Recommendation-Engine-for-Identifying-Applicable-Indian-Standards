from __future__ import annotations

import argparse
import getpass
import os

import httpx


def require_ok(response: httpx.Response, label: str) -> dict:
    if response.status_code >= 400:
        raise RuntimeError(f"{label} failed with {response.status_code}: {response.text[:300]}")
    return response.json()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run authenticated post-deployment smoke checks.")
    parser.add_argument("--url", default=os.getenv("DEPLOY_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--username", default=os.getenv("DEPLOY_USERNAME"))
    parser.add_argument("--password", default=os.getenv("DEPLOY_PASSWORD"))
    args = parser.parse_args()

    username = args.username or input("Username: ").strip()
    password = args.password or getpass.getpass("Password: ")
    with httpx.Client(base_url=args.url.rstrip("/"), timeout=30) as client:
        live = require_ok(client.get("/health/live"), "Liveness")
        ready = require_ok(client.get("/health/ready"), "Readiness")
        user = require_ok(
            client.post("/auth/login", json={"username": username, "password": password}),
            "Login",
        )
        recommendation = require_ok(
            client.post(
                "/recommend",
                json={"query": "TMT bars for RCC work", "limit": 3, "mode": "hybrid"},
            ),
            "Recommendation",
        )
        if recommendation["results"][0]["standard_code"] != "IS 1786:2008":
            raise RuntimeError("Recommendation smoke check returned an unexpected top result.")
        if user["role"] == "admin":
            require_ok(client.get("/verification-queue", params={"limit": 1}), "Admin queue")

    print(
        f"Smoke test passed: {live['status']}, {ready['status']}, "
        f"role={user['role']}, top={recommendation['results'][0]['standard_code']}"
    )


if __name__ == "__main__":
    main()
