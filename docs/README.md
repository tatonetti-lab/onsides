# Example queries

## Find all ingredients that are labeled for renal injury

```sql
SELECT
    DISTINCT i.*
FROM
    product_label
    -- Product to ingredients
    INNER JOIN product_to_rxnorm USING (label_id)
    INNER JOIN vocab_rxnorm_ingredient_to_product ON rxnorm_product_id = product_id
    INNER JOIN vocab_rxnorm_ingredient i ON ingredient_id = rxnorm_id
    -- Product to adverse effects
    INNER JOIN product_adverse_effect ON label_id = product_label_id
    INNER JOIN vocab_meddra_adverse_effect ON effect_meddra_id = meddra_id
WHERE
    meddra_name = 'Renal injury';
```

## Compute the fraction of US drug products that have a label for headache

```sql
WITH n_headache AS (
    SELECT
        COUNT(DISTINCT label_id) AS n
    FROM
        product_label
        INNER JOIN product_adverse_effect ON label_id = product_label_id
        INNER JOIN vocab_meddra_adverse_effect ON effect_meddra_id = meddra_id
    WHERE
        source = 'US'
        AND meddra_name = 'Headache'
),
n_overall AS (
    SELECT
        COUNT(DISTINCT label_id) AS n
    FROM
        product_label
        INNER JOIN product_adverse_effect ON label_id = product_label_id
        INNER JOIN vocab_meddra_adverse_effect ON effect_meddra_id = meddra_id
    WHERE
        source = 'US'
)
SELECT
    CAST(n_headache.n AS real) / n_overall.n AS frac_with_headache
FROM
    n_headache,
    n_overall;
```

## Find the adverse effects that appear for the most ingredients

```sql
SELECT
    meddra_name,
    count(DISTINCT ingredient_id) AS n_ingredients
FROM
    product_label
    INNER JOIN product_to_rxnorm USING (label_id)
    INNER JOIN vocab_rxnorm_ingredient_to_product ON rxnorm_product_id = product_id
    INNER JOIN vocab_rxnorm_ingredient i ON ingredient_id = rxnorm_id
    INNER JOIN product_adverse_effect ON label_id = product_label_id
    INNER JOIN vocab_meddra_adverse_effect ON effect_meddra_id = meddra_id
GROUP BY
    meddra_name
ORDER BY
    n_ingredients DESC
LIMIT
    10;
```

## Find the adverse effects that appear most commonly on UK drug labels

```sql
SELECT
    meddra_name,
    count(DISTINCT label_id) AS n_products
FROM
    product_label
    INNER JOIN product_adverse_effect ON label_id = product_label_id
    INNER JOIN vocab_meddra_adverse_effect ON effect_meddra_id = meddra_id
WHERE
    source = 'UK'
GROUP BY
    meddra_name
ORDER BY
    n_products DESC
LIMIT
    10;
```

## Find the top ingredients that have the most labeled adverse effects

```sql
SELECT
    i.rxnorm_name,
    COUNT(DISTINCT meddra_id) AS n_adverse_effects
FROM
    product_label
    INNER JOIN product_to_rxnorm USING (label_id)
    INNER JOIN vocab_rxnorm_ingredient_to_product ON rxnorm_product_id = product_id
    INNER JOIN vocab_rxnorm_ingredient i ON ingredient_id = rxnorm_id
    INNER JOIN product_adverse_effect ON label_id = product_label_id
    INNER JOIN vocab_meddra_adverse_effect ON effect_meddra_id = meddra_id
GROUP BY
    i.rxnorm_name
ORDER BY
    n_adverse_effects DESC
LIMIT
    10;
```

## Find all products containing acetaminophen

```sql
SELECT
    DISTINCT pl.source_product_name, pl.source_label_url
FROM
    product_label pl
    INNER JOIN product_to_rxnorm USING (label_id)
    INNER JOIN vocab_rxnorm_ingredient_to_product ON rxnorm_product_id = product_id
    INNER JOIN vocab_rxnorm_ingredient i ON ingredient_id = rxnorm_id
WHERE
    i.rxnorm_name = 'acetaminophen';
```

## Compare the prevalence of nausea as an adverse effect between US and UK drug labels

```sql
SELECT
    pl.source,
    COUNT(DISTINCT label_id) AS products_with_nausea,
    (SELECT COUNT(DISTINCT label_id) FROM product_label WHERE source = pl.source) AS total_products,
    CAST(COUNT(DISTINCT label_id) AS REAL) / (SELECT COUNT(DISTINCT label_id) FROM product_label WHERE source = pl.source) AS fraction
FROM
    product_label pl
    INNER JOIN product_adverse_effect ON label_id = product_label_id
    INNER JOIN vocab_meddra_adverse_effect ON effect_meddra_id = meddra_id
WHERE
    meddra_name = 'Nausea'
    AND pl.source IN ('US', 'UK')
GROUP BY
    pl.source;
```

## Identify the most common adverse effects reported in a specific label section

```sql
SELECT
    meddra_name,
    COUNT(DISTINCT label_id) AS occurrence_count
FROM
    product_label
    INNER JOIN product_adverse_effect ON label_id = product_label_id
    INNER JOIN vocab_meddra_adverse_effect ON effect_meddra_id = meddra_id
WHERE
    label_section = 'WP'
GROUP BY
    meddra_name
ORDER BY
    occurrence_count DESC
LIMIT
    15;
```

## Find products with the highest confidence predictions for a specific adverse effect

```sql
SELECT
    pl.source_product_name,
    pae.pred1 AS confidence_score,
    pl.source_label_url
FROM
    product_label pl
    INNER JOIN product_adverse_effect pae ON pl.label_id = pae.product_label_id
    INNER JOIN vocab_meddra_adverse_effect vmae ON pae.effect_meddra_id = vmae.meddra_id
WHERE
    vmae.meddra_name = 'Anaphylaxis'
ORDER BY
    pae.pred1 DESC
LIMIT
    20;
```
