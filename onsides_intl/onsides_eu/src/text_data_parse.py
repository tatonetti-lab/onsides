import numpy as np 
import pandas as pd
import requests
from tqdm import tqdm
from glob import glob
import ast, re, json, orjson
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
    txts = glob(data_folder+'raw_txt/*')

    isExist = os.path.exists(data_folder+'raw_json')
    if not isExist:
        os.mkdir(data_folder+'raw_json')

    #add in titles as reference. may use these in the future.
    titles = ['1. NAME OF THE MEDICINAL PRODUCT','2. QUALITATIVE AND QUANTITATIVE COMPOSITION', '3. PHARMACEUTICAL FORM', '4. CLINICAL PARTICULARS', 
              '5. PHARMACOLOGICAL PROPERTIES', '6. PHARMACEUTICAL PARTICULARS', '7. MARKETING AUTHORISATION HOLDER', '8. MARKETING AUTHORISATION NUMBER',
              '9. DATE OF FIRST AUTHORISATION/RENEWAL OF THE AUTHORISATION','10. DATE OF REVISION OF THE TEXT']

    #iterate through all text files and extract the 4. CLINICAL PARTICULARS section
    not_found = []
    not_found_next = []
    for txt in tqdm(txts):
        drug = txt.split('/')[-1].replace('.txt','')
        with open(txt, 'r+') as fi:
            txt = fi.read()
            txt = txt.split('ANNEX II')[0]
        #we're interested in "4.CLINICAL PARTICULARS". extract this section
        if '4. CLINICAL' in txt:
            if '5. PHARMACOLOGICAL' in txt:
                sec_dict = {}
                sec_dict['4. CLINICAL PARTICULARS'] = '4. CLINICAL'+txt.split('4. CLINICAL')[1].split('5. PHARMACOLOGICAL')[0]+'5. PHARMACOLOGICAL'
                with open(data_folder+'raw_json/{}.json'.format(drug), "w") as out:
                    json.dump(sec_dict, out)
            elif '6. PHARMACEUTICAL' in txt:
                sec_dict = {}
                sec_dict['4. CLINICAL PARTICULARS'] = '4. CLINICAL'+txt.split('4. CLINICAL')[1].split('6. PHARMACEUTICAL')[0]+'6. PHARMACEUTICAL'
                with open(data_folder+'raw_json/{}.json'.format(drug), "w") as out:
                    json.dump(sec_dict, out)
            else:
                not_found_next.append(txt)
        else:
            if '4.1 Therapeutic' in txt:
                sec_dict = {}
                sec_dict['4. CLINICAL PARTICULARS'] = '4. CLINICAL PARTICULARS'+txt.split('4.1 Therapeutic')[1].split('5. PHARMACOLOGICAL')[0]+'5. PHARMACOLOGICAL'
                with open(data_folder+'raw_json/{}.json'.format(drug), "w") as out:
                    json.dump(sec_dict, out)
            elif '4. CLINICAL' in txt.replace('\n',''):
                sec_dict = {}
                sec_dict['4. CLINICAL PARTICULARS'] = '4. CLINICAL'+txt.replace('\n','').split('4. CLINICAL')[1].split('5. PHARMACOLOGICAL')[0]+'5. PHARMACOLOGICAL'
                with open(data_folder+'raw_json/{}.json'.format(drug), "w") as out:
                    json.dump(sec_dict, out)
            elif '4. CLINICAL' in ' '.join(txt.split()):
                sec_dict = {}
                sec_dict['4. CLINICAL PARTICULARS'] = '4. CLINICAL'+' '.join(txt.split()).split('4. CLINICAL')[1].split('5. PHARMACOLOGICAL')[0]+'5. PHARMACOLOGICAL'
                with open(data_folder+'raw_json/{}.json'.format(drug), "w") as out:
                    json.dump(sec_dict, out)
            else:
                not_found.append(txt)
        len(not_found), len(not_found_next)

    ########################################################
    #now, we want to extract the ADEs from the 4. CLINICAL PARTICULARS section
    isExist = os.path.exists(data_folder+'raw_json_ue')
    if not isExist:
        os.mkdir(data_folder+'raw_json_ue')

    sec4_titles = ['4.1 Therapeutic indications', '4.2 Posology and method of administration', '4.3 Contraindications', '4.4 Special warnings and precautions for use', 
                   '4.5 Interaction with other medicinal products and other forms of interaction', '4.6 Fertility, pregnancy and lactation', '4.7 Effects on ability to drive and use machines',
                   '4.8 Undesirable effects', '4.9 Overdose']

    jsons = glob(data_folder+'raw_json/*')
    not_found_ue = []
    for j in tqdm(jsons):
        with open(j, 'r+') as fi:
            d = orjson.loads(fi.read())
        try:
            txt = d['4. CLINICAL PARTICULARS']
            txt = ' '.join(txt.split())
            ue = txt.split('4.8 Undesirable')[1].split('4.9 Overdose')[0]
            ue_dict = {}
            ue_dict['Undesirable effects'] = ue
            drug = j.split('/')[-1].replace('.json','')
            with open(data_folder+'raw_json_ue/{}.json'.format(drug), "w") as out:
                json.dump(ue_dict, out)
        except:
            not_found_ue.append(json)

    jsons = glob(data_folder+'raw_json_ue/*')
    print('we found the undesirable effects section for {j} and weren\'t able to find it for {nf}'.format(j = str(len(jsons)), nf = str(len(not_found_ue))))

    ########################################################
    #now, we format the json files into a table to use. 
    ade_list = []
    for j in tqdm(jsons):
        with open(j, 'r+') as fi:
            d = orjson.loads(fi.read())
        ade = d['Undesirable effects']
        pattern = r'[^\n\w\s.,]'
        clean_ade = re.sub(r'[^\n\w\s.,]', '', ade)
        drug = j.split('/')[-1].replace('.json','')
        ade_list.append([drug, clean_ade])
    
    ade_text_table_df = pd.DataFrame(ade_list, columns=['drug', 'ade_text'])
    ade_text_table_df.to_csv(data_folder+'ade_text_table.csv', index=False)

    print('finish extracting text data.')

if __name__ == '__main__':
    main()