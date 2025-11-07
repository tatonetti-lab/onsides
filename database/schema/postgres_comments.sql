-- Column comments for OnSIDES PostgreSQL schema
-- Safe to run repeatedly; COMMENT ON is idempotent.

SET search_path TO onsides, public;

-- Table-level comments
COMMENT ON TABLE product_label IS 'Individual drug product labels from four sources (US, UK, EU, JP).';
COMMENT ON TABLE product_adverse_effect IS 'Extracted adverse effects linked to product labels with MedDRA mapping and model scores.';
COMMENT ON TABLE product_to_rxnorm IS 'Mapping from product_label to RxNorm products (many-to-many).';
COMMENT ON TABLE vocab_meddra_adverse_effect IS 'MedDRA adverse effect vocabulary (IDs, names, term types).';
COMMENT ON TABLE vocab_rxnorm_product IS 'RxNorm product vocabulary (IDs, names, term types).';
COMMENT ON TABLE vocab_rxnorm_ingredient IS 'RxNorm ingredient vocabulary (IDs, names, term types).';
COMMENT ON TABLE vocab_rxnorm_ingredient_to_product IS 'Mapping from RxNorm products to RxNorm ingredients (many-to-many).';
COMMENT ON TABLE z_qa_faers_wc_import_log IS 'QA log of file vs database counts, including CSV-aware record counts.';

-- product_label
COMMENT ON COLUMN product_label.label_id IS 'Surrogate primary key for a drug product label.';
COMMENT ON COLUMN product_label.source IS 'Source region of the label: US, UK, EU, or JP.';
COMMENT ON COLUMN product_label.source_product_name IS 'Product name as reported by the source authority.';
COMMENT ON COLUMN product_label.source_product_id IS 'Source-specific product identifier.';
COMMENT ON COLUMN product_label.source_label_url IS 'URL to the product label at the source site (when available).';

-- vocab_meddra_adverse_effect
COMMENT ON COLUMN vocab_meddra_adverse_effect.meddra_id IS 'MedDRA concept identifier (e.g., a Preferred Term ID).';
COMMENT ON COLUMN vocab_meddra_adverse_effect.meddra_name IS 'MedDRA concept name (e.g., Preferred Term).';
COMMENT ON COLUMN vocab_meddra_adverse_effect.meddra_term_type IS 'MedDRA term type (e.g., PT, LLT).';

-- vocab_rxnorm_ingredient
COMMENT ON COLUMN vocab_rxnorm_ingredient.rxnorm_id IS 'RxNorm ingredient concept identifier (e.g., IN/PIN).';
COMMENT ON COLUMN vocab_rxnorm_ingredient.rxnorm_name IS 'RxNorm ingredient name.';
COMMENT ON COLUMN vocab_rxnorm_ingredient.rxnorm_term_type IS 'RxNorm term type (TTY), e.g., IN, PIN.';

-- vocab_rxnorm_product
COMMENT ON COLUMN vocab_rxnorm_product.rxnorm_id IS 'RxNorm product concept identifier (e.g., SCD/SBD).';
COMMENT ON COLUMN vocab_rxnorm_product.rxnorm_name IS 'RxNorm product name.';
COMMENT ON COLUMN vocab_rxnorm_product.rxnorm_term_type IS 'RxNorm term type (TTY), e.g., SCD, SBD.';

-- product_adverse_effect
COMMENT ON COLUMN product_adverse_effect.product_label_id IS 'FK to product_label.label_id for the product whose label contains the effect.';
COMMENT ON COLUMN product_adverse_effect.effect_id IS 'Surrogate primary key for a product adverse effect row.';
COMMENT ON COLUMN product_adverse_effect.label_section IS 'Label section where the effect was found: AE (Adverse Reactions), WP (Warnings and Precautions), BW (Boxed Warning), or NA.';
COMMENT ON COLUMN product_adverse_effect.effect_meddra_id IS 'FK to vocab_meddra_adverse_effect.meddra_id for the mapped MedDRA concept.';
COMMENT ON COLUMN product_adverse_effect.match_method IS 'Extraction method: SM (string match) or PMB (model-scored).';
COMMENT ON COLUMN product_adverse_effect.pred0 IS 'Model score/confidence for the non-ADE class (if available).';
COMMENT ON COLUMN product_adverse_effect.pred1 IS 'Model score/confidence for ADE (higher indicates more likely, used for thresholding).';

-- product_to_rxnorm
COMMENT ON COLUMN product_to_rxnorm.label_id IS 'FK to product_label.label_id for the product label.';
COMMENT ON COLUMN product_to_rxnorm.rxnorm_product_id IS 'FK to vocab_rxnorm_product.rxnorm_id for the mapped RxNorm product.';

-- vocab_rxnorm_ingredient_to_product
COMMENT ON COLUMN vocab_rxnorm_ingredient_to_product.ingredient_id IS 'FK to vocab_rxnorm_ingredient.rxnorm_id (ingredient).';
COMMENT ON COLUMN vocab_rxnorm_ingredient_to_product.product_id IS 'FK to vocab_rxnorm_product.rxnorm_id (product).';

-- QA log
COMMENT ON COLUMN z_qa_faers_wc_import_log.log_filename IS 'Basename of the source file.';
COMMENT ON COLUMN z_qa_faers_wc_import_log.filename IS 'Full path to the source file at logging time.';
COMMENT ON COLUMN z_qa_faers_wc_import_log.onsides_release_version IS 'OnSIDES release tag or short dataset tag (e.g., v3.1.0, FAERS, LAERS).';
COMMENT ON COLUMN z_qa_faers_wc_import_log.yr IS 'Dataset year (YY or YYYY).';
COMMENT ON COLUMN z_qa_faers_wc_import_log.qtr IS 'Dataset quarter (1–4).';
COMMENT ON COLUMN z_qa_faers_wc_import_log.wc_l_count IS 'Physical line count from wc -l (includes header; not CSV-aware).';
COMMENT ON COLUMN z_qa_faers_wc_import_log.loaded_at IS 'Timestamp when the log row was inserted.';
COMMENT ON COLUMN z_qa_faers_wc_import_log.select_count_on_domain IS 'SELECT COUNT(*) from the target domain table at logging time.';
COMMENT ON COLUMN z_qa_faers_wc_import_log.select_count_diff IS 'Difference: select_count_on_domain - wc_l_count.';
COMMENT ON COLUMN z_qa_faers_wc_import_log.select_count_diff_pct IS 'Relative difference vs wc_l_count.';
COMMENT ON COLUMN z_qa_faers_wc_import_log.execution_id IS 'Optional execution identifier for grouping logs.';
COMMENT ON COLUMN z_qa_faers_wc_import_log.csv_record_count IS 'CSV-aware logical record count (header skipped; embedded newlines handled).';
COMMENT ON COLUMN z_qa_faers_wc_import_log.csv_count_diff IS 'Difference: select_count_on_domain - csv_record_count.';
COMMENT ON COLUMN z_qa_faers_wc_import_log.csv_count_diff_pct IS 'Relative difference vs csv_record_count.';
