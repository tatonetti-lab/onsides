-- Populate or update the onsides.about table with metadata
-- Run after schema creation and data loads

INSERT INTO onsides.about (
    id,
    version,
    description,
    updated_at,
    data_sources,
    record_counts,
    notes
) VALUES (
    1,
    'v3.1.0',
    'OnSIDES: Comprehensive database of drugs and adverse events extracted from product labels using fine-tuned NLP models.',
    CURRENT_TIMESTAMP,
    'US (DailyMed), EU (EMA), UK (EMC), JP (KEGG)',
    jsonb_build_object(
        'product_label', (SELECT COUNT(*) FROM onsides.product_label),
        'product_adverse_effect', (SELECT COUNT(*) FROM onsides.product_adverse_effect),
        'vocab_meddra_adverse_effect', (SELECT COUNT(*) FROM onsides.vocab_meddra_adverse_effect WHERE is_placeholder IS NOT TRUE),
        'vocab_rxnorm_product', (SELECT COUNT(*) FROM onsides.vocab_rxnorm_product WHERE is_placeholder IS NOT TRUE),
        'product_to_rxnorm', (SELECT COUNT(*) FROM onsides.product_to_rxnorm),
        'vocab_rxnorm_ingredient', (SELECT COUNT(*) FROM onsides.vocab_rxnorm_ingredient),
        'vocab_rxnorm_ingredient_to_product', (SELECT COUNT(*) FROM onsides.vocab_rxnorm_ingredient_to_product),
        'high_confidence', (SELECT COUNT(*) FROM onsides.high_confidence)
    ),
    'Includes QA logs, restored constraints, and placeholder vocab entries for missing IDs. Data loaded from CSVs in data/csv/.'
)
ON CONFLICT (id) DO UPDATE SET
    version = EXCLUDED.version,
    description = EXCLUDED.description,
    updated_at = EXCLUDED.updated_at,
    data_sources = EXCLUDED.data_sources,
    record_counts = EXCLUDED.record_counts,
    notes = EXCLUDED.notes;
