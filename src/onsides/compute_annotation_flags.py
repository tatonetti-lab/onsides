"""
compute_annotation_flags.py

Add Flag 2 (information source) values to Demner-Fushman annotation JSONs.

Flag 2 classifies each annotated adverse event by the type of evidence:
  - "human": Drug-specific human clinical data (default, ~95% of events)
  - "drug_class": Inferred from drug class membership
  - "animal": Observed only in animal/nonclinical studies

Flag 1 (annotation quality: clean/duplicate/unmapped) is computed on-the-fly
during reference set construction and does not need to be stored.

The heuristic examines the section text around each event's position for
characteristic language patterns. Results are stored as event[7] in the
annotation JSONs (extending the 7-element format to 8 elements).

Usage:
    onsides-compute-flags
    onsides-compute-flags --dry-run
"""

import argparse
import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

ANNOTATION_DIR = Path("database/annotations")

DRUG_CLASS_PATTERNS = [
    r"\bclass\s+effect\b",
    r"\bclass\s+of\s+drug",
    r"\bdrug\s*class\b",
    r"\bclass[\s-]+related\b",
    r"\bdrugs\s+in\s+this\s+class\b",
    r"\bother\s+drugs\s+in\s+the\s+same\s+class\b",
    r"\bclass\s+of\s+(antidepressant|antipsychotic|opioid|nsaid|ace\s+inhibitor|statin|beta|laba|corticosteroid|fluoroquinolone|thiazolidinedione)",
    r"\b(?:drugs|agents|compounds)\s+(?:of|in)\s+this\s+(?:class|type|category)\b",
]

ANIMAL_PATTERNS = [
    r"\bin\s+animal\s+(?:studies|experiments|models|toxicology|reproductive)",
    r"\bnonclinical\s+toxicology\b",
    r"\bcarcinogenesis\b",
    r"\bmutagenesis\b",
    r"\breproductive\s+toxicology\b",
    r"\bteratogenic(?:ity)?\s+(?:effects?|studies?)\b",
    r"\banimal\s+(?:data|reproduction)\b",
    r"\bin\s+(?:rats?|mice|rabbits?|dogs?|monkeys?|primates?|cynomolgus)\b",
    r"\b(?:embryo|fetal)\s*[-–]?\s*(?:lethality|toxicity|death)\b",
    r"\bprenatal\s+and\s+postnatal\b",
]

DRUG_CLASS_RE = re.compile("|".join(DRUG_CLASS_PATTERNS), re.IGNORECASE)
ANIMAL_RE = re.compile("|".join(ANIMAL_PATTERNS), re.IGNORECASE)

PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n|\n(?=\s*\d+\.\d+\s)")


def _classify_paragraphs(section_text: str) -> list[tuple[int, int, str]]:
    """Split section text into paragraphs and classify each.

    Returns list of (start, end, flag2) tuples.
    """
    splits = [m.start() for m in PARAGRAPH_SPLIT_RE.finditer(section_text)]
    boundaries = [0] + splits + [len(section_text)]

    classified = []
    for i in range(len(boundaries) - 1):
        start = boundaries[i]
        end = boundaries[i + 1]
        para = section_text[start:end]

        if DRUG_CLASS_RE.search(para):
            flag = "drug_class"
        elif ANIMAL_RE.search(para):
            flag = "animal"
        else:
            flag = "human"
        classified.append((start, end, flag))

    return classified


def classify_event(
    paragraphs: list[tuple[int, int, str]], start: int
) -> str:
    """Classify a single event based on its containing paragraph."""
    for p_start, p_end, flag in paragraphs:
        if p_start <= start < p_end:
            return flag
    return "human"


def add_flags_to_file(path: Path, dry_run: bool = False) -> dict[str, int]:
    """Add Flag 2 to all events in an annotation JSON file."""
    with open(path) as f:
        data = json.load(f)

    counts = {"human": 0, "drug_class": 0, "animal": 0}

    for record in data:
        section_text = record.get("section_text", "")
        events = record.get("adverse_events", [])
        paragraphs = _classify_paragraphs(section_text)

        for event in events:
            start = int(event[5]) if event[5] is not None else 0
            flag2 = classify_event(paragraphs, start)
            counts[flag2] += 1

            if len(event) > 7:
                event[7] = flag2
            else:
                event.append(flag2)

    if not dry_run:
        with open(path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Updated {path}")

    return counts


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Add Flag 2 (information source) to annotation JSONs."
    )
    parser.add_argument(
        "--annotations", type=Path, default=ANNOTATION_DIR,
        help="Annotation JSON directory.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Compute flags but don't modify files.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    )

    total_counts: dict[str, int] = {"human": 0, "drug_class": 0, "animal": 0}

    for filename in [
        "demner-fushman-train-labels.json",
        "demner-fushman-test-labels.json",
    ]:
        path = args.annotations / filename
        if not path.exists():
            logger.warning(f"Skipping {path} (not found)")
            continue

        logger.info(f"Processing {path}...")
        counts = add_flags_to_file(path, dry_run=args.dry_run)
        for k, v in counts.items():
            total_counts[k] += v

        logger.info(f"  {filename}: {counts}")

    total = sum(total_counts.values())
    logger.info(f"Total events: {total}")
    for flag, count in sorted(total_counts.items()):
        pct = count / total * 100 if total else 0
        logger.info(f"  {flag}: {count} ({pct:.1f}%)")

    if args.dry_run:
        logger.info("Dry run — no files modified.")


if __name__ == "__main__":
    main()
