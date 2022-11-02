CREATE TABLE `adverse_reactions_bylabel` (
`section` varchar(2) DEFAULT NULL,
`zip_id` varchar(45) DEFAULT NULL,
`label_id` varchar(36) DEFAULT NULL,
`set_id` varchar(36) DEFAULT NULL,
`spl_version` int(11) DEFAULT NULL,
`pt_meddra_id` int(11) DEFAULT NULL,
`pt_meddra_term` varchar(53) DEFAULT NULL,
`meddra_id` double DEFAULT NULL,
`pred0` double DEFAULT NULL,
`pred1` double DEFAULT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

alter table adverse_reactions_bylabel add index (`zip_id`);
alter table adverse_reactions_bylabel add index (`label_id`);
alter table adverse_reactions_bylabel add index (`set_id`);
alter table adverse_reactions_bylabel add index (`spl_version`);
alter table adverse_reactions_bylabel add index (`pt_meddra_id`);

CREATE TABLE `boxed_warnings_bylabel` (
`section` varchar(2) DEFAULT NULL,
`zip_id` varchar(45) DEFAULT NULL,
`label_id` varchar(36) DEFAULT NULL,
`set_id` varchar(36) DEFAULT NULL,
`spl_version` int(11) DEFAULT NULL,
`pt_meddra_id` int(11) DEFAULT NULL,
`pt_meddra_term` varchar(53) DEFAULT NULL,
`meddra_id` double DEFAULT NULL,
`pred0` double DEFAULT NULL,
`pred1` double DEFAULT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

alter table boxed_warnings_bylabel add index (`zip_id`);
alter table boxed_warnings_bylabel add index (`label_id`);
alter table boxed_warnings_bylabel add index (`set_id`);
alter table boxed_warnings_bylabel add index (`spl_version`);
alter table boxed_warnings_bylabel add index (`pt_meddra_id`);

CREATE TABLE `adverse_reactions_bylabel_active` (
`section` varchar(2) DEFAULT NULL,
`zip_id` varchar(45) DEFAULT NULL,
`label_id` varchar(36) DEFAULT NULL,
`set_id` varchar(36) DEFAULT NULL,
`spl_version` int(11) DEFAULT NULL,
`pt_meddra_id` int(11) DEFAULT NULL,
`pt_meddra_term` varchar(53) DEFAULT NULL,
`meddra_id` double DEFAULT NULL,
`pred0` double DEFAULT NULL,
`pred1` double DEFAULT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

alter table adverse_reactions_bylabel_active add index (`zip_id`);
alter table adverse_reactions_bylabel_active add index (`label_id`);
alter table adverse_reactions_bylabel_active add index (`set_id`);
alter table adverse_reactions_bylabel_active add index (`spl_version`);
alter table adverse_reactions_bylabel_active add index (`pt_meddra_id`);

CREATE TABLE `boxed_warnings_bylabel_active` (
`section` varchar(2) DEFAULT NULL,
`zip_id` varchar(45) DEFAULT NULL,
`label_id` varchar(36) DEFAULT NULL,
`set_id` varchar(36) DEFAULT NULL,
`spl_version` int(11) DEFAULT NULL,
`pt_meddra_id` int(11) DEFAULT NULL,
`pt_meddra_term` varchar(53) DEFAULT NULL,
`meddra_id` double DEFAULT NULL,
`pred0` double DEFAULT NULL,
`pred1` double DEFAULT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

alter table boxed_warnings_bylabel_active add index (`zip_id`);
alter table boxed_warnings_bylabel_active add index (`label_id`);
alter table boxed_warnings_bylabel_active add index (`set_id`);
alter table boxed_warnings_bylabel_active add index (`spl_version`);
alter table boxed_warnings_bylabel_active add index (`pt_meddra_id`);

CREATE TABLE `rxnorm_mappings` (
`setid` varchar(36) DEFAULT NULL,
`spl_version` int(11) DEFAULT NULL,
`rxcui` int(11) DEFAULT NULL,
`rxstring` varchar(611) DEFAULT NULL,
`rxtty` varchar(4) DEFAULT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

alter table rxnorm_mappings add index (`setid`);
alter table rxnorm_mappings add index (`rxcui`);
alter table rxnorm_mappings add index (`rxtty`);

CREATE TABLE `dm_spl_zip_files_meta_data` (
`setid` varchar(37) DEFAULT NULL,
`zip_file_name` varchar(50) DEFAULT NULL,
`upload_date` varchar(10) DEFAULT NULL,
`spl_version` int(11) DEFAULT NULL,
`title` varchar(423) DEFAULT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

alter table dm_spl_zip_files_meta_data add index (`setid`);

CREATE TABLE `pharmacologic_class_mappings` (
`spl_setid` varchar(36) DEFAULT NULL,
`spl_version` int(11) DEFAULT NULL,
`pharma_setid` varchar(36) DEFAULT NULL,
`pharma_version` int(11) DEFAULT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

alter table dm_spl_zip_files_meta_data add index (`spl_setid`);
alter table dm_spl_zip_files_meta_data add index (`pharma_setid`);

CREATE TABLE `rxcui_setid_map` (
`setid` varchar(36) DEFAULT NULL,
`rxcui` int(11) DEFAULT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

alter table rxnorm_to_setid add index (`setid`);
alter table rxnorm_to_setid add index (`rxcui`);

CREATE TABLE `rxnorm_product_to_ingredient` (
`product_rx_cui` int(11) DEFAULT NULL,
`product_name` varchar(255) DEFAULT NULL,
`product_omop_concept_id` int(11) DEFAULT NULL,
`ingredient_rx_cui` int(11) DEFAULT NULL,
`ingredient_name` varchar(94) DEFAULT NULL,
`ingredient_omop_concept_id` int(11) DEFAULT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

alter table rxnorm_product_to_ingredient add index (`product_rx_cui`);
alter table rxnorm_product_to_ingredient add index (`product_omop_concept_id`);
alter table rxnorm_product_to_ingredient add index (`ingredient_rx_cui`);
alter table rxnorm_product_to_ingredient add index (`ingredient_omop_concept_id`);

CREATE TABLE `ingredients` (
`set_id` varchar(36) DEFAULT NULL,
`ingredient_rx_cui` int(11) DEFAULT NULL,
`ingredient_name` varchar(98) DEFAULT NULL,
`ingredient_omop_concept_id` int(11) DEFAULT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

alter table ingredients add index (`set_id`);
alter table ingredients add index (`ingredient_rx_cui`);
alter table ingredients add index (`ingredient_omop_concept_id`);

create table latest_labels_byingredient
select ingredient_concept_id, substring_index(group_concat(xml_id order by zip_id desc), ',', 1) latest_xml_id, substring_index(group_concat(zip_id order by zip_id desc), ',', 1) latest_zip_id
from ingredients
join label_map using (xml_id)
group by ingredient_concept_id;

create table adverse_reactions
select xml_id, c.concept_name, vocabulary_id, domain_id, concept_class_id, concept_code as meddra_id, concept_id as omop_concept_id, ingredients, concept_codes as rxnorm_ids, concept_ids as drug_concept_ids
from adverse_reactions_bylabel l
join latest_labels_bydrug on (xml_id = latest_xml_id)
join {OMOP_V5_SCHEMA}.concept c using (concept_code)
where vocabulary_id = 'MedDRA';

alter table adverse_reactions add index (`xml_id`);
alter table adverse_reactions add index (`meddra_id`);
alter table adverse_reactions add index (`omop_concept_id`);

create table boxed_warnings
select xml_id, c.concept_name, vocabulary_id, domain_id, concept_class_id, concept_code as meddra_id, concept_id as omop_concept_id, ingredients, concept_codes as rxnorm_ids, concept_ids as drug_concept_ids
from boxed_warnings_bylabel l
join latest_labels_bydrug on (xml_id = latest_xml_id)
join {OMOP_V5_SCHEMA}.concept c using (concept_code)
where vocabulary_id = 'MedDRA';

alter table boxed_warnings add index (`xml_id`);
alter table boxed_warnings add index (`meddra_id`);
alter table boxed_warnings add index (`omop_concept_id`);
