# OnSIDES v2.0.0 schema/files description

Samples of each of these files is available in [release_sample](release_sample).

## adverse_reactions[.csv]

The `adverse_reactions` table/file is derived from the source OnSIDES data and created to be a convenient table to use for downstream analysis. This is one of the two primary tables that users of OnSIDES should use first as it should satisfy most of the use cases. Each drug ingredient or combination of ingredients is included in this table only once using the See [DATABASE.md](DATABASE.md) for specifics on how this table is created.

- `ingredient_rxcuis`, string list of comma separated RxNORM identifiers for the ingredients
- `ingredient_names`, string list of comma separated ingredients in the drug product (most are single but many combination medications as well)
- `num_ingredients`, number of ingredients in this drug product
- `pt_meddra_id`, the MedDRA preferred term code for the adverse reaction term identified
- `pt_meddra_term`, the MedDRA preferred term for the adverse reaction term identified
- `percent_labels`, the proportion of labels for which this adverse reaction was extracted (0-1)
- `num_labels`, the number of active labels for this ingredient or ingredient combination

## adverse_reactions_active_labels[.csv]

The `adverse_reactions_active_labels` table/file is derived from the source OnSIDES data and created to be a convenient table to use for downstream analysis. This is one of the two primary tables that users of OnSIDES should use first as it should satisfy most of the use cases. Each drug product (a drug product may be a single drug or a combination of drugs) is included in this table only once using the drug product's current active label (as determined by the meta data provided my DailyMed). See [DATABASE.md](DATABASE.md) for specifics on how this table is created.

- `set_id`, unique identifier for a group of SPLs, the `set_id` and `spl_version` uniquely identify a label
- `spl_version`, the version number of the SPL
- `pt_meddra_id`, the MedDRA preferred term code for the adverse reaction term identified
- `pt_meddra_term`, the MedDRA preferred term for the adverse reaction term identified
- `num_ingredients`, number of ingredients in this drug product
- `ingredient_rxcuis`, string list of comma separated RxNORM identifiers for the ingredients
- `ingredient_names`, string list of comma separated ingredients in the drug product (most are single but many combination medications as well)

## adverse_reactions_all_labels[.csv]

Filtered output from the model joined with the example file. Rows are filtered for those with scores (pred1) above the decision threshold (see the `release.json` file for threshold values).

- `section`, the code for the section of the structured product label (SPL), AR for adverse reactions
- `zip_id`, identifier for the structured product label zip download file
- `label_id`, unique identifier for this version of the SPL
- `set_id`, unique identifier for a group of SPLs, the `set_id` and `spl_version` uniquely identify a label
- `spl_version`, the version number of the SPL
- `pt_meddra_id`, the MedDRA preferred term code for the adverse reaction term identified
- `pt_meddra_term`, the MedDRA preferred term for the adverse reaction term identified
- `pred0`, score from the model that the MedDRA term is not a reported drug side effect
- `pred1`, score from the model that the MedDRA term is a reported drug side effect

## boxed_warnings[.csv]

The `boxed_warnings` table/file is derived from the source OnSIDES data and created to be a convenient table to use for downstream analysis. This is one of the two primary tables that users of OnSIDES should use first as it should satisfy most of the use cases. Each drug ingredient or combination of ingredients is included in this table only once using the See [DATABASE.md](DATABASE.md) for specifics on how this table is created.

- `ingredient_rxcuis`, string list of comma separated RxNORM identifiers for the ingredients
- `ingredient_names`, string list of comma separated ingredients in the drug product (most are single but many combination medications as well)
- `num_ingredients`, number of ingredients in this drug product
- `pt_meddra_id`, the MedDRA preferred term code for the adverse reaction term identified
- `pt_meddra_term`, the MedDRA preferred term for the adverse reaction term identified
- `percent_labels`, the proportion of labels for which this adverse reaction was extracted (0-1)
- `num_labels`, the number of active labels for this ingredient or ingredient combination

## boxed_warnings_active_labels[.csv]

Same as the `adverse_reactions_active_labels` table above except for the BOXED WARNINGS section of the structured product label. Note that the performance for this section is significantly lower than that found for the ADVERSE REACTIONS section. See the [README.md](README.md) file for the latest performance metrics.

- `set_id`, unique identifier for a group of SPLs, the `set_id` and `spl_version` uniquely identify a label
- `spl_version`, the version number of the SPL
- `pt_meddra_id`, the MedDRA preferred term code for the adverse reaction term identified
- `pt_meddra_term`, the MedDRA preferred term for the adverse reaction term identified
- `num_ingredients`, number of ingredients in this drug product
- `ingredient_rxcuis`, string list of comma separated RxNORM identifiers for the ingredients
- `ingredient_names`, string list of comma separated ingredients in the drug product (most are single but many combination medications as well)

## boxed_warnings_all_labels[.csv]

Filtered output from the model joined with the example file. Rows are filtered for those with scores (pred1) above the decision threshold (see the `release.json` file for threshold values).

- `section`, the code for the section of the structured product label (SPL), AR for adverse reactions
- `zip_id`, identifier for the structured product label zip download file
- `label_id`, unique identifier for this version of the SPL
- `set_id`, unique identifier for a group of SPLs, the `set_id` and `spl_version` uniquely identify a label
- `spl_version`, the version number of the SPL
- `pt_meddra_id`, the MedDRA preferred term code for the adverse reaction term identified
- `pt_meddra_term`, the MedDRA preferred term for the adverse reaction term identified
- `pred0`, score from the model that the MedDRA term is not a reported drug side effect
- `pred1`, score from the model that the MedDRA term is a reported drug side effect

## ingredients[.csv]

Ingredients for each drug product (`set_id`) as an RxNorm ingredient.

- `set_id`, identifier for a group of structured product label versions
- `ingredient_rx_cui`, RxNorm identifier for the ingredient
- `ingredient_name`, string description of the ingredient
- `ingredient_omop_concept_id`, OMOP concept identifier for the RxNorm term

## rxnorm_mappings[.csv]

File provided by DailyMed that maps drug products to their RxNorm identifiers. Included here to preserve the version of the file used to create the database.

- `set_id`, identifier for a group of structured product label (SPL) versions
- `spl_version`, structured product label version
- `rx_cui`, RxNorm identifier for the drug product (note this isn't the ingredient level identifier as is used in other tables)
- `rx_string`, RxNorm drug product description
- `rx_tty`, RxNorm term type (https://www.nlm.nih.gov/research/umls/rxnorm/docs/appendix5.html)

## dm_spl_zip_files_meta_data[.csv]

File provided by DailyMed that identifies which version of the label is the current version. Used to create `adverse_reactions` from `adverse_reactions_all_labels`. Included here to preserve the version of the file used to create the database.

- `set_id`, identifier for a group of structured product label (SPL) versions
- `zip_file_name`, file name of the SPL zip archive
- `upload_date`, date label version was uploaded (MM/DD/YYYY)
- `spl_version`, the current version of the label for the `set_id`
- `title`, the product title
