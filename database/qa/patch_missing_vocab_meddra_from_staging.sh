#!/usr/bin/env bash
set -euo pipefail

# Create placeholder entries in vocab_meddra_adverse_effect for meddra ids present in
# product_adverse_effect_staging but missing from vocab_meddra_adverse_effect, then
# attempt reinserting product_adverse_effect rows from staging.

PGUSER=${PGUSER:-postgres}
PGDATABASE=${PGDATABASE:-cem_development_2025}
PGPORT=${PGPORT:-5433}

echo "Patching missing vocab_meddra_adverse_effect entries from product_adverse_effect_staging"

psql -v ON_ERROR_STOP=1 -d "$PGDATABASE" -p "$PGPORT" -U "$PGUSER" <<'PSQL'
SET search_path TO onsides, public;

-- Insert placeholder meddra vocab entries for any meddra ids referenced in staging but not present
INSERT INTO vocab_meddra_adverse_effect (meddra_id, meddra_name, meddra_term_type)
SELECT DISTINCT (s.effect_meddra_id)::int, '[placeholder]', NULL
FROM product_adverse_effect_staging s
LEFT JOIN vocab_meddra_adverse_effect v ON v.meddra_id = (s.effect_meddra_id)::int
WHERE v.meddra_id IS NULL AND trim(s.effect_meddra_id) <> '';

-- Report how many placeholders inserted
SELECT 'placeholders_inserted', COUNT(*) FROM vocab_meddra_adverse_effect WHERE meddra_name = '[placeholder]';

-- Try inserting product_adverse_effect missing rows (again) for which parents now exist
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
WHERE NOT EXISTS (SELECT 1 FROM product_adverse_effect p WHERE p.effect_id = (s.effect_id)::int);

-- Report final target count
SELECT 'target_count_after', COUNT(*) FROM product_adverse_effect;

-- Update sequence for effect_id
SELECT setval(pg_get_serial_sequence('product_adverse_effect','effect_id'), COALESCE((SELECT max(effect_id) FROM product_adverse_effect),0));
PSQL

echo "Done patching vocab_meddra_adverse_effect and reinserting product_adverse_effect." 
