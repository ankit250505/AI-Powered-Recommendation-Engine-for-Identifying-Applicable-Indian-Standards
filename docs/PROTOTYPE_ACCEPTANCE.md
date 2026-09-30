# Prototype Acceptance

## User Workflow

- Sign in with procurement, reviewer, and administrator roles.
- Search a typed procurement requirement in keyword, hybrid, or embedding mode.
- Upload TXT, PDF, and DOCX documents up to 10 MB.
- Extract document text and receive clause-level standard recommendations.
- Inspect confidence, explanation, matched terms, applicability note, evidence, verification status, and source reference.
- Filter recommendations by text and confidence.
- Download the saved recommendation run as a formatted PDF or CSV.
- Browse and filter the 250-record standards library.
- Compare up to three catalogue standards side by side.
- Reopen a recent run with its originally saved results.

## Review Workflow

- Record useful or not-useful feedback.
- Accept or reject a recommendation with a reviewer note.
- Export reviewer decisions as labeled CSV data.
- Correct standard metadata through administrator-only overrides.
- Preserve verification changes in append-only audit history.

## Quality And Operations

- Run 35 automated tests.
- Enforce Top-1, Top-5, and mean reciprocal rank release thresholds.
- Keep displayed retrieval metrics synchronized with the quality gate.
- Provide structured logs, request IDs, security headers, login throttling, and role checks.
- Provide liveness, readiness, and Prometheus-compatible metrics endpoints.
- Create integrity-checked SQLite backups.
- Package the service with Docker and a non-root runtime user.
- Provide a CI pipeline, smoke test, demo procurement PDF, and release checklist.
- Provide a repeatable judge demo script and presentation checklist.

## Prototype Boundary

The software prototype is feature-complete. Production use still requires authoritative BIS verification of every catalogue record, real tender evaluation with procurement specialists, deployment behind HTTPS, unique production credentials, scheduled off-host backups, and operational monitoring.
