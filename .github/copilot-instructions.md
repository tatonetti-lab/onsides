# AI Coding Agent Guidelines for OnSIDES

## Overview
OnSIDES is a comprehensive database of drugs and their adverse events, extracted from drug product labels using fine-tuned natural language processing models. The project is structured to support database generation, querying, and analysis workflows.

### Key Components:
1. **Data**: Raw data files and annotations are stored in the `data/` directory.
2. **Database**: Schema files and helper scripts for MySQL, PostgreSQL, and SQLite are in `database/schema/`.
3. **Source Code**: Python scripts for data processing, database interactions, and predictions are in `src/onsides/`.
4. **Snakemake Pipelines**: Workflow automation scripts for data parsing and evaluation are in `snakemake/`.
5. **Documentation**: Example queries and developer notes are in `docs/`.

---

## Developer Workflows

### Setting Up the Database
- Use the schema files in `database/schema/` to create the database.
- Example scripts for loading data:
  - `database_scripts/mysql.sh`
  - `database_scripts/postgres.sh`
  - `database_scripts/sqlite.sh`
- For PostgreSQL, use `data_our_improvements/schema/postgres_v3.1.0_fixed.sql` for the latest schema.

### Running Snakemake Pipelines
- Navigate to the appropriate subdirectory in `snakemake/` (e.g., `snakemake/eu/parse/`).
- Execute the pipeline:
  ```bash
  snakemake --snakefile Snakefile
  ```

### Querying the Database
- Example SQL queries are provided in `docs/README.md`.
- Use `summarize.sql` and `test.sql` in `database/` for testing and summarization.

---

## Project-Specific Conventions

### Code Organization
- Python modules are in `src/onsides/`.
  - `db.py`: Database connection utilities.
  - `predict.py`: Prediction logic using ClinicalBERT.
  - `stringsearch.py`: String matching utilities.

### Data Loading
- CSV files are in `data/csv/`.
- Use `load_remaining_onsides.sh` to load additional data.

### Testing
- Unit tests are in `src/onsides/test_stringsearch.py`.
- Run tests with:
  ```bash
  pytest src/onsides/
  ```

---

## Integration Points

### External Dependencies
- **Podman**: Used for containerized database setups.
- **pgloader**: For importing SQLite databases into PostgreSQL.
- **Snakemake**: Workflow management.

### Cross-Component Communication
- Data flows from `data/` to `database/` via schema scripts and loading utilities.
- Snakemake pipelines automate parsing and evaluation workflows.

---

## Examples

### Example Query: Find Ingredients for Renal Injury
```sql
SELECT DISTINCT i.*
FROM product_label
INNER JOIN product_to_rxnorm USING (label_id)
INNER JOIN vocab_rxnorm_ingredient_to_product ON rxnorm_product_id = product_id
INNER JOIN vocab_rxnorm_ingredient i ON ingredient_id = rxnorm_id
INNER JOIN product_adverse_effect ON label_id = product_label_id
INNER JOIN vocab_meddra_adverse_effect ON effect_meddra_id = meddra_id
WHERE meddra_name = 'Renal injury';
```

### Example Query: Fraction of US Products with Headache Label
```sql
WITH n_headache AS (
    SELECT COUNT(DISTINCT label_id) AS n
    FROM product_label
    INNER JOIN product_adverse_effect ON label_id = product_label_id
    INNER JOIN vocab_meddra_adverse_effect ON effect_meddra_id = meddra_id
    WHERE source = 'US' AND meddra_name = 'Headache'
),
n_overall AS (
    SELECT COUNT(DISTINCT label_id) AS n
    FROM product_label
    INNER JOIN product_adverse_effect ON label_id = product_label_id
    INNER JOIN vocab_meddra_adverse_effect ON effect_meddra_id = meddra_id
    WHERE source = 'US'
)
SELECT CAST(n_headache.n AS real) / n_overall.n AS frac_with_headache
FROM n_headache, n_overall;
```

---

## Contact
For questions or issues, refer to the [README.md](../README.md) or contact the maintainers via GitHub Issues.