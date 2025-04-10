-- ===============================================
-- 1. Load the SQLite extension and attach the SQLite database
-- ===============================================
LOAD sqlite;

ATTACH IF NOT EXISTS 'data/onsides.db' AS db (TYPE sqlite);

USE db;

-- ===============================================
-- 2. Handle product_to_rxnorm issues (Tests 1a & 2a)
--    Delete rows where:
--      - The rxnorm_product_id is missing from vocab_rxnorm_product, OR
--      - The label_id is missing from product_label.
-- ===============================================
CREATE
OR REPLACE TEMPORARY VIEW deficient_product_to_rxnorm AS
SELECT
    pt.*
FROM
    product_to_rxnorm pt
    LEFT JOIN vocab_rxnorm_product vp ON pt.rxnorm_product_id = vp.rxnorm_id
    LEFT JOIN product_label pl ON pt.label_id = pl.label_id
WHERE
    vp.rxnorm_id IS NULL
    OR pl.label_id IS NULL;

COPY (
    SELECT
        *
    FROM
        deficient_product_to_rxnorm
) TO 'log/product_to_rxnorm_deficient.parquet' (FORMAT 'parquet');

DELETE FROM
    product_to_rxnorm USING deficient_product_to_rxnorm d
WHERE
    product_to_rxnorm.label_id = d.label_id
    AND product_to_rxnorm.rxnorm_product_id = d.rxnorm_product_id;

-- ===============================================
-- 3. Handle product_adverse_effect issues (Tests 1b & 2b)
--    Delete rows where:
--      - The effect_meddra_id is missing from vocab_meddra_adverse_effect, OR
--      - The product_label_id is missing from product_label.
-- ===============================================
CREATE
OR REPLACE TEMPORARY VIEW deficient_product_adverse_effect AS
SELECT
    pae.*
FROM
    product_adverse_effect pae
    LEFT JOIN vocab_meddra_adverse_effect va ON pae.effect_meddra_id = va.meddra_id
    LEFT JOIN product_label pl ON pae.product_label_id = pl.label_id
WHERE
    va.meddra_id IS NULL
    OR pl.label_id IS NULL;

COPY (
    SELECT
        *
    FROM
        deficient_product_adverse_effect
) TO 'log/product_adverse_effect_deficient.parquet' (FORMAT 'parquet');

DELETE FROM
    product_adverse_effect USING deficient_product_adverse_effect d
WHERE
    product_adverse_effect.effect_id = d.effect_id;

-- ===============================================
-- 4. Handle product_label issues (Test 3b)
--    Delete rows where the product has no ingredient mapping.
-- ===============================================
CREATE
OR REPLACE TEMPORARY VIEW deficient_product_label AS
SELECT
    pl.*
FROM
    product_label pl
WHERE
    NOT EXISTS (
        SELECT
            1
        FROM
            product_to_rxnorm p2r
            JOIN vocab_rxnorm_ingredient_to_product vi2p ON p2r.rxnorm_product_id = vi2p.product_id
        WHERE
            p2r.label_id = pl.label_id
    );

COPY (
    SELECT
        *
    FROM
        deficient_product_label
) TO 'log/product_label_missing_ingredient.parquet' (FORMAT 'parquet');

DELETE FROM
    product_label USING deficient_product_label d
WHERE
    product_label.label_id = d.label_id;

-- ===============================================
-- 5. Clean up orphaned rows in mapping tables referencing deleted product_label rows
-- ===============================================
-- 5a. Remove orphaned rows from product_to_rxnorm.
CREATE
OR REPLACE TEMPORARY VIEW orphan_product_to_rxnorm AS
SELECT
    p2r.*
FROM
    product_to_rxnorm p2r
    LEFT JOIN product_label pl ON p2r.label_id = pl.label_id
WHERE
    pl.label_id IS NULL;

COPY (
    SELECT
        *
    FROM
        orphan_product_to_rxnorm
) TO 'log/orphan_product_to_rxnorm.parquet' (FORMAT 'parquet');

DELETE FROM
    product_to_rxnorm USING orphan_product_to_rxnorm o
WHERE
    product_to_rxnorm.label_id = o.label_id
    AND product_to_rxnorm.rxnorm_product_id = o.rxnorm_product_id;

-- 5b. Remove orphaned rows from product_adverse_effect.
CREATE
OR REPLACE TEMPORARY VIEW orphan_product_adverse_effect AS
SELECT
    pae.*
FROM
    product_adverse_effect pae
    LEFT JOIN product_label pl ON pae.product_label_id = pl.label_id
WHERE
    pl.label_id IS NULL;

COPY (
    SELECT
        *
    FROM
        orphan_product_adverse_effect
) TO 'log/orphan_product_adverse_effect.parquet' (FORMAT 'parquet');

DELETE FROM
    product_adverse_effect USING orphan_product_adverse_effect o
WHERE
    product_adverse_effect.effect_id = o.effect_id;

-- ===============================================
-- 6. Remove orphaned vocabulary entries (Tests 4a & 4c)
-- ===============================================
-- 6a. Remove orphaned entries from vocab_rxnorm_product (Test 4a)
CREATE
OR REPLACE TEMPORARY VIEW orphan_vocab_rxnorm_product AS
SELECT
    vp.*
FROM
    vocab_rxnorm_product vp
    LEFT JOIN product_to_rxnorm p2r ON vp.rxnorm_id = p2r.rxnorm_product_id
WHERE
    p2r.label_id IS NULL;

COPY (
    SELECT
        *
    FROM
        orphan_vocab_rxnorm_product
) TO 'log/orphan_vocab_rxnorm_product.parquet' (FORMAT 'parquet');

DELETE FROM
    vocab_rxnorm_product USING orphan_vocab_rxnorm_product o
WHERE
    vocab_rxnorm_product.rxnorm_id = o.rxnorm_id;

-- 6b. Remove orphaned entries from vocab_meddra_adverse_effect (Test 4c)
CREATE
OR REPLACE TEMPORARY VIEW orphan_vocab_meddra_adverse_effect AS
SELECT
    va.*
FROM
    vocab_meddra_adverse_effect va
    LEFT JOIN product_adverse_effect pae ON va.meddra_id = pae.effect_meddra_id
WHERE
    pae.effect_id IS NULL;

COPY (
    SELECT
        *
    FROM
        orphan_vocab_meddra_adverse_effect
) TO 'log/orphan_vocab_meddra_adverse_effect.parquet' (FORMAT 'parquet');

DELETE FROM
    vocab_meddra_adverse_effect USING orphan_vocab_meddra_adverse_effect o
WHERE
    vocab_meddra_adverse_effect.meddra_id = o.meddra_id;

-- ===============================================
-- 7. Final Notes:
--   - Steps 2 and 3 clean up the mapping tables (product_to_rxnorm and product_adverse_effect)
--     by removing rows with invalid foreign keys.
--   - Step 4 deletes product_label rows with no ingredient mapping (fixing Test 3b).
--   - Step 5 removes mapping rows that become orphaned after deleting product_label rows.
--   - Step 6 deletes vocabulary entries that are not referenced anywhere,
--     thereby fixing Test 4a (for vocab_rxnorm_product) and Test 4c (for vocab_meddra_adverse_effect).
--   All deleted rows are exported as Parquet files in the 'log' directory for further review if needed.
-- ===============================================
