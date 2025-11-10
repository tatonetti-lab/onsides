CREATE TABLE product_label (
    label_id SERIAL NOT NULL,
    source VARCHAR NOT NULL,
    source_product_name VARCHAR NOT NULL,
    source_product_id VARCHAR NOT NULL,
    source_label_url VARCHAR,
    PRIMARY KEY (label_id)
);

CREATE TABLE vocab_meddra_adverse_effect (
    meddra_id SERIAL NOT NULL,
    meddra_name VARCHAR NOT NULL,
    meddra_term_type VARCHAR NOT NULL,
    PRIMARY KEY (meddra_id)
);

CREATE TABLE vocab_rxnorm_ingredient (
    rxnorm_id VARCHAR NOT NULL,
    rxnorm_name VARCHAR NOT NULL,
    rxnorm_term_type VARCHAR NOT NULL,
    PRIMARY KEY (rxnorm_id)
);

CREATE TABLE vocab_rxnorm_product (
    rxnorm_id VARCHAR NOT NULL,
    rxnorm_name VARCHAR NOT NULL,
    rxnorm_term_type VARCHAR NOT NULL,
    PRIMARY KEY (rxnorm_id)
);

CREATE TABLE product_adverse_effect (
    product_label_id INTEGER,
    effect_id SERIAL NOT NULL,
    label_section VARCHAR NOT NULL,
    effect_meddra_id INTEGER,
    match_method VARCHAR NOT NULL,
    pred0 FLOAT,
    pred1 FLOAT,
    PRIMARY KEY (effect_id),
    FOREIGN KEY(product_label_id) REFERENCES product_label (label_id),
    FOREIGN KEY(effect_meddra_id) REFERENCES vocab_meddra_adverse_effect (meddra_id)
);

CREATE TABLE product_to_rxnorm (
    label_id INTEGER NOT NULL,
    rxnorm_product_id VARCHAR NOT NULL,
    PRIMARY KEY (label_id, rxnorm_product_id),
    FOREIGN KEY(label_id) REFERENCES product_label (label_id),
    FOREIGN KEY(rxnorm_product_id) REFERENCES vocab_rxnorm_product (rxnorm_id)
);

CREATE TABLE vocab_rxnorm_ingredient_to_product (
    ingredient_id VARCHAR NOT NULL,
    product_id VARCHAR NOT NULL,
    PRIMARY KEY (ingredient_id, product_id),
    FOREIGN KEY(ingredient_id) REFERENCES vocab_rxnorm_ingredient (rxnorm_id),
    FOREIGN KEY(product_id) REFERENCES vocab_rxnorm_product (rxnorm_id)
);

-- Metadata table for OnSIDES database instance
CREATE TABLE IF NOT EXISTS onsides.about (
    id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),  -- Single-row table
    version VARCHAR(50),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_sources TEXT,
    record_counts JSONB,
    notes TEXT
);

-- Add comment for documentation
COMMENT ON TABLE onsides.about IS 'Metadata table for the OnSIDES database, including version, sources, and key statistics.';
COMMENT ON COLUMN onsides.about.version IS 'Release version of the OnSIDES data (e.g., v3.1.0).';
COMMENT ON COLUMN onsides.about.description IS 'Brief description of the database contents.';
COMMENT ON COLUMN onsides.about.created_at IS 'Timestamp when the database was created.';
COMMENT ON COLUMN onsides.about.updated_at IS 'Timestamp of the last major update or data load.';
COMMENT ON COLUMN onsides.about.data_sources IS 'Comma-separated list of data sources (e.g., US, EU, UK, JP).';
COMMENT ON COLUMN onsides.about.record_counts IS 'JSON object with approximate row counts for key tables.';
COMMENT ON COLUMN onsides.about.notes IS 'Additional notes or context about the database instance.';
