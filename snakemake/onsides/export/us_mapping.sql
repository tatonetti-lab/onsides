CREATE TABLE IF NOT EXISTS mrconso AS
SELECT
    * EXCLUDE('column18')
FROM
    read_csv(
        'data/mrconso.rrf',
        delim = '|',
        header = false,
        quote = '',
        NAMES = ['CUI', 'LAT', 'TS', 'LUI', 'STT', 'SUI', 'ISPREF', 'AUI', 'SAUI',
          'SCUI', 'SDUI', 'SAB', 'TTY', 'CODE', 'STR', 'SRL', 'SUPPRESS', 'CVF']
    );

CREATE TABLE us_final AS WITH us_preds AS (
    SELECT
        split_part(text_id, '.', 1) AS setid,
        split_part(text_id, '.', 3) AS spl_version,
        split_part(text_id, '.', 4) AS label_section,
        term_id,
        pred0,
        pred1
    FROM
        '_onsides/combined/label_english_preds.parquet'
    WHERE
        ends_with(text_id, 'US')
),
us_map AS (
    SELECT
        setid,
        spl_version,
        rxcui
    FROM
        read_csv(
            '_onsides/us/map_download/rxnorm_mappings.txt',
            sep = '|'
        )
),
us_name AS (
    SELECT
        setid,
        spl_version,
        title AS source_product_name
    FROM
        read_csv(
            '_onsides/us/map_download/dm_spl_zip_files_meta_data.txt',
            sep = '|'
        )
    WHERE
        title != 'NOT A DRUG LABEL'
)
SELECT
    *,
    setid || '.' || spl_version AS source_product_id
FROM
    us_preds
    INNER JOIN us_map USING (setid, spl_version)
    INNER JOIN us_name USING (setid, spl_version);

-- Export tables
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
    ) WITH us_inner AS (
        SELECT
            DISTINCT setid,
            source_product_id,
            source_product_name
        FROM
            us_final
    )
SELECT
    'US' AS source,
    source_product_name,
    source_product_id,
    'https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?' || setid AS source_label_url
FROM
    us_inner;

-- Product to RxNorm
INSERT INTO
    db.product_to_rxnorm (label_id, rxnorm_product_id) WITH new_labels AS (
        SELECT
            label_id,
            source_product_id
        FROM
            db.product_label
        WHERE
            source = 'US'
    )
SELECT
    DISTINCT label_id,
    RXCUI AS rxnorm_product_id
FROM
    new_labels
    INNER JOIN us_final USING (source_product_id);

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
            source = 'US'
    )
SELECT
    label_id AS product_label_id,
    label_section,
    term_id AS effect_meddra_id,
    'PMB' AS match_method,
    pred0,
    pred1
FROM
    new_labels
    INNER JOIN us_final USING (source_product_id);
