-- Indexes for OnSIDES PostgreSQL schema-- Indexes for OnSIDES PostgreSQL schema

-- Safe to run repeatedly (IF NOT EXISTS)-- Safe to run repeatedly (IF NOT EXISTS)



SET search_path TO onsides, public;-- Ensure we target the onsides schema by default

SET search_path TO onsides, public;

-- product_adverse_effect

CREATE INDEX IF NOT EXISTS idx_pae_match_method ON product_adverse_effect (match_method);-- product_adverse_effect

CREATE INDEX IF NOT EXISTS idx_pae_label_section ON product_adverse_effect (label_section);-- Primary key already indexes effect_id; adding targeted indexes used in filters/joins

CREATE INDEX IF NOT EXISTS idx_pae_effect_meddra_id ON product_adverse_effect (effect_meddra_id);CREATE INDEX IF NOT EXISTS idx_pae_match_method ON product_adverse_effect (match_method);

CREATE INDEX IF NOT EXISTS idx_pae_product_label_id ON product_adverse_effect (product_label_id);CREATE INDEX IF NOT EXISTS idx_pae_label_section ON product_adverse_effect (label_section);

CREATE INDEX IF NOT EXISTS idx_pae_effect_meddra_id ON product_adverse_effect (effect_meddra_id);

-- product_labelCREATE INDEX IF NOT EXISTS idx_pae_product_label_id ON product_adverse_effect (product_label_id);

CREATE INDEX IF NOT EXISTS idx_pl_source ON product_label (source);

-- product_label

-- vocab_meddra_adverse_effectCREATE INDEX IF NOT EXISTS idx_pl_source ON product_label (source);

CREATE INDEX IF NOT EXISTS idx_vmae_name ON vocab_meddra_adverse_effect (meddra_name);

CREATE INDEX IF NOT EXISTS idx_vmae_term_type ON vocab_meddra_adverse_effect (meddra_term_type);-- vocab_meddra_adverse_effect

-- PK on meddra_id already exists; add name/type for lookups

-- vocab_rxnorm_ingredientCREATE INDEX IF NOT EXISTS idx_vmae_name ON vocab_meddra_adverse_effect (meddra_name);

CREATE INDEX IF NOT EXISTS idx_vri_name ON vocab_rxnorm_ingredient (rxnorm_name);CREATE INDEX IF NOT EXISTS idx_vmae_term_type ON vocab_meddra_adverse_effect (meddra_term_type);

CREATE INDEX IF NOT EXISTS idx_vri_term_type ON vocab_rxnorm_ingredient (rxnorm_term_type);

-- vocab_rxnorm_ingredient

-- vocab_rxnorm_product-- PK on rxnorm_id already exists; add name/type for lookups

CREATE INDEX IF NOT EXISTS idx_vrp_name ON vocab_rxnorm_product (rxnorm_name);CREATE INDEX IF NOT EXISTS idx_vri_name ON vocab_rxnorm_ingredient (rxnorm_name);

CREATE INDEX IF NOT EXISTS idx_vrp_term_type ON vocab_rxnorm_product (rxnorm_term_type);CREATE INDEX IF NOT EXISTS idx_vri_term_type ON vocab_rxnorm_ingredient (rxnorm_term_type);



-- vocab_rxnorm_ingredient_to_product-- vocab_rxnorm_product

CREATE INDEX IF NOT EXISTS idx_vrip_product_id ON vocab_rxnorm_ingredient_to_product (product_id);-- PK on rxnorm_id already exists; add name/type for lookups

CREATE INDEX IF NOT EXISTS idx_vrp_name ON vocab_rxnorm_product (rxnorm_name);
CREATE INDEX IF NOT EXISTS idx_vrp_term_type ON vocab_rxnorm_product (rxnorm_term_type);

-- vocab_rxnorm_ingredient_to_product
-- Composite PK (ingredient_id, product_id) supports ingredient->products lookups.
-- Add reverse index to speed product->ingredients lookups.
CREATE INDEX IF NOT EXISTS idx_vrip_product_id ON vocab_rxnorm_ingredient_to_product (product_id);
