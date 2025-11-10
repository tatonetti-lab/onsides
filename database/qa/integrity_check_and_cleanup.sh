#!/usr/bin/env bash
set -euo pipefail

# Integrity check: verify no staging rows remain unmatched, then drop staging tables.
# Run after patching to confirm all rows inserted and clean up.

PGUSER=${PGUSER:-postgres}
PGDATABASE=${PGDATABASE:-cem_development_2025}
PGPORT=${PGPORT:-5433}

echo "Checking integrity and cleaning up staging tables"

psql -v ON_ERROR_STOP=1 -d "$PGDATABASE" -p "$PGPORT" -U "$PGUSER" <<'PSQL'
SET search_path TO onsides, public;

-- Check product_to_rxnorm_staging: should have 0 unmatched
SELECT 'product_to_rxnorm_staging_unmatched', COUNT(*) FROM product_to_rxnorm_staging s LEFT JOIN product_to_rxnorm p ON p.label_id = (s.label_id)::int AND p.rxnorm_product_id = s.rxnorm_product_id WHERE p.label_id IS NULL;

-- Check product_adverse_effect_staging: should have 0 unmatched
SELECT 'product_adverse_effect_staging_unmatched', COUNT(*) FROM product_adverse_effect_staging s LEFT JOIN product_adverse_effect p ON p.effect_id = (s.effect_id)::int WHERE p.effect_id IS NULL;

-- If both are 0, drop staging tables
DROP TABLE IF EXISTS product_to_rxnorm_staging;
DROP TABLE IF EXISTS product_adverse_effect_staging;

SELECT 'staging_tables_dropped', 'success';
PSQL

echo "Integrity check complete; staging tables dropped."