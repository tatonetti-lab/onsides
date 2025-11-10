-- Ensure schema and log table exist
CREATE SCHEMA IF NOT EXISTS onsides;

CREATE TABLE IF NOT EXISTS onsides.z_qa_faers_wc_import_log (
    log_filename varchar(255) NOT NULL,
    filename varchar(255) NOT NULL,
  onsides_release_version varchar(32) NOT NULL,
    yr int4 NOT NULL,
    qtr int4 NOT NULL,
    wc_l_count int4 NOT NULL,
    loaded_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
    select_count_on_domain int4 NULL,
    select_count_diff int4 NULL,
    select_count_diff_pct float8 NULL,
    execution_id int4 NULL,
  csv_record_count int4 NULL,
  csv_count_diff int4 NULL,
  csv_count_diff_pct float8 NULL
);

-- Optional index to speed review by year/quarter
CREATE INDEX IF NOT EXISTS z_qa_faers_wc_import_log_yq_idx
  ON onsides.z_qa_faers_wc_import_log (yr, qtr);

-- Ensure new CSV-aware columns exist when table was created previously
ALTER TABLE onsides.z_qa_faers_wc_import_log
  ADD COLUMN IF NOT EXISTS csv_record_count int4;
ALTER TABLE onsides.z_qa_faers_wc_import_log
  ADD COLUMN IF NOT EXISTS csv_count_diff int4;
ALTER TABLE onsides.z_qa_faers_wc_import_log
  ADD COLUMN IF NOT EXISTS csv_count_diff_pct float8;

-- Remove deprecated awk-based column if present
ALTER TABLE onsides.z_qa_faers_wc_import_log
  DROP COLUMN IF EXISTS awk_nl_count;
