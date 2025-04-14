create table uk_preds as
select
    text_id as effect_meddra_id,
    split_part(text_id, '.', 1) as source_product_id,
    term_id,
    pred0,
    pred1
from
    '_onsides/combined/label_english_preds.parquet'
where
    ends_with(text_id, 'UK');

create table uk_meta as
select
    name as source_product_name,
    code as source_product_id,
    page_url as source_label_url
from
    '_onsides/uk/label_text.parquet';

create table uk_rxnorm as
select
    code as source_product_id,
    rxcui as rxnorm_product_id
from
    '_onsides/uk/labels_to_rxnorm.parquet';

create table uk_final as
select
    source_product_name,
    source_product_id,
    source_label_url,
    term_id,
    rxnorm_product_id,
    pred0,
    pred1
from
    uk_preds
    inner join uk_meta using (source_product_id)
    inner join uk_rxnorm using (source_product_id);

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
uk_inner as (
    select distinct
        source_product_name,
        source_product_id,
        source_label_url
    from
        uk_final
)
select
    'UK' as source,
    source_product_name,
    source_product_id,
    source_label_url
from
    uk_inner;

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
        source = 'UK'
),
joined_labels as (
    SELECT DISTINCT
        label_id,
        rxnorm_product_id
    FROM
        new_labels
        INNER JOIN uk_final USING (source_product_id)
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
        source = 'UK'
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
    INNER JOIN uk_final USING (source_product_id);
