-- ===============================================
-- Validation Script with PASS/FAIL Reporting for SQLite
-- ===============================================
-- Test 1a: Validate that every product in product_to_rxnorm exists in vocab_rxnorm_product.
SELECT
    'Test 1a: All product_to_rxnorm entries reference a valid vocab_rxnorm_product' AS Test,
    CASE
        WHEN COUNT(*) = 0 THEN 'PASS'
        ELSE 'FAIL (' || COUNT(*) || ' missing vocab_rxnorm_product entries)'
    END AS Result
FROM
    product_to_rxnorm pt
    LEFT JOIN vocab_rxnorm_product vp ON pt.rxnorm_product_id = vp.rxnorm_id
WHERE
    vp.rxnorm_id IS NULL;

-- Test 1b: Validate that every adverse effect in product_adverse_effect exists in vocab_meddra_adverse_effect.
SELECT
    'Test 1b: All product_adverse_effect entries reference a valid vocab_meddra_adverse_effect' AS Test,
    CASE
        WHEN COUNT(*) = 0 THEN 'PASS'
        ELSE 'FAIL (' || COUNT(*) || ' missing vocab_meddra_adverse_effect entries)'
    END AS Result
FROM
    product_adverse_effect pae
    LEFT JOIN vocab_meddra_adverse_effect va ON pae.effect_meddra_id = va.meddra_id
WHERE
    va.meddra_id IS NULL;

-- Test 2a: Validate that every row in product_to_rxnorm references an existing product in product_label.
SELECT
    'Test 2a: All product_to_rxnorm entries reference an existing product_label' AS Test,
    CASE
        WHEN COUNT(*) = 0 THEN 'PASS'
        ELSE 'FAIL (' || COUNT(*) || ' orphaned product_label references in product_to_rxnorm)'
    END AS Result
FROM
    product_to_rxnorm p2r
    LEFT JOIN product_label pl ON p2r.label_id = pl.label_id
WHERE
    pl.label_id IS NULL;

-- Test 2b: Validate that every row in product_adverse_effect references an existing product in product_label.
SELECT
    'Test 2b: All product_adverse_effect entries reference an existing product_label' AS Test,
    CASE
        WHEN COUNT(*) = 0 THEN 'PASS'
        ELSE 'FAIL (' || COUNT(*) || ' orphaned product_label references in product_adverse_effect)'
    END AS Result
FROM
    product_adverse_effect pae
    LEFT JOIN product_label pl ON pae.product_label_id = pl.label_id
WHERE
    pl.label_id IS NULL;

-- Test 3a: Validate that every ingredient_id in vocab_rxnorm_ingredient_to_product exists in vocab_rxnorm_ingredient.
SELECT
    'Test 3a: All ingredient_ids in vocab_rxnorm_ingredient_to_product exist in vocab_rxnorm_ingredient' AS Test,
    CASE
        WHEN COUNT(*) = 0 THEN 'PASS'
        ELSE 'FAIL (' || COUNT(*) || ' missing vocab_rxnorm_ingredient entries)'
    END AS Result
FROM
    vocab_rxnorm_ingredient_to_product vrip
    LEFT JOIN vocab_rxnorm_ingredient vri ON vrip.ingredient_id = vri.rxnorm_id
WHERE
    vri.rxnorm_id IS NULL;

-- Test 3b: Validate that every product in product_label has at least one ingredient.
SELECT
    'Test 3b: Every product in product_label has at least one ingredient' AS Test,
    CASE
        WHEN COUNT(*) = 0 THEN 'PASS'
        ELSE 'FAIL (' || COUNT(*) || ' product_label entries missing an ingredient mapping)'
    END AS Result
FROM
    (
        SELECT
            pl.label_id
        FROM
            product_label pl
            LEFT JOIN product_to_rxnorm p2r ON pl.label_id = p2r.label_id
            LEFT JOIN vocab_rxnorm_ingredient_to_product vi2p ON p2r.rxnorm_product_id = vi2p.product_id
        GROUP BY
            pl.label_id
        HAVING
            COUNT(vi2p.ingredient_id) = 0
    ) AS sub;

-- Test 4a: Check for vocabulary products that are not linked to any product label.
SELECT
    'Test 4a: All vocab_rxnorm_product entries are linked to a product label' AS Test,
    CASE
        WHEN COUNT(*) = 0 THEN 'PASS'
        ELSE 'FAIL (' || COUNT(*) || ' vocab_rxnorm_product entries not linked)'
    END AS Result
FROM
    vocab_rxnorm_product vp
    LEFT JOIN product_to_rxnorm p2r ON vp.rxnorm_id = p2r.rxnorm_product_id
WHERE
    p2r.label_id IS NULL;

-- Test 4b: Check for vocabulary ingredients that are not used in any ingredient-to-product mapping.
SELECT
    'Test 4b: All vocab_rxnorm_ingredient entries are used in ingredient-to-product mapping' AS Test,
    CASE
        WHEN COUNT(*) = 0 THEN 'PASS'
        ELSE 'FAIL (' || COUNT(*) || ' vocab_rxnorm_ingredient entries not linked)'
    END AS Result
FROM
    vocab_rxnorm_ingredient vi
    LEFT JOIN vocab_rxnorm_ingredient_to_product vi2p ON vi.rxnorm_id = vi2p.ingredient_id
WHERE
    vi2p.product_id IS NULL;

-- Test 4c: Check for MedDRA adverse effects that are not linked to any product adverse effect.
SELECT
    'Test 4c: All vocab_meddra_adverse_effect entries are used in product_adverse_effect mapping' AS Test,
    CASE
        WHEN COUNT(*) = 0 THEN 'PASS'
        ELSE 'FAIL (' || COUNT(*) || ' vocab_meddra_adverse_effect entries not linked)'
    END AS Result
FROM
    vocab_meddra_adverse_effect va
    LEFT JOIN product_adverse_effect pae ON va.meddra_id = pae.effect_meddra_id
WHERE
    pae.effect_id IS NULL;

-- Test 5a: Check that required fields in product_label are not null.
SELECT
    'Test 5a: All required fields in product_label are not null' AS Test,
    CASE
        WHEN COUNT(*) = 0 THEN 'PASS'
        ELSE 'FAIL (' || COUNT(*) || ' product_label rows with missing required fields)'
    END AS Result
FROM
    product_label
WHERE
    source IS NULL
    OR source_product_name IS NULL
    OR source_product_id IS NULL;

-- Test 5b: Check that required fields in vocab_rxnorm_product are not null.
SELECT
    'Test 5b: All required fields in vocab_rxnorm_product are not null' AS Test,
    CASE
        WHEN COUNT(*) = 0 THEN 'PASS'
        ELSE 'FAIL (' || COUNT(*) || ' vocab_rxnorm_product rows with missing required fields)'
    END AS Result
FROM
    vocab_rxnorm_product
WHERE
    rxnorm_name IS NULL
    OR rxnorm_term_type IS NULL;
