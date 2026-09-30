from __future__ import annotations

import csv
import json
import random
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STANDARDS_CSV = ROOT / "data" / "indian_standards_seed.csv"
OUTPUT_CSV = ROOT / "data" / "procurement_query_examples.csv"
OUTPUT_JSON = ROOT / "data" / "procurement_query_examples.json"
EXAMPLES_PER_STANDARD = 15
RANDOM_SEED = 260108


PREFIXES = [
    "Procurement of",
    "Supply and installation of",
    "Tender specification for",
    "Rate contract for",
    "Purchase requirement for",
    "Technical bid for",
    "Supply of",
    "Annual requirement for",
    "BOQ item for",
    "Department requirement for",
]

CONTEXTS = [
    "for government building work",
    "for public infrastructure project",
    "for municipal use",
    "for hospital procurement",
    "for school facility maintenance",
    "for water supply scheme",
    "for electrical maintenance work",
    "for construction site use",
    "for laboratory testing and acceptance",
    "for institutional bulk purchase",
]

QUALITY_PHRASES = [
    "as per applicable Indian Standard",
    "with BIS compliant specification",
    "meeting relevant IS code requirements",
    "with test certificate and standard marking where applicable",
    "including inspection and acceptance criteria",
    "with quality assurance documentation",
    "with relevant safety and performance requirements",
]

QUESTION_TEMPLATES = [
    "Which Indian Standard applies for {item}?",
    "Find IS code for {item} {context}.",
    "Applicable BIS standard for {item} with {terms}.",
    "Recommend standard for procurement of {item}.",
    "What standard should be used for tender item: {example}?",
]


def split_terms(value: str) -> list[str]:
    terms = [term.strip() for term in re.split(r"[;|,]", value or "") if term.strip()]
    return list(dict.fromkeys(terms))


def compact_title(title: str) -> str:
    cleaned = re.sub(r"\s+-\s+Specification$", "", title, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+-\s+Code of Practice$", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def choose_terms(row: dict[str, str], count: int = 3) -> list[str]:
    terms = split_terms(row["keywords"]) + split_terms(row["related_terms"])
    if not terms:
        terms = [compact_title(row["title"])]
    random.shuffle(terms)
    return terms[:count]


def build_query(row: dict[str, str], variant_index: int) -> tuple[str, str]:
    title = compact_title(row["title"])
    keywords = choose_terms(row, count=3)
    example = row["procurement_examples"].split(";")[0].strip()
    context = random.choice(CONTEXTS)
    quality = random.choice(QUALITY_PHRASES)
    prefix = random.choice(PREFIXES)

    item = random.choice([title, example, keywords[0]])
    terms = ", ".join(keywords)

    templates = [
        (f"{prefix} {item} {context} {quality}.", "procurement_statement"),
        (f"{prefix} {title} including {terms} {quality}.", "technical_specification"),
        (f"{example} - require {quality} and applicable IS reference.", "boq_line"),
        (f"{random.choice(QUESTION_TEMPLATES).format(item=item, context=context, terms=terms, example=example)}", "user_question"),
        (f"{row['subcategory']} item: {item}; category {row['category']}; required terms: {terms}.", "structured_description"),
    ]

    return templates[variant_index % len(templates)]


def main() -> None:
    random.seed(RANDOM_SEED)

    with STANDARDS_CSV.open(newline="", encoding="utf-8") as dataset:
        standards = list(csv.DictReader(dataset))

    rows: list[dict[str, str]] = []
    for standard in standards:
        for variant_index in range(EXAMPLES_PER_STANDARD):
            query, query_type = build_query(standard, variant_index)
            rows.append(
                {
                    "example_id": f"QEX-{len(rows) + 1:05d}",
                    "query_text": query,
                    "query_type": query_type,
                    "target_standard_id": standard["id"],
                    "target_standard_code": standard["standard_code"],
                    "target_title": standard["title"],
                    "category": standard["category"],
                    "subcategory": standard["subcategory"],
                    "split": "train",
                }
            )

    random.shuffle(rows)
    train_cutoff = int(len(rows) * 0.8)
    validation_cutoff = int(len(rows) * 0.9)

    for index, row in enumerate(rows):
        if index < train_cutoff:
            row["split"] = "train"
        elif index < validation_cutoff:
            row["split"] = "validation"
        else:
            row["split"] = "test"

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    with OUTPUT_JSON.open("w", encoding="utf-8") as output:
        json.dump(rows, output, indent=2)

    print(f"Generated {len(rows)} query examples")
    print(f"CSV: {OUTPUT_CSV}")
    print(f"JSON: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
