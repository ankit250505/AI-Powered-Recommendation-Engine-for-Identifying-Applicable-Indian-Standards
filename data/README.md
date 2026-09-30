# Indian Standards Dataset

This folder contains the starter catalog for the AI-powered recommendation engine.

## Files

- `indian_standards_seed.csv` - source-of-truth seed catalog for editing and database imports.
- `indian_standards_seed.json` - JSON export generated from the CSV for direct API loading.
- `procurement_query_examples.csv` - generated labeled procurement queries for search evaluation, ranking experiments, and train/validation/test splits.
- `procurement_query_examples.json` - JSON export of the generated labeled query examples.

## Current Size

- 250 standards rows
- 3,750 labeled procurement query examples
- 14 columns
- Coverage includes civil, electrical, water, plumbing, mechanical, fire safety, PPE, medical, food, packaging, testing, and consumer goods procurement categories.

## Column Contract

| Column | Purpose |
| --- | --- |
| `id` | Stable internal row id. |
| `standard_code` | Indian Standard code or standard series identifier. |
| `title` | Human-readable standard title. |
| `category` | Broad procurement domain. |
| `subcategory` | More specific product or use group. |
| `keywords` | Semicolon-separated matching terms for keyword search. |
| `scope_summary` | Short description used for explanations. |
| `related_terms` | Extra aliases and technical terms. |
| `procurement_examples` | Example tender/specification phrases. |
| `mandatory_hint` | Non-legal hint about possible mandatory/advisory nature. |
| `source_url` | Starting source URL for verification. |
| `verify_status` | Verification state of the row. |
| `last_reviewed` | Dataset review date. |
| `embedding_text` | Clean text field intended for vector embedding generation. |

## Verification Policy

This is a production-shaped seed dataset, not a legal compliance database.

Before using it in a real procurement system:

1. Verify every `standard_code`, `title`, and revision year against BIS.
2. Confirm whether the standard is active, withdrawn, revised, or superseded.
3. Confirm mandatory certification status from current BIS Quality Control Orders or CRS lists.
4. Replace generic `source_url` values with the exact BIS standard detail page or official circular.
5. Add versioning so old recommendations can be reproduced later.

## Recommended Database Use

Use this as a `standards` table first. Later split into normalized tables:

- `standards`
- `standard_keywords`
- `standard_sources`
- `standard_mandatory_status`
- `recommendation_feedback`
- `query_logs`

## Training and Evaluation Dataset

The `procurement_query_examples` files map realistic procurement text to the target standard.

Current split:

| Split | Rows |
| --- | ---: |
| `train` | 3,000 |
| `validation` | 375 |
| `test` | 375 |

Use this dataset to measure retrieval accuracy before adding semantic search:

- top-1 accuracy
- top-3 accuracy
- top-5 accuracy
- mean reciprocal rank
- latency per query

Do not treat these generated examples as real tenders. They are synthetic-but-controlled examples for model development and performance testing.

To regenerate:

```bash
python scripts/generate_training_examples.py
```
