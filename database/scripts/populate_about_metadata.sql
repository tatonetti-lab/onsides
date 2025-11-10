-- Populate the _about.about table with metadata for OnSIDES tables
-- Run after data loads to log table statistics

-- Insert row counts for each table
INSERT INTO "_about".about ("schema", "table", attribute, value, "timestamp")
SELECT 'onsides', 'product_label', 'row_count', COUNT(*)::text, CURRENT_TIMESTAMP
FROM onsides.product_label;

INSERT INTO "_about".about ("schema", "table", attribute, value, "timestamp")
SELECT 'onsides', 'product_adverse_effect', 'row_count', COUNT(*)::text, CURRENT_TIMESTAMP
FROM onsides.product_adverse_effect;

INSERT INTO "_about".about ("schema", "table", attribute, value, "timestamp")
SELECT 'onsides', 'vocab_meddra_adverse_effect', 'row_count', COUNT(*)::text, CURRENT_TIMESTAMP
FROM onsides.vocab_meddra_adverse_effect
WHERE is_placeholder IS NOT TRUE;

INSERT INTO "_about".about ("schema", "table", attribute, value, "timestamp")
SELECT 'onsides', 'vocab_rxnorm_product', 'row_count', COUNT(*)::text, CURRENT_TIMESTAMP
FROM onsides.vocab_rxnorm_product
WHERE is_placeholder IS NOT TRUE;

INSERT INTO "_about".about ("schema", "table", attribute, value, "timestamp")
SELECT 'onsides', 'product_to_rxnorm', 'row_count', COUNT(*)::text, CURRENT_TIMESTAMP
FROM onsides.product_to_rxnorm;

INSERT INTO "_about".about ("schema", "table", attribute, value, "timestamp")
SELECT 'onsides', 'vocab_rxnorm_ingredient', 'row_count', COUNT(*)::text, CURRENT_TIMESTAMP
FROM onsides.vocab_rxnorm_ingredient;

INSERT INTO "_about".about ("schema", "table", attribute, value, "timestamp")
SELECT 'onsides', 'vocab_rxnorm_ingredient_to_product', 'row_count', COUNT(*)::text, CURRENT_TIMESTAMP
FROM onsides.vocab_rxnorm_ingredient_to_product;

INSERT INTO "_about".about ("schema", "table", attribute, value, "timestamp")
SELECT 'onsides', 'high_confidence', 'row_count', COUNT(*)::text, CURRENT_TIMESTAMP
FROM onsides.high_confidence;

-- Insert version info from onsides.about
INSERT INTO "_about".about ("schema", "table", attribute, value, "timestamp")
SELECT 'onsides', 'about', 'version', version, CURRENT_TIMESTAMP
FROM onsides.about;

INSERT INTO "_about".about ("schema", "table", attribute, value, "timestamp")
SELECT 'onsides', 'about', 'data_sources', data_sources, CURRENT_TIMESTAMP
FROM onsides.about;