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
    
    #the original drug table
    #read in table of drug info (and filter for relevant columns)
    df = pd.read_excel(data_folder+'Medicines_output_european_public_assessment_reports.xlsx', skiprows=8)
    df = df[df.Category == 'Human'][['Medicine name', 'Product number', 'Active substance', 'Authorisation status',
                                    'International non-proprietary name (INN) / common name',
                                    'ATC code']]
    #df = df[df['Medicine name'].str.lower().isin(ade_all_labels.drug)]
    print(df.shape)

    #read in UMLS rxnorm
    rxnorm = pd.read_csv(external_data_folder+'umls_rxnorm.csv')
    rxnorm = rxnorm[['CODE', 'STR']]
    rxnorm.STR = rxnorm.STR.apply(lambda x: x.lower())
    rxnorm_dict = dict(zip(rxnorm.STR, rxnorm.CODE))

    df['rxnorm_code'] = df['International non-proprietary name (INN) / common name'].apply(lambda x: 
                                                                                       list(set([rxnorm_dict[i] for i in x.split(', ') if i in rxnorm_dict.keys()])) 
                                                                                       if str(x) != 'nan' else None)
    #next map on substance name if INN name doesn't work
    df['rxnorm_code'] = df.apply(lambda x:
                                list(set([rxnorm_dict[i] for i in x['Active substance'].split(', ') if i in rxnorm_dict.keys()]))
                                if len(str(x.rxnorm_code)) <= 3 #if it's either NaN or []
                                else x['rxnorm_code'],
                                axis = 1)
    df['num_ingredients'] = df.rxnorm_code.apply(lambda x: len(x) if x is not None else 0)
    print('mapped {} drugs'.format(str(df[df.num_ingredients > 0].shape[0])))

    for i, row in tqdm(df.iterrows()):
        try:
            if row['num_ingredients'] == 0:
                drugs = row['International non-proprietary name (INN) / common name'].split(', ')
                drug_codes = []
                for drug in drugs:
                    if drug in rxnorm_dict.keys():
                        drug_codes.append(rxnorm_dict[drug])
                    else:
                        url = 'https://rxnav.nlm.nih.gov/REST/rxcui.json?name={}&search=1'.format(drug)
                        j = requests.get(url).json()
                        drug_codes.extend(j['idGroup']['rxnormId'])
                drug_codes = list(set(drug_codes))
                if len(drug_codes) > 0:
                    df.at[i, 'rxnorm_code'] = drug_codes
        except:
            continue

    df['num_ingredients'] = df.rxnorm_code.apply(lambda x: len(x) if x is not None else 0)  
    print('mapped {} drugs'.format(str(df[df.num_ingredients > 0].shape[0])))

    #next map with OHDSI RxNorm
    rxnorm = pd.read_csv(external_data_folder+'athena_rxnorm_atc/CONCEPT.csv', delimiter = '\t')
    rxnorm = rxnorm[(rxnorm.domain_id == 'Drug')&(rxnorm.vocabulary_id.isin(['RxNorm', 'RxNorm Extension']))&(rxnorm.concept_class_id.str.contains('Ingredient'))]
    rxnorm['concept_name'] = rxnorm['concept_name'].apply(lambda x: x.lower())
    for i, row in tqdm(df.iterrows()):
        if row['num_ingredients'] == 0 and str(row['International non-proprietary name (INN) / common name']) != 'nan':
            codes = []
            d_df = rxnorm[rxnorm.concept_name == row['International non-proprietary name (INN) / common name'].lower()]
            if d_df.shape[0] > 0:
                codes = d_df.concept_id.tolist()
                df.at[i, 'rxnorm_code'] = codes
    df['num_ingredients'] = df.rxnorm_code.apply(lambda x: len(x) if x is not None else 0)
    print('mapped {} drugs'.format(str(df[df.num_ingredients > 0].shape[0])))

    #next map with OHDSI RxNorm using Brand Names
    rxnorm = pd.read_csv(external_data_folder+'athena_rxnorm_atc/CONCEPT.csv', delimiter = '\t')
    rxnorm = rxnorm[(rxnorm.domain_id == 'Drug')&(rxnorm.vocabulary_id.isin(['RxNorm', 'RxNorm Extension']))&(rxnorm.concept_class_id.str.contains('Brand Name'))]
    rxnorm['concept_name'] = rxnorm['concept_name'].apply(lambda x: x.lower())
    for i, row in tqdm(df.iterrows()):
        if row['num_ingredients'] == 0 and str(row['Medicine name']) != 'nan':
            codes = []
            d_df = rxnorm[rxnorm.concept_name == row['Medicine name'].lower()]
            if d_df.shape[0] > 0:
                codes = d_df.concept_id.tolist()
                df.at[i, 'rxnorm_code'] = codes
    df['num_ingredients'] = df.rxnorm_code.apply(lambda x: len(x) if x is not None else 0)
    print('mapped {} drugs'.format(str(df[df.num_ingredients > 0].shape[0])))

    #save ingredient dataframe.
    df.to_csv(data_folder+'ingredients.csv', index=False)


if __name__ == '__main__':
    main()