CREATE TABLE uk_preds AS
SELECT
    text_id AS effect_meddra_id,
    split_part(text_id, '.', 1) AS source_product_id,
    term_id,
    pred0,
    pred1
FROM
    '_onsides/combined/label_english_preds.parquet'
WHERE
    ends_with(text_id, 'UK');

CREATE TABLE uk_meta AS
SELECT
    name AS source_product_name,
    code AS source_product_id,
    page_url AS source_label_url
FROM
    '_onsides/uk/label_text.parquet';

CREATE TABLE uk_rxnorm AS
SELECT
    code AS source_product_id,
    rxcui AS rxnorm_product_id
FROM
    '_onsides/uk/labels_to_rxnorm.parquet';

CREATE TABLE uk_final AS
SELECT
    source_product_name,
    source_product_id,
    source_label_url,
    term_id,
    rxnorm_product_id,
    pred0,
    pred1
FROM
    uk_preds
    INNER JOIN uk_meta USING (source_product_id)
    INNER JOIN uk_rxnorm USING (source_product_id);

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
    ) WITH uk_inner AS (
        SELECT
            DISTINCT source_product_name,
            source_product_id,
            source_label_url
        FROM
            uk_final
    )
SELECT
    'UK' AS source,
    source_product_name,
    source_product_id,
    source_label_url
FROM
    uk_inner;

-- Product to RxNorm
INSERT INTO
    db.product_to_rxnorm (label_id, rxnorm_product_id) WITH new_labels AS (
        SELECT
            label_id,
            source_product_id
        FROM
            db.product_label
        WHERE
            source = 'UK'
    ),
    joined_labels AS (
        SELECT
            DISTINCT label_id,
            rxnorm_product_id
        FROM
            new_labels
            INNER JOIN uk_final USING (source_product_id)
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
            source = 'UK'
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
    INNER JOIN uk_final USING (source_product_id);
