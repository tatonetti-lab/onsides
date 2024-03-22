import numpy as np 
import pandas as pd
import requests
from tqdm import tqdm
import ast, re, json
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
    parser.add_argument('--api_key', required=True, help='Path to json file where api keys are stored.', default='api_keys.json')


    args = parser.parse_args()
    data_folder = args.data_folder
    external_data_folder = args.external_data
    api_file = args.api_key

    with open(api_file) as apis:
        apis = json.load(apis)
    api = apis['umls_api_key']

    df = pd.read_csv(data_folder+'drug_data.csv')
    ingredient_df = pd.read_csv(data_folder+'ingredient_data.csv')
    print(ingredient_df.shape)

    #simple merge on OHDSI RxNorm
    athena = external_data_folder+'athena_rxnorm/'
    athena_map = pd.read_csv(athena+'CONCEPT.csv', delimiter = '\t')
    athena_map = athena_map[athena_map.vocabulary_id == 'RxNorm']
    athena_ingredients = athena_map[athena_map.concept_class_id.isin(['Ingredient', 'Multiple Ingredients', 'Precise Ingredient'])][['concept_id', 'concept_code', 'concept_name']]
    ingredient_df = ingredient_df.merge(athena_ingredients, left_on = 'ingredient_name', right_on = 'concept_name', how = 'left')

    #use UMLS mapping
    for i, row in tqdm(ingredient_df.iterrows()):
        concept_code = row['concept_code'] 
        if str(concept_code) == 'nan':
            ingredient_name = row['ingredient_name']
            url = 'https://uts-ws.nlm.nih.gov/rest/search/current?string={a}&returnIdType=sourceConcept&apiKey={k}'.format(a=ingredient_name, k=api) 
            result = requests.get(url).json()
            if result['result']['recCount'] > 0:
                for r in result['result']['results']:
                    if r['rootSource'] == 'RXNORM':
                        ingredient_df.at[i, 'concept_code'] = r['ui']
                        ingredient_df.at[i, 'concept_name'] = r['name'] 
                        #print(concept_code, ingredient_name, r['ui'], r['name'])
    
    #use RxNav mapping
    for i, row in tqdm(ingredient_df.iterrows()):
        if str(row['concept_code']) == 'nan':
            name = row['ingredient_name']
            url = 'https://rxnav.nlm.nih.gov/REST/rxcui.json?name={}&search=0'.format(name.replace(' ', '+'))
            r = requests.get(url).json()
            try:
                rxnorm_id = r['idGroup']['rxnormId'][0]
                ingredient_df.at[i, 'concept_code'] = rxnorm_id
            except:
                try:
                    url = 'https://rxnav.nlm.nih.gov/REST/rxcui.json?name={}&search=1'.format(name.replace(' ', '+'))
                    r = requests.get(url).json()
                    rxnorm_id = r['idGroup']['rxnormId'][0]
                    ingredient_df.at[i, 'concept_code'] = rxnorm_id
                except:
                    pass 

    ingredient_df.to_csv(data_folder+'ingredient_data.csv', index=False)

    print('mapped drugs to rxnorm - successful : {s}, failed : {f}'.format(s = str(ingredient_df[ingredient_df.concept_code.notna()].shape[0]), 
                                                                           f = str(ingredient_df[ingredient_df.concept_code.isna()].shape[0])))

if __name__ == '__main__':
    main()