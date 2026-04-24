"""
construct_training_data.py

Build reference/training sets for the ClinicalBERT adverse event classifier.

For each drug label section, finds all MedDRA terms via Aho-Corasick string
matching, classifies each as is_event/not_event against gold-standard
annotations, and generates context strings for BERT training.

Produces CSV files consumable by ``onsides-train``.

Usage:
    onsides-construct-ref --method 14 --nwords 125 --section ALL
"""

import argparse
import csv
import json
import logging
import math
import random
from dataclasses import dataclass, field
from pathlib import Path

import duckdb
from ahocorasick import Automaton

logger = logging.getLogger(__name__)

ANNOTATION_DIR = Path("database/annotations")
VOCAB_PATH = Path("_onsides/vocab/meddra_english.parquet")

SECTION_CODES = {
    "adverse reactions": "AR",
    "boxed warnings": "BW",
    "warnings and precautions": "WP",
}
SECTION_NAMES = {v: k for k, v in SECTION_CODES.items()}


# ---------------------------------------------------------------------------
# Method configuration
# ---------------------------------------------------------------------------

@dataclass
class MethodConfig:
    """Flags derived from the integer method parameter (0-15)."""

    sub_event: bool = False
    sub_nonsense: bool = False
    prepend_event: bool = False
    prepend_source: bool = False
    prop_before: float = 0.5
    random_words: bool = False


_METHOD_TABLE: dict[int, MethodConfig] = {
    0:  MethodConfig(sub_event=True, prepend_event=True),
    1:  MethodConfig(prepend_event=True),
    2:  MethodConfig(sub_event=True),
    3:  MethodConfig(),
    4:  MethodConfig(sub_event=True, sub_nonsense=True),
    5:  MethodConfig(random_words=True),
    6:  MethodConfig(sub_event=True, prepend_event=True, prop_before=1.0),
    7:  MethodConfig(sub_event=True, prepend_event=True, prop_before=0.0),
    8:  MethodConfig(sub_event=True, prepend_event=True, prop_before=0.125),
    9:  MethodConfig(sub_event=True, prepend_event=True, prop_before=0.25),
    10: MethodConfig(sub_event=True, prepend_event=True, prop_before=0.75),
    11: MethodConfig(sub_event=True, prepend_event=True, prop_before=0.875),
    12: MethodConfig(sub_event=True, prepend_event=True, prepend_source=True),
    13: MethodConfig(sub_event=True, prepend_event=True, prepend_source=True, prop_before=0.25),
    14: MethodConfig(sub_event=True, prepend_event=True, prepend_source=True, prop_before=0.125),
    15: MethodConfig(sub_event=True, prepend_event=True, prepend_source=True, prop_before=0.0),
}


def get_method_config(method: int) -> MethodConfig:
    if method not in _METHOD_TABLE:
        raise ValueError(f"Unknown method {method}. Expected 0-15.")
    return _METHOD_TABLE[method]


# ---------------------------------------------------------------------------
# MedDRA vocabulary
# ---------------------------------------------------------------------------

@dataclass
class MedDRAVocab:
    """MedDRA vocabulary with Aho-Corasick automaton and LLT→PT mapping."""

    automaton: Automaton
    code_to_term: dict[str, str]
    llt_to_pt: dict[str, tuple[str, str]]  # llt_code → (pt_code, pt_name)


def load_meddra_vocab(
    vocab_path: Path = VOCAB_PATH,
    omop_concept_path: Path | None = None,
    omop_relationship_path: Path | None = None,
) -> MedDRAVocab:
    """Load MedDRA terms and build search structures.

    Args:
        vocab_path: Parquet with columns (text_id, text) — one row per
            MedDRA term (LLTs + PTs).
        omop_concept_path: OMOP CONCEPT.csv for LLT→PT mapping.
        omop_relationship_path: OMOP CONCEPT_RELATIONSHIP.csv.
    """
    if omop_concept_path is None:
        omop_concept_path = Path("data/omop_vocab/CONCEPT.csv")
    if omop_relationship_path is None:
        omop_relationship_path = Path("data/omop_vocab/CONCEPT_RELATIONSHIP.csv")

    # Build Aho-Corasick automaton from vocab parquet
    con = duckdb.connect()
    terms = con.execute(
        "SELECT text_id AS code, text AS term FROM read_parquet(?)",
        [str(vocab_path)],
    ).fetchall()

    automaton = Automaton()
    code_to_term: dict[str, str] = {}

    for code, term in terms:
        term_lower = term.lower()
        code_to_term[code] = term
        automaton.add_word(term_lower, (code, term_lower))

    automaton.make_automaton()
    logger.info(f"Built automaton with {len(code_to_term)} MedDRA terms")

    # Build LLT→PT mapping from OMOP vocab
    llt_to_pt: dict[str, tuple[str, str]] = {}

    if omop_concept_path.exists() and omop_relationship_path.exists():
        rows = con.execute(
            """
            WITH meddra AS (
                SELECT concept_id, concept_name, concept_class_id, concept_code
                FROM read_csv(?, delim='\t', header=true, quote='')
                WHERE vocabulary_id = 'MedDRA'
                  AND concept_class_id IN ('PT', 'LLT')
                  AND invalid_reason IS NULL
            )
            SELECT
                llt.concept_code AS llt_code,
                pt.concept_code  AS pt_code,
                pt.concept_name  AS pt_name
            FROM meddra llt
            JOIN read_csv(?, delim='\t', header=true, quote='') cr
                ON llt.concept_id = cr.concept_id_1
            JOIN meddra pt
                ON cr.concept_id_2 = pt.concept_id
            WHERE llt.concept_class_id = 'LLT'
              AND pt.concept_class_id  = 'PT'
              AND cr.relationship_id   = 'Is a'
              AND cr.invalid_reason IS NULL
            """,
            [str(omop_concept_path), str(omop_relationship_path)],
        ).fetchall()

        for llt_code, pt_code, pt_name in rows:
            llt_to_pt[llt_code] = (pt_code, pt_name)

        logger.info(f"Built LLT→PT mapping: {len(llt_to_pt)} entries")
    else:
        logger.warning(
            "OMOP vocab files not found — LLT→PT mapping unavailable. "
            "PT metadata columns will be incomplete."
        )

    con.close()
    return MedDRAVocab(
        automaton=automaton,
        code_to_term=code_to_term,
        llt_to_pt=llt_to_pt,
    )


# ---------------------------------------------------------------------------
# Term finding
# ---------------------------------------------------------------------------

@dataclass
class FoundTerm:
    term: str
    code: str
    start: int
    length: int
    pt_code: str
    pt_name: str
    source: str = "exact"


def find_terms_in_text(
    text_lower: str, vocab: MedDRAVocab
) -> list[FoundTerm]:
    """Find all MedDRA terms in lowercased text."""
    found: list[FoundTerm] = []
    for end_index, (code, matched_term) in vocab.automaton.iter(text_lower):
        start = end_index - len(matched_term) + 1
        pt_code, pt_name = vocab.llt_to_pt.get(
            code, (code, vocab.code_to_term.get(code, matched_term))
        )
        found.append(FoundTerm(
            term=matched_term,
            code=code,
            start=start,
            length=len(matched_term),
            pt_code=pt_code,
            pt_name=pt_name,
        ))
    return found


# ---------------------------------------------------------------------------
# Example string generation
# ---------------------------------------------------------------------------

def generate_example(
    text: str,
    term: str,
    start: int,
    length: int,
    nwords: int,
    config: MethodConfig,
    source: str = "exact",
) -> str:
    """Generate a BERT training example string from a found term in context.

    Matches the logic from the original construct_training_data.py methods 0-15.
    """
    if config.random_words:
        return " ".join(random.sample(text.split(), min(nwords, len(text.split()))))

    if nwords == 3:
        return term

    term_nwords = len(term.split())
    size_before = max(int((nwords - 2 * term_nwords) * config.prop_before), 1)
    size_after = max(int((nwords - 2 * term_nwords) * (1 - config.prop_before)), 1)

    event_string = term
    if config.sub_event:
        event_string = "EVENT"
    if config.sub_nonsense:
        event_string = "YIHFKEHDK"

    start_string = ""
    if config.prepend_event:
        start_string = term
    if config.prepend_source:
        source_tag = "exact" if source == "exact" else "split"
        start_string = f"{start_string} {source_tag}" if start_string else source_tag

    before_text = text[:start]
    after_text = text[start + length:]

    parts: list[str] = []
    if start_string:
        parts.append(start_string)
    if config.prop_before > 0:
        parts.extend(before_text.split()[-size_before:])
    parts.append(event_string)
    if config.prop_before < 1:
        parts.extend(after_text.split()[:size_after])

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Annotation loading
# ---------------------------------------------------------------------------

@dataclass
class AnnotationRecord:
    drug: str
    section_code: str
    text: str
    annotated_codes: set[str] = field(default_factory=set)
    tac: str = "train"


def _is_valid_id(val) -> bool:
    if val is None:
        return False
    if isinstance(val, float) and math.isnan(val):
        return False
    return True


def load_onsides_annotations(
    sections: list[str],
    annotations_dir: Path = Path("annotations/adverse_events"),
    labels_parquet: Path = Path("_onsides/us/label_text.parquet"),
) -> list[AnnotationRecord]:
    """Load annotations produced by the OnSIDES annotation tool.

    Reads JSON files from the annotation tool's output directory and
    converts them into AnnotationRecord objects for the reference set
    construction pipeline.

    Args:
        sections: List of section codes (AR, BW, WP).
        annotations_dir: Root directory of annotation tool output.
        labels_parquet: Path to label text parquet for section text lookup.

    Returns:
        List of AnnotationRecord, one per drug-section combination.
    """
    con = duckdb.connect()
    label_texts = {}
    for row in con.execute(
        "SELECT set_id, " + ", ".join(sections)
        + " FROM read_parquet(?)",
        [str(labels_parquet)],
    ).fetchall():
        label_texts[row[0]] = {
            sec: row[1 + i] or "" for i, sec in enumerate(sections)
        }
    con.close()

    records: list[AnnotationRecord] = []
    total_events = 0

    for annotator_dir in sorted(annotations_dir.iterdir()):
        if not annotator_dir.is_dir():
            continue
        for path in sorted(annotator_dir.glob("*.json")):
            with open(path) as f:
                doc = json.load(f)

            set_id = doc["label_id"]
            texts = label_texts.get(set_id, {})

            for sec_code in sections:
                anns = doc.get("sections", {}).get(sec_code, [])
                if not anns:
                    continue

                text = texts.get(sec_code, "")
                if not text.strip():
                    continue

                annotated_codes: set[str] = set()
                for a in anns:
                    if a.get("pt_code"):
                        annotated_codes.add(str(a["pt_code"]))
                    if a.get("term_code"):
                        annotated_codes.add(str(a["term_code"]))

                total_events += len(anns)
                records.append(AnnotationRecord(
                    drug=set_id.upper(),
                    section_code=sec_code,
                    text=text,
                    annotated_codes=annotated_codes,
                    tac="test",
                ))

    logger.info(
        f"Loaded {len(records)} OnSIDES annotation records "
        f"for sections {sections} ({total_events} events)"
    )
    return records


def load_annotations(
    sections: list[str],
    annotation_dir: Path = ANNOTATION_DIR,
    exclude_flag1: set[str] | None = None,
    exclude_flag2: set[str] | None = None,
) -> list[AnnotationRecord]:
    """Load Demner-Fushman annotation JSONs for the requested sections.

    Args:
        sections: List of section codes (AR, BW, WP).
        annotation_dir: Directory containing the annotation JSON files.
        exclude_flag1: Flag 1 values to exclude (e.g. {"duplicate", "unmapped"}).
            Flag 1 is auto-computed: "unmapped" if pt_id is missing,
            "duplicate" if the same PT appears multiple times for a
            drug+section, otherwise "clean".
        exclude_flag2: Flag 2 values to exclude (e.g. {"drug_class", "animal"}).
            Flag 2 is read from event[7] in extended annotation format.
            Defaults to "human" when not present.

    Returns:
        List of AnnotationRecord, one per drug-section combination.
    """
    section_names = {SECTION_NAMES[s].lower() for s in sections}

    records: list[AnnotationRecord] = []
    total_events = 0
    excluded_f1 = 0
    excluded_f2 = 0

    for tac_label, filename in [
        ("train", "demner-fushman-train-labels.json"),
        ("test", "demner-fushman-test-labels.json"),
    ]:
        path = annotation_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Annotation file not found: {path}")

        with open(path) as f:
            data = json.load(f)

        for entry in data:
            section_name = entry.get("section_name", "").lower()
            if section_name not in section_names:
                continue

            section_code = SECTION_CODES.get(section_name)
            if section_code is None:
                continue

            drug = entry["label_id"].upper()
            text = entry.get("section_text", "")
            events = entry.get("adverse_events", [])
            total_events += len(events)

            # First pass: count PT occurrences for duplicate detection
            pt_counts: dict[str, int] = {}
            for event in events:
                pt_id = event[2]
                if _is_valid_id(pt_id):
                    pt_key = str(int(float(pt_id)))
                    pt_counts[pt_key] = pt_counts.get(pt_key, 0) + 1

            # Second pass: apply flag filters
            annotated_codes: set[str] = set()
            for event in events:
                pt_id = event[2]
                llt_id = event[4]

                # Compute Flag 1
                if not _is_valid_id(pt_id):
                    flag1 = "unmapped"
                elif pt_counts.get(str(int(float(pt_id))), 0) > 1:
                    flag1 = "duplicate"
                else:
                    flag1 = "clean"

                # Read Flag 2 from extended event format
                flag2 = event[7] if len(event) > 7 else "human"

                if exclude_flag1 and flag1 in exclude_flag1:
                    excluded_f1 += 1
                    continue
                if exclude_flag2 and flag2 in exclude_flag2:
                    excluded_f2 += 1
                    continue

                if _is_valid_id(pt_id):
                    annotated_codes.add(str(int(float(pt_id))))
                if _is_valid_id(llt_id):
                    annotated_codes.add(str(int(float(llt_id))))

            records.append(AnnotationRecord(
                drug=drug,
                section_code=section_code,
                text=text,
                annotated_codes=annotated_codes,
                tac=tac_label,
            ))

    logger.info(
        f"Loaded {len(records)} annotation records "
        f"for sections {sections} ({total_events} events)"
    )
    if excluded_f1:
        logger.info(f"Excluded {excluded_f1} events by Flag 1 filter")
    if excluded_f2:
        logger.info(f"Excluded {excluded_f2} events by Flag 2 filter")
    return records


# ---------------------------------------------------------------------------
# Main construction logic
# ---------------------------------------------------------------------------

def construct_reference_set(
    records: list[AnnotationRecord],
    vocab: MedDRAVocab,
    method: int,
    nwords: int,
) -> list[list[str]]:
    """Build the full reference set from annotations and vocabulary.

    Returns rows as lists of strings matching the output CSV columns:
    [section, drug, tac, meddra_id, pt_meddra_id, source_method, class,
     pt_meddra_term, found_term, string]
    """
    config = get_method_config(method)
    random.seed(222)

    rows: list[list[str]] = []
    total_pos = 0
    total_neg = 0

    for record in records:
        text_lower = " ".join(record.text.split()).lower()

        found_terms = find_terms_in_text(text_lower, vocab)
        logger.info(
            f"  {record.drug}/{record.section_code}: "
            f"{len(found_terms)} term occurrences in text"
        )

        num_pos = 0
        num_neg = 0

        for ft in found_terms:
            is_event = (
                ft.code in record.annotated_codes
                or ft.pt_code in record.annotated_codes
            )
            string_class = "is_event" if is_event else "not_event"

            example = generate_example(
                text_lower, ft.term, ft.start, ft.length,
                nwords, config, ft.source,
            )

            rows.append([
                record.section_code,
                record.drug,
                record.tac,
                ft.code,
                ft.pt_code,
                ft.source,
                string_class,
                ft.pt_name,
                ft.term,
                example,
            ])

            if is_event:
                num_pos += 1
            else:
                num_neg += 1

        total_pos += num_pos
        total_neg += num_neg
        logger.info(
            f"    pos={num_pos}, neg={num_neg}"
        )

    logger.info(
        f"Reference set complete: {total_pos} positive, "
        f"{total_neg} negative, {total_pos + total_neg} total"
    )
    return rows


def write_reference_csv(
    output_path: Path,
    rows: list[list[str]],
) -> None:
    """Write reference set rows to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "section", "drug", "tac", "meddra_id", "pt_meddra_id",
            "source_method", "class", "pt_meddra_term", "found_term", "string",
        ])
        writer.writerows(rows)
    logger.info(f"Wrote {len(rows)} rows to {output_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _resolve_sections(section_arg: str) -> list[str]:
    """Expand section argument to list of section codes."""
    if section_arg in ("AR", "BW", "WP"):
        return [section_arg]
    if section_arg == "ALL":
        return ["AR", "BW", "WP"]
    if section_arg == "ARBW":
        return ["AR", "BW"]
    raise ValueError(f"Unknown section: {section_arg}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Construct BERT training reference sets from annotations."
    )
    parser.add_argument(
        "--method", type=int, required=True,
        help="Example construction method (0-15). Method 14 is recommended.",
    )
    parser.add_argument(
        "--nwords", type=int, default=125,
        help="Number of context words per example (default: 125).",
    )
    parser.add_argument(
        "--section", type=str, default="AR",
        choices=["AR", "BW", "WP", "ALL", "ARBW"],
        help="Label section(s) to include.",
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Output CSV path. Default: data/refs/ref{method}_nwords{nwords}_..._{section}.txt",
    )
    parser.add_argument(
        "--vocab", type=Path, default=VOCAB_PATH,
        help="MedDRA vocabulary parquet path.",
    )
    parser.add_argument(
        "--annotations", type=Path, default=ANNOTATION_DIR,
        help="Annotation JSON directory.",
    )
    parser.add_argument(
        "--exclude-flag1", type=str, default=None,
        help="Comma-separated Flag 1 values to exclude (e.g. 'duplicate,unmapped'). "
        "Flag 1 is auto-computed from annotations.",
    )
    parser.add_argument(
        "--exclude-flag2", type=str, default=None,
        help="Comma-separated Flag 2 values to exclude (e.g. 'drug_class,animal'). "
        "Flag 2 is read from extended annotation format (event[7]).",
    )
    parser.add_argument(
        "--onsides-annotations", type=Path, default=None,
        help="Path to OnSIDES annotation tool output directory "
        "(e.g. 'annotations/adverse_events'). "
        "These annotations are added as test-split records.",
    )

    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    )

    if args.nwords < 3:
        parser.error("--nwords must be >= 3")
    if args.nwords == 3 and args.method != 0:
        parser.error("--method must be 0 when --nwords is 3")

    sections = _resolve_sections(args.section)

    exclude_flag1 = set(args.exclude_flag1.split(",")) if args.exclude_flag1 else None
    exclude_flag2 = set(args.exclude_flag2.split(",")) if args.exclude_flag2 else None

    output_path = args.output
    if output_path is None:
        output_path = (
            Path("data/refs")
            / f"ref{args.method}_nwords{args.nwords}"
            f"_clinical_bert_reference_set_{args.section}.txt"
        )

    logger.info(f"Method: {args.method}, nwords: {args.nwords}, sections: {sections}")
    if exclude_flag1:
        logger.info(f"Excluding Flag 1: {exclude_flag1}")
    if exclude_flag2:
        logger.info(f"Excluding Flag 2: {exclude_flag2}")

    vocab = load_meddra_vocab(args.vocab)

    if args.onsides_annotations:
        records = load_onsides_annotations(
            sections, args.onsides_annotations,
        )
    else:
        records = load_annotations(
            sections, args.annotations,
            exclude_flag1=exclude_flag1,
            exclude_flag2=exclude_flag2,
        )

    rows = construct_reference_set(records, vocab, args.method, args.nwords)
    write_reference_csv(output_path, rows)


if __name__ == "__main__":
    main()
