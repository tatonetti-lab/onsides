-- Begin an atomic transaction.
BEGIN TRANSACTION;

-- 1. Remove rows from product_adverse_effect with pred1 <= 3.258.
DELETE FROM
    product_adverse_effect
WHERE
    pred1 <= 3.258;

-- 2. Delete product_label rows that are no longer referenced in product_adverse_effect.
DELETE FROM
    product_label
WHERE
    label_id NOT IN (
        SELECT
            DISTINCT product_label_id
        FROM
            product_adverse_effect
    );

-- 3. Delete entries in product_to_rxnorm that reference a deleted product_label.
DELETE FROM
    product_to_rxnorm
WHERE
    label_id NOT IN (
        SELECT
            label_id
        FROM
            product_label
    );

-- 4. Prune vocab_meddra_adverse_effect rows that are no longer referenced in product_adverse_effect.
DELETE FROM
    vocab_meddra_adverse_effect
WHERE
    meddra_id NOT IN (
        SELECT
            DISTINCT effect_meddra_id
        FROM
            product_adverse_effect
        WHERE
            effect_meddra_id IS NOT NULL
    );

-- 5. Prune vocab_rxnorm_product rows that are no longer referenced in product_to_rxnorm.
DELETE FROM
    vocab_rxnorm_product
WHERE
    rxnorm_id NOT IN (
        SELECT
            DISTINCT rxnorm_product_id
        FROM
            product_to_rxnorm
    );

-- 6. In vocab_rxnorm_ingredient_to_product, delete rows that refer to a non-existent product (from vocab_rxnorm_product)
--    or to a non-existent ingredient (from vocab_rxnorm_ingredient).
DELETE FROM
    vocab_rxnorm_ingredient_to_product
WHERE
    product_id NOT IN (
        SELECT
            rxnorm_id
        FROM
            vocab_rxnorm_product
    )
    OR ingredient_id NOT IN (
        SELECT
            rxnorm_id
        FROM
            vocab_rxnorm_ingredient
    );

-- 7. Finally, prune vocab_rxnorm_ingredient rows that are no longer referenced in vocab_rxnorm_ingredient_to_product.
DELETE FROM
    vocab_rxnorm_ingredient
WHERE
    rxnorm_id NOT IN (
        SELECT
            DISTINCT ingredient_id
        FROM
            vocab_rxnorm_ingredient_to_product
    );

-- Commit the transaction.
COMMIT;
