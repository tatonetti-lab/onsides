import numpy as np 
import pandas as pd
import requests
from tqdm import tqdm
from glob import glob
import ast, re
from time import sleep
import argparse
import warnings
warnings.filterwarnings('ignore')
import os

def main():
    parser = argparse.ArgumentParser(description='let the code know where the data is held')
    parser.add_argument('--data_folder', required=True, help='Path to the data folder.')
    parser.add_argument('--external_data', required=True, help='Path to the where the external data is housed.')

    args = parser.parse_args()
    data_folder = args.data_folder
    external_data_folder = args.external_data

    #get list of all tabular files.
    tbls = glob(data_folder+'raw_tbl/*')

    #iterate through all tabular files and extract the relevant tables (i.e. those with the columns of interest)
    ade_tbl = []
    for tbl in tqdm(tbls):
        drug = tbl.split('/')[-1].split('_')[0]
        try:
            df = pd.read_csv(tbl)
            if any([i in list(df.columns) for i in ['System', 'Very common', 'Common', 'Not known', 'Rare', 'Uncommon']]):
                col = df.columns.tolist()
                for i in col:
                    l = ' '.join([i for i in df[i].tolist() if str(i) != 'nan'])
                    ade_tbl.append([drug, i, l])
        except:
            pass
    
    ades_df = pd.DataFrame(ade_tbl, columns = ['drug', 'col', 'txt'])
    ades_df.to_csv(data_folder+'raw_ade_table_v0924.csv', index=False)

    ##############################################################################################################
    ades_df = pd.read_csv(data_folder+'data/raw_ade_table_v0924.csv')
    ades_df['ade'] = ades_df['txt'].apply(lambda x: str(x).replace('- ', ''))

    freqs = ['very common', 'common', 'uncommon', 'rare', 'very rare', 'not known']
    socs =  ['blood and lymphatic system disorders','cardiac disorders', 'congenital, familial and genetic disorders',
            'ear and labyrinth disorders', 'endocrine disorders', 'eye disorders', 'gastrointestinal disorders', 
            'general disorders and administration site conditions', 'hepatobiliary disorders', 'immune system disorders',
            'infections and infestations', 'injury, poisoning and procedural complications', 'investigations', 'metabolism and nutrition disorders',
            'musculoskeletal and connective tissue disorders', 'neoplasms benign, malignant and unspecified (incl cysts and polyps)',
            'nervous system disorders', 'pregnancy, puerperium and perinatal conditions', 'psychiatric disorders',
            'renal and urinary disorders', 'reproductive system and breast disorders', 'respiratory, thoracic and mediastinal disorders',
            'skin and subcutaneous tissue disorders', 'social circumstances', 'surgical and medical procedures', 'vascular disorders', 'product issues']
    titles = ['system organ class', 'frequency', 'adverse events']

    meddra_df = pd.read_csv(external_data_folder+'umls_meddra_en.csv')
    meddra_df['STR'] = meddra_df.STR.apply(lambda x: x.lower())
    meddra_df['len'] = meddra_df.STR.apply(lambda x: len(x))
    meddra_dict = dict(zip(meddra_df.STR, meddra_df.SDUI))
    meddra_df = meddra_df[(meddra_df.TTY == 'PT')|(meddra_df['len'] > 5)]

    found_ades = []
    meddra_names = meddra_df.STR.tolist()
    for ade_text in tqdm(df.ade.tolist()):
        ar_text = ' '.join(ade_text.split()).lower() 
        #remove all of the freqs, socs, and titles
        for f in freqs:
            ar_text = ar_text.replace(f, '')
        for s in socs:
            ar_text = ar_text.replace(s, '')
        for t in titles:
            ar_text = ar_text.replace(t, '')
        found_terms = []
        for concept_name in meddra_names:
            if ar_text.find(concept_name) == -1:
                continue
            else:
                found_terms.append(concept_name)
        found_ades.append(found_terms)
    
    ades_df['exact_match_list'] = found_ades
    ades_df['matched_codes'] = ades_df.exact_match_list.apply(lambda x: [meddra_dict[i] for i in x] if str(x) != 'nan' else None)
    ades_df.to_csv(data_folder+'parsed_ade_tabular.csv', index=False)

if __name__ == '__main__':
    main()