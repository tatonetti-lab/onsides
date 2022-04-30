CREATE TABLE `adverse_reactions_bylabel` (
`col0` int(11) DEFAULT NULL,
`xml_id` varchar(37) DEFAULT NULL,
`concept_name` varchar(53) DEFAULT NULL,
`concept_code` double DEFAULT NULL,
`pred0` double DEFAULT NULL,
`pred1` double DEFAULT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

# Prescription Drug Labels
load data local infile './bestepoch-bydrug-CB-output-part1_app8-AR_ref8-AR_222_24_10_1e-06_256_256.csv' into table adverse_reactions_bylabel fields terminated by ',' optionally enclosed by '"' lines terminated by '\n' ignore 1 lines;
load data local infile './bestepoch-bydrug-CB-output-part2_app8-AR_ref8-AR_222_24_10_1e-06_256_256.csv' into table adverse_reactions_bylabel fields terminated by ',' optionally enclosed by '"' lines terminated by '\n' ignore 1 lines;
load data local infile './bestepoch-bydrug-CB-output-part3_app8-AR_ref8-AR_222_24_10_1e-06_256_256.csv' into table adverse_reactions_bylabel fields terminated by ',' optionally enclosed by '"' lines terminated by '\n' ignore 1 lines;
load data local infile './bestepoch-bydrug-CB-output-part4_app8-AR_ref8-AR_222_24_10_1e-06_256_256.csv' into table adverse_reactions_bylabel fields terminated by ',' optionally enclosed by '"' lines terminated by '\n' ignore 1 lines;

alter table adverse_reactions_bylabel add index (`concept_code`);
alter table adverse_reactions_bylabel add index (`xml_id`);

CREATE TABLE `boxed_warnings_bylabel` (
`col0` int(11) DEFAULT NULL,
`xml_id` varchar(37) DEFAULT NULL,
`concept_name` varchar(53) DEFAULT NULL,
`concept_code` double DEFAULT NULL,
`pred0` double DEFAULT NULL,
`pred1` double DEFAULT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

# Prescription Drug Labels
load data local infile './bestepoch-bydrug-CB-output-part1-rx_app8-BW_ref8-BW_222_24_10_1e-06_256_256.csv' into table boxed_warnings_bylabel fields terminated by ',' optionally enclosed by '"' lines terminated by '\n' ignore 1 lines;
load data local infile './bestepoch-bydrug-CB-output-part2-rx_app8-BW_ref8-BW_222_24_10_1e-06_256_256.csv' into table boxed_warnings_bylabel fields terminated by ',' optionally enclosed by '"' lines terminated by '\n' ignore 1 lines;
load data local infile './bestepoch-bydrug-CB-output-part3-rx_app8-BW_ref8-BW_222_24_10_1e-06_256_256.csv' into table boxed_warnings_bylabel fields terminated by ',' optionally enclosed by '"' lines terminated by '\n' ignore 1 lines;
load data local infile './bestepoch-bydrug-CB-output-part4-rx_app8-BW_ref8-BW_222_24_10_1e-06_256_256.csv' into table boxed_warnings_bylabel fields terminated by ',' optionally enclosed by '"' lines terminated by '\n' ignore 1 lines;

alter table boxed_warnings_bylabel add index (`concept_code`);
alter table boxed_warnings_bylabel add index (`xml_id`);

CREATE TABLE `label_map` (
`xml_id` varchar(37) DEFAULT NULL,
`zip_id` varchar(46) DEFAULT NULL,
`set_id` varchar(37) DEFAULT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

load data local infile './labels_to_xmlfiles_to_drugs.txt' into table label_map fields terminated by '|' lines terminated by '\n';

alter table label_map add index (`xml_id`);
alter table label_map add index (`set_id`);

CREATE TABLE `rxnorm_map` (
`set_id` varchar(37) DEFAULT NULL,
`spl_version` int(11) DEFAULT NULL,
`rx_cui` int(11) DEFAULT NULL,
`rx_string` varchar(2300) DEFAULT NULL,
`rx_tty` varchar(4) DEFAULT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

load data local infile './rxnorm_mappings.txt' into table rxnorm_map fields terminated by '|' lines terminated by '\n' ignore 1 lines;

alter table rxnorm_map add index (`set_id`);
alter table rxnorm_map add index (`rx_cui`);
alter table rxnorm_map add index (`rx_tty`);

create table `rxnorm_to_setid`
select distinct set_id, rx_cui
from rxnorm_map;

alter table rxnorm_to_setid add index (`set_id`);
alter table rxnorm_to_setid add index (`rx_cui`);

create table rxnorm_product_to_ingredient
select a.concept_code product_concept_code, a.concept_name product_concept_name, a.concept_id product_concept_id,
	   b.concept_code ingredient_concept_code, b.concept_name ingredient_concept_name, b.concept_id ingredient_concept_id
from clinical_merge_v5_2022q1.concept a
join clinical_merge_v5_2022q1.concept_ancestor on (a.concept_id = descendant_concept_id)
join clinical_merge_v5_2022q1.concept b on (b.concept_id = ancestor_concept_id)
where a.vocabulary_id = 'RxNorm'
and b.vocabulary_id = 'RxNorm'
and b.concept_class_id = 'Ingredient';

alter table rxnorm_product_to_ingredient add index (`product_concept_code`);
alter table rxnorm_product_to_ingredient add index (`product_concept_id`);
alter table rxnorm_product_to_ingredient add index (`ingredient_concept_code`);
alter table rxnorm_product_to_ingredient add index (`ingredient_concept_id`);

create table ingredients
select xml_id, ingredient_concept_code, ingredient_concept_name, ingredient_concept_id, 'RxNorm' as vocabulary_id, 'Ingredient' as concept_class_id
from effect_onsides_v01.label_map
join effect_onsides_v01.rxnorm_to_setid using (set_id)
join effect_onsides_v01.rxnorm_product_to_ingredient on (product_concept_code = rx_cui)
group by xml_id, ingredient_concept_code, ingredient_concept_name, ingredient_concept_id;

alter table ingredients add index (`xml_id`);
alter table ingredients add index (`ingredient_concept_id`);
alter table ingredients add index (`ingredient_concept_code`);
alter table ingredients add index (`vocabulary_id`);
alter table ingredients add index (`concept_class_id`);

create table latest_labels_bydrug
select ingredient_concept_id, substring_index(group_concat(xml_id order by zip_id desc), ',', 1) latest_xml_id, substring_index(group_concat(zip_id order by zip_id desc), ',', 1) latest_zip_id
from ingredientspart
join label_map using (xml_id)
group by ingredient_concept_id;

SET session group_concat_max_len=15000;

create table latest_labels_bydrug
select ingredients, concept_codes, concept_ids, substring_index(group_concat(xml_id order by zip_id desc), ',', 1) latest_xml_id, substring_index(group_concat(zip_id order by zip_id desc), ',', 1) latest_zip_id
from
(
	select xml_id, group_concat(ingredient_concept_code order by ingredient_concept_code separator ', ') concept_codes,
			   group_concat(ingredient_concept_name order by ingredient_concept_code separator ', ') ingredients,
			   group_concat(ingredient_concept_id order by ingredient_concept_code separator ', ') concept_ids
	from ingredients
	group by xml_id
) ing
join label_map using (xml_id)
group by ingredients, concept_codes, concept_ids;

alter table latest_labels_bydrug modify latest_xml_id varchar(37);
alter table latest_labels_bydrug modify latest_zip_id varchar(46);
alter table latest_labels_bydrug add index (`latest_xml_id`);

create table adverse_reactions
select xml_id, c.concept_name, vocabulary_id, domain_id, concept_class_id, concept_code as meddra_id, concept_id as omop_concept_id, ingredients, concept_codes as rxnorm_ids, concept_ids as drug_concept_ids
from adverse_reactions_bylabel l
join latest_labels_bydrug on (xml_id = latest_xml_id)
join clinical_merge_v5_2022q1.concept c using (concept_code)
where vocabulary_id = 'MedDRA';

alter table adverse_reactions add index (`xml_id`);
alter table adverse_reactions add index (`meddra_id`);
alter table adverse_reactions add index (`omop_concept_id`);

create table boxed_warnings
select xml_id, c.concept_name, vocabulary_id, domain_id, concept_class_id, concept_code as meddra_id, concept_id as omop_concept_id, ingredients, concept_codes as rxnorm_ids, concept_ids as drug_concept_ids
from boxed_warnings_bylabel l
join latest_labels_bydrug on (xml_id = latest_xml_id)
join clinical_merge_v5_2022q1.concept c using (concept_code)
where vocabulary_id = 'MedDRA';

alter table boxed_warnings add index (`xml_id`);
alter table boxed_warnings add index (`meddra_id`);
alter table boxed_warnings add index (`omop_concept_id`);
