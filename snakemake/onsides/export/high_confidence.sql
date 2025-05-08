LOAD sqlite;

ATTACH IF NOT EXISTS 'database/onsides.db' AS db (TYPE sqlite);

USE db;

COPY (
    WITH ingredient_effect_by_source AS (
        SELECT
            l.source,
            pi.ingredient_id,
            a.effect_meddra_id
        FROM
            product_label l
            INNER JOIN product_to_rxnorm lp USING (label_id)
            INNER JOIN vocab_rxnorm_product p ON lp.rxnorm_product_id = p.rxnorm_id
            INNER JOIN vocab_rxnorm_ingredient_to_product pi ON p.rxnorm_id = pi.product_id
            INNER JOIN product_adverse_effect a ON l.label_id = a.product_label_id
    )
    SELECT
        ingredient_id,
        effect_meddra_id
    FROM
        ingredient_effect_by_source
    GROUP BY
        ingredient_id,
        effect_meddra_id
    HAVING
        count(DISTINCT source) == 4
) TO 'database/csv/high_confidence.csv' (FORMAT csv, HEADER TRUE, DELIMITER ',');
