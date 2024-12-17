import numpy as np 
import pandas as pd
import requests
from tqdm import tqdm
import ast, re
from time import sleep
import argparse
import warnings
warnings.filterwarnings('ignore')
import os
import collections

def main():
    print('run the model')
    parser = argparse.ArgumentParser(description='let the code know where the data is held')
    parser.add_argument('--data_folder', required=True, help='Path to the data folder.')
    parser.add_argument('--external_data', required=True, help='Path to the where the external data is housed.')
    parser.add_argument('--final_data', required=True, help='Path to the where the final output should be written.')

    args = parser.parse_args()
    data_folder = args.data_folder
    external_data_folder = args.external_data
    final_folder = args.final_data
    
    #read in free-text data
    free_text_df = pd.read_csv(data_folder+'ade_text_table_onsides_pred.csv')
    free_text_df = free_text_df[free_text_df.pt_meddra_id.notna()]
    #read in tabular data
    tabular_df = pd.read_csv(data_folder+'parsed_ade_tabular.csv')
    tabular_df['exact_match_list'] = tabular_df['exact_match_list'].apply(lambda x: ast.literal_eval(x))
    tabular_df['matched_codes'] = tabular_df['matched_codes'].apply(lambda x: ast.literal_eval(x))

    tab_df = tabular_df.explode(['exact_match_list', 'matched_codes'])[['drug', 'exact_match_list', 'matched_codes']]
    tab_df.columns = ['drug', 'pt_meddra_term', 'pt_meddra_id']
    txt_df = free_text_df[['label_id', 'pt_meddra_term', 'pt_meddra_id']]
    txt_df.columns = ['drug', 'pt_meddra_term', 'pt_meddra_id']
    print(tab_df.shape[0], txt_df.shape[0])
    ade_all_labels = pd.concat([tab_df, txt_df]).drop_duplicates()
    print(ade_all_labels.shape[0])

    #the ingredients dataframe
    ingr_df = pd.read_csv(data_folder+'ingredients.csv')

    #read in external athena data. TODO : incorporate this step into map_drugs_to_rxnorm.py instead of here. 
    rxnorm = pd.read_csv(external_data_folder+'athena_rxnorm_atc/CONCEPT.csv', delimiter = '\t')
    rxnorm = rxnorm[(rxnorm.domain_id == 'Drug')&(rxnorm.vocabulary_id.isin(['RxNorm', 'RxNorm Extension']))&(rxnorm.concept_class_id.str.contains('Ingredient'))]
    rxnorm['concept_name'] = rxnorm['concept_name'].apply(lambda x: x.lower())
    rxnorm['concept_code'] = rxnorm['concept_code'].astype(str)
    rxnorm_concept_rxnorm = dict(zip(rxnorm.concept_code, rxnorm.concept_id))

    #format the final ingredient dataframe
    ingr_df['rxnorm_code'] = ingr_df['rxnorm_code'].apply(lambda x: [str(i) for i in x] if x != '' else '')
    ingr_df['omop_concept_id'] = ingr_df['rxnorm_code'].apply(lambda x: [rxnorm_concept_rxnorm[i] for i in x if i in rxnorm_concept_rxnorm.keys()] if x != '' else '')
    ingr_final = ingr_df[['Product number', 'International non-proprietary name (INN) / common name', 'rxnorm_code', 'num_ingredients', 'omop_concept_id']]
    ingr_final.columns = ['product_id', 'ingredients', 'num_ingredients', 'rxnorm_id', 'omop_concept_id']
    ingr_final.to_csv(final_folder+'ingredients.csv', index=False)

    #generate the all-label dataframe
    ade_all_labels = ade_all_labels.merge(ingr_df, left_on = 'drug', right_on = 'Medicine name', how = 'left')
    ade_all_labels = ade_all_labels[['Product number', 'Medicine name', 'International non-proprietary name (INN) / common name', 'rxnorm_code', 'pt_meddra_id', 'pt_meddra_term', 'num_ingredients', 'Authorisation status']]
    ade_all_labels.columns = ['product_id', 'drug_name', 'ingredient_names', 'ingredient_codes', 'pt_meddra_id', 'pt_meddra_term', 'num_ingredients', 'auth']
    ade_all_labels.to_csv(final_folder+'adverse_events_all_labels.csv', index=False)

    #filter for only active labels
    ade_all_labels_active = ade_all_labels[ade_all_labels.auth == 'Authorised']
    ade_all_labels_active.to_csv(final_folder+'adverse_events_active_labels.csv', index=False)

    #finally, generate the main dataframe
    ade_all_labels['ingredient_codes'] = ade_all_labels.ingredient_codes.apply(lambda x: str(x).replace("'",'').replace('[','').replace(']',''))
    ade_all_labels['pt_meddra_id'] = ade_all_labels['pt_meddra_id'].apply(lambda x: int(float(x)) if str(x) != 'nan' else '')
    uniq_ingr = ade_all_labels[['drug_name', 'ingredient_names', 'ingredient_codes', 'num_ingredients']].drop_duplicates()
    uniq_ingr = uniq_ingr.groupby('ingredient_codes')['drug_name'].apply(list).reset_index()
    uniq_ingr['num_labels'] = uniq_ingr.drug_name.apply(lambda x: len(x))
    uniq_event = ade_all_labels[['pt_meddra_id', 'pt_meddra_term']].drop_duplicates()
    ade_count = ade_all_labels[['ingredient_codes', 'pt_meddra_id']].groupby('ingredient_codes')['pt_meddra_id'].apply(list).reset_index()
    ade_count['pt_meddra_list'] = ade_count['pt_meddra_id'].apply(lambda x: collections.Counter(x))
    ade_count['pt_meddra_id'] = ade_count['pt_meddra_list'].apply(lambda x: x.keys())
    ade_count = ade_count.explode('pt_meddra_id')
    ade_count['num_events'] = ade_count.apply(lambda x: x['pt_meddra_list'][x['pt_meddra_id']], axis = 1)
    ade_all_labels = uniq_ingr.merge(ade_count[['ingredient_codes', 'pt_meddra_id', 'num_events']], on = 'ingredient_codes', how = 'left')
    ade_all_labels['pct_labels'] = ade_all_labels.apply(lambda x: x['num_events'] / x['num_labels'], axis = 1)
    ade_all_labels = ade_all_labels.merge(uniq_event, on = 'pt_meddra_id', how = 'left')

    ades = uniq_ingr.merge(ade_count[['ingredient_codes', 'pt_meddra_id', 'num_events']], on = 'ingredient_codes', how = 'left')
    ades['pct_labels'] = ades.apply(lambda x: x['num_events'] / x['num_labels'], axis = 1)
    ades = ades.merge(uniq_event, on = 'pt_meddra_id', how = 'left')
    ades = ades.drop(['drug_name', 'product_id', 'auth'], axis = 1).drop_duplicates()
    ades.to_csv(final_folder+'adverse_events.csv', index=False) 

if __name__ == '__main__':
    main()