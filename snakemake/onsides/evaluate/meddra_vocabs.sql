-- Full UMLS
DROP TABLE IF EXISTS mrconso;

CREATE TABLE mrconso AS
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

-- Japanese MedDRA
DROP TABLE IF EXISTS meddra_jpn;

CREATE TABLE meddra_jpn AS
SELECT
    *
FROM
    mrconso
WHERE
    LAT = 'JPN'
    AND SAB = 'MDRJPN'
    AND tty IN ('PT', 'LLT');

-- English MedDRA
DROP TABLE IF EXISTS meddra_eng;

CREATE TABLE meddra_eng AS
SELECT
    *
FROM
    mrconso
WHERE
    lat = 'ENG'
    AND sab = 'MDR'
    AND tty IN ('PT', 'LLT');

-- Joined MedDRA
-- SELECT
--     code,
--     meddra_eng.tty AS tty,
--     meddra_eng.str AS eng_str,
--     meddra_jpn.str AS jpn_str
-- FROM
--     meddra_eng
--     JOIN meddra_jpn USING (code)
-- LIMIT
--     5;
COPY (
    SELECT
        DISTINCT code AS text_id,
        str AS text
    FROM
        meddra_eng
) TO '_onsides/vocab/meddra_english.parquet' (FORMAT parquet);

COPY (
    SELECT
        DISTINCT code AS text_id,
        str AS text
    FROM
        meddra_jpn
) TO '_onsides/vocab/meddra_japanese.parquet' (FORMAT parquet);
