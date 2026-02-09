-- Adapted SQL for derived tables in OnSIDES ETL
-- Uses final SQLite DB table names and SQLite-compatible functions

drop table if exists derived_ingred_to_adr_cnt;
create table derived_ingred_to_adr_cnt as 
with labs as (
 select distinct ptr.rxnorm_product_id,  
                 pl.* 
 from product_to_rxnorm ptr 
   inner join product_label pl on pl.label_id = ptr.label_id
)
select distinct c2.rxnorm_id ingred_concept_id, c2.rxnorm_id ingred_rxcui, c2.rxnorm_name ingred_name, label_section, 
       c1.meddra_id meddra_concept_id, c1.meddra_id meddra_code, c1.meddra_name meddra_term, c1.meddra_term_type meddra_term_type,
       count(distinct pae.product_label_id) cnt
from labs 
  inner join product_adverse_effect pae on pae.product_label_id = labs.label_id
  inner join vocab_meddra_adverse_effect c1 on c1.meddra_id = pae.effect_meddra_id
  inner join vocab_rxnorm_ingredient_to_product ca on ca.product_id = labs.rxnorm_product_id
  inner join vocab_rxnorm_ingredient c2 on ca.ingredient_id = c2.rxnorm_id  
where c2.rxnorm_term_type = 'Ingredient'
  and pae.match_method = 'PMB' 
  and labs.source = 'US'  
  and pae.pred1 >= 3.258
group by c2.rxnorm_id, c2.rxnorm_id, c2.rxnorm_name, label_section,
       c1.meddra_id, c1.meddra_id, c1.meddra_name, c1.meddra_term_type
order by ingred_name, label_section, meddra_term, meddra_term_type;

create index derived_ingred_to_adr_cnt_ingred_rxcui_idx on derived_ingred_to_adr_cnt(ingred_rxcui);
create index derived_ingred_to_adr_cnt_ingred_meddra_code_idx on derived_ingred_to_adr_cnt(meddra_code);

drop table if exists derived_branded_product_labels;
create table derived_branded_product_labels as
select distinct substr(pl.source_product_id, 1, instr(pl.source_product_id, '.') - 1) AS setid, 
                substr(pl.source_product_id, instr(pl.source_product_id, '.') + 1) AS label_version,
                c1.rxnorm_name label_title,                                
                c2.rxnorm_id ingred_concept_id, c2.rxnorm_id ingred_rxcui, c2.rxnorm_name ingred_name
from product_to_rxnorm ptr 
  inner join product_label pl on pl.label_id = ptr.label_id
  inner join vocab_rxnorm_product c1 on c1.rxnorm_id = ptr.rxnorm_product_id
  inner join vocab_rxnorm_ingredient_to_product ca on c1.rxnorm_id = ca.product_id
  inner join vocab_rxnorm_ingredient c2 on c2.rxnorm_id = ca.ingredient_id 
where pl.source = 'US'
 and c1.rxnorm_term_type in ('Branded Dose Group','Branded Drug','Branded Drug Comp','Branded Drug Form','Branded Pack','Brand Name')
 and c2.rxnorm_term_type = 'Ingredient';

create index derived_branded_product_labels_ingred_rxcui on derived_branded_product_labels(ingred_rxcui);
create index derived_branded_product_labels_ingred_setid on derived_branded_product_labels(setid);

drop table if exists derived_generic_product_labels;
create table derived_generic_product_labels as
select distinct substr(pl.source_product_id, 1, instr(pl.source_product_id, '.') - 1) AS setid, 
                substr(pl.source_product_id, instr(pl.source_product_id, '.') + 1) AS label_version,
                c1.rxnorm_name label_title,                                
                c2.rxnorm_id ingred_concept_id, c2.rxnorm_id ingred_rxcui, c2.rxnorm_name ingred_name
from product_to_rxnorm ptr 
  inner join product_label pl on pl.label_id = ptr.label_id
  inner join vocab_rxnorm_product c1 on c1.rxnorm_id = ptr.rxnorm_product_id
  inner join vocab_rxnorm_ingredient_to_product ca on c1.rxnorm_id = ca.product_id
  inner join vocab_rxnorm_ingredient c2 on c2.rxnorm_id = ca.ingredient_id 
where pl.source = 'US'
 and c1.rxnorm_term_type not in ('Branded Dose Group','Branded Drug','Branded Drug Comp','Branded Drug Form','Branded Pack','Brand Name')
 and c2.rxnorm_term_type = 'Ingredient';

create index derived_generic_product_labels_ingred_rxcui on derived_generic_product_labels(ingred_rxcui);
create index derived_generic_product_labels_ingred_setid on derived_generic_product_labels(setid);
