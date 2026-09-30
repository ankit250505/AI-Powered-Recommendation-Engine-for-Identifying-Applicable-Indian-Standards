# AI-Powered Indian Standards Recommendation Engine

This project is starting with a production-shaped Indian Standards seed dataset and a basic keyword search layer.

## Prototype Status

Version 1.0 is feature-complete for demonstration and controlled evaluation. See `docs/PROTOTYPE_ACCEPTANCE.md` for the accepted workflow and the remaining production boundary.

## Dataset

The standards catalog is stored in:

- `data/indian_standards_seed.csv`
- `data/indian_standards_seed.json`
- `data/procurement_query_examples.csv`
- `data/procurement_query_examples.json`

The CSV is the source of truth. The JSON is generated from the CSV.

The standards catalog contains 250 standards. The procurement query dataset contains 3,750 labeled examples for train/validation/test evaluation.

## Basic Search

Run a search from the project root:

```bash
python src/standards_search.py "TMT bars for RCC work" --limit 5
```

Other examples:

```bash
python src/standards_search.py "LED street lights for road project" --limit 5
python src/standards_search.py "drinking water quality testing fluoride nitrate coliform" --limit 5
python src/standards_search.py "IS 1786" --limit 3
```

## Backend API

Create and use the local virtual environment:

```bash
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Start the API:

```bash
.\.venv\Scripts\python.exe -m uvicorn src.api:app --host 127.0.0.1 --port 8000
```

Create users before signing in:

```bash
.\.venv\Scripts\python.exe scripts\create_user.py buyer --role procurement
.\.venv\Scripts\python.exe scripts\create_user.py reviewer --role reviewer
.\.venv\Scripts\python.exe scripts\create_user.py admin --role admin
```

The command securely prompts for a password. Passwords use PBKDF2-SHA256 with individual random salts. Login sessions use random, hashed, eight-hour tokens stored in SQLite and an HTTP-only, SameSite cookie.

Open the prototype UI:

```text
http://127.0.0.1:8000/
```

Open the admin review console:

```text
http://127.0.0.1:8000/admin
```

Open the interactive API docs:

```text
http://127.0.0.1:8000/docs
```

Available endpoints:

- `GET /health`
- `GET /health/live`
- `GET /health/ready`
- `GET /metrics`
- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`
- `POST /recommend`
- `POST /extract-document`
- `POST /recommend-document`
- `POST /feedback`
- `POST /reviews`
- `GET /reviews`
- `GET /review-summary`
- `GET /verification-queue`
- `PUT /admin/standards/{standard_id}/verification`
- `GET /verification-history`
- `GET /search-history`
- `GET /search-history/{search_id}`
- `GET /analytics`
- `GET /dataset-quality`
- `GET /retrieval-quality`
- `GET /demo-document`
- `GET /reports/search/{search_id}.csv`
- `GET /reports/search/{search_id}.pdf`
- `GET /reports/dataset-quality.csv`
- `GET /reports/review-dataset.csv`
- `GET /standards`
- `GET /standards/{standard_id}`

Example request body for `POST /recommend`:

```json
{
  "query": "TMT bars for RCC work",
  "limit": 5,
  "mode": "hybrid"
}
```

## Frontend Prototype

The frontend is a static browser UI served by FastAPI from `frontend/`.

It includes:

- procurement specification text area
- TXT/PDF/DOCX document upload
- extract text action
- extract and recommend action
- sample queries
- result limit selector
- ranked recommendation cards
- matched terms
- useful/not useful feedback buttons
- score, category, verification status, and explanation text
- search mode selector for `hybrid`, `embedding`, or `keyword`
- optional sentence-transformer `embedding` search mode
- heuristic confidence bands for each recommendation
- exact supporting clauses for document-based recommendations
- reviewer accept/reject decisions with optional notes
- searchable standards library with category filtering
- recent-run reopening with the originally saved ranked results
- source references and applicability notes on recommendation cards
- downloadable multi-category demonstration PDF
- result filtering by standard, title, category, and confidence
- side-by-side comparison for up to three catalogue standards
- downloadable presentation-ready PDF reports and CSV data exports

## Search Modes

`keyword` searches these fields:

- `title`
- `keywords`
- `related_terms`
- `procurement_examples`
- `embedding_text`

`hybrid` combines keyword scoring with a lightweight in-memory vector similarity layer built from:

- title
- category and subcategory
- keywords and related terms
- procurement examples
- scope summary
- embedding text

The current vector layer is dependency-light and local. It is structured so a future model-based embedding engine can replace it without changing the API contract.

`embedding` uses `sentence-transformers/all-MiniLM-L6-v2` to encode the standards catalog and query, then blends cosine similarity with the keyword score. The model and the 250 catalog embeddings are loaded once on the first embedding request. Hybrid remains the default because it has the strongest measured Top-1 and MRR on the held-out test split; embedding mode provides the strongest Top-5 recall.

It returns:

- standard code
- title
- score
- category and subcategory
- matched fields
- matched terms
- short explanation
- procurement example

## Document Upload

Supported upload formats:

- `.txt`
- `.pdf`
- `.docx`

Upload limit:

- 10 MB

Document endpoints:

```text
POST /extract-document
POST /recommend-document
```

`/extract-document` returns extracted text and preview. `/recommend-document` extracts text and sends it through the selected search mode.

Document recommendation splits extracted text into distinct clauses, searches each clause, and aggregates repeated standard matches. Results include up to three triggering excerpts and a ranking-confidence score. The confidence value is a retrieval heuristic for review prioritization, not a legal determination of applicability.

PDFs must contain selectable text. When a scanned image-only PDF is detected, the API returns an explicit instruction to run OCR and re-upload the searchable document.

## Persistence and Feedback

Searches and feedback are stored locally in SQLite:

```text
app_data/recommendations.db
```

This file is ignored by git.

Persistence endpoints:

```text
POST /feedback
GET /search-history
GET /analytics
```

The frontend sends feedback for each recommendation card. This creates the foundation for later ranking improvements based on useful/not useful signals.

## Admin Review Console

The admin console is served from:

```text
http://127.0.0.1:8000/admin
```

It shows:

- saved search count
- useful/not useful feedback totals
- standards count
- records needing official verification
- generic BIS source URL count
- recent search history
- feedback hotspots by standard
- top dataset categories
- CSV exports for saved recommendation runs and dataset quality
- held-out Top-1, Top-5, and mean reciprocal rank metrics

## Report Exports

Each completed text or document search receives a persistent `search_id`. The search UI uses that ID to download the exact ranked results shown to the evaluator as a formatted PDF report or CSV data file, including scores, matched terms, explanations, verification status, and source URLs.

The admin console can also export the current dataset-quality summary as CSV for review in spreadsheet tools.

The reviewer workspace includes a Recent Runs view. Reopening a run loads the exact recommendation payload saved at search time so demonstrations and later audits are reproducible.

## Demonstration Document

Authenticated users can download `output/pdf/demo_procurement_specification.pdf` from `/demo-document`. It contains reinforcement-steel, LED street-lighting, drinking-water, and fire-protection clauses so one upload demonstrates multi-clause extraction, ranking, and evidence display.

The complete presentation sequence, speaking points, expected results, and judge questions are in `docs/JUDGE_DEMO_GUIDE.md`.

## Human Review Workflow

Each recommendation card includes an optional reviewer note and Accept/Reject actions. A reviewer can revise a decision; the existing `(search, standard)` label is updated instead of duplicated.

The admin console shows accepted, rejected, and pending totals plus recent decisions. `GET /reports/review-dataset.csv` exports reviewed query-standard pairs with binary relevance labels (`1` accepted, `0` rejected). These are reviewer judgments and do not replace official BIS verification.

## Access Control

The prototype has three roles:

- `procurement`: search standards, upload documents, submit usefulness feedback, and export search results
- `reviewer`: procurement access plus accept/reject decisions, review history, analytics, and labeled-data exports
- `admin`: full access, including the same review and dataset-quality controls

Reviewer identity is saved with every new or updated review decision. Use `scripts/create_user.py` to provision accounts; passwords are never stored directly.

## Standards Verification Workspace

Administrators can filter the standards catalog by verification status or search by code/title in the admin console. A verification update records:

- corrected official title
- official BIS source URL
- verification status and review date
- required audit note
- administrator identity and timestamp

Updates are stored as database overrides so the original seed CSV remains unchanged. Effective metadata is applied immediately to keyword, hybrid, and embedding search indexes after cache invalidation. Every update also creates an append-only verification-history record.

## Deployment

Copy `.env.example` to `.env` and adjust the environment values. For HTTPS deployments, set `SESSION_COOKIE_SECURE=true` and configure `TRUSTED_HOSTS` with the public hostname.

Run with Docker Compose:

```bash
docker compose up --build -d
docker compose ps
```

The container runs as a non-root user, persists SQLite data and the embedding-model cache in named volumes, and includes a readiness-based Docker health check.

Runtime configuration:

- `APP_ENV`: deployment name such as `development`, `staging`, or `production`
- `DATABASE_PATH`: SQLite database location
- `SESSION_HOURS`: login-session lifetime
- `SESSION_COOKIE_SECURE`: require HTTPS for the session cookie
- `LOG_LEVEL`: structured JSON logging level
- `TRUSTED_HOSTS`: comma-separated accepted hostnames
- `EMBEDDING_MODEL`: sentence-transformer model identifier
- `EMBEDDING_LOCAL_ONLY`: disable runtime model downloads after caching
- `LOGIN_ATTEMPT_LIMIT`: failed sign-ins allowed per user/IP window
- `LOGIN_WINDOW_SECONDS`: login throttling window

Health endpoints:

- `/health/live`: confirms the process is running
- `/health/ready`: verifies SQLite integrity, user-table access, and standards loading

Create an online, integrity-checked SQLite backup:

```bash
.\.venv\Scripts\python.exe scripts\backup_database.py --keep 14
```

With Docker Compose:

```bash
docker compose --profile maintenance run --rm backup
```

Application request logs are emitted as one JSON object per line and include request ID, method, path, status, duration, and environment. Every response also includes `X-Request-ID` for tracing.

Release automation is defined in `.github/workflows/ci.yml`. It runs the complete test suite, dependency consistency check, retrieval quality gate, bytecode compilation, and a Docker image build. Use `scripts/smoke_test.py` for authenticated checks after deployment and follow `docs/RELEASE_CHECKLIST.md` for staging acceptance.

## Tests

Run:

```bash
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

## Generate Training Examples

The generated query dataset maps procurement-like text to the target standard:

```bash
python scripts/generate_training_examples.py
```

Current split:

- train: 3,000
- validation: 375
- test: 375

## Evaluate Basic Search

Run:

```bash
.\.venv\Scripts\python.exe scripts\evaluate_basic_search.py --split validation --mode keyword
.\.venv\Scripts\python.exe scripts\evaluate_basic_search.py --split validation --mode hybrid
.\.venv\Scripts\python.exe scripts\evaluate_basic_search.py --split test --mode keyword
.\.venv\Scripts\python.exe scripts\evaluate_basic_search.py --split test --mode hybrid
.\.venv\Scripts\python.exe scripts\evaluate_basic_search.py --split validation --mode embedding
.\.venv\Scripts\python.exe scripts\evaluate_basic_search.py --split test --mode embedding
```

Tune the semantic blend on validation data only:

```bash
.\.venv\Scripts\python.exe scripts\tune_embedding_search.py --split validation
```

Current baseline on the generated dataset:

| Mode | Split | Top-1 | Top-3 | Top-5 | MRR |
| --- | --- | ---: | ---: | ---: | ---: |
| keyword | validation | 0.872 | 0.936 | 0.949 | 0.904 |
| hybrid | validation | 0.880 | 0.947 | 0.955 | 0.913 |
| embedding | validation | 0.915 | 0.947 | 0.952 | 0.933 |
| keyword | test | 0.899 | 0.965 | 0.973 | 0.933 |
| hybrid | test | 0.915 | 0.971 | 0.973 | 0.943 |
| embedding | test | 0.912 | 0.965 | 0.979 | 0.941 |

## Next Engineering Step

Deploy to a staging host behind HTTPS, configure scheduled backups and external uptime alerts, then run acceptance testing with verified BIS records and real procurement documents.
