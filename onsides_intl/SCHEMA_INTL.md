# OnSIDES-INTL v2.0.0 schema/files description

We have tried to keep the schema for the adverse reaction tables for the OnSIDES-INTL databases as consistent as possible with the FDA-derived OnSIDES database. Any neccessary changes will be noted here. 

### adverse_reactions[.csv]

The `adverse_reactions` table/file is derived from the source OnSIDES data and created to be a convenient table to use for downstream analysis. This is one of the two primary tables that users of OnSIDES should use first as it should satisfy most of the use cases. Each drug ingredient or combination of ingredients is included in this table only once using the See [DATABASE.md](DATABASE.md) for specifics on how this table is created.

- `ingredient_rxcuis`, string list of comma separated RxNORM identifiers for the ingredients
- `ingredient_names`, string list of comma separated ingredients in the drug product (most are single but many combination medications as well)
- `num_ingredients`, number of ingredients in this drug product
- `pt_meddra_id`, the MedDRA preferred term code for the adverse reaction term identified
- `pt_meddra_term`, the MedDRA preferred term for the adverse reaction term identified
- `percent_labels`, the proportion of labels for which this adverse reaction was extracted (0-1)
- `num_labels`, the number of active labels for this ingredient or ingredient combination

### adverse_reactions_active_labels[.csv]

The adverse_reactions_active_labels table/file is derived from the source OnSIDES data and created to be a convenient table to use for downstream analysis. This is one of the two primary tables that users of OnSIDES should use first as it should satisfy most of the use cases. Each drug product (a drug product may be a single drug or a combination of drugs) is included in this table only once using the drug product's current active label (as determined by the meta data provided my DailyMed). See DATABASE.md for specifics on how this table is created.

- `set_id`, unique identifier for a group of SPLs, the `set_id` and `spl_version` uniquely identify a label
- `spl_version`, the version number of the SPL
- `pt_meddra_id`, the MedDRA preferred term code for the adverse reaction term identified
- `pt_meddra_term`, the MedDRA preferred term for the adverse reaction term identified
- `num_ingredients`, number of ingredients in this drug product
- `ingredient_rxcuis`, string list of comma separated RxNORM identifiers for the ingredients
- `ingredient_names`, string list of comma separated ingredients in the drug product (most are single but many combination medications as well)

### ingredients[.csv]

Ingredients for each drug product (`set_id`) as an RxNorm ingredient.

- `set_id`, identifier for a group of structured product label versions
- `ingredient_rx_cui`, RxNorm identifier for the ingredient
- `ingredient_name`, string description of the ingredient
- `ingredient_omop_concept_id`, OMOP concept identifier for the RxNorm term