-- Everything that maps to an RxNorm or RxNorm extension concept
CREATE TABLE if not exists concept AS
FROM
    read_csv(
        'data/omop_vocab/CONCEPT.csv',
        sep = '\t',
        quote = ''
    );

CREATE TABLE if not exists concept_relationship AS
FROM
    read_csv(
        'data/omop_vocab/CONCEPT_RELATIONSHIP.csv',
        sep = '\t',
        quote = ''
    );

COPY (
    SELECT
        c1.concept_name AS term,
        c2.concept_code
    FROM
        concept c1
        INNER JOIN concept_relationship cr ON c1.concept_id = cr.concept_id_1
        INNER JOIN concept c2 ON cr.concept_id_2 = c2.concept_id
    WHERE
        c2.vocabulary_id IN ('RxNorm', 'RxNorm Extension')
        AND cr.relationship_id = 'Maps to'
    UNION
    SELECT
        c.concept_name AS term,
        c.concept_code
    FROM
        concept c
    WHERE
        c.vocabulary_id IN ('RxNorm', 'RxNorm Extension')
) TO '_onsides/combined/rxnorm_terms.parquet' (format parquet);
