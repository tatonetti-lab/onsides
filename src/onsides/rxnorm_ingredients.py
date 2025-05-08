from pathlib import Path

import duckdb
import polars as pl
from bs4 import BeautifulSoup, Tag

rxtty_to_concept_class_ids: dict[str, list[str]] = {
    "BN": ["Brand Name"],
    "PIN": ["Precise Ingredient"],
    "DF": ["Dose Form"],
    "SBDC": ["Branded Drug Comp"],
    "SCD": ["Clinical Drug", "Quant Clinical Drug"],
    "BPCK": ["Branded Pack"],
    "IN": ["Ingredient"],
    "SCDF": ["Clinical Dose Form"],
    "SCDC": ["Clinical Drug Comp"],
    "SBD": ["Branded Drug", "Quant Branded Drug"],
    "DFG": ["Dose Form Group"],
    "MIN": ["Multiple Ingredients"],
    "SBDG": ["Branded Dose Group"],  # "Branded Dose Form Group"
    "GPCK": ["Clinical Pack"],  # "Generic Pack"
    "SBDF": ["Branded Drug Form"],
    "SCDG": ["Clinical Dose Group"],
}

concept_class_id_to_rxtty: dict[str, str] = {
    "Brand Name": "BN",
    "Precise Ingredient": "PIN",
    "Dose Form": "DF",
    "Branded Drug Comp": "SBDC",
    "Clinical Drug": "SCD",
    "Quant Clinical Drug": "SCD",
    "Branded Pack": "BPCK",
    "Ingredient": "IN",
    "Clinical Drug Form": "SCDF",
    "Clinical Drug Comp": "SCDC",
    "Branded Drug": "SBD",
    "Quant Branded Drug": "SBD",
    "Dose Form Group": "DFG",
    "Multiple Ingredients": "MIN",
    "Branded Dose Group": "SBDG",
    "Clinical Pack": "GPCK",
    "Branded Drug Form": "SBDF",
    "Clinical Dose Group": "SCDG",
}

# Determined by scanning OnSIDES v3.0 to see what concept_class_ids are
# represented among the products in product_label
starting_concept_class_ids = [
    "Clinical Drug",
    "Branded Drug",
    "Quant Clinical Drug",
    "Quant Branded Drug",
    "Brand Name",
    "Branded Pack",
    "Clinical Pack",
    "Ingredient",
    "Clinical Drug Comp",
    "Branded Drug Form",
    "Branded Drug Comp",
    "Clinical Drug Form",
    "Multiple Ingredients",
    "Precise Ingredient",
    "Branded Dose Group",
]

assert all(s in concept_class_id_to_rxtty for s in starting_concept_class_ids)


def extract_paths(table_path: Path, save_path: Path | None = None) -> list[str]:
    def parse_path(path_str: Tag):
        return path_str.text.strip().split(" => ")

    with open(table_path) as f:
        s = f.read()

    soup = BeautifulSoup(s, "html.parser")
    body = soup.find("tbody")
    assert isinstance(body, Tag)

    raw_rows = body.find_all("tr")

    rows = list()
    for row in raw_rows:
        assert isinstance(row, Tag)

        cells = row.find_all("td")
        assert len(cells) == 4

        _, b, _, d = cells
        assert isinstance(b, Tag)
        assert isinstance(d, Tag)
        rows.append(parse_path(b))
        rows.append(parse_path(d))

    assert 2 * len(raw_rows) == len(rows)  # Each source row has four columns
    if save_path is not None:
        pl.DataFrame({"path": rows}).write_parquet(save_path)
    return rows


def build_path_query(concept_class_id_path: list[list[str]]) -> str:
    # Format from [["A", "B"]] to ["('A', 'B')"]
    concept_class_id_strs = [
        "(" + ", ".join(f"'{item}'" for item in step) + ")"
        for step in concept_class_id_path
    ]

    n_concepts = len(concept_class_id_path)
    from_clause = """
        FROM sqlite_db.product_label
        INNER JOIN sqlite_db.product_to_rxnorm USING (label_id)
        INNER JOIN concept c1 ON rxnorm_product_id = c1.concept_code
    """
    where_clause = f"""
        WHERE c1.vocabulary_id IN ('RxNorm', 'RxNorm Extension')
          AND c1.concept_class_id IN {concept_class_id_strs[0]}
    """
    for i in range(2, n_concepts + 1):
        from_clause += f"""
            INNER JOIN concept_relationship cr{i - 1}
                ON c{i - 1}.concept_id = cr{i - 1}.concept_id_1
            INNER JOIN concept c{i} ON cr{i - 1}.concept_id_2 = c{i}.concept_id
        """
        where_clause += f"""
            AND c{i}.vocabulary_id IN ('RxNorm', 'RxNorm Extension')
            AND c{i}.concept_class_id IN {concept_class_id_strs[i - 1]}
        """

    tbl = f"c{n_concepts}"
    query = f"""
    SELECT DISTINCT rxnorm_product_id AS product_id,
           {tbl}.concept_code AS ingredient_id
    {from_clause}
    {where_clause}
    """
    return query.strip().replace("\n", " ")


def build_full_query(
    starting_concept_class_ids: list[str],
    paths: list[str] | None = None,
    save_path: Path | None = None,
) -> str:
    # Get all valid RxTTY starts
    rxtty_starts = {concept_class_id_to_rxtty[x] for x in starting_concept_class_ids}

    # Get all paths leading to ingredients
    if save_path is not None:
        paths = pl.read_parquet(save_path)["path"].to_list()

    assert paths is not None, "Paths must be provided"

    # Only keep those paths that end with Ingredients
    paths = [p for p in paths if p[-1] == "IN"]

    full_query = None
    for p in paths:
        if p[0] not in rxtty_starts:
            continue

        mapped_path = [rxtty_to_concept_class_ids[x] for x in p]
        path_query = build_path_query(mapped_path)
        if full_query is None:
            full_query = path_query
        else:
            full_query = f"{full_query} UNION {path_query}"

    assert isinstance(full_query, str)
    full_query = (
        f"CREATE TABLE sqlite_db.vocab_rxnorm_ingredient_to_product AS {full_query};"
    )
    return full_query


def generate_rxnorm_map(table_path: Path):
    paths = extract_paths(table_path)
    query = build_full_query(starting_concept_class_ids, paths)
    setup_queries = [
        "LOAD sqlite;",
        "ATTACH 'database/onsides.db' AS sqlite_db (TYPE sqlite);",
        "DROP TABLE IF EXISTS sqlite_db.vocab_rxnorm_ingredient_to_product",
        """CREATE TABLE IF NOT EXISTS concept AS
           SELECT *
           FROM
               read_csv(
                   'data/omop_vocab/CONCEPT.csv',
                   sep = '\t',
                   quote = ''
               );
        """,
        """CREATE TABLE IF NOT EXISTS concept_relationship AS
           SELECT *
           FROM
               read_csv(
                   'data/omop_vocab/CONCEPT_RELATIONSHIP.csv',
                   sep = '\t',
                   quote = ''
               );
        """,
    ]
    with duckdb.connect("duck.db") as con:
        for q in setup_queries:
            con.sql(q)
        con.sql(query)
