-- Archive and delete orphan rows in cem_development_2025 (dry-run by default)
-- Usage (dry-run):
--   psql -p 5433 -d cem_development_2025 -v do_commit=false -f database/scripts/archive_and_delete_orphans_2025.sql
-- To actually commit changes (careful):
--   psql -p 5433 -d cem_development_2025 -v do_commit=true -f database/scripts/archive_and_delete_orphans_2025.sql

\set ON_ERROR_STOP on

SET search_path TO onsides, public;

-- Create archive tables (structure copied from original tables, plus metadata)
CREATE TABLE IF NOT EXISTS onsides.orphan_product_adverse_effect_archive (
  LIKE onsides.product_adverse_effect INCLUDING ALL,
  archived_at timestamptz DEFAULT now(),
  source_db text
);

CREATE TABLE IF NOT EXISTS onsides.orphan_product_to_rxnorm_archive (
  LIKE onsides.product_to_rxnorm INCLUDING ALL,
  archived_at timestamptz DEFAULT now(),
  source_db text
);

-- We'll run each archive/cleanup in a single transaction. Default behavior: DRY RUN (ROLLBACK) unless do_commit=true
BEGIN;

-- 1) Archive product_adverse_effect rows whose effect_meddra_id has no parent
INSERT INTO onsides.orphan_product_adverse_effect_archive
SELECT pae.*, now() AS archived_at, current_database() AS source_db
FROM onsides.product_adverse_effect pae
LEFT JOIN onsides.vocab_meddra_adverse_effect v ON pae.effect_meddra_id = v.meddra_id
WHERE v.meddra_id IS NULL;

-- Report how many would be archived and how many orphan rows remain (sanity check)
\echo 'ARCHIVE product_adverse_effect'
SELECT 'to_archive_count' AS label, COUNT(*) FROM onsides.orphan_product_adverse_effect_archive WHERE source_db = current_database();
SELECT 'current_orphan_count' AS label, COUNT(*) FROM onsides.product_adverse_effect pae LEFT JOIN onsides.vocab_meddra_adverse_effect v ON pae.effect_meddra_id = v.meddra_id WHERE v.meddra_id IS NULL;

-- 2) Archive product_to_rxnorm rows whose rxnorm_product_id has no parent
INSERT INTO onsides.orphan_product_to_rxnorm_archive
SELECT ptr.*, now() AS archived_at, current_database() AS source_db
FROM onsides.product_to_rxnorm ptr
LEFT JOIN onsides.vocab_rxnorm_product v ON ptr.rxnorm_product_id = v.rxnorm_id
WHERE v.rxnorm_id IS NULL;

\echo 'ARCHIVE product_to_rxnorm'
SELECT 'to_archive_count' AS label, COUNT(*) FROM onsides.orphan_product_to_rxnorm_archive WHERE source_db = current_database();
SELECT 'current_orphan_count' AS label, COUNT(*) FROM onsides.product_to_rxnorm ptr LEFT JOIN onsides.vocab_rxnorm_product v ON ptr.rxnorm_product_id = v.rxnorm_id WHERE v.rxnorm_id IS NULL;

-- At this point archive tables contain the orphan rows. Now delete from child tables if we're committing.
-- Note: deletions are safe (targeting only rows still orphaned at time of execution).

\echo 'Preparing to delete archived orphan rows (will only commit if do_commit=true)'

\if :do_commit
  -- Perform deletes and commit
  DELETE FROM onsides.product_adverse_effect pae
  WHERE NOT EXISTS (SELECT 1 FROM onsides.vocab_meddra_adverse_effect v WHERE v.meddra_id = pae.effect_meddra_id);

  SELECT 'deleted_product_adverse_effect' AS label, COUNT(*) FROM onsides.product_adverse_effect pae WHERE NOT EXISTS (SELECT 1 FROM onsides.vocab_meddra_adverse_effect v WHERE v.meddra_id = pae.effect_meddra_id);

  DELETE FROM onsides.product_to_rxnorm ptr
  WHERE NOT EXISTS (SELECT 1 FROM onsides.vocab_rxnorm_product v WHERE v.rxnorm_id = ptr.rxnorm_product_id);

  SELECT 'deleted_product_to_rxnorm' AS label, COUNT(*) FROM onsides.product_to_rxnorm ptr WHERE NOT EXISTS (SELECT 1 FROM onsides.vocab_rxnorm_product v WHERE v.rxnorm_id = ptr.rxnorm_product_id);

  COMMIT;
  \echo 'COMMITTED: orphan deletes applied.'
\else
  -- Dry run: rollback so no data is changed
  ROLLBACK;
  \echo 'DRY RUN complete: no changes committed. To apply deletions, re-run with -v do_commit=true.'
\endif

-- Summary notes (printed by client):
\echo 'Script finished.'
