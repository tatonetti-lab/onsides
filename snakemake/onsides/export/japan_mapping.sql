CREATE TABLE IF NOT EXISTS concept AS
SELECT
    *
FROM
    read_csv(
        'data/omop_vocab/CONCEPT.csv',
        sep = '\t',
        quote = ''
    );

CREATE TABLE IF NOT EXISTS concept_relationship AS
SELECT
    *
FROM
    read_csv(
        'data/omop_vocab/CONCEPT_RELATIONSHIP.csv',
        sep = '\t',
        quote = ''
    );

DROP TABLE IF EXISTS kegg_map;

CREATE TABLE kegg_map AS
WITH
raw_kegg AS (
    SELECT
        REPLACE(kegg_id, 'dr:', '') AS kegg_id,
        REPLACE(REPLACE(ndc_id, 'ndc:', ''), '-', '') AS ndc_id
    FROM
        read_csv(
            '_onsides/jp/kegg_drug_to_ndc.txt',
            sep = '\t',
            quote = '',
            header = false,
            NAMES = ['kegg_id', 'ndc_id']
        )
)
SELECT
    kegg_id,
    CASE
        WHEN length(ndc_id) == 8 THEN '0' || ndc_id
        ELSE ndc_id
    END AS ndc_id
FROM
    raw_kegg;

drop table if exists kegg_drug_to_rxnorm;

CREATE TABLE kegg_drug_to_rxnorm AS
SELECT
    kegg_id,
    c2.concept_code AS rxnorm_code
FROM
    kegg_map
    INNER JOIN concept c1 ON REPLACE(kegg_map.ndc_id, '-', '') = c1.concept_code
    INNER JOIN concept_relationship cr ON c1.concept_id = cr.concept_id_1
    INNER JOIN concept c2 ON cr.concept_id_2 = c2.concept_id
WHERE
    c1.vocabulary_id = 'NDC'
    AND c2.vocabulary_id IN ('RxNorm', 'RxNorm Extension')
    AND cr.relationship_id = 'Maps to';

drop table if exists jp_labels_meta;

CREATE TABLE jp_labels_meta AS
WITH
raw_meta AS (
    SELECT
        name,
        code,
        kegg_id,
        page_url
    FROM
        '_onsides/jp/combined_download_files.parquet'
)
SELECT
    name AS source_product_name,
    code AS source_product_id,
    kegg_id,
    page_url AS source_label_url,
    rxnorm_code AS rxnorm_id
FROM
    kegg_drug_to_rxnorm
    INNER JOIN raw_meta USING (kegg_id);

drop table if exists japan_final_full;

CREATE TABLE japan_final_full AS
WITH
raw_matches AS (
    SELECT
        split_part(text_id, '.', 1) AS japic_code,
        term_id
    FROM
        '_onsides/combined/label_japanese_string_match.parquet'
)
SELECT
    *
FROM
    raw_matches
    INNER JOIN jp_labels_meta ON japic_code = source_product_id;

-- Insert tables
INSTALL sqlite;

LOAD sqlite;

ATTACH IF NOT EXISTS 'data/onsides.db' AS db (TYPE sqlite);

INSERT INTO
    db.product_label (
        source,
        source_product_name,
        source_product_id,
        source_label_url
    )
with
jp_inner as (
    select distinct
        source_product_name,
        source_product_id,
        source_label_url
    from
        japan_final_full
)
SELECT
    'JP' AS source,
    source_product_name,
    source_product_id,
    source_label_url
FROM
    jp_inner;

INSERT INTO
    db.product_to_rxnorm (label_id, rxnorm_product_id)
WITH
new_labels AS (
    SELECT
        label_id,
        source_product_id
    FROM
        db.product_label
    WHERE
        source = 'JP'
)
SELECT DISTINCT
    label_id,
    rxnorm_id AS rxnorm_product_id
FROM
    new_labels
    INNER JOIN japan_final_full USING (source_product_id);

INSERT INTO
    db.product_adverse_effect (
        product_label_id,
        label_section,
        effect_meddra_id,
        match_method
    )
WITH
new_labels AS (
    SELECT
        label_id,
        source_product_id
    FROM
        db.product_label
    WHERE
        source = 'JP'
)
SELECT
    label_id AS product_label_id,
    'NA' AS label_section,
    term_id AS effect_meddra_id,
    'SM' AS match_method
FROM
    new_labels
    INNER JOIN japan_final_full USING (source_product_id);
