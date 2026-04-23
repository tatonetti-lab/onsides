"""
Characterize the OnSIDES reference/annotation sets (Issue #27).

Produces summary statistics for each annotation dataset:
- Record and event counts
- Section text word and character counts (mean, median, min, max)
- Event term word counts
- MedDRA mapping rate (proportion of terms with a valid PT ID)
- Breakdown by section

Usage:
    uv run python analyses/characterize_reference_sets.py
"""

import json
import math
from collections import defaultdict
from pathlib import Path


ANNOTATION_DIR = Path("database/annotations")

DATASETS = [
    ("US-Train (Denmer-Fushman)", "demner-fushman-train-labels.json"),
    ("US-Test (Denmer-Fushman)", "demner-fushman-test-labels.json"),
    ("UK (OnSIDES-ANNOT)", "uk-annot.json"),
    ("EU (OnSIDES-ANNOT)", "eu-annot.json"),
    ("JP (OnSIDES-ANNOT)", "jp-annot.json"),
    ("US-Peds (OnSIDES-ANNOT)", "fda-pediatric-special-populations-annot.json"),
]


def _is_mapped(pt_id) -> bool:
    """Check if a MedDRA PT ID is present (not null/NaN)."""
    if pt_id is None:
        return False
    if isinstance(pt_id, float) and math.isnan(pt_id):
        return False
    if isinstance(pt_id, str) and pt_id.strip() == "":
        return False
    return True


def _percentile(values: list[int | float], p: float) -> float:
    """Compute the p-th percentile (0-100) of a sorted list."""
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * p / 100
    f = int(k)
    c = f + 1 if f + 1 < len(s) else f
    return s[f] + (k - f) * (s[c] - s[f])


def characterize_dataset(name: str, path: Path) -> dict:
    """Compute summary statistics for one annotation dataset."""
    with open(path) as f:
        data = json.load(f)

    # Per-section breakdown
    section_stats = defaultdict(lambda: {
        "records": 0,
        "records_with_events": 0,
        "total_events": 0,
        "mapped_events": 0,
        "word_counts": [],
        "char_counts": [],
        "term_word_counts": [],
    })

    for record in data:
        section = record.get("section_name", "unknown")
        events = record.get("adverse_events", [])
        text = record.get("section_text", "")

        stats = section_stats[section]
        stats["records"] += 1
        stats["word_counts"].append(len(text.split()))
        stats["char_counts"].append(len(text))

        if events:
            stats["records_with_events"] += 1
            stats["total_events"] += len(events)
            for event in events:
                stats["term_word_counts"].append(len(str(event[0]).split()))
                if _is_mapped(event[2]):
                    stats["mapped_events"] += 1

    return {"name": name, "sections": dict(section_stats)}


def print_summary(result: dict) -> None:
    """Print formatted summary for one dataset."""
    name = result["name"]
    sections = result["sections"]

    # Aggregate totals
    total_records = sum(s["records"] for s in sections.values())
    total_with_events = sum(s["records_with_events"] for s in sections.values())
    total_events = sum(s["total_events"] for s in sections.values())
    total_mapped = sum(s["mapped_events"] for s in sections.values())
    all_word_counts = [w for s in sections.values() for w in s["word_counts"]]
    all_char_counts = [c for s in sections.values() for c in s["char_counts"]]
    all_term_words = [t for s in sections.values() for t in s["term_word_counts"]]

    map_rate = total_mapped / total_events * 100 if total_events else 0

    print(f"{'=' * 70}")
    print(f" {name}")
    print(f"{'=' * 70}")
    print()
    print(f"  Records:            {total_records} ({total_with_events} with events)")
    print(f"  Sections:           {', '.join(sorted(sections.keys()))}")
    print(f"  Total events:       {total_events}")
    print(f"  Events/record:      {total_events / total_records:.1f} avg")
    print()

    # Section text statistics
    print(f"  Section text (words):")
    print(f"    Mean:   {sum(all_word_counts) / len(all_word_counts):.0f}")
    print(f"    Median: {_percentile(all_word_counts, 50):.0f}")
    print(f"    Min:    {min(all_word_counts)}")
    print(f"    Max:    {max(all_word_counts)}")
    print(f"    P25:    {_percentile(all_word_counts, 25):.0f}")
    print(f"    P75:    {_percentile(all_word_counts, 75):.0f}")
    print()
    print(f"  Section text (chars):")
    print(f"    Mean:   {sum(all_char_counts) / len(all_char_counts):.0f}")
    print(f"    Median: {_percentile(all_char_counts, 50):.0f}")
    print()

    # Event term statistics
    if all_term_words:
        print(f"  Event term length (words):")
        print(f"    Mean:   {sum(all_term_words) / len(all_term_words):.1f}")
        print(f"    Median: {_percentile(all_term_words, 50):.0f}")
        print(f"    Max:    {max(all_term_words)}")
        print()

    # MedDRA mapping
    print(f"  MedDRA mapping:     {total_mapped}/{total_events} ({map_rate:.1f}%)")
    unmapped = total_events - total_mapped
    if unmapped:
        print(f"  Unmapped terms:     {unmapped}")
    print()

    # Per-section breakdown
    if len(sections) > 1:
        print(f"  --- Breakdown by section ---")
        print()
        for section_name in sorted(sections.keys()):
            s = sections[section_name]
            n_events = s["total_events"]
            n_mapped = s["mapped_events"]
            n_records = s["records"]
            avg_words = (
                sum(s["word_counts"]) / len(s["word_counts"])
                if s["word_counts"]
                else 0
            )
            sr = n_mapped / n_events * 100 if n_events else 0
            print(f"  [{section_name}]")
            print(f"    Records: {n_records}, Events: {n_events}, "
                  f"Events/record: {n_events / n_records:.1f}")
            print(f"    Avg words: {avg_words:.0f}, "
                  f"MedDRA mapped: {n_mapped}/{n_events} ({sr:.1f}%)")
            print()


def print_cross_dataset_summary(results: list[dict]) -> None:
    """Print a comparison table across all datasets."""
    print()
    print(f"{'=' * 70}")
    print(f" Cross-Dataset Summary")
    print(f"{'=' * 70}")
    print()
    header = (
        f"  {'Dataset':<30} {'Records':>8} {'Events':>8} "
        f"{'Ev/Rec':>7} {'AvgWords':>9} {'Mapped%':>8}"
    )
    print(header)
    print(f"  {'-' * 73}")

    for result in results:
        name = result["name"][:30]
        sections = result["sections"]
        n_records = sum(s["records"] for s in sections.values())
        n_events = sum(s["total_events"] for s in sections.values())
        n_mapped = sum(s["mapped_events"] for s in sections.values())
        all_words = [w for s in sections.values() for w in s["word_counts"]]
        avg_words = sum(all_words) / len(all_words) if all_words else 0
        map_pct = n_mapped / n_events * 100 if n_events else 0
        ev_rec = n_events / n_records if n_records else 0

        print(
            f"  {name:<30} {n_records:>8} {n_events:>8} "
            f"{ev_rec:>7.1f} {avg_words:>9.0f} {map_pct:>7.1f}%"
        )

    # Totals
    all_records = sum(
        sum(s["records"] for s in r["sections"].values()) for r in results
    )
    all_events = sum(
        sum(s["total_events"] for s in r["sections"].values()) for r in results
    )
    all_mapped = sum(
        sum(s["mapped_events"] for s in r["sections"].values()) for r in results
    )
    total_map = all_mapped / all_events * 100 if all_events else 0
    print(f"  {'-' * 73}")
    print(
        f"  {'TOTAL':<30} {all_records:>8} {all_events:>8} "
        f"{'':>7} {'':>9} {total_map:>7.1f}%"
    )
    print()


def main():
    results = []
    for name, filename in DATASETS:
        path = ANNOTATION_DIR / filename
        if not path.exists():
            print(f"WARNING: {path} not found, skipping.")
            continue
        result = characterize_dataset(name, path)
        results.append(result)
        print_summary(result)

    if len(results) > 1:
        print_cross_dataset_summary(results)

    print()
    print("NOTES:")
    print("  - The Denmer-Fushman JSON files were rebuilt from the original TAC")
    print("    2017 source data (FinalReferenceStandard200Labels.csv and per-drug")
    print("    section text files) to include all three sections: Adverse Reactions,")
    print("    Boxed Warnings, and Warnings and Precautions.")
    print("  - 'unknown' sections are records missing the section_name key.")
    print("  - JP word counts are low because Japanese text has few whitespace-")
    print("    delimited words; char counts are more representative.")


if __name__ == "__main__":
    main()
