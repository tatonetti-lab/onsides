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

CREATE TABLE vocab_rxnorm AS WITH combined_rxnorm AS (
    SELECT
        code AS rxnorm_id,
        str AS rxnorm_name,
        tty AS rxnorm_term_type,
        1 AS source_priority -- Priority for MRCONSO (lower number = higher priority)
    FROM
        mrconso
    WHERE
        sab = 'RXNORM'
    UNION
    ALL
    SELECT
        concept_code AS rxnorm_id,
        concept_name AS rxnorm_name,
        concept_class_id AS rxnorm_term_type,
        2 AS source_priority -- Priority for concept table
    FROM
        concept
    WHERE
        vocabulary_id IN ('RxNorm', 'RxNorm Extension')
)
SELECT
    DISTINCT rxnorm_id,
    rxnorm_name,
    rxnorm_term_type
FROM
    (
        SELECT
            rxnorm_id,
            rxnorm_name,
            rxnorm_term_type,
            ROW_NUMBER() OVER (
                PARTITION BY rxnorm_id
                ORDER BY
                    source_priority
            ) AS rn
        FROM
            combined_rxnorm
    ) ranked
WHERE
    rn = 1;

LOAD sqlite;

ATTACH IF NOT EXISTS 'database/onsides.db' AS db (TYPE sqlite);

-- Products: LEFT JOIN so all referenced rxnorm_product_ids get a vocab entry,
-- even if they are missing from MRCONSO/OMOP.
INSERT INTO
    db.vocab_rxnorm_product (
        rxnorm_id,
        rxnorm_name,
        rxnorm_term_type
    )
SELECT
    DISTINCT rxnorm_product_id AS rxnorm_id,
    COALESCE(rxnorm_name, 'Unknown') AS rxnorm_name,
    COALESCE(rxnorm_term_type, 'Unknown') AS rxnorm_term_type
FROM
    db.product_to_rxnorm
    LEFT JOIN vocab_rxnorm ON rxnorm_product_id = rxnorm_id;

-- Ingredients: LEFT JOIN so all ingredient_ids get a vocab entry.
INSERT INTO
    db.vocab_rxnorm_ingredient (
        rxnorm_id,
        rxnorm_name,
        rxnorm_term_type
    )
SELECT
    DISTINCT ingredient_id AS rxnorm_id,
    COALESCE(concept_name, 'Unknown') AS rxnorm_name,
    COALESCE(concept_class_id, 'Unknown') AS rxnorm_term_type
FROM
    db.vocab_rxnorm_ingredient_to_product
    LEFT JOIN concept
        ON concept_code = ingredient_id
        AND vocabulary_id IN ('RxNorm', 'RxNorm Extension');

-- MedDRA: Use both OMOP and MRCONSO as sources so all referenced effect_meddra_ids
-- get a vocab entry. Removes the domain_id = 'Condition' filter which was too
-- restrictive and excluded valid MedDRA terms classified under other OMOP domains.
INSERT INTO
    db.vocab_meddra_adverse_effect (
        meddra_id,
        meddra_name,
        meddra_term_type
    )
WITH meddra_from_omop AS (
    SELECT
        DISTINCT cast(concept_code AS int) AS meddra_id,
        concept_name AS meddra_name,
        concept_class_id AS meddra_term_type
    FROM
        concept
    WHERE
        vocabulary_id = 'MedDRA'
        AND concept_class_id IN ('PT', 'LLT')
),
meddra_from_mrconso AS (
    SELECT
        DISTINCT cast(CODE AS int) AS meddra_id,
        STR AS meddra_name,
        TTY AS meddra_term_type
    FROM
        mrconso
    WHERE
        SAB = 'MDR'
        AND LAT = 'ENG'
        AND TTY IN ('PT', 'LLT')
)
SELECT
    DISTINCT ids.effect_meddra_id AS meddra_id,
    COALESCE(omop.meddra_name, mrc.meddra_name, 'Unknown') AS meddra_name,
    COALESCE(omop.meddra_term_type, mrc.meddra_term_type, 'Unknown') AS meddra_term_type
FROM
    (SELECT DISTINCT effect_meddra_id FROM db.product_adverse_effect
     WHERE effect_meddra_id IS NOT NULL) ids
    LEFT JOIN meddra_from_omop omop ON ids.effect_meddra_id = omop.meddra_id
    LEFT JOIN meddra_from_mrconso mrc ON ids.effect_meddra_id = mrc.meddra_id;
