-- ===============================================
-- 1. Load the SQLite extension and attach the SQLite database
-- ===============================================
LOAD sqlite;

ATTACH IF NOT EXISTS 'database/onsides.db' AS db (TYPE sqlite);

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

USE duck.main;

CREATE TEMPORARY TABLE non_deficient_adverse_effect AS
SELECT
    pae.*
FROM
    db.product_adverse_effect pae
WHERE
    effect_meddra_id IN (
        SELECT
            meddra_id
        FROM
            db.vocab_meddra_adverse_effect
    )
    AND product_label_id IN (
        SELECT
            label_id
        FROM
            db.product_label
    );

DROP TABLE db.product_adverse_effect;

CREATE TABLE db.product_adverse_effect AS
SELECT
    *
FROM
    non_deficient_adverse_effect;

USE db;

-- ===============================================
-- 4. Handle product_label issues (Test 3b)
--    Delete rows where the product has no ingredient mapping.
-- ===============================================
COPY (
    SELECT
        pl.label_id
    FROM
        product_label pl ANTI
        JOIN (
            SELECT
                DISTINCT label_id
            FROM
                product_to_rxnorm p2r
                INNER JOIN vocab_rxnorm_ingredient_to_product vi2p ON p2r.rxnorm_product_id = vi2p.product_id
        ) AS labels_with_ingredients USING (label_id)
) TO 'log/product_label_missing_ingredient.parquet' (FORMAT 'parquet');

USE duck.main;

CREATE TEMPORARY TABLE non_deficient_products AS
SELECT
    p.*
FROM
    db.product_label p
    INNER JOIN (
        SELECT
            DISTINCT label_id
        FROM
            db.product_to_rxnorm p2r
            INNER JOIN db.vocab_rxnorm_ingredient_to_product vi2p ON p2r.rxnorm_product_id = vi2p.product_id
    ) AS labels_with_ingredients USING (label_id);

DROP TABLE db.product_label;

CREATE TABLE db.product_label AS
SELECT
    *
FROM
    non_deficient_products;

USE db;

-- ===============================================
-- 5. Clean up orphaned rows in mapping tables referencing deleted product_label rows
-- ===============================================
-- 5a. Remove orphaned rows from product_to_rxnorm.
COPY (
    SELECT
        p2r.*
    FROM
        product_to_rxnorm p2r ANTI
        JOIN product_label pl ON p2r.label_id = pl.label_id
) TO 'log/orphan_product_to_rxnorm.parquet' (FORMAT 'parquet');

USE duck.main;

CREATE TEMPORARY TABLE non_orphan_product_to_rxnorm AS
SELECT
    p.*
FROM
    db.product_to_rxnorm p
    INNER JOIN db.product_label l USING (label_id);

DROP TABLE db.product_to_rxnorm;

CREATE TABLE db.product_to_rxnorm AS
SELECT
    *
FROM
    non_orphan_product_to_rxnorm;

USE db;

-- 5b. Remove orphaned rows from product_adverse_effect.
COPY (
    SELECT
        pae.*
    FROM
        product_adverse_effect pae ANTI
        JOIN product_label pl ON pae.product_label_id = pl.label_id
) TO 'log/orphan_product_adverse_effect.parquet' (FORMAT 'parquet');

USE duck.main;

CREATE TEMPORARY TABLE non_deficient_product_adverse_effect AS
SELECT
    pae.*
FROM
    db.product_adverse_effect pae
    INNER JOIN db.product_label pl ON pae.product_label_id = pl.label_id;

DROP TABLE db.product_adverse_effect;

CREATE TABLE db.product_adverse_effect AS
SELECT
    *
FROM
    non_deficient_product_adverse_effect;

USE db;

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
