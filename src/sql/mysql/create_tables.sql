# These queries were validated against MySQL 5.7.35

CREATE TABLE `adverse_reactions` (
`ingredients_rxcuis` varchar(255) DEFAULT NULL,
`ingredients_names` varchar(255) DEFAULT NULL,
`num_ingredients` int(11) DEFAULT NULL,
`pt_meddra_id` int(11) DEFAULT NULL,
`pt_meddra_term` varchar(53) DEFAULT NULL,
`percent_labels` double DEFAULT NULL,
`num_labels` int(11) DEFAULT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

alter table adverse_reactions add index (`ingredients_rxcuis`);
alter table adverse_reactions add index (`pt_meddra_id`);

CREATE TABLE `boxed_warnings` (
`ingredients_rxcuis` varchar(255) DEFAULT NULL,
`ingredients_names` varchar(255) DEFAULT NULL,
`num_ingredients` int(11) DEFAULT NULL,
`pt_meddra_id` int(11) DEFAULT NULL,
`pt_meddra_term` varchar(53) DEFAULT NULL,
`percent_labels` double DEFAULT NULL,
`num_labels` int(11) DEFAULT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

alter table boxed_warnings add index (`ingredients_rxcuis`);
alter table boxed_warnings add index (`pt_meddra_id`);

CREATE TABLE `warnings_and_precautions` (
`ingredients_rxcuis` varchar(255) DEFAULT NULL,
`ingredients_names` varchar(255) DEFAULT NULL,
`num_ingredients` int(11) DEFAULT NULL,
`pt_meddra_id` int(11) DEFAULT NULL,
`pt_meddra_term` varchar(53) DEFAULT NULL,
`percent_labels` double DEFAULT NULL,
`num_labels` int(11) DEFAULT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

alter table warnings_and_precautions add index (`ingredients_rxcuis`);
alter table warnings_and_precautions add index (`pt_meddra_id`);

CREATE TABLE `adverse_reactions_all_labels` (
`section` varchar(2) DEFAULT NULL,
`zip_id` varchar(45) DEFAULT NULL,
`label_id` varchar(36) DEFAULT NULL,
`set_id` varchar(36) DEFAULT NULL,
`spl_version` int(11) DEFAULT NULL,
`pt_meddra_id` int(11) DEFAULT NULL,
`pt_meddra_term` varchar(53) DEFAULT NULL,
`pred0` double DEFAULT NULL,
`pred1` double DEFAULT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

alter table adverse_reactions_all_labels add index (`zip_id`);
alter table adverse_reactions_all_labels add index (`label_id`);
alter table adverse_reactions_all_labels add index (`set_id`);
alter table adverse_reactions_all_labels add index (`spl_version`);
alter table adverse_reactions_all_labels add index (`pt_meddra_id`);

CREATE TABLE `boxed_warnings_all_labels` (
`section` varchar(2) DEFAULT NULL,
`zip_id` varchar(45) DEFAULT NULL,
`label_id` varchar(36) DEFAULT NULL,
`set_id` varchar(36) DEFAULT NULL,
`spl_version` int(11) DEFAULT NULL,
`pt_meddra_id` int(11) DEFAULT NULL,
`pt_meddra_term` varchar(53) DEFAULT NULL,
`pred0` double DEFAULT NULL,
`pred1` double DEFAULT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

alter table boxed_warnings_all_labels add index (`zip_id`);
alter table boxed_warnings_all_labels add index (`label_id`);
alter table boxed_warnings_all_labels add index (`set_id`);
alter table boxed_warnings_all_labels add index (`spl_version`);
alter table boxed_warnings_all_labels add index (`pt_meddra_id`);

CREATE TABLE `warnings_and_precautions_all_labels` (
`section` varchar(2) DEFAULT NULL,
`zip_id` varchar(45) DEFAULT NULL,
`label_id` varchar(36) DEFAULT NULL,
`set_id` varchar(36) DEFAULT NULL,
`spl_version` int(11) DEFAULT NULL,
`pt_meddra_id` int(11) DEFAULT NULL,
`pt_meddra_term` varchar(53) DEFAULT NULL,
`pred0` double DEFAULT NULL,
`pred1` double DEFAULT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

alter table warnings_and_precautions_all_labels add index (`zip_id`);
alter table warnings_and_precautions_all_labels add index (`label_id`);
alter table warnings_and_precautions_all_labels add index (`set_id`);
alter table warnings_and_precautions_all_labels add index (`spl_version`);
alter table warnings_and_precautions_all_labels add index (`pt_meddra_id`);

CREATE TABLE `adverse_reactions_active_labels` (
`set_id` varchar(36) DEFAULT NULL,
`spl_version` int(11) DEFAULT NULL,
`pt_meddra_id` int(11) DEFAULT NULL,
`pt_meddra_term` varchar(53) DEFAULT NULL,
`num_ingredients` int(11) DEFAULT NULL,
`ingredients_rxcuis` varchar(255) DEFAULT NULL,
`ingredients_names` varchar(255) DEFAULT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

alter table adverse_reactions_active_labels add index (`set_id`);
alter table adverse_reactions_active_labels add index (`spl_version`);
alter table adverse_reactions_active_labels add index (`pt_meddra_id`);

CREATE TABLE `boxed_warnings_active_labels` (
`set_id` varchar(36) DEFAULT NULL,
`spl_version` int(11) DEFAULT NULL,
`pt_meddra_id` int(11) DEFAULT NULL,
`pt_meddra_term` varchar(53) DEFAULT NULL,
`num_ingredients` int(11) DEFAULT NULL,
`ingredients_rxcuis` varchar(255) DEFAULT NULL,
`ingredients_names` varchar(255) DEFAULT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

alter table boxed_warnings_active_labels add index (`set_id`);
alter table boxed_warnings_active_labels add index (`spl_version`);
alter table boxed_warnings_active_labels add index (`pt_meddra_id`);

CREATE TABLE `warnings_and_precautions_active_labels` (
`set_id` varchar(36) DEFAULT NULL,
`spl_version` int(11) DEFAULT NULL,
`pt_meddra_id` int(11) DEFAULT NULL,
`pt_meddra_term` varchar(53) DEFAULT NULL,
`num_ingredients` int(11) DEFAULT NULL,
`ingredients_rxcuis` varchar(255) DEFAULT NULL,
`ingredients_names` varchar(255) DEFAULT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

alter table warnings_and_precautions_active_labels add index (`set_id`);
alter table warnings_and_precautions_active_labels add index (`spl_version`);
alter table warnings_and_precautions_active_labels add index (`pt_meddra_id`);

CREATE TABLE `rxnorm_mappings` (
`setid` varchar(36) DEFAULT NULL,
`spl_version` int(11) DEFAULT NULL,
`rxcui` int(11) DEFAULT NULL,
`rxstring` TEXT DEFAULT NULL,
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
`title` TEXT DEFAULT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

alter table dm_spl_zip_files_meta_data add index (`setid`);

CREATE TABLE `rxcui_setid_map` (
`setid` varchar(36) DEFAULT NULL,
`rxcui` int(11) DEFAULT NULL
) ENGINE=MyISAM DEFAULT CHARSET=latin1;

alter table rxcui_setid_map add index (`setid`);
alter table rxcui_setid_map add index (`rxcui`);

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
