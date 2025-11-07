#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<USAGE
Usage: $0 \
  --file PATH \
  --source TEXT \
  --year YYYY \
  --quarter 1|2|3|4 \
  --domain-table TABLE_NAME \
  [--domain-schema SCHEMA] \
  [--execution-id ID] \
  [--log-filename NAME]

Notes:
- Uses PG* env vars for connection (PGHOST, PGPORT, PGUSER, PGDATABASE, PGPASSWORD, etc.).
- Computes wc -l on the file and SELECT COUNT(*) from <schema>.<table>.
- Inserts a log row into onsides.z_qa_faers_wc_import_log.
- The "--source" can be a free-form tag (e.g., FAERS, LAERS, or a release like v3.1.0). Max length 32.
USAGE
}

FILE=""
SOURCE=""
YEAR=""
QUARTER=""
DOMAIN_TABLE=""
DOMAIN_SCHEMA="onsides"
EXECUTION_ID=""
LOG_FILENAME=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --file) FILE="$2"; shift 2 ;;
    --source) SOURCE="$2"; shift 2 ;;
    --year) YEAR="$2"; shift 2 ;;
    --quarter) QUARTER="$2"; shift 2 ;;
    --domain-table) DOMAIN_TABLE="$2"; shift 2 ;;
    --domain-schema) DOMAIN_SCHEMA="$2"; shift 2 ;;
    --execution-id) EXECUTION_ID="$2"; shift 2 ;;
    --log-filename) LOG_FILENAME="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

[[ -z "$FILE" || -z "$SOURCE" || -z "$YEAR" || -z "$QUARTER" || -z "$DOMAIN_TABLE" ]] && { usage; exit 2; }

if [[ ! -f "$FILE" ]]; then
  echo "File not found: $FILE" >&2
  exit 1
fi

########################################
# Normalize and validate
########################################

# Allow any non-empty source/tag up to 32 chars (column is varchar(32))
if [[ ${#SOURCE} -gt 32 ]]; then
  echo "--source length must be <= 32 characters (got ${#SOURCE})" >&2
  exit 2
fi
SOURCE_UPPER=$(echo "$SOURCE" | tr '[:lower:]' '[:upper:]')

if ! [[ "$YEAR" =~ ^[0-9]{2}$|^[0-9]{4}$ ]]; then
  echo "--year must be either YY or YYYY (e.g., 25 or 2025)" >&2; exit 2
fi

if ! [[ "$QUARTER" =~ ^[1-4]$ ]]; then
  echo "--quarter must be 1-4" >&2; exit 2
fi

if [[ -z "$LOG_FILENAME" ]]; then
  LOG_FILENAME=$(basename -- "$FILE")
fi

WC_L_COUNT=$(wc -l < "$FILE" | tr -d ' ')

# CSV-aware logical record count (excludes header; handles embedded newlines)
CSV_RECORD_COUNT=$(python3 - <<'PY' "$FILE"
import csv, sys
fn = sys.argv[1]
count = 0
with open(fn, 'r', newline='') as f:
  reader = csv.reader(f)
  try:
    next(reader)  # skip header
  except StopIteration:
    print(0)
    raise SystemExit(0)
  for _ in reader:
    count += 1
print(count)
PY
)

QUALIFIED_TABLE="${DOMAIN_SCHEMA}.${DOMAIN_TABLE}"

# Ensure the log table exists (safe to run repeatedly)
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
psql -v ON_ERROR_STOP=1 -f "$SCRIPT_DIR/z_qa_faers_wc_import_log.sql"

# Get domain table count
DOMAIN_COUNT=$(psql -tA -v ON_ERROR_STOP=1 -c "SELECT COUNT(*) FROM ${QUALIFIED_TABLE};")

escape_sql() { printf "%s" "${1//\'/''}"; }

LOG_FN_ESC=$(escape_sql "$LOG_FILENAME")
FILE_ESC=$(escape_sql "$FILE")
SOURCE_ESC=$(escape_sql "$SOURCE_UPPER")

if [[ -z "$EXECUTION_ID" ]]; then EXEC_SQL="NULL"; else EXEC_SQL="$EXECUTION_ID"; fi

SQL_STMT="INSERT INTO onsides.z_qa_faers_wc_import_log
  (log_filename, filename, onsides_release_version, yr, qtr, wc_l_count,
   select_count_on_domain, select_count_diff, select_count_diff_pct,
   execution_id, csv_record_count, csv_count_diff, csv_count_diff_pct)
VALUES
  ('$LOG_FN_ESC', '$FILE_ESC', '$SOURCE_ESC', ${YEAR}::int, ${QUARTER}::int, ${WC_L_COUNT}::int,
   ${DOMAIN_COUNT}::int,
   (${DOMAIN_COUNT}::int - ${WC_L_COUNT}::int),
   CASE WHEN ${WC_L_COUNT}::int = 0 THEN NULL
     ELSE ((${DOMAIN_COUNT})::float8 - (${WC_L_COUNT})::float8) / NULLIF((${WC_L_COUNT})::float8, 0)
   END,
   ${EXEC_SQL},
   ${CSV_RECORD_COUNT}::int,
   (${DOMAIN_COUNT}::int - ${CSV_RECORD_COUNT}::int),
   CASE WHEN ${CSV_RECORD_COUNT}::int = 0 THEN NULL
     ELSE ((${DOMAIN_COUNT})::float8 - (${CSV_RECORD_COUNT})::float8) / NULLIF((${CSV_RECORD_COUNT})::float8, 0)
   END
  );"

psql -v ON_ERROR_STOP=1 -c "$SQL_STMT"

echo "Logged: file=$FILE source=$SOURCE_UPPER year=$YEAR qtr=$QUARTER wc_l=$WC_L_COUNT csv_records=$CSV_RECORD_COUNT domain=${QUALIFIED_TABLE} domain_count=$DOMAIN_COUNT"
