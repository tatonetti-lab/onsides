#!/usr/bin/env bash
set -euo pipefail

# Load missing rows from product_to_rxnorm.csv into onsides.product_to_rxnorm
# Usage: ./load_missing_product_to_rxnorm.sh /path/to/product_to_rxnorm.csv

CSV_FILE=${1:-data/csv/product_to_rxnorm.csv}
PGUSER=${PGUSER:-postgres}
PGDATABASE=${PGDATABASE:-cem_development_2025}
PGPORT=${PGPORT:-5433}

echo "Staging CSV: $CSV_FILE"

psql -v ON_ERROR_STOP=1 -d "$PGDATABASE" -p "$PGPORT" -U "$PGUSER" <<'PSQL'
SET search_path TO onsides, public;
DROP TABLE IF EXISTS product_to_rxnorm_staging;
CREATE TABLE product_to_rxnorm_staging (
  label_id text,
  rxnorm_product_id text
);
PSQL

PGUSER=$PGUSER PGDATABASE=$PGDATABASE PGPORT=$PGPORT psql -v ON_ERROR_STOP=1 -c "\copy onsides.product_to_rxnorm_staging FROM '$CSV_FILE' WITH (FORMAT csv, HEADER true)"

psql -v ON_ERROR_STOP=1 -d "$PGDATABASE" -p "$PGPORT" -U "$PGUSER" <<'PSQL'
SET search_path TO onsides, public;
SELECT 'staged_count', COUNT(*) FROM product_to_rxnorm_staging;

INSERT INTO product_to_rxnorm (label_id, rxnorm_product_id)
SELECT
  (s.label_id)::int,
  s.rxnorm_product_id
FROM product_to_rxnorm_staging s
WHERE NOT EXISTS (
  SELECT 1 FROM product_to_rxnorm p
  WHERE p.label_id = (s.label_id)::int AND p.rxnorm_product_id = s.rxnorm_product_id
)
  AND (
    s.label_id IS NULL OR s.label_id = '' OR EXISTS (SELECT 1 FROM product_label pl WHERE pl.label_id = (s.label_id)::int)
  )
  AND (
    s.rxnorm_product_id IS NULL OR s.rxnorm_product_id = '' OR EXISTS (SELECT 1 FROM vocab_rxnorm_product v WHERE v.rxnorm_id = s.rxnorm_product_id)
  );

SELECT 'target_count', COUNT(*) FROM product_to_rxnorm;
SELECT 'staged_unmatched_count', COUNT(*) FROM product_to_rxnorm_staging s LEFT JOIN product_to_rxnorm p ON p.label_id = (s.label_id)::int AND p.rxnorm_product_id = s.rxnorm_product_id WHERE p.label_id IS NULL;
PSQL

echo "Done." 
