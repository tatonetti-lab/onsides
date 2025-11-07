#!/usr/bin/env bash
set -euo pipefail

# run_qa_bulk.sh
# Run the QA logger for all CSVs in a given directory (defaults to data/csv)
# Usage: ./run_qa_bulk.sh [--dir path] [--source TAG] [--year YYYY|YY] [--quarter 1-4] [--schema onsides]

DIR=${1:-data/csv}
SOURCE=${2:-v3.1.0}
YEAR=${3:-2025}
QUARTER=${4:-1}
SCHEMA=${5:-onsides}
PGUSER=${PGUSER:-rw_grp}
PGDATABASE=${PGDATABASE:-cem_development_2025}
PGPORT=${PGPORT:-5433}

if [[ ! -d "$DIR" ]]; then
  echo "Directory not found: $DIR" >&2; exit 2
fi

i=1
for f in "$DIR"/*.csv; do
  [[ -f "$f" ]] || continue
  base=$(basename "$f" .csv)
  exec_id=$((1000 + i))
  echo "Processing $f -> ${SCHEMA}.${base} (exec_id=$exec_id)"
  PGUSER=$PGUSER PGDATABASE=$PGDATABASE PGPORT=$PGPORT bash "$(dirname "$0")/qa_faers_wc_import_log.sh" --file "$f" --source "$SOURCE" --year "$YEAR" --quarter "$QUARTER" --domain-table "$base" --domain-schema "$SCHEMA" --execution-id "$exec_id"
  i=$((i+1))
done

echo "Finished processing CSVs in $DIR"
