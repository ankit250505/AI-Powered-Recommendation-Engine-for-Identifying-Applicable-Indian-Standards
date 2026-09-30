# Project Context

Last reviewed: 2026-09-30

## 1. Project Summary

This repository contains a working prototype of an **AI-Powered Recommendation Engine for Identifying Applicable Indian Standards for Procurement Specifications**.

The application accepts a typed procurement requirement or an uploaded TXT, PDF, or DOCX specification and returns ranked Indian Standard recommendations. Each recommendation includes an explanation, matched terminology, confidence, verification status, source link, applicability guidance, and, for documents, the clauses that triggered the match.

The system is intentionally a **decision-support and human-review tool**. It does not claim to make a legally binding determination of which standard is mandatory.

Current product status: **feature-complete prototype suitable for demonstration and controlled evaluation**. The next priority is official data validation, testing against real tender documents, and presentation preparation rather than adding more software features.

## 2. Current Verified Status

- API version: `1.0.0`
- Standards catalogue: 250 records
- Labeled query examples: 3,750
- Query splits: 3,000 train, 375 validation, 375 test
- Automated tests: 35 passing
- Hybrid held-out test metrics:
  - Top-1 accuracy: 0.915
  - Top-5 accuracy: 0.973
  - Mean reciprocal rank: 0.943
- Quality gate: passing
- Python dependency check: passing
- Frontend JavaScript syntax checks: passing
- Local readiness endpoint: healthy at the time of this review
- Docker files and CI workflow: implemented
- Local Docker image build: not verified because Docker is not installed on the current machine

The recorded metrics come from a controlled synthetic held-out dataset. They are useful regression and prototype-quality measurements, but they are not evidence of 91.5% accuracy across all real Indian tenders.

## 3. High-Level Architecture

```text
Browser UI
  |-- Login page
  |-- Procurement workspace
  |-- Standards library and comparison
  |-- Reviewer/admin console
  |
  v
FastAPI application (`src/api.py`)
  |-- Authentication and role checks
  |-- Search orchestration
  |-- Document upload/extraction
  |-- Review, feedback, and verification APIs
  |-- Reports, analytics, health, and metrics
  |
  +--> Retrieval layer
  |      |-- Weighted keyword search
  |      |-- Lightweight local hybrid similarity
  |      `-- Optional sentence-transformer embeddings
  |
  +--> Document layer
  |      |-- TXT/PDF/DOCX extraction
  |      |-- Clause splitting
  |      `-- Cross-clause result aggregation and evidence
  |
  +--> Data files
  |      |-- 250-record standards seed CSV
  |      |-- JSON export
  |      `-- 3,750 labeled query examples
  |
  `--> SQLite persistence
         |-- users and sessions
         |-- saved searches and result snapshots
         |-- usefulness feedback
         |-- reviewer decisions
         |-- standard metadata overrides
         `-- verification audit history
```

The frontend is plain HTML, CSS, and JavaScript served by FastAPI. There is no separate Node build process or frontend framework.

## 4. Main Request Flows

### Text Recommendation

1. An authenticated user enters procurement text and chooses `keyword`, `hybrid`, or `embedding` mode.
2. `POST /recommend` validates the request.
3. The selected retrieval engine ranks standards.
4. The API computes heuristic confidence labels and explanation fields.
5. The exact recommendation payload is saved in SQLite.
6. The UI displays results and enables PDF/CSV export using the saved `search_id`.

### Document Recommendation

1. An authenticated user uploads a TXT, PDF, or DOCX file of at most 10 MB.
2. `src/document_processing.py` extracts and normalizes selectable text.
3. `src/document_analysis.py` splits the text into up to 80 clauses, with a maximum of 600 characters per clause.
4. Each clause is searched separately.
5. Matches are aggregated by standard, with repeated support improving rank.
6. Up to three strongest source clauses are attached as evidence.
7. The exact document result snapshot is stored and can be reopened or exported.

Image-only PDFs are detected when no selectable text is found. The user is instructed to run OCR and upload a searchable PDF; native OCR is not bundled.

### Human Review and Verification

1. Any authenticated role can mark a recommendation useful or not useful.
2. Reviewers and administrators can accept or reject a saved recommendation and add a note.
3. Administrators can correct standard title, source URL, verification status, and review notes.
4. Standard corrections are stored as database overrides, leaving the seed CSV unchanged.
5. Every verification update creates an append-only audit-history record and clears retrieval caches.

## 5. Retrieval Implementation

### Keyword Mode

Implemented in `src/standards_search.py`.

Searches the following fields:

- `title`
- `keywords`
- `related_terms`
- `procurement_examples`
- `embedding_text`

The fields have different weights. Exact normalized phrases and direct standard-code matches receive additional score. Results expose matched terms and fields.

### Hybrid Mode

Implemented in `src/hybrid_search.py` and used as the default mode.

It combines weighted keyword scoring with a dependency-light local similarity vector built from tokens, bigrams, character features, and a small procurement synonym map. It does **not** use the sentence-transformer model. This mode is fast, deterministic, local, and currently has the strongest measured Top-1 and MRR on the held-out test split.

### Embedding Mode

Implemented in `src/embedding_search.py`.

It uses `sentence-transformers/all-MiniLM-L6-v2`, normalizes catalogue and query embeddings, calculates cosine similarity, and blends semantic and keyword scores. The model and catalogue embeddings are cached in memory after first use. The model must already be cached when `EMBEDDING_LOCAL_ONLY=true`; otherwise the first use may require network access.

### Confidence

Confidence is a heuristic based on relative retrieval score, matched-term count, document evidence count, and rank. Labels are `high`, `moderate`, or `low`. Confidence is for review prioritization and is not a probability of legal applicability.

## 6. Dataset

### Standards Catalogue

Source of truth: `data/indian_standards_seed.csv`

JSON export: `data/indian_standards_seed.json`

The catalogue has 250 rows and 14 columns:

- `id`
- `standard_code`
- `title`
- `category`
- `subcategory`
- `keywords`
- `scope_summary`
- `related_terms`
- `procurement_examples`
- `mandatory_hint`
- `source_url`
- `verify_status`
- `last_reviewed`
- `embedding_text`

Current seed-file verification distribution:

- `needs_official_verification`: 221
- `partially_verified`: 26
- `verified_from_search`: 3
- `officially_verified`: 0 in the seed CSV

The running application can contain additional verified metadata through SQLite overrides. At the time of review, the local database had one standard override and one verification-history record.

### Labeled Query Dataset

Files:

- `data/procurement_query_examples.csv`
- `data/procurement_query_examples.json`

Columns:

- `example_id`
- `query_text`
- `query_type`
- `target_standard_id`
- `target_standard_code`
- `target_title`
- `category`
- `subcategory`
- `split`

These 3,750 examples are synthetic-but-controlled procurement phrases. They support retrieval evaluation, ranking experiments, and regression testing. They must not be presented as 3,750 genuine government tenders or as proof that a supervised model was trained.

## 7. Database

Default database: `app_data/recommendations.db`

The path is configurable with `DATABASE_PATH`. The database is ignored by Git and initialized automatically.

### Tables

| Table | Purpose |
| --- | --- |
| `users` | Username, PBKDF2 password hash/salt, role, active flag |
| `sessions` | Hashed session tokens and expiration times |
| `searches` | Query/document metadata and immutable JSON result snapshot |
| `feedback` | Useful/not-useful recommendation signals |
| `reviews` | Reviewer accept/reject label, note, and reviewer identity |
| `standard_overrides` | Effective corrections to seed standard metadata |
| `verification_history` | Append-only before/after verification audit records |

Reviewer decisions are unique by `(search_id, standard_id)` and are updated rather than duplicated.

### Current Local Runtime Data

This data is volatile and not part of the source repository. At the time of review:

- Users: 3
- Saved searches: 57
- Feedback records: 9
- Review records: 3
- Standard overrides: 1
- Verification-history records: 1

No credentials are stored in this document.

## 8. Authentication and Roles

Passwords use PBKDF2-SHA256 with individual random salts and 600,000 iterations. Sessions use random tokens; only token hashes are stored. The browser receives an HTTP-only, SameSite `strict` cookie. Secure cookies are enabled by configuration for HTTPS deployment.

Roles:

| Role | Access |
| --- | --- |
| `procurement` | Search, document upload, feedback, catalogue, result reports |
| `reviewer` | Procurement access plus reviews, history, analytics, quality views, review export |
| `admin` | Full access plus verification queue, metadata overrides, and audit history |

Failed login attempts are throttled in memory by client IP and normalized username.

## 9. API Surface

### Public Operational Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Basic application and catalogue status |
| GET | `/health/live` | Process liveness |
| GET | `/health/ready` | SQLite integrity, user-table access, and catalogue readiness |
| GET | `/metrics` | Prometheus-compatible process/request counters |
| GET | `/login` | Login page |
| POST | `/auth/login` | Authenticate and create session cookie |
| POST | `/auth/logout` | Delete session |

### Authenticated Procurement Endpoints

Available to `procurement`, `reviewer`, and `admin` unless noted:

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/auth/me` | Current user |
| GET | `/` | Main workspace |
| GET | `/demo-document` | Download demonstration PDF |
| POST | `/recommend` | Text recommendation |
| POST | `/extract-document` | Extract TXT/PDF/DOCX text |
| POST | `/recommend-document` | Extract, split, rank, and store document recommendations |
| POST | `/feedback` | Save useful/not-useful signal |
| GET | `/standards` | List/filter catalogue records |
| GET | `/standards/{standard_id}` | Retrieve one catalogue record |
| GET | `/reports/search/{search_id}.csv` | Export a saved recommendation run |
| GET | `/reports/search/{search_id}.pdf` | Export a formatted recommendation report |

### Reviewer and Administrator Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/admin` | Review and operations console |
| POST | `/reviews` | Accept/reject a saved recommendation |
| GET | `/reviews` | Recent review decisions |
| GET | `/review-summary` | Accepted/rejected/pending counts |
| GET | `/search-history` | Recent saved runs |
| GET | `/search-history/{search_id}` | Exact stored result snapshot |
| GET | `/analytics` | Search and feedback totals |
| GET | `/dataset-quality` | Coverage and verification metrics |
| GET | `/retrieval-quality` | Recorded held-out retrieval metrics |
| GET | `/reports/dataset-quality.csv` | Dataset-quality export |
| GET | `/reports/review-dataset.csv` | Binary relevance-label export |

### Administrator-Only Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/verification-queue` | Filter standards by verification status or text |
| PUT | `/admin/standards/{standard_id}/verification` | Save verified metadata override |
| GET | `/verification-history` | Verification audit trail |

Interactive OpenAPI documentation is available at `/docs` while the service is running.

## 10. Frontend Features

### Login

- Username/password login
- Session-based redirects
- Friendly validation and error states

### Procurement Workspace

- Typed procurement requirement
- Search mode and result-count controls
- Sample queries
- TXT/PDF/DOCX upload
- Extract-only and extract-and-recommend actions
- Ranked recommendation cards
- Score, confidence, category, verification status, and applicability note
- Explanation, matched terms, and document evidence clauses
- Official/source reference links
- Useful/not-useful feedback
- Reviewer notes and accept/reject controls for authorized roles
- Text and confidence result filters
- PDF recommendation report and CSV export

### Standards Library

- Loads all 250 standards through the API
- Searches code, title, and keywords
- Filters by category
- Displays source and verification status
- Compares up to three standards side by side

### Recent Runs

- Reviewer/admin view
- Reopens the exact recommendation payload saved at search time
- Preserves demonstration and audit reproducibility

### Admin Console

- Search and feedback metrics
- Review-decision metrics and recent decisions
- Dataset coverage and quality metrics
- Held-out retrieval quality panel
- Recent saved searches and report links
- Feedback hotspots
- Verification queue with status/text filters
- Verification edit dialog
- Verification audit history
- Dataset-quality and reviewed-label CSV exports

## 11. Reports and Demonstration Assets

- `src/report_generation.py` builds multi-page PDF recommendation reports with query metadata, rank, score, confidence, explanation, applicability, verification status, matched terms, source URL, evidence, and disclaimer.
- CSV search reports preserve all saved result fields for spreadsheet use.
- `output/pdf/demo_procurement_specification.pdf` includes reinforcement-steel, LED street-lighting, drinking-water, and fire-protection requirements.
- `docs/JUDGE_DEMO_GUIDE.md` contains a seven-minute demonstration sequence, USP, expected results, limitations, and judge questions.

## 12. Security and Operations

Implemented controls:

- Role-based endpoint authorization
- PBKDF2 password hashing
- Hashed session-token storage
- HTTP-only, SameSite strict cookies
- Configurable secure-cookie flag
- Login throttling
- Trusted-host middleware
- Request IDs
- Structured JSON logs
- Content Security Policy
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- restrictive referrer and browser-permission policies
- SQLite integrity checks
- liveness, readiness, and Prometheus-compatible metrics
- non-root Docker runtime
- integrity-checked SQLite backup script with retention

Runtime settings are read from environment variables documented in `.env.example`:

- `APP_ENV`
- `APP_PORT`
- `DATABASE_PATH`
- `SESSION_HOURS`
- `SESSION_COOKIE_SECURE`
- `LOG_LEVEL`
- `TRUSTED_HOSTS`
- `EMBEDDING_MODEL`
- `EMBEDDING_LOCAL_ONLY`
- `LOGIN_ATTEMPT_LIMIT`
- `LOGIN_WINDOW_SECONDS`

## 13. Testing and Quality

Test modules:

- `tests/test_standards_search.py`: keyword/hybrid retrieval and embedding-text construction
- `tests/test_document_analysis.py`: clause splitting and evidence aggregation
- `tests/test_api_contract.py`: authentication, permissions, search, document upload, persistence, reports, quality endpoints, verification, and scanned-PDF behavior
- `tests/test_deployment.py`: settings, login throttling, metrics, backup integrity, and retention

Release checks:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe scripts\check_quality_gate.py --split test --mode hybrid
.\.venv\Scripts\python.exe -m pip check
node --check frontend/app.js
node --check frontend/admin.js
node --check frontend/login.js
```

The quality gate requires at least 0.90 Top-1, 0.96 Top-5, and 0.93 MRR. It also fails if `data/retrieval_quality.json` is stale relative to the current evaluation.

CI in `.github/workflows/ci.yml` installs dependencies, runs tests, checks dependencies, runs the quality gate, compiles Python files, and builds the Docker image.

## 14. Important Files

| Path | Responsibility |
| --- | --- |
| `README.md` | Main setup, feature, deployment, and evaluation documentation |
| `src/api.py` | FastAPI app, schemas, authorization, routes, orchestration |
| `src/standards_search.py` | Weighted keyword retrieval and CLI search |
| `src/hybrid_search.py` | Local feature-vector hybrid retrieval |
| `src/embedding_search.py` | Sentence-transformer retrieval |
| `src/document_processing.py` | TXT/PDF/DOCX extraction and validation |
| `src/document_analysis.py` | Clause splitting and result aggregation |
| `src/storage.py` | SQLite schema and persistence operations |
| `src/auth.py` | Password hashing and session lifecycle |
| `src/report_generation.py` | Formatted recommendation PDF generation |
| `src/config.py` | Environment-based settings |
| `src/security.py` | Login rate limiter |
| `src/logging_config.py` | JSON logging |
| `src/monitoring.py` | In-process Prometheus counters |
| `frontend/index.html` | Procurement workspace structure |
| `frontend/app.js` | Search, upload, filtering, comparison, history, feedback/review UI |
| `frontend/admin.html` | Admin/reviewer console structure |
| `frontend/admin.js` | Admin metrics and verification workflow |
| `frontend/styles.css` | Shared responsive visual system |
| `data/indian_standards_seed.csv` | Standards source-of-truth seed file |
| `data/procurement_query_examples.csv` | Labeled retrieval examples |
| `data/retrieval_quality.json` | Published held-out quality metrics |
| `scripts/check_quality_gate.py` | Release thresholds and metric synchronization |
| `scripts/evaluate_basic_search.py` | Retrieval evaluation |
| `scripts/generate_training_examples.py` | Synthetic query generation |
| `scripts/backup_database.py` | Online SQLite backup and retention |
| `scripts/create_user.py` | Role-based account provisioning |
| `scripts/smoke_test.py` | Authenticated post-deployment smoke test |
| `Dockerfile` | Production-shaped non-root image |
| `compose.yaml` | App, volumes, and maintenance backup service |
| `.github/workflows/ci.yml` | Test and container CI |
| `docs/PROTOTYPE_ACCEPTANCE.md` | Accepted prototype scope and boundary |
| `docs/RELEASE_CHECKLIST.md` | Deployment and release checks |
| `docs/JUDGE_DEMO_GUIDE.md` | Presentation and live-demo guide |

## 15. Running the Project

Install and start locally:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\create_user.py admin --role admin
.\.venv\Scripts\python.exe -m uvicorn src.api:app --host 127.0.0.1 --port 8000
```

URLs:

- Main application: `http://127.0.0.1:8000/`
- Admin/reviewer console: `http://127.0.0.1:8000/admin`
- API documentation: `http://127.0.0.1:8000/docs`

Docker deployment:

```powershell
docker compose up --build -d
docker compose ps
```

Create a verified database backup:

```powershell
.\.venv\Scripts\python.exe scripts\backup_database.py --keep 14
```

## 16. Pending Work

### Important Before SIH Presentation

These are evidence and validation tasks, not missing prototype features:

1. Manually verify 20-30 high-priority standards against official BIS sources and store exact source URLs and audit notes through the admin workspace.
2. Evaluate 10-20 genuine or independently written procurement specifications. Record the expected standard, Top-1 result, Top-5 list, hit/miss, and reviewer comments.
3. Create a dataset-transparency slide that distinguishes the seed catalogue, synthetic query examples, held-out metrics, manually verified subset, and legal limitations.
4. Prepare offline demonstration assets: PPT and PDF, screenshots, exported recommendation report, demo input document, short MP4 demonstration, and setup instructions.
5. Rehearse a fixed text-query and multi-clause PDF flow using `docs/JUDGE_DEMO_GUIDE.md`.

### Required Before Real Production Use

1. Verify the full catalogue against current authoritative BIS records, amendments, withdrawal/revision status, and exact standard pages.
2. Confirm mandatory certification status from current Quality Control Orders and applicable regulations; do not infer it from retrieval score.
3. Obtain permission/licensing for any authoritative standard text or metadata that will be stored or redistributed.
4. Evaluate with real tender documents and procurement/domain specialists; report results separately from the synthetic benchmark.
5. Deploy behind HTTPS with unique credentials and `SESSION_COOKIE_SECURE=true`.
6. Schedule backups, copy them off-host, and verify restoration.
7. Add external uptime/log/metrics monitoring and an incident process.
8. Cache and version the embedding model if embedding mode is part of the deployed service.
9. Establish dataset and model versioning so past recommendations remain reproducible after catalogue updates.

### Optional Future Enhancements

- Native OCR service for image-only PDFs
- Authoritative BIS data connector or controlled import pipeline
- Supervised reranker trained from sufficiently large, expert-reviewed labels
- Multilingual procurement input
- Organization-specific SSO and tenant isolation
- PostgreSQL/object storage for larger deployments
- Background job processing for large tender packages
- Richer model monitoring, drift analysis, and reviewer-agreement metrics

None of these optional items is required to demonstrate the present prototype.

## 17. Known Limitations and Honest Claims

- Most catalogue records are not yet officially verified.
- Many source links are starting points rather than exact standard detail pages.
- The 3,750 examples are synthetic and controlled, not genuine tenders.
- The prototype metrics measure retrieval on that synthetic held-out set.
- Hybrid mode is a lightweight local similarity engine; only embedding mode uses a pretrained transformer.
- Confidence is heuristic and does not express legal certainty.
- Native OCR is not included.
- Search indexes and application metrics are in-process and suited to the current prototype scale.
- SQLite is appropriate for the local prototype but requires careful volume, backup, and concurrency planning in deployment.
- Docker packaging exists but has not been built on the current workstation.
- The system recommends candidates for human review; it does not replace BIS, legal, engineering, or procurement authority.

## 18. Current Project Position

The application already demonstrates the complete intended prototype journey:

```text
procurement language or document
  -> extraction and clause analysis
  -> ranked and explainable standards
  -> source and verification context
  -> human feedback/review
  -> persistent audit record
  -> reproducible PDF/CSV report
```

The core USP is the combination of procurement-specific retrieval, clause-level evidence, transparent verification state, human review, and reproducible audit/reporting workflows. The project should now be treated as **code-frozen except for genuine defects** while validation, PPT preparation, video recording, and presentation rehearsal proceed.
