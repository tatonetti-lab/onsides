-- # These queries modified for postgres

-- Set the schema for all following tables
SET search_path TO 

CREATE TABLE adverse_reactions (
  ingredients_rxcuis text NULL,
  ingredients_names text NULL,
  num_ingredients int4 NULL,
  pt_meddra_id int4 NULL,
  pt_meddra_term varchar(255) NULL,
  percent_labels float8 NULL,
  num_labels int4 NULL
);

CREATE INDEX adverse_reactions_ingredients_rxcuis_idx ON adverse_reactions USING btree (ingredients_rxcuis);
CREATE INDEX adverse_reactions_pt_meddra_id_idx ON adverse_reactions USING btree (pt_meddra_id);

CREATE TABLE boxed_warnings (
  ingredients_rxcuis text NULL,
  ingredients_names text NULL,
  num_ingredients int4 NULL,
  pt_meddra_id int4 NULL,
  pt_meddra_term text NULL,
  percent_labels float8 NULL,
  num_labels int4 NULL
);
CREATE INDEX boxed_warnings_ingredients_rxcuis_idx ON boxed_warnings USING btree (ingredients_rxcuis);
CREATE INDEX boxed_warnings_pt_meddra_id_idx ON boxed_warnings USING btree (pt_meddra_id);
CREATE TABLE adverse_reactions_all_labels (
  "section" varchar(2) NULL,
  zip_id text NULL,
  label_id text NULL,
  set_id text NULL,
  spl_version int4 NULL,
  pt_meddra_id int4 NULL,
  pt_meddra_term text NULL,
  pred0 float8 NULL,
  pred1 float8 NULL
);

CREATE INDEX adverse_reactions_all_labels_zip_id_idx ON adverse_reactions_all_labels USING btree (zip_id);
CREATE INDEX adverse_reactions_all_labels_label_id_idx ON adverse_reactions_all_labels USING btree (label_id);
CREATE INDEX adverse_reactions_all_labels_set_id_idx ON adverse_reactions_all_labels USING btree (set_id);
CREATE INDEX adverse_reactions_all_labels_spl_version_idx ON adverse_reactions_all_labels USING btree (spl_version);
CREATE INDEX adverse_reactions_all_labels_pt_meddra_id_idx ON adverse_reactions_all_labels USING btree (pt_meddra_id);

CREATE TABLE boxed_warnings_all_labels (
  "section" varchar(2) NULL,
  zip_id text NULL,
  label_id varchar(36) NULL,
  set_id text NULL,
  spl_version int4 NULL,
  pt_meddra_id int4 NULL,
  pt_meddra_term text NULL,
  pred0 float8 NULL,
  pred1 float8 NULL
);
CREATE INDEX boxed_warnings_all_labels_zip_id_idx ON boxed_warnings_all_labels USING btree (zip_id);
CREATE INDEX boxed_warnings_all_labels_label_id_idx ON boxed_warnings_all_labels USING btree (label_id);
CREATE INDEX boxed_warnings_all_labels_set_id_idx ON boxed_warnings_all_labels USING btree (set_id);
CREATE INDEX boxed_warnings_all_labels_spl_version_idx ON boxed_warnings_all_labels USING btree (spl_version);
CREATE INDEX boxed_warnings_all_labels_pt_meddra_id_idx ON boxed_warnings_all_labels USING btree (pt_meddra_id);

CREATE TABLE adverse_reactions_active_labels (
  set_id varchar(36) NULL,
  spl_version int4 NULL,
  pt_meddra_id int4 NULL,
  pt_meddra_term text NULL,
  num_ingredients int4 NULL,
  ingredients_rxcuis text NULL,
  ingredients_names text NULL
);

CREATE INDEX adverse_reactions_active_labels_set_id_idx ON adverse_reactions_active_labels USING btree (set_id);
CREATE INDEX adverse_reactions_active_labels_spl_version_idx ON adverse_reactions_active_labels USING btree (spl_version);
CREATE INDEX adverse_reactions_active_labels_pt_meddra_id_idx ON adverse_reactions_active_labels USING btree (pt_meddra_id);

CREATE TABLE boxed_warnings_active_labels (
  set_id varchar(36) NULL,
  spl_version int4 NULL,
  pt_meddra_id int4 NULL,
  pt_meddra_term text NULL,
  num_ingredients int4 NULL,
  ingredients_rxcuis text NULL,
  ingredients_names text NULL
);
CREATE INDEX boxed_warnings_active_labels_set_id_idx ON boxed_warnings_active_labels USING btree (set_id);
CREATE INDEX boxed_warnings_active_labels_spl_version_idx ON boxed_warnings_active_labels USING btree (spl_version);
CREATE INDEX boxed_warnings_active_labels_pt_meddra_id_idx ON boxed_warnings_active_labels USING btree (pt_meddra_id);

CREATE TABLE rxnorm_mappings (
  setid text NULL,
  spl_version int4 NULL,
  rxcui int4 NULL,
  rxstring text NULL,
  rxtty varchar(4) NULL
);

CREATE INDEX rxnorm_mappings_setid_idx ON rxnorm_mappings USING btree (setid);
CREATE INDEX rxnorm_mappings_rxcui_idx ON rxnorm_mappings USING btree (rxcui);
CREATE INDEX rxnorm_mappings_rxtty_idx ON rxnorm_mappings USING btree (rxtty);

CREATE TABLE dm_spl_zip_files_meta_data (
  setid varchar(37) NULL,
  zip_file_name varchar(50) NULL,
  upload_date date NULL,
  spl_version int4 NULL,
  title text NULL
);

CREATE INDEX dm_spl_zip_files_meta_data_setid_idx ON dm_spl_zip_files_meta_data USING btree (setid);

CREATE TABLE rxcui_setid_map (
  setid text NULL,
  rxcui int4 NULL
);

CREATE INDEX rxcui_setid_map_setid_idx ON rxcui_setid_map USING btree (setid);
CREATE INDEX rxcui_setid_map_rxcui_idx ON rxcui_setid_map USING btree (rxcui);

CREATE TABLE rxnorm_product_to_ingredient (
  product_rx_cui int4 NULL,
  product_name varchar(255) NULL,
  product_omop_concept_id int4 NULL,
  ingredient_rx_cui int4 NULL,
  ingredient_name text NULL,
  ingredient_omop_concept_id int4 NULL
);

CREATE INDEX rxnorm_product_to_ingredient_product_rx_cui_idx ON rxnorm_product_to_ingredient USING btree (product_rx_cui);
CREATE INDEX rxnorm_product_to_ingredient_product_omop_concept_id_idx ON rxnorm_product_to_ingredient USING btree (product_omop_concept_id);
CREATE INDEX rxnorm_product_to_ingredient_ingredient_rx_cui_idx ON rxnorm_product_to_ingredient USING btree (ingredient_rx_cui);
CREATE INDEX rxnorm_product_to_ingredient_ingredient_omop_concept_id_idx ON rxnorm_product_to_ingredient USING btree (ingredient_omop_concept_id);

CREATE TABLE ingredients (
  set_id text NULL,
  ingredient_rx_cui int4 NULL,
  ingredient_name text NULL,
  ingredient_omop_concept_id int4 NULL
);

CREATE INDEX ingredients_set_id_idx ON ingredients USING btree (set_id);
CREATE INDEX ingredients_ingredient_rx_cui_idx ON ingredients USING btree (ingredient_rx_cui);
CREATE INDEX ingredients_ingredient_omop_concept_id_idx ON ingredients USING btree (ingredient_omop_concept_id);
