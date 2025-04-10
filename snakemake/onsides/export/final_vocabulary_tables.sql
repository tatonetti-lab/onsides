create table if not exists mrconso AS
SELECT
    * EXCLUDE('column18')
FROM
    read_csv(
        'data/mrconso.rrf',
        delim = '|',
        header = false,
        quote = '',
        NAMES = ['CUI', 'LAT', 'TS', 'LUI', 'STT', 'SUI', 'ISPREF', 'AUI', 'SAUI',
          'SCUI', 'SDUI', 'SAB', 'TTY', 'CODE', 'STR', 'SRL', 'SUPPRESS', 'CVF']
    );

create table if not exists concept as
select
    *
from
    read_csv(
        'data/omop_vocab/CONCEPT.csv',
        sep = '\t',
        quote = ''
    );

create table if not exists concept_relationship as
select
    *
from
    read_csv(
        'data/omop_vocab/CONCEPT_RELATIONSHIP.csv',
        sep = '\t',
        quote = ''
    );

CREATE TABLE vocab_rxnorm AS
WITH
combined_rxnorm AS (
    SELECT
        code AS rxnorm_id,
        str AS rxnorm_name,
        tty AS rxnorm_term_type,
        1 AS source_priority -- Priority for MRCONSO (lower number = higher priority)
    FROM
        mrconso
    WHERE
        sab = 'RXNORM'
    UNION ALL
    SELECT
        concept_code AS rxnorm_id,
        concept_name AS rxnorm_name,
        concept_class_id AS rxnorm_term_type,
        2 AS source_priority -- Priority for concept table
    FROM
        concept
    WHERE
        vocabulary_id IN ('RxNorm', 'RxNorm Extension')
)
SELECT distinct
    rxnorm_id,
    rxnorm_name,
    rxnorm_term_type
FROM
    (
        SELECT
            rxnorm_id,
            rxnorm_name,
            rxnorm_term_type,
            ROW_NUMBER() OVER (
                PARTITION BY rxnorm_id
                ORDER BY
                    source_priority
            ) AS rn
        FROM
            combined_rxnorm
    ) ranked
WHERE
    rn = 1;

LOAD sqlite;

ATTACH IF NOT EXISTS 'data/onsides.db' AS db (TYPE sqlite);

-- Products
insert into
    db.vocab_rxnorm_product (
        rxnorm_id,
        rxnorm_name,
        rxnorm_term_type
    )
select distinct
    rxnorm_id,
    rxnorm_name,
    rxnorm_term_type
from
    db.product_label
    inner join db.product_to_rxnorm using (label_id)
    inner join vocab_rxnorm on rxnorm_product_id = rxnorm_id;

-- Product to ingredients
insert into
    db.vocab_rxnorm_ingredient_to_product (ingredient_id, product_id)
with
one_hop as (
    select distinct
        c1.concept_code as ingredient_id,
        c2.concept_code as product_id
    from
        concept c1
        inner join concept_relationship on c1.concept_id = concept_id_1
        inner join concept c2 on concept_id_2 = c2.concept_id
    where
        relationship_id = 'RxNorm ing of'
),
two_hop as (
    select distinct
        c3.concept_code as ingredient_id,
        c1.concept_code as product_id
    from
        concept c1
        inner join concept_relationship cr1 on c1.concept_id = cr1.concept_id_1
        inner join concept c2 on cr1.concept_id_2 = c2.concept_id
        inner join concept_relationship cr2 on c2.concept_id = cr2.concept_id_1
        inner join concept c3 on cr2.concept_id_2 = c3.concept_id
    where
        c1.vocabulary_id = 'RxNorm'
        and c2.vocabulary_id = 'RxNorm'
        and c3.vocabulary_id = 'RxNorm'
        and c3.concept_class_id ilike '%ingred%'
),
three_hop as (
    select
        c4.concept_code as ingredient_id,
        c1.concept_code as product_id
    from
        concept c1
        inner join concept_relationship cr1 on c1.concept_id = cr1.concept_id_1
        inner join concept c2 on cr1.concept_id_2 = c2.concept_id
        inner join concept_relationship cr2 on c2.concept_id = cr2.concept_id_1
        inner join concept c3 on cr2.concept_id_2 = c3.concept_id
        inner join concept_relationship cr3 on c3.concept_id = cr3.concept_id_1
        inner join concept c4 on cr3.concept_id_2 = c4.concept_id
    where
        c1.vocabulary_id = 'RxNorm'
        and c2.vocabulary_id = 'RxNorm'
        and c3.vocabulary_id = 'RxNorm'
        and c4.vocabulary_id = 'RxNorm'
        and c4.concept_class_id ilike '%ingred%'
),
prod_to_ingred as (
    select distinct
        ingredient_id,
        product_id
    from
        one_hop
    union all
    select distinct
        ingredient_id,
        product_id
    from
        two_hop
    union all
    select distinct
        ingredient_id,
        product_id
    from
        three_hop
)
select distinct
    ingredient_id,
    product_id
from
    db.product_label
    inner join db.product_to_rxnorm using (label_id)
    inner join prod_to_ingred on rxnorm_product_id = product_id;

-- Ingredients
insert into
    db.vocab_rxnorm_ingredient (
        rxnorm_id,
        rxnorm_name,
        rxnorm_term_type
    )
select distinct
    concept_code as rxnorm_id,
    concept_name as rxnorm_name,
    concept_class_id as rxnorm_term_type
from
    concept
    inner join db.vocab_rxnorm_ingredient_to_product on concept_code = ingredient_id
where
    vocabulary_id in ('RxNorm', 'RxNorm Extension');

-- MedDRA
insert into
    db.vocab_meddra_adverse_effect (
        meddra_id,
        meddra_name,
        meddra_term_type
    )
select distinct
    cast(concept_code as int) as meddra_id,
    concept_name as meddra_name,
    concept_class_id as meddra_term_type
from
    concept
    inner join db.product_adverse_effect on cast(concept_code as int) = effect_meddra_id
where
    vocabulary_id = 'MedDRA'
    and concept_class_id in ('PT', 'LLT')
    and domain_id = 'Condition';
