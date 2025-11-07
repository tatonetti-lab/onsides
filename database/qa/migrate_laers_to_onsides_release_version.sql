-- Idempotent migration: rename laers_or_faers -> onsides_release_version
SET search_path TO onsides, public;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'onsides'
      AND table_name = 'z_qa_faers_wc_import_log'
      AND column_name = 'laers_or_faers'
  ) THEN
    RAISE NOTICE 'Renaming column laers_or_faers -> onsides_release_version';
    EXECUTE 'ALTER TABLE onsides.z_qa_faers_wc_import_log RENAME COLUMN laers_or_faers TO onsides_release_version';
  ELSE
    RAISE NOTICE 'Column laers_or_faers not present, skipping';
  END IF;
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Migration error: %', SQLERRM;
END $$;
