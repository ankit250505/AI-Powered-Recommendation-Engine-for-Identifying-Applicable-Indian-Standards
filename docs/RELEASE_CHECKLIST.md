# Release Checklist

## Before Deployment

- Run `python -m unittest discover -s tests`.
- Run `python scripts/check_quality_gate.py --split test --mode hybrid`.
- Run `python -m pip check`.
- Create and verify a database backup.
- Set `APP_ENV=production`.
- Set `SESSION_COOKIE_SECURE=true` when HTTPS is active.
- Restrict `TRUSTED_HOSTS` to the deployment hostnames.
- Use unique passwords for provisioned accounts.
- Cache the embedding model, then set `EMBEDDING_LOCAL_ONLY=true` if outbound access is disabled.

## Deployment

- Terminate TLS at the platform load balancer or reverse proxy.
- Mount persistent volumes for `/app/app_data`, `/app/backups`, and `/app/model_cache`.
- Confirm `/health/live` and `/health/ready` return HTTP 200.
- Configure uptime monitoring against `/health/ready`.
- Scrape `/metrics` when Prometheus-compatible monitoring is available.
- Schedule `scripts/backup_database.py` and copy backups to separate storage.

## Acceptance

- Run `scripts/smoke_test.py` against the deployed URL.
- Sign in with each role and confirm permission boundaries.
- Upload TXT, PDF, and DOCX procurement samples.
- Confirm recommendation, review, verification, and CSV export workflows.
- Confirm logs contain request IDs and do not contain passwords or session tokens.
- Restore a backup in an isolated environment and run `/health/ready`.

## Release Decision

- Record the deployed version and commit.
- Record retrieval quality-gate metrics.
- Record backup and restore evidence.
- Record remaining unverified BIS catalog entries.
- Obtain procurement-domain reviewer approval before production use.
