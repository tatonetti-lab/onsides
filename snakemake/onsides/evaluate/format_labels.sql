-- Load raw label text files
CREATE TABLE raw_labels_us AS
SELECT
    *
FROM
    read_parquet('_onsides/us/label_text.parquet');

CREATE TABLE raw_labels_uk AS
SELECT
    *
FROM
    read_parquet('_onsides/uk/label_text.parquet');

CREATE TABLE raw_labels_eu AS
SELECT
    *
FROM
    read_parquet('_onsides/eu/label_text.parquet');

CREATE TABLE raw_labels_jp AS
SELECT
    *
FROM
    read_parquet('_onsides/jp/med_label_text.parquet');

-- Reformat raw labels
CREATE TABLE fmt_labels_us AS WITH unpivoted AS (
    unpivot raw_labels_us ON ar,
    bw,
    wp INTO name section value text
)
SELECT
    concat(
        set_id,
        '.',
        label_id,
        '.',
        spl_version,
        '.',
        section,
        '.US'
    ) AS text_id,
    text
FROM
    unpivoted
WHERE
    text IS NOT NULL
    AND strlen(text) > 0;

CREATE TABLE fmt_labels_uk AS
SELECT
    concat(code, '.AR.UK') AS text_id,
    text
FROM
    raw_labels_uk
WHERE
    text IS NOT NULL
    AND strlen(text) > 0;

CREATE TABLE fmt_labels_eu AS
SELECT
    concat(code, '.AR.EU') AS text_id,
    text
FROM
    raw_labels_eu
WHERE
    text IS NOT NULL
    AND strlen(text) > 0;

CREATE TABLE fmt_labels_jp AS
SELECT
    concat(code, '.AR.JP') AS text_id,
    text
FROM
    raw_labels_jp
WHERE
    text IS NOT NULL
    AND strlen(text) > 0;

-- Combine formatted english tables
CREATE TABLE combined_english_labels AS
SELECT
    *
FROM
    fmt_labels_us
UNION
SELECT
    *
FROM
    fmt_labels_uk
UNION
SELECT
    *
FROM
    fmt_labels_eu;

COPY combined_english_labels TO '_onsides/combined/english_labels.parquet' (FORMAT parquet);

COPY fmt_labels_jp TO '_onsides/combined/japanese_labels.parquet' (FORMAT parquet);
