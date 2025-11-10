#!/usr/bin/env bash
set -euo pipefail

# Create placeholder entries in vocab_rxnorm_product for rxnorm ids present in
# product_to_rxnorm_staging but missing from vocab_rxnorm_product, then
# attempt reinserting product_to_rxnorm rows from staging.

PGUSER=${PGUSER:-postgres}
PGDATABASE=${PGDATABASE:-cem_development_2025}
PGPORT=${PGPORT:-5433}

echo "Patching missing vocab_rxnorm_product entries from product_to_rxnorm_staging"

psql -v ON_ERROR_STOP=1 -d "$PGDATABASE" -p "$PGPORT" -U "$PGUSER" <<'PSQL'
SET search_path TO onsides, public;

-- Insert placeholder vocab entries for any rxnorm ids referenced in staging but not present
INSERT INTO vocab_rxnorm_product (rxnorm_id, rxnorm_name, rxnorm_term_type)
SELECT DISTINCT s.rxnorm_product_id::text, '[placeholder]', NULL
FROM product_to_rxnorm_staging s
LEFT JOIN vocab_rxnorm_product v ON v.rxnorm_id = s.rxnorm_product_id::text
WHERE v.rxnorm_id IS NULL AND trim(s.rxnorm_product_id) <> '';

-- Report how many placeholders inserted
SELECT 'placeholders_inserted', COUNT(*) FROM vocab_rxnorm_product WHERE rxnorm_name = '[placeholder]';

-- Try inserting product_to_rxnorm missing rows (again)
INSERT INTO product_to_rxnorm (label_id, rxnorm_product_id)
SELECT (s.label_id)::int, s.rxnorm_product_id
FROM product_to_rxnorm_staging s
WHERE NOT EXISTS (
  SELECT 1 FROM product_to_rxnorm p
  WHERE p.label_id = (s.label_id)::int AND p.rxnorm_product_id = s.rxnorm_product_id
);

SELECT 'target_count_after', COUNT(*) FROM product_to_rxnorm;
PSQL

echo "Done patching vocab_rxnorm_product and reinserting product_to_rxnorm." 
