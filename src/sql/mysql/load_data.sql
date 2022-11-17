# Validated for MySQL 5.7.35
# Assumes working from directory with onsides release files

load data local infile './adverse_reactions_active_labels.csv'
into table adverse_reactions_active_labels
fields terminated by ',' optionally enclosed by '"'
lines terminated by '\r\n'
ignore 1 lines;

load data local infile './adverse_reactions_all_labels.csv'
into table adverse_reactions_all_labels
fields terminated by ',' optionally enclosed by '"'
lines terminated by '\r\n'
ignore 1 lines;

load data local infile './adverse_reactions.csv'
into table adverse_reactions
fields terminated by ',' optionally enclosed by '"'
lines terminated by '\r\n'
ignore 1 lines;

load data local infile './boxed_warnings_active_labels.csv'
into table boxed_warnings_active_labels
fields terminated by ',' optionally enclosed by '"'
lines terminated by '\r\n'
ignore 1 lines;

load data local infile './boxed_warnings_all_labels.csv'
into table boxed_warnings_all_labels
fields terminated by ',' optionally enclosed by '"'
lines terminated by '\r\n'
ignore 1 lines;

load data local infile './boxed_warnings.csv'
into table boxed_warnings
fields terminated by ',' optionally enclosed by '"'
lines terminated by '\r\n'
ignore 1 lines;

load data local infile './dm_spl_zip_files_meta_data.csv'
into table dm_spl_zip_files_meta_data
fields terminated by ',' optionally enclosed by '"'
lines terminated by '\n'
ignore 1 lines;

load data local infile './ingredients.csv'
into table ingredients
fields terminated by ',' optionally enclosed by '"'
lines terminated by '\r\n'
ignore 1 lines;

load data local infile './rxcui_setid_map.csv'
into table rxcui_setid_map
fields terminated by ',' optionally enclosed by '"'
lines terminated by '\n'
ignore 1 lines;

load data local infile './rxnorm_mappings.csv'
into table rxnorm_mappings
fields terminated by ',' optionally enclosed by '"'
lines terminated by '\n'
ignore 1 lines;

load data local infile './rxnorm_product_to_ingredient.csv'
into table rxnorm_product_to_ingredient
fields terminated by ',' optionally enclosed by '"'
lines terminated by '\r\n'
ignore 1 lines;
