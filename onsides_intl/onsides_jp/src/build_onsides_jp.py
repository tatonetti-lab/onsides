import numpy as np 
import pandas as pd
import requests
from tqdm import tqdm
import ast, re
from time import sleep
import argparse
import warnings
warnings.filterwarnings('ignore')
from bs4 import BeautifulSoup
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

    #read in drug table csv file that we generated in map_drugs_to_rxnorm.py, and the raw ADE table
    drug_df = pd.read_csv(data_folder+'kegg_drug_info_mapped.csv')
    ades_df = pd.read_csv(data_folder+'rx_drug_ade_raw.csv')

    #read in the drug-ade prediction files.
    #we will use the drug-ade predictions to generate the drug-ade table.
    extr_uniq_df = pd.read_csv(data_folder+'rx_raw_ade_extraction.csv')
    pred_df= pd.read_csv(data_folder+'ade_text_table_onsides_pred.csv')

    drug_df = pd.read_csv(data_folder+'rx_drug_overview_parsed.csv')
    drug_df['KEGG DRUG'] = drug_df['KEGG DRUG'].apply(lambda x: BeautifulSoup(x) if str(x) != 'nan' else None)
    drug_df['KEGG DRUG'] = drug_df['KEGG DRUG'].apply(lambda x: [i.text for i in x.find_all('a') if i.text[0] == 'D'][0] if x != None else None)
    drug_df['en_name'] = drug_df['欧文一般名'].apply(lambda x: x.lower() if str(x) != 'nan' else None)
    drug_filtered = drug_df[['japic_code', 'version', '総称名', '薬効分類名', 'ATCコード', 'en_name']]
    drug_filtered.to_csv(data_folder+'drugs_all.csv', index=False)

    rxnorm = pd.read_csv(external_data_folder+'umls_rxnorm.csv')
    rxnorm = rxnorm[['CODE', 'STR']]
    rxnorm.STR = rxnorm.STR.apply(lambda x: x.lower())
    drug_df = drug_df.merge(rxnorm, left_on = 'en_name', right_on = 'STR', how = 'left')
    drug_df = drug_df[['japic_code', '一般名', 'en_name', 'KEGG DRUG', 'CODE']]
    drug_df['KEGG DRUG'] = drug_df['KEGG DRUG'].apply(lambda x: [i.text for i in x.find_all('a') if i.text[0] == 'D'][0] if x != None else None)
    kegg_map = pd.read_csv(data_folder+'drug_atc_kegg.csv')
    kegg_dict = dict(zip(kegg_map.kegg, kegg_map.rxnorm))
    drug_df['CODE'] = drug_df.apply(lambda x: kegg_dict(x['KEGG DRUG']) if x.CODE == None and x['KEGG DRUG'] in kegg_dict.keys() else x.CODE, axis = 1)
    drug_df.to_csv(data_folder+'ingredients.csv', index=False)

    kegg_df = pd.read_csv(data_folder+'kegg_rx_drug_data.csv')
    kegg_df.columns = ['product', 'ingredient', 'indication', 'kegg_id', 'japic_code']
    condition_df = pd.read_csv(data_folder+'ade/rx_ade_table.csv')
    conditions = condition_df[['japic_code', 'ade', 'category', 'percentage']]
    conditions = conditions.merge(kegg_df[['japic_code', 'kegg_id']], on = 'japic_code', how = 'left')
    unique_ades = pd.read_csv(data_folder+'ade/rx_raw_ade_list.csv')
    unique_ades['SDUI'] = unique_ades.SDUI.apply(lambda x: ast.literal_eval(x) if str(x)!='nan' else None)
    unique_ades = unique_ades[['ade', 'SDUI']].explode('SDUI')
    conditions = conditions.merge(unique_ades[['ade', 'SDUI']], on = 'ade', how = 'left')
    conditions = conditions[['japic_code', 'percentage', 'SDUI']]
    conditions = conditions[conditions.SDUI.notna()]
    conditions.japic_code = conditions.japic_code.apply(lambda x: str(int(x)))
    print(conditions.shape)
    umls_rxnorm = pd.read_csv(external_data_folder+'umls_rxnorm.csv')[['CODE', 'STR']].drop_duplicates(subset='CODE')
    umls_rxnorm.columns = ['ingredients_rxcuis', 'ingredient_names']
    umls_meddra = pd.read_csv(external_data_folder+'umls_meddra_en.csv')[['CODE', 'STR']].drop_duplicates(subset='CODE')
    umls_meddra.columns = ['pt_meddra_id', 'pt_meddra_term']
    
    #build all label dataframe
    extr_uniq_df['freq'] = 'not known'
    extr_uniq_df.columns = ['product_id', 'pt_meddra_id', 'pt_meddra_term', 'freq']
    cond = pd.concat([conditions, extr_uniq_df])
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