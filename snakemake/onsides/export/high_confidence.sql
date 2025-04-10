with
adverse_by_source as (
    select
        source,
        effect_meddra_id,
        rxnorm_product_id
    from
        product_label
        inner join product_adverse_effect on label_id = product_label_id
        inner join product_to_rxnorm using (label_id)
),
filtered as (
    select
        effect_meddra_id,
        rxnorm_product_id
    from
        adverse_by_source
    group by
        effect_meddra_id,
        rxnorm_product_id
    having
        count(distinct source) == 4
)
select
    count(*)
from
    filtered;
