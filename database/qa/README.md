# QA workflow: FAERS/LAERS import log

This workflow logs basic QA metrics comparing a source data file's line count to the row count in a target database table. Results are inserted into `onsides.z_qa_faers_wc_import_log`.

## What it records
- `log_filename` (varchar(255), NOT NULL): basename of the source file (placeholder; can be customized)
- `filename` (varchar(255), NOT NULL): full path to the source file at logging time
- `onsides_release_version` (varchar(32), NOT NULL): OnSIDES release tag or short dataset tag, e.g. `v3.1.0`, `FAERS`, or `LAERS`
- `yr` (int, NOT NULL): dataset year (YY or YYYY)
- `qtr` (int, NOT NULL): dataset quarter (1–4)
- `wc_l_count` (int, NOT NULL): raw `wc -l` physical line count of the source file (includes header)
- `loaded_at` (timestamp, DEFAULT CURRENT_TIMESTAMP): when the log row was inserted
- `select_count_on_domain` (int, NULL): `SELECT COUNT(*)` on the specified domain table at logging time
- `select_count_diff` (int, NULL): `select_count_on_domain - wc_l_count`
- `select_count_diff_pct` (float, NULL): `select_count_diff / NULLIF(wc_l_count,0)` as a float
- `execution_id` (int, NULL): optional execution identifier for grouping runs
- `csv_record_count` (int, NULL): CSV-aware logical record count (header skipped; embedded newlines handled)
- `csv_count_diff` (int, NULL): `select_count_on_domain - csv_record_count`
- `csv_count_diff_pct` (float, NULL): `csv_count_diff / NULLIF(csv_record_count,0)` as a float

Notes about schema changes
- The table DDL adds the CSV-aware columns (`csv_record_count`, `csv_count_diff`, `csv_count_diff_pct`) when the table already exists. These columns are present in the current DDL.
- A previously-used `awk_nl_count` column (awk-based physical line count) was removed from the DDL; the workflow now uses `wc -l` for physical counts and a CSV-aware parser for logical counts.

## Usage

The script uses your normal PostgreSQL environment variables (e.g., `PGHOST`, `PGPORT`, `PGUSER`, `PGDATABASE`, etc.).

```
# Ensure the log table exists (one-time or on demand)
psql -v ON_ERROR_STOP=1 -f database/qa/z_qa_faers_wc_import_log.sql

# Log a dataset (example with release tag v3.1.0, YY=25, Q2)
bash database/qa/qa_faers_wc_import_log.sh \
  --file /path/to/source_file.txt \
  --source v3.1.0 \
  --year 25 \
  --quarter 2 \
  --domain-table product_adverse_effect \
  --domain-schema onsides \
  --execution-id 123
```

Notes:
- If `--domain-schema` is omitted, it defaults to `onsides`.
- `--log-filename` is optional; defaults to `basename --file`.
- Year supports YY or YYYY (e.g., 25 or 2025).
- `select_count_on_domain` is computed from `SELECT COUNT(*) FROM <schema>.<table>`.

## Troubleshooting
- Permission denied: ensure your DB user can `SELECT` from the domain table and `INSERT` into `onsides.z_qa_faers_wc_import_log`.
- Table not found: pass `--domain-schema` if your table is not in `onsides`.
- Line counts include headers: this workflow uses raw `wc -l` as requested.

### About physical vs logical row counts
- `wc -l` counts physical newline characters; it includes the header row and is unaware of CSV quoting.
- `awk 'END{print NR}'` also counts physical lines and usually equals `wc -l` (they only differ by one if a file is missing a trailing newline).
- `csv_record_count` is computed with a CSV parser: it skips the header and treats embedded newlines inside quoted fields as part of the same record. This is the correct basis for comparing to database row counts after a CSV import.

In particular for `product_label.csv`:
- `wc -l` and `awk` report 63,282 (physical lines).
- `csv_record_count` is 59,515 (logical records, excluding the header).
- `SELECT COUNT(*)` on `onsides.product_label` is 59,515, so `csv_count_diff = 0`. Any non-zero `select_count_diff` in this case is due to the use of physical lines instead of logical records.

# 11/04/2025 load

Today, we focused on logging QA metrics for the OnSIDES v3.1.0 release. This included running the QA logger for additional input files and ensuring that the logical CSV record counts match the row counts in the database tables. Discrepancies were investigated (for example, `product_label.csv` had embedded newlines in quoted fields which made `wc -l` differ from logical CSV record counts). The README and DDL were updated to reflect the CSV-aware columns and the removal of the old `awk_nl_count` field.
