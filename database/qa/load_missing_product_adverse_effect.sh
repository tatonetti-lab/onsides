#!/usr/bin/env bash
set -euo pipefail

# Load missing rows from product_adverse_effect.csv into onsides.product_adverse_effect
# Usage: ./load_missing_product_adverse_effect.sh /path/to/product_adverse_effect.csv

CSV_FILE=${1:-data/csv/product_adverse_effect.csv}
PGUSER=${PGUSER:-postgres}
PGDATABASE=${PGDATABASE:-cem_development_2025}
PGPORT=${PGPORT:-5433}

echo "Staging CSV: $CSV_FILE"

psql -v ON_ERROR_STOP=1 -d "$PGDATABASE" -p "$PGPORT" -U "$PGUSER" <<'PSQL'
SET search_path TO onsides, public;
DROP TABLE IF EXISTS product_adverse_effect_staging;
CREATE TABLE product_adverse_effect_staging (
  product_label_id text,
  effect_id text,
  label_section text,
  effect_meddra_id text,
  match_method text,
  pred0 text,
  pred1 text
);
PSQL

# copy using psql \copy for client-side file access
PGUSER=$PGUSER PGDATABASE=$PGDATABASE PGPORT=$PGPORT psql -v ON_ERROR_STOP=1 -c "\copy onsides.product_adverse_effect_staging FROM '$CSV_FILE' WITH (FORMAT csv, HEADER true)"

psql -v ON_ERROR_STOP=1 -d "$PGDATABASE" -p "$PGPORT" -U "$PGUSER" <<'PSQL'
SET search_path TO onsides, public;
-- Count staged rows
SELECT 'staged_count', COUNT(*) FROM product_adverse_effect_staging;

-- Insert only rows whose effect_id is missing and whose parents exist
INSERT INTO product_adverse_effect (product_label_id, effect_id, label_section, effect_meddra_id, match_method, pred0, pred1)
SELECT
  (CASE WHEN trim(s.product_label_id) = '' THEN NULL ELSE (s.product_label_id)::int END)::int,
  (s.effect_id)::int,
  s.label_section,
  (CASE WHEN trim(s.effect_meddra_id) = '' THEN NULL ELSE (s.effect_meddra_id)::int END),
  s.match_method,
  (CASE WHEN trim(s.pred0) = '' THEN NULL ELSE (s.pred0)::float END),
  (CASE WHEN trim(s.pred1) = '' THEN NULL ELSE (s.pred1)::float END)
FROM product_adverse_effect_staging s
WHERE NOT EXISTS (SELECT 1 FROM product_adverse_effect p WHERE p.effect_id = (s.effect_id)::int)
  AND (s.product_label_id IS NULL OR s.product_label_id = '' OR EXISTS (SELECT 1 FROM product_label pl WHERE pl.label_id = (s.product_label_id)::int))
  AND (s.effect_meddra_id IS NULL OR s.effect_meddra_id = '' OR EXISTS (SELECT 1 FROM vocab_meddra_adverse_effect v WHERE v.meddra_id = (s.effect_meddra_id)::int));

-- Report how many now in target and how many staged remain unmatched
SELECT 'target_count', COUNT(*) FROM product_adverse_effect;
SELECT 'staged_unmatched_count', COUNT(*) FROM product_adverse_effect_staging s LEFT JOIN product_adverse_effect p ON p.effect_id = (s.effect_id)::int WHERE p.effect_id IS NULL;
-- Update sequence for effect_id
SELECT setval(pg_get_serial_sequence('product_adverse_effect','effect_id'), COALESCE((SELECT max(effect_id) FROM product_adverse_effect),0));
PSQL

echo "Done." 
