CREATE TABLE product_label (
    label_id INTEGER NOT NULL,
    source VARCHAR(2) NOT NULL,
    source_product_name VARCHAR NOT NULL,
    source_product_id VARCHAR NOT NULL,
    source_label_url VARCHAR,
    PRIMARY KEY (label_id)
);

CREATE TABLE vocab_meddra_adverse_effect (
    meddra_id INTEGER NOT NULL,
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
    effect_id INTEGER NOT NULL,
    label_section VARCHAR(2) NOT NULL,
    effect_meddra_id INTEGER,
    match_method VARCHAR(3) NOT NULL,
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
