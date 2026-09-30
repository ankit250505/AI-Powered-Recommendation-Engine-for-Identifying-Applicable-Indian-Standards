# Judge Demo Guide

## One-Line Pitch

Indian Standards Finder converts ordinary procurement specifications into ranked, explainable Indian Standard recommendations, while keeping a human reviewer in control.

## What Problem It Solves

Procurement officers may describe a product by material, grade, application, or performance requirement rather than by a standard number. Manually searching a large standards catalogue is slow and can miss relevant terminology. This prototype searches the requirement, ranks likely standards, shows why each result matched, and records the decision trail.

## Seven-Minute Demonstration

### 1. Introduce the Workspace (30 seconds)

Open `http://127.0.0.1:8000/` and sign in. Point out the text search, document upload, standards library, recent runs, and API health status.

Say: "This is a decision-support system, not an automatic legal ruling. It shortlists likely standards and exposes the evidence for a technical reviewer."

### 2. Run a Text Search (60 seconds)

Choose the sample query **TMT bars for RCC work** and keep **Hybrid** mode selected. Click **Recommend Standards**.

Show:

- the ranked standard code and title;
- retrieval score and confidence;
- plain-language match reason and matched terms;
- verification status, applicability note, and source reference;
- result filtering by text or confidence.

Expected leading result: `IS 1786:2008`.

### 3. Upload a Procurement Document (90 seconds)

Download **Demo PDF**, select it in Document Upload, and click **Extract & Recommend**.

The sample contains reinforcement steel, LED street lighting, drinking-water testing, and fire-protection clauses. Explain that the engine splits the document into clauses, searches each clause, combines repeated matches, and shows the exact clause that triggered each recommendation.

### 4. Export the Evidence (45 seconds)

Click **PDF Report** to download a presentation-ready recommendation report. Mention that **CSV Data** provides the same saved run for spreadsheet analysis or system integration. Both exports use the persistent search ID, so the displayed and downloaded rankings are reproducible.

### 5. Compare Catalogue Records (60 seconds)

Open **Standards Library**, search or filter the 250-record catalogue, select two or three records with **Compare**, and open the comparison. Show code, scope, category, applicability, verification, and source side by side.

### 6. Show Human Review and Governance (60 seconds)

With a reviewer or administrator account, open **Recent Runs**, reopen the document analysis, add a note, and accept or reject a recommendation. Open **Admin Review** to show search analytics, feedback, verification queue, audit history, dataset quality, and held-out retrieval metrics.

### 7. Close With Measured Results (45 seconds)

State the held-out hybrid-search results:

- Top-1 accuracy: 91.5%
- Top-5 accuracy: 97.3%
- Mean reciprocal rank: 94.3%
- Catalogue: 250 standards
- Labeled query examples: 3,750

Clarify that these metrics measure retrieval on the prototype's labeled dataset; authoritative BIS validation and real tender benchmarking are the next production steps.

## Why It Works

The engine searches several kinds of information together: standard title, keywords, related terminology, procurement examples, scope, and semantic text. Hybrid mode combines exact keyword evidence with similarity-based retrieval. This helps when a buyer's wording differs from a catalogue title while preserving understandable match reasons.

For documents, clause-level analysis prevents unrelated requirements from being compressed into one vague query. Results carry evidence excerpts, confidence, verification state, and provenance. Feedback and reviewer decisions are stored for audit and future ranking improvement.

## Main USP

The key distinction is not merely "AI search." It is a procurement-specific, explainable, reviewable workflow:

- accepts real specifications as text, PDF, or DOCX;
- returns ranked standards with the exact reasons and clauses;
- distinguishes retrieval confidence from legal applicability;
- exposes source and verification status;
- supports reviewer decisions, audit history, reproducible reports, and operational monitoring;
- runs locally, so sensitive tender content does not need to leave the deployment environment.

## Likely Judge Questions

**Is the recommendation legally binding?**  
No. It is a shortlist for technical review. Mandatory status and the latest edition must be confirmed against authoritative BIS and regulatory sources.

**Why not use a normal search box?**  
A normal search mainly matches literal words. This system combines procurement synonyms, examples, semantic similarity, clause evidence, ranking, confidence, verification metadata, and reviewer feedback in one workflow.

**How do you measure accuracy?**  
The project has fixed train, validation, and held-out test splits. Its release quality gate checks Top-1, Top-5, and mean reciprocal rank and fails if quality drops below configured thresholds.

**Can it read scanned PDFs?**  
It detects when a PDF has no selectable text and asks for OCR. Native OCR is intentionally left as a deployment integration because it requires an OCR engine and language packs.

**How does it improve over time?**  
Useful/not-useful feedback and reviewer accept/reject labels are persisted and exportable. They provide supervised examples for later reranking and model evaluation.

**Is it production-ready?**  
The software is deployment-shaped: authentication, roles, security headers, structured logs, health and metrics endpoints, backups, Docker, CI, and smoke tests are present. Production adoption still requires authoritative dataset licensing and verification, user acceptance testing on real tenders, HTTPS deployment, off-host backups, and monitored infrastructure.

## Demo Safety Checklist

- Start the API and confirm the status indicator says **API online**.
- Verify the demo user credentials before the presentation.
- Run the demo PDF once and confirm expected standards appear.
- Keep Hybrid mode selected for the measured default.
- Do not describe confidence as legal certainty.
- Keep `docs/PROTOTYPE_ACCEPTANCE.md` available for scope questions.
