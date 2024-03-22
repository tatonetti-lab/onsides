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
from bs4 import BeautifulSoup

def main():
    parser = argparse.ArgumentParser(description='let the code know where the data is held')
    parser.add_argument('--data_folder', required=True, help='Path to the data folder.')
    parser.add_argument('--external_data', required=True, help='Path to the where the external data is housed.')
    #parser.add_argument('--final_data', required=True, help='Path to the where the final output should be written.')

    args = parser.parse_args()
    data_folder = args.data_folder
    external_data_folder = args.external_data
    #final_folder = args.final_data

    kegg_drug_rows = []
    for i in tqdm(range(303)):
        url = 'https://www.kegg.jp/medicus-bin/search_drug?uid=1681797824120106&display=kegg_drug&page={}'.format(str(i+1))
        r = requests.get(url)
        r.encoding = r.apparent_encoding
        s = BeautifulSoup(r.text, 'html.parser')
        table = s.find(class_='list1')
        table_rows = table.find_all('tr')
        table_items = [i.find_all('td') for i in table_rows][1:]
        kegg_drug_rows.extend(table_items)
    
    kegg_drug_df = pd.DataFrame(kegg_drug_rows, columns = ['kegg_id', 'general_name', 'product_name', 'indication'])
    kegg_drug_df.to_csv(data_folder+'kegg_drug_info_raw.csv', index=False)

    kegg_drug_df = pd.read_csv(data_folder+'kegg_drug_info_raw.csv')
    kegg_drug_df['kegg_id'] = kegg_drug_df.kegg_id.apply(lambda x: BeautifulSoup(x).text)
    kegg_drug_df['general_name'] = kegg_drug_df.general_name.apply(lambda x: BeautifulSoup(x))
    kegg_drug_df['product_name'] = kegg_drug_df.product_name.apply(lambda x: BeautifulSoup(x))
    kegg_drug_df['indication'] = kegg_drug_df.indication.apply(lambda x: BeautifulSoup(x).text)
    #parse only english names
    kegg_drug_df['general_en_name'] = kegg_drug_df.general_name.apply(lambda x: [i.split(' (')[0].lower() for i in x.text.split('\n') if i.isascii()])

    #use umls file to directly map
    rxnorm = pd.read_csv(external_data_folder+'umls_rxnorm.csv')
    rxnorm = rxnorm[['CODE', 'STR']]
    rxnorm.STR = rxnorm.STR.apply(lambda x: x.lower())

    df = kegg_drug_df[['kegg_id', 'general_en_name']].explode('general_en_name').merge(rxnorm, left_on = 'general_en_name', right_on = 'STR', how = 'left').groupby('kegg_id')['CODE'].apply(set).reset_index()
    df['CODE'] = df.CODE.apply(lambda x: [i for i in list(x) if str(i) != 'nan'])
    df = df.merge(kegg_drug_df[['kegg_id', 'general_en_name']], on = 'kegg_id', how = 'left')
    df.to_csv(data_folder+'kegg_drug_info_mapped.csv', index=False)

    #use RxNav API to map any remaining drugs
    df = pd.read_csv(data_folder+'kegg_drug_info_mapped.csv')
    df['CODE'] = df['CODE'].apply(lambda x: ast.literal_eval(x))
    df['general_en_name'] = df['general_en_name'].apply(lambda x: ast.literal_eval(x))
    codes = []
    for i, row in tqdm(df.iterrows()):
        try:
            if len(row['CODE']) == 0:
                drug_codes = []
                for drug in row['general_en_name']:
                    url = 'https://rxnav.nlm.nih.gov/REST/rxcui.json?name={}&search=1'.format(drug)
                    j = requests.get(url).json()
                    try:
                        drug_codes.extend(j['idGroup']['rxnormId'])
                    except:
                        pass
                drug_codes = list(set(drug_codes))
                codes.append([row['kegg_id'], drug_codes])
        except:
            continue
    codes_dict = {i[0]:i[1] for i in codes} 
    df['CODE'] = df.apply(lambda x: codes_dict[x.kegg_id] if x.kegg_id in codes_dict.keys() else x.CODE, axis = 1)
    df.to_csv(data_folder+'kegg_drug_info_mapped.csv', index=False)

    #use athena file to map any remaining drugs that aren't caugth by RxNav
    #TODO : determine if this is the best way to do this
    df = pd.read_csv(data_folder+'kegg_drug_info_mapped.csv')
    df['CODE'] = df['CODE'].apply(lambda x: ast.literal_eval(x))
    df['general_en_name'] = df['general_en_name'].apply(lambda x: ast.literal_eval(x))

    rx_ext = pd.read_csv(external_data_folder+'athena_rxnorm_extension/CONCEPT.csv', delimiter = '\t')
    rx_ext = rx_ext[rx_ext.vocabulary_id == 'RxNorm Extension'][['concept_id', 'concept_code', 'concept_name']]
    rx_ext['concept_name'] = rx_ext.concept_name.apply(lambda x: x.lower())

    found_dict = {}
    for i, row in tqdm(df.iterrows()):
        if len(row['CODE']) == 0:
            try:
                name = row['general_en_name'][0]
                codes = rx_ext[rx_ext.concept_name == name].concept_code.tolist()[0]
                if len(codes) > 0:
                    found_dict[row['kegg_id']] = codes
            except:
                continue
    df['CODE'] = df.apply(lambda x: found_dict[x.kegg_id] if x.kegg_id in found_dict.keys() else x.CODE, axis = 1)
    df.to_csv(data_folder+'kegg_drug_info_mapped.csv', index=False)
    
if __name__ == '__main__':
    main()