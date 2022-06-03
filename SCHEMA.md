# OnSIDES schema/tables description

## adverse_reactions[.csv]

The `adverse_reactions` table/file is derived from the source OnSIDES data and created to be a convenient table to use for downstream analysis. This is the primary table that users of OnSIDES should use first as it should satisfy most of the use cases. For this reason we have included links out to outside vocabularies within the table. Each drug product (a drug product may be a single drug or a combination of drugs) is included in this table only once using the drug product's most recent label. See the `src/load_onsides_db.sql` script for specifics on how this table is created.

- `xml_id`, identifier for the structured product label xml file
- `concept_name`, string description of the MedDRA concept
- `vocabulary_id`, OMOP vocabulary identifier (in this case they are all currently MedDRA terms)
- `domain_id`, OMOP domain identifier (currently this is only Condition)
- `concept_class_id`, MedDRA class, either PT (preferred term) or LLT (lower level term)
- `meddra_id`, MedDRA identifier for the side effect term
- `omop_concept_id`, OMOP identifier for the side effect term
- `ingredients`, string list of comma separated ingredients in the drug product (most are single but many combination medications as well)
- `rxnorm_ids`, string list of comma separated RxNORM identifiers for the ingredients
- `drug_concept_ids`, string list of comma separeated OMOP concept identiers for the ingredients


## adverse_reactions_bylabel[.csv]

Filtered output from the model. Rows are filtered for those with scores (pred1) above the decision threshold.

- `row_id`, internal identifier resulting from the analysis
- `xml_id`, identifier for the structured product label xml file
- `concept_name`, string description of the MedDRA concept
- `concept_code`, MedDRA concept identifier
- `pred0`, score from the model that the MedDRA term is not a reported drug side effect
- `pred1', score from the model that the MedDRA term is a reported drug side effect

## boxed_warnings[.csv]

Same as the `adverse_reactions` table above except for the BOXED WARNINGS section of the structured product label. Note that the performance for this section is significantly lower than that found for the ADVERSE REACTIONS section. See the `src/load_onsides_db.sql` script for specifics on how this table is created.

- `xml_id`, identifier for the structured product label xml file
- `concept_name`, string description of the MedDRA concept
- `vocabulary_id`, OMOP vocabulary identifier (in this case they are all currently MedDRA terms)
- `domain_id`, OMOP domain identifier (currently this is only Condition)
- `concept_class_id`, MedDRA class, either PT (preferred term) or LLT (lower level term)
- `meddra_id`, MedDRA identifier for the side effect term
- `omop_concept_id`, OMOP identifier for the side effect term
- `ingredients`, string list of comma separated ingredients in the drug product (most are single but many combination medications as well)
- `rxnorm_ids`, string list of comma separated RxNORM identifiers for the ingredients
- `drug_concept_ids`, string list of comma separeated OMOP concept identiers for the ingredients

## boxed_warnings_bylabel[.csv]

Same as the `adverse_reactions_by_label` above except for the BOXED WARNINGS section of the structured product label.

- `row_id`, internal identifier resulting from the analysis
- `xml_id`, identifier for the structured product label xml file
- `concept_name`, string description of the MedDRA concept
- `concept_code`, MedDRA concept identifier
- `pred0`, score from the model that the MedDRA term is not a reported drug side effect
- `pred1', score from the model that the MedDRA term is a reported drug side effect

## ingredients[.csv]

Map of ingredients, identified in RxNorm, to the structured product labels, identified by xml_id.

- `xml_id`, identifier for the structured product label xml file
- `ingredient_concept_code`, RxNorm identifier for the ingredient
- `ingredient_concept_name`, string description of the ingredient
- `ingredient_concept_id`, OMOP concept identifier for the RxNorm term
- `vocabulary_id`, OMOP vocabulary identifier (currently all RxNorm)
- `concept_class_id`, RxNorm term class (currently all Ingredient)

## label_map[.csv]

- `xml_id`, identifier for the structured product label xml file
- `zip_id`, identifier for the zip file which contains the xml file and some supporting images
- `set_id`, the drug product id

## latest_labels_bydrug[.csv]

- `ingredients`, string list of comma separated ingredient names
- `concept_codes`, string list of comma separated RxNorm identifiers
- `concept_ids`, string list of comma separated OMOP ingredient identifiers
- `latest_xml_id`, xml_id for the most recently released structured product label for this combination of ingredients
- `latest_zip_id`, zip_id for the most recently released structured product label for this combination of ingredients

## rxnorm_map[.csv]

- `set_id`, FDA drug product identifier
- `spl_version`, structured product label version
- `rx_cui`, RxNorm identifier for the drug product (note this isn't the ingredient level identifier as is used in other tables)
- `rx_string`, RxNorm drug product description
- `rx_tty`, RxNorm term type (https://www.nlm.nih.gov/research/umls/rxnorm/docs/appendix5.html)

## rxnorm_product_to_ingredients[.csv]

- `product_concept_code`, RxNorm drug product identifier
- `product_concept_name`, RxNorm drug product description string
- `product_concept_id`, OMOP drug product identifier
- `ingredient_concept_code`, RxNorm ingredient identifier
- `ingredient_concept_name`, RxNorm ingredient description string
- `ingredient_concept_id`, OMOP ingredient identifier

## rxnorm_to_setid[.csv]

- `set_id`, FDA drug product set identifier
- `rx_cui`, RxNorm drug product identifier





