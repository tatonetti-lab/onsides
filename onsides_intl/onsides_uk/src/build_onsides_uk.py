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
    parser = argparse.ArgumentParser(description='let the code know where the data is held')
    parser.add_argument('--data_folder', required=True, help='Path to the data folder.')
    parser.add_argument('--external_data', required=True, help='Path to the where the external data is housed.')
    parser.add_argument('--final_data', required=True, help='Path to the where the final output should be written.')

    args = parser.parse_args()
    data_folder = args.data_folder
    external_data_folder = args.external_data
    final_folder = args.final_data

    #load the drug data
    drug_df = pd.read_csv(data_folder+'ingredients.csv')
    drug_df['product_id'] = drug_df['product_id'].astype(str)

    #free-text data
    free_text_df = pd.read_csv(data_folder+'ade_text_table_onsides_predcsv')
    free_text_df = free_text_df[free_text_df.pt_meddra_id.notna()][['label_id', 'pt_meddra_id', 'pt_meddra_term']]
    free_text_df['pt_meddra_id'] = free_text_df['pt_meddra_id'].apply(lambda x: int(float(x)))
    free_text_df['pt_meddra_term'] = free_text_df['pt_meddra_term'].apply(lambda x: x.lower())
    free_text_df = free_text_df.drop_duplicates()

    #tabular data
    conditions = pd.read_csv(data_folder+'drug_ade_data_parsed.csv')
    conditions['product_id'] = conditions['product_id'].apply(lambda x: str(x))
    conditions['matched_codes'] = conditions['matched_codes'].apply(lambda x: ast.literal_eval(x) if str(x) != 'nan' else None)
    conditions['exact_match_list'] = conditions['exact_match_list'].apply(lambda x: ast.literal_eval(x) if str(x) != 'nan' else None)
    conditions = conditions[['product_id', 'freq', 'exact_match_list', 'matched_codes']].explode(['exact_match_list', 'matched_codes'])
    conditions['freq'] = conditions.freq.apply(lambda x: 'not known' if str(x) == 'nan' else x)
    conditions.columns = ['product_id', 'freq', 'pt_meddra_term', 'pt_meddra_id']
    conditions = conditions[conditions.pt_meddra_term.notna()].drop_duplicates(['pt_meddra_term', 'pt_meddra_id', 'product_id'])

    #build all label dataframe
    free_text_df['freq'] = 'not known'
    free_text_df.columns = ['product_id', 'pt_meddra_id', 'pt_meddra_term', 'freq']
    cond = pd.concat([conditions, free_text_df])
    print(cond.shape[0])
    cond['product_id'] = cond['product_id'].astype(str)
    cond = cond.drop_duplicates(['pt_meddra_term', 'pt_meddra_id', 'product_id'])
    print(cond.shape[0])
    
    raw_tally = conditions.merge(drug_df[['ingredient_rxnorm', 'active_ingredients', 'product_id']], on = 'product_id', how = 'left')
    #raw_tally = raw_tally[['product_id', 'ingredient_rxnorm', 'active_ingredients', 'pt_meddra_id', 'pt_meddra_term', 'freq']]
    raw_tally.to_csv(final_folder+'adverse_events_all_labels_w_freq.csv', index=False)

    #for now, the active labels are the same as the all labels - this will change over time as we add more labels and the labels are updated.
    #TODO : add functionality to allow for these updates
    raw_tally.to_csv(final_folder+'adverse_events_active_labels_w_freq.csv', index=False)

    #build the drug label dataframe
    uniq_ingr = drug_df[['product_id', 'product_name', 'active_ingredients', 'ingredient_rxnorm']]
    uniq_ingr['num_ingredients'] = uniq_ingr.ingredient_rxnorm.apply(lambda x: len(x.split(', ')) if str(x) != 'nan' else 0)
    uniq_ingr = uniq_ingr.groupby('ingredient_rxnorm')['product_name'].apply(list).reset_index()
    uniq_ingr['num_labels'] = uniq_ingr.product_name.apply(lambda x: len(x))
    uniq_event = raw_tally[['pt_meddra_id', 'pt_meddra_term']].drop_duplicates()

    ade_count = raw_tally[['ingredient_rxnorm', 'pt_meddra_id']].groupby('ingredient_rxnorm')['pt_meddra_id'].apply(list).reset_index()
    ade_count['pt_meddra_list'] = ade_count['pt_meddra_id'].apply(lambda x: collections.Counter(x))
    ade_count['pt_meddra_id'] = ade_count['pt_meddra_list'].apply(lambda x: x.keys())
    ade_count = ade_count.explode('pt_meddra_id')
    ade_count['num_events'] = ade_count.apply(lambda x: x['pt_meddra_list'][x['pt_meddra_id']], axis = 1)

    ades = uniq_ingr.merge(ade_count[['ingredient_rxnorm', 'pt_meddra_id', 'num_events']], on = 'ingredient_rxnorm', how = 'left')
    ades['pct_labels'] = ades.apply(lambda x: x['num_events'] / x['num_labels'], axis = 1)
    ades = ades.merge(uniq_event, on = 'pt_meddra_id', how = 'left')

    a = raw_tally.drop('freq', axis = 1).drop_duplicates()
    a = a.merge(ades[['ingredient_rxnorm', 'pt_meddra_id', 'pct_labels', 'num_labels', 'num_events']], on = ['ingredient_rxnorm', 'pt_meddra_id'], how = 'left').drop_duplicates()
    a.to_csv(final_folder+'adverse_events.csv', index=False) 

if __name__ == '__main__':
    main()