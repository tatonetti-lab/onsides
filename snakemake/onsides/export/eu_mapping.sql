CREATE TABLE eu_preds AS
SELECT
    text_id AS effect_meddra_id,
    split_part(text_id, '.', 1) AS source_product_id,
    term_id,
    pred0,
    pred1
FROM
    '_onsides/combined/label_english_preds.parquet'
WHERE
    ends_with(text_id, 'EU');

CREATE TABLE eu_meta AS
SELECT
    name AS source_product_name,
    code AS source_product_id,
    page_url AS source_label_url
FROM
    '_onsides/eu/label_text.parquet';

CREATE TABLE eu_rxnorm AS
SELECT
    code AS source_product_id,
    rxcui AS rxnorm_product_id
FROM
    '_onsides/eu/labels_to_rxnorm.parquet';

CREATE TABLE eu_final AS
SELECT
    source_product_name,
    source_product_id,
    source_label_url,
    term_id,
    rxnorm_product_id,
    pred0,
    pred1
FROM
    eu_preds
    INNER JOIN eu_meta USING (source_product_id)
    INNER JOIN eu_rxnorm USING (source_product_id);

--------------------------------------------------------------------------------
--------------------------------------------------------------------------------
--------------------------------------------------------------------------------
INSTALL sqlite;

LOAD sqlite;

ATTACH IF NOT EXISTS 'database/onsides.db' AS db (TYPE sqlite);

-- Product label
INSERT INTO
    db.product_label (
        source,
        source_product_name,
        source_product_id,
        source_label_url
    ) WITH eu_inner AS (
        SELECT
            DISTINCT source_product_name,
            source_product_id,
            source_label_url
        FROM
            eu_final
    )
SELECT
    'EU' AS source,
    source_product_name,
    source_product_id,
    source_label_url
FROM
    eu_inner;

-- Product to RxNorm
INSERT INTO
    db.product_to_rxnorm (label_id, rxnorm_product_id) WITH new_labels AS (
        SELECT
            label_id,
            source_product_id
        FROM
            db.product_label
        WHERE
            source = 'EU'
    ),
    joined_labels AS (
        SELECT
            DISTINCT label_id,
            rxnorm_product_id
        FROM
            new_labels
            INNER JOIN eu_final USING (source_product_id)
    )
SELECT
    label_id,
    rxnorm_product_id
FROM
    joined_labels
WHERE
    rxnorm_product_id != '';

-- Adverse effect
INSERT INTO
    db.product_adverse_effect (
        product_label_id,
        label_section,
        effect_meddra_id,
        match_method,
        pred0,
        pred1
    ) WITH new_labels AS (
        SELECT
            label_id,
            source_product_id
        FROM
            db.product_label
        WHERE
            source = 'EU'
    )
SELECT
    label_id AS product_label_id,
    'NA' AS label_section,
    term_id AS effect_meddra_id,
    'PMB' AS match_method,
    pred0,
    pred1
FROM
    new_labels
    INNER JOIN eu_final USING (source_product_id);
