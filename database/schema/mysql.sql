CREATE TABLE product_label (
    label_id INTEGER NOT NULL AUTO_INCREMENT,
    source ENUM('US', 'UK', 'EU', 'JP') NOT NULL,
    source_product_name VARCHAR(255) NOT NULL,
    source_product_id VARCHAR(255) NOT NULL,
    source_label_url VARCHAR(255),
    PRIMARY KEY (label_id)
);

CREATE TABLE vocab_meddra_adverse_effect (
    meddra_id INTEGER NOT NULL AUTO_INCREMENT,
    meddra_name VARCHAR(255) NOT NULL,
    meddra_term_type VARCHAR(255) NOT NULL,
    PRIMARY KEY (meddra_id)
);

CREATE TABLE vocab_rxnorm_ingredient (
    rxnorm_id VARCHAR(255) NOT NULL,
    rxnorm_name VARCHAR(255) NOT NULL,
    rxnorm_term_type VARCHAR(255) NOT NULL,
    PRIMARY KEY (rxnorm_id)
);

CREATE TABLE vocab_rxnorm_product (
    rxnorm_id VARCHAR(255) NOT NULL,
    rxnorm_name VARCHAR(255) NOT NULL,
    rxnorm_term_type VARCHAR(255) NOT NULL,
    PRIMARY KEY (rxnorm_id)
);

CREATE TABLE product_adverse_effect (
    product_label_id INTEGER,
    effect_id INTEGER NOT NULL AUTO_INCREMENT,
    label_section ENUM('AE', 'WP', 'BW', 'NA') NOT NULL,
    effect_meddra_id INTEGER,
    match_method ENUM('SM', 'PMB') NOT NULL,
    pred0 FLOAT,
    pred1 FLOAT,
    PRIMARY KEY (effect_id),
    FOREIGN KEY(product_label_id) REFERENCES product_label (label_id),
    FOREIGN KEY(effect_meddra_id) REFERENCES vocab_meddra_adverse_effect (meddra_id)
);

CREATE TABLE product_to_rxnorm (
    label_id INTEGER NOT NULL,
    rxnorm_product_id VARCHAR(255) NOT NULL,
    PRIMARY KEY (label_id, rxnorm_product_id),
    FOREIGN KEY(label_id) REFERENCES product_label (label_id),
    FOREIGN KEY(rxnorm_product_id) REFERENCES vocab_rxnorm_product (rxnorm_id)
);

CREATE TABLE vocab_rxnorm_ingredient_to_product (
    ingredient_id VARCHAR(255) NOT NULL,
    product_id VARCHAR(255) NOT NULL,
    PRIMARY KEY (ingredient_id, product_id),
    FOREIGN KEY(ingredient_id) REFERENCES vocab_rxnorm_ingredient (rxnorm_id),
    FOREIGN KEY(product_id) REFERENCES vocab_rxnorm_product (rxnorm_id)
);
