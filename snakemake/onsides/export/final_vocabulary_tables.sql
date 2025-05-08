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

-- Products
INSERT INTO
    db.vocab_rxnorm_product (
        rxnorm_id,
        rxnorm_name,
        rxnorm_term_type
    )
SELECT
    DISTINCT rxnorm_id,
    rxnorm_name,
    rxnorm_term_type
FROM
    db.product_label
    INNER JOIN db.product_to_rxnorm USING (label_id)
    INNER JOIN vocab_rxnorm ON rxnorm_product_id = rxnorm_id;

-- Ingredients
INSERT INTO
    db.vocab_rxnorm_ingredient (
        rxnorm_id,
        rxnorm_name,
        rxnorm_term_type
    )
SELECT
    DISTINCT concept_code AS rxnorm_id,
    concept_name AS rxnorm_name,
    concept_class_id AS rxnorm_term_type
FROM
    concept
    INNER JOIN db.vocab_rxnorm_ingredient_to_product ON concept_code = ingredient_id
WHERE
    vocabulary_id IN ('RxNorm', 'RxNorm Extension');

-- MedDRA
INSERT INTO
    db.vocab_meddra_adverse_effect (
        meddra_id,
        meddra_name,
        meddra_term_type
    )
SELECT
    DISTINCT cast(concept_code AS int) AS meddra_id,
    concept_name AS meddra_name,
    concept_class_id AS meddra_term_type
FROM
    concept
    INNER JOIN db.product_adverse_effect ON cast(concept_code AS int) = effect_meddra_id
WHERE
    vocabulary_id = 'MedDRA'
    AND concept_class_id IN ('PT', 'LLT')
    AND domain_id = 'Condition';
