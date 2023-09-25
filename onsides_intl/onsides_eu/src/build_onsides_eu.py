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

def main():
    print('run the model')
    parser = argparse.ArgumentParser(description='let the code know where the data is held')
    parser.add_argument('--data_folder', required=True, help='Path to the data folder.')
    parser.add_argument('--external_data', required=True, help='Path to the where the external data is housed.')

    args = parser.parse_args()
    data_folder = args.data_folder
    external_data_folder = args.external_data
    
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

    


if __name__ == '__main__':
    main()