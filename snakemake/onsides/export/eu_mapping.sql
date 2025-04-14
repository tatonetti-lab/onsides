create table eu_preds as
select
    text_id as effect_meddra_id,
    split_part(text_id, '.', 1) as source_product_id,
    term_id,
    pred0,
    pred1
from
    '_onsides/combined/label_english_preds.parquet'
where
    ends_with(text_id, 'EU');

create table eu_meta as
select
    name as source_product_name,
    code as source_product_id,
    page_url as source_label_url
from
    '_onsides/eu/label_text.parquet';

create table eu_rxnorm as
select
    code as source_product_id,
    rxcui as rxnorm_product_id
from
    '_onsides/eu/labels_to_rxnorm.parquet';

create table eu_final as
select
    source_product_name,
    source_product_id,
    source_label_url,
    term_id,
    rxnorm_product_id,
    pred0,
    pred1
from
    eu_preds
    inner join eu_meta using (source_product_id)
    inner join eu_rxnorm using (source_product_id);

--------------------------------------------------------------------------------
--------------------------------------------------------------------------------
--------------------------------------------------------------------------------
INSTALL sqlite;

LOAD sqlite;

ATTACH IF NOT EXISTS 'database/onsides.db' AS db (TYPE sqlite);

-- Product label
insert into
    db.product_label (
        source,
        source_product_name,
        source_product_id,
        source_label_url
    )
with
eu_inner as (
    select distinct
        source_product_name,
        source_product_id,
        source_label_url
    from
        eu_final
)
select
    'EU' as source,
    source_product_name,
    source_product_id,
    source_label_url
from
    eu_inner;

-- Product to RxNorm
INSERT INTO
    db.product_to_rxnorm (label_id, rxnorm_product_id)
WITH
new_labels AS (
    SELECT
        label_id,
        source_product_id
    FROM
        db.product_label
    WHERE
        source = 'EU'
),
joined_labels as (
    SELECT DISTINCT
        label_id,
        rxnorm_product_id
    FROM
        new_labels
        INNER JOIN eu_final USING (source_product_id)
)
select
    label_id,
    rxnorm_product_id
from
    joined_labels
where
    rxnorm_product_id != '';

-- Adverse effect
INSERT INTO
    db.product_adverse_effect (
        product_label_id,
        label_section,
        effect_meddra_id,
        match_method,
        pred0,
        pred1
    )
WITH
new_labels AS (
    SELECT
        label_id,
        source_product_id
    FROM
        db.product_label
    WHERE
        source = 'EU'
)
SELECT
    label_id AS product_label_id,
    'NA' as label_section,
    term_id AS effect_meddra_id,
    'PMB' AS match_method,
    pred0,
    pred1
FROM
    new_labels
    INNER JOIN eu_final USING (source_product_id);
