LOAD sqlite;

ATTACH IF NOT EXISTS 'database/onsides.db' AS db (TYPE sqlite);

USE db;

COPY (
    with
    ingredient_effect_by_source as (
        select
            l.source,
            pi.ingredient_id,
            a.effect_meddra_id
        from
            product_label l
            inner join product_to_rxnorm lp using (label_id)
            inner join vocab_rxnorm_product p on lp.rxnorm_product_id = p.rxnorm_id
            inner join vocab_rxnorm_ingredient_to_product pi on p.rxnorm_id = pi.product_id
            inner join product_adverse_effect a on l.label_id = a.product_label_id
    )
    select
        ingredient_id,
        effect_meddra_id
    from
        ingredient_effect_by_source
    group by
        ingredient_id,
        effect_meddra_id
    having
        count(distinct source) == 4
) TO 'database/csv/high_confidence.csv' (FORMAT csv, HEADER true, DELIMITER ',');
