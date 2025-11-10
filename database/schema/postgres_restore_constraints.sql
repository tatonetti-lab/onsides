SET search_path TO onsides, public;

-- vocab_meddra_adverse_effect
ALTER TABLE vocab_meddra_adverse_effect ADD CONSTRAINT vocab_meddra_adverse_effect_pkey PRIMARY KEY (meddra_id);

-- vocab_rxnorm_ingredient
ALTER TABLE vocab_rxnorm_ingredient ADD CONSTRAINT vocab_rxnorm_ingredient_pkey PRIMARY KEY (rxnorm_id);

-- vocab_rxnorm_product
ALTER TABLE vocab_rxnorm_product ADD CONSTRAINT vocab_rxnorm_product_pkey PRIMARY KEY (rxnorm_id);

-- product_adverse_effect
ALTER TABLE product_adverse_effect ADD CONSTRAINT product_adverse_effect_pkey PRIMARY KEY (effect_id);
ALTER TABLE product_adverse_effect ADD CONSTRAINT product_adverse_effect_product_label_id_fkey FOREIGN KEY (product_label_id) REFERENCES product_label(label_id);
ALTER TABLE product_adverse_effect ADD CONSTRAINT product_adverse_effect_effect_meddra_id_fkey FOREIGN KEY (effect_meddra_id) REFERENCES vocab_meddra_adverse_effect(meddra_id);

-- product_to_rxnorm
ALTER TABLE product_to_rxnorm ADD CONSTRAINT product_to_rxnorm_pkey PRIMARY KEY (label_id, rxnorm_product_id);
ALTER TABLE product_to_rxnorm ADD CONSTRAINT product_to_rxnorm_label_id_fkey FOREIGN KEY (label_id) REFERENCES product_label(label_id);
ALTER TABLE product_to_rxnorm ADD CONSTRAINT product_to_rxnorm_rxnorm_product_id_fkey FOREIGN KEY (rxnorm_product_id) REFERENCES vocab_rxnorm_product(rxnorm_id);

-- vocab_rxnorm_ingredient_to_product
ALTER TABLE vocab_rxnorm_ingredient_to_product ADD CONSTRAINT vocab_rxnorm_ingredient_to_product_pkey PRIMARY KEY (ingredient_id, product_id);
ALTER TABLE vocab_rxnorm_ingredient_to_product ADD CONSTRAINT vocab_rxnorm_ingredient_to_product_ingredient_id_fkey FOREIGN KEY (ingredient_id) REFERENCES vocab_rxnorm_ingredient(rxnorm_id);
ALTER TABLE vocab_rxnorm_ingredient_to_product ADD CONSTRAINT vocab_rxnorm_ingredient_to_product_product_id_fkey FOREIGN KEY (product_id) REFERENCES vocab_rxnorm_product(rxnorm_id);
