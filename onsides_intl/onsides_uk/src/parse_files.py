import numpy as np 
import pandas as pd
import requests
from tqdm import tqdm
import ast, re
from time import sleep
from bs4 import BeautifulSoup
import argparse
import warnings
warnings.filterwarnings('ignore')

def main():
    parser = argparse.ArgumentParser(description='download drug labels from EU EMA website')
    parser.add_argument('--data_folder', required=True, help='Path to the data folder.')
    args = parser.parse_args()
    data_folder = args.data_folder

    drug_df = pd.read_csv(data_folder+'drug_data.csv')
    print('parse data for {} products'.format(str(drug_df.shape[0])))

    #extract the undesirable effects section from each data file.
    drug_ade_text = []
    for product in tqdm(drug_df.product_id.unique().tolist()):
        f = (data_folder+'raw/{}.txt'.format(product.split('/')[-2]))
        with open(f) as fi:
            s = BeautifulSoup(fi, 'html.parser')
        for i in s.find_all('details'):
            if '4.8 Undesirable effects' in i.text:
                ade_text = i
                drug_ade_text.append([product.split('/')[-2], ade_text])
    drug_ade_df = pd.DataFrame(drug_ade_text, columns = ['product_id', 'drug_text'])
    drug_ade_df.to_csv(data_folder+'drug_ade_data_raw.csv', index=False) 

    #first, extract the table data from the section data.
    drug_ade_df = pd.read_csv(data_folder+'drug_ade_data_raw.csv')
    print('parse the tabular data for {} products'.format(str(drug_ade_df.shape[0])))

    big_table_list = []
    for p_id, i in tqdm(zip(drug_ade_df.product_id.tolist(), drug_ade_df.drug_text.tolist())):
        i = BeautifulSoup(i, 'html.parser')
        if len(i.find_all('table')) > 0:
            table = i.find('table')
            rows = table.find_all('tr')
            for row in rows:
                big_table_list.append([p_id, row])
    
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

    processed_list = []
    for row in tqdm(big_table_list):
        drug = row[0]
        r = row[1]
        items = [i.text.replace('\n','').lower() for i in r.find_all('td')]
        if any([True for e in titles if e in items]):
            continue
        else:
            f, s, a = None, None, None
            for i in items: 
                i = i.strip().replace('*','')
                if i in freqs: f = i 
                elif i in socs: s = i
                else: a = i
                processed_list.append([drug, f, s, a])
    
    processed_df = pd.DataFrame(processed_list, columns = ['product_id', 'freq', 'soc', 'ade'])
    processed_df['freq'] = processed_df.apply(lambda x: str(x.ade).split(':')[0] if str(x.ade) !='nan' and str(x.ade).split(':')[0] in freqs else x.freq , axis = 1)
    processed_df.to_csv(data_folder+'drug_ade_table_data_parsed.csv', index=False)
    print('finished processing of tabular data for {} products'.format(str(processed_df.product_id.nunique())))

    #next, extract the raw text from the section data.
    drug_ade_df = pd.read_csv(data_folder+'drug_ade_data_raw.csv')
    print('parse the free-txt data for {} products'.format(str(drug_ade_df.shape[0])))
    text_list = []
    for p_id, i in tqdm(zip(drug_ade_df.product_id.tolist(), drug_ade_df.drug_text.tolist())):
        i = BeautifulSoup(i, 'html.parser')
        if len(i.find_all('table')) > 0:
            i.find('table').decompose() #remove the tables
        text_list.append([p_id, i.text])
    
    processed_text_df = pd.DataFrame(text_list, columns = ['product_id', 'text'])
    processed_text_df['text'] = processed_text_df['text'].apply(lambda x: str(x).lower().split('reporting of suspected adverse reactions')[0].split('4.8 undesirable effects')[-1].replace('\n',''))
    processed_text_df.to_csv(data_folder+'drug_ade_text_parsed.csv', index=False)
    print('finished processing of free-text data for {} products'.format(str(processed_df.product_id.nunique())))

if __name__ == '__main__':
    main()