# QA Import Summary

This document explains the QA logging process for OnSIDES CSV imports into PostgreSQL.

## Overview

The QA scripts (`qa_faers_wc_import_log.sh` and `run_qa_bulk.sh`) validate that CSV data was imported correctly by comparing file counts to database counts.

## Metrics Explained

### wc_l_count
- **Definition**: Raw line count from `wc -l` on the CSV file.
- **Includes**: Header line + all data lines, but **overcounts** if CSV fields contain embedded newlines (multiline fields).
- **Example**: A CSV with 10,000 records but multiline fields might show 10,500 lines.

### csv_record_count
- **Definition**: Logical record count using Python's `csv` module reader.
- **Handles**: Embedded newlines correctly, counts actual data rows (excludes header).
- **Accuracy**: This is the true count of importable records.

### select_count_on_domain
- **Definition**: `SELECT COUNT(*)` from the target database table.
- **For vocab tables**: Excludes placeholder rows (`WHERE is_placeholder IS NOT TRUE`) if the column exists.
- **Represents**: Actual rows in the database after import.

### Diff Metrics

#### select_count_diff
- **Formula**: `select_count_on_domain - wc_l_count`
- **Purpose**: Highlights discrepancies due to multiline CSV fields.
- **Expected**: Often negative for CSVs with embedded newlines (e.g., drug label text fields).
- **Not a failure indicator**: Just shows `wc -l` isn't reliable for complex CSVs.

#### csv_count_diff
- **Formula**: `select_count_on_domain - csv_record_count`
- **Purpose**: Validates import accuracy.
- **Expected**: `0` for successful imports (database matches logical CSV records).
- **Key metric**: Non-zero values indicate import issues.

#### Percentage Diffs
- `select_count_diff_pct`: `(select_count_diff / wc_l_count) * 100`
- `csv_count_diff_pct`: `(csv_count_diff / csv_record_count) * 100`
- Useful for large datasets to see relative discrepancies.

## Example: product_label.csv

From recent QA run:
- `wc_l_count`: 63,282 (raw lines)
- `csv_record_count`: 59,515 (logical records)
- `select_count_on_domain`: 59,515 (database rows)
- `select_count_diff`: -3,767 (multiline fields cause overcount)
- `csv_count_diff`: 0 (import successful)

## Usage

Run QA for a single file:
```bash
./qa_faers_wc_import_log.sh \
  --file data/csv/product_label.csv \
  --source V3.1.0 \
  --year 2025 \
  --quarter 1 \
  --domain-table product_label
```

Run QA for all CSVs in a directory:
```bash
./run_qa_bulk.sh data/csv
```

## Interpretation

- **csv_count_diff = 0**: Import successful.
- **csv_count_diff ≠ 0**: Investigate import process (e.g., data type mismatches, missing rows).
- **select_count_diff < 0**: Normal for CSVs with multiline fields; ignore unless csv_count_diff is also off.

## Troubleshooting

- If `csv_count_diff > 0`: Database has extra rows (e.g., placeholders, duplicates).
- If `csv_count_diff < 0`: Missing rows in database (import failed or filtered out).
- Check logs for COPY errors or constraint violations during import.