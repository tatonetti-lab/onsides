.mode table
-- ===============================================
-- Summary Script for Database Reports
-- ===============================================
-- 1. Fraction of products that map to ingredients
WITH
product_ingredient_stats AS (
    SELECT
        pl.label_id,
        COUNT(DISTINCT vi2p.ingredient_id) AS ingredient_count
    FROM
        product_label pl
        LEFT JOIN product_to_rxnorm p2r ON pl.label_id = p2r.label_id
        LEFT JOIN vocab_rxnorm_ingredient_to_product vi2p ON p2r.rxnorm_product_id = vi2p.product_id
    GROUP BY
        pl.label_id
)
SELECT
    (
        SELECT
            COUNT(*)
        FROM
            product_ingredient_stats
        WHERE
            ingredient_count > 0
    ) AS products_with_ingredients,
    (
        SELECT
            COUNT(*)
        FROM
            product_label
    ) AS total_products,
    CAST(
        (
            SELECT
                COUNT(*)
            FROM
                product_ingredient_stats
            WHERE
                ingredient_count > 0
        ) AS FLOAT
    ) / (
        SELECT
            COUNT(*)
        FROM
            product_label
    ) AS fraction_products_with_ingredients;

-- ===============================================
-- 2. Count of products by source (from product_label)
SELECT
    source,
    COUNT(*) AS product_count
FROM
    product_label
GROUP BY
    source
ORDER BY
    product_count DESC;

-- ===============================================
-- 4. Summary statistics of ingredient mappings per product
WITH
ingredient_counts AS (
    SELECT
        pl.label_id,
        COUNT(DISTINCT vi2p.ingredient_id) AS ingredient_count
    FROM
        product_label pl
        LEFT JOIN product_to_rxnorm p2r ON pl.label_id = p2r.label_id
        LEFT JOIN vocab_rxnorm_ingredient_to_product vi2p ON p2r.rxnorm_product_id = vi2p.product_id
    GROUP BY
        pl.label_id
)
SELECT
    AVG(ingredient_count) AS avg_ingredients,
    MIN(ingredient_count) AS min_ingredients,
    MAX(ingredient_count) AS max_ingredients,
    COUNT(*) AS total_products
FROM
    ingredient_counts;

-- ===============================================
-- 5. Summary statistics for adverse effects per product
WITH
effect_counts AS (
    SELECT
        pl.label_id,
        COUNT(pae.effect_id) AS effect_count
    FROM
        product_label pl
        LEFT JOIN product_adverse_effect pae ON pl.label_id = pae.product_label_id
    GROUP BY
        pl.label_id
)
SELECT
    AVG(effect_count) AS avg_effects,
    MIN(effect_count) AS min_effects,
    MAX(effect_count) AS max_effects,
    COUNT(*) AS total_products
FROM
    effect_counts;

-- ===============================================
-- 6. Mapping totals for product mappings
-- Summary: Count and Percent of product_label with an RxNorm mapping
-- ============================================================
SELECT
    (
        SELECT
            COUNT(DISTINCT label_id)
        FROM
            product_to_rxnorm
    ) AS product_labels_with_rxnorm_mapping,
    (
        SELECT
            COUNT(*)
        FROM
            product_label
    ) AS total_product_labels,
    (
        CAST(
            (
                SELECT
                    COUNT(DISTINCT label_id)
                FROM
                    product_to_rxnorm
            ) AS FLOAT
        ) / (
            SELECT
                COUNT(*)
            FROM
                product_label
        )
    ) * 100 AS percent_with_rxnorm_mapping;

-- ===============================================
-- 7. Fraction of adverse event terms that are meddra conditions
-- ============================================================
SELECT
    (
        SELECT
            COUNT(*)
        FROM
            product_adverse_effect
            inner join vocab_meddra_adverse_effect on effect_meddra_id = meddra_id
    ) AS mapped_adverse_effects,
    (
        SELECT
            COUNT(*)
        FROM
            product_adverse_effect
    ) AS total_adverse_events,
    (
        CAST(
            (
                SELECT
                    COUNT(*)
                FROM
                    product_adverse_effect
                    inner join vocab_meddra_adverse_effect on effect_meddra_id = meddra_id
            ) AS FLOAT
        ) / (
            SELECT
                COUNT(*)
            FROM
                product_adverse_effect
        )
    ) * 100 AS percent_with_meddra_condition_mapping;
