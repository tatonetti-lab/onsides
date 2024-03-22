import numpy as np
import argparse
import pandas as pd
import requests
from tqdm import tqdm
from glob import glob
import ast, json
from bs4 import BeautifulSoup
from functions import format_code

def extract_metadata(kegg_df, data_folder, type = 'rx'):
    label_folder = data_folder + 'raw_{}/'.format(type)
    
    japic_list, failed = [], []
    for japic_code in tqdm(kegg_df['kegg_product_id'].tolist()):
        file_path = label_folder+'{}.txt'.format(format_code(japic_code))
        with open(file_path) as f:
            s = BeautifulSoup(f, 'html.parser')

        ##TODO : change for OTC
        try:
            version = s.find(class_='revision').text
        except:
            version = None

        try: ##version 1
            info = s.find(class_='drug-info clearfix').find('table')
            k,v = [i.text for i in info.find_all('th')], info.find_all('td')
            info_dict = dict(zip(k, v))
            japic_list.append([japic_code, version, info_dict, 1])
        except:
            try: ##version 2
                info = s.find(id='panel_japic_document').find('table')
                k,v = [i.text for i in info.find_all(class_='title')], info.find_all(class_='item')
                info_dict = dict(zip(k, v))
                japic_list.append([japic_code, version, info_dict, 2])
            except: ##check for failed files
                failed.append(japic_code)
    
    japic_df = pd.DataFrame(japic_list, columns = ['japic_code', 'version', 'info_dict', 'type'])
    japic_df.to_csv(data_folder+'{}_drug_overview_raw.csv'.format(type), index=False)
    print(len(japic_list), len(failed))

    return japic_df
def parse_metadata_df(japic_df, data_folder, type = 'rx'):
    japic_df['info_dict'] = japic_df.info_dict.apply(lambda x: dict(zip([i.split(': <')[0].replace('"','') for i in x.replace("\'", '"').replace('{','').replace('}','').split(', "')],
                                                                        ['<'+i.split(': <')[-1] for i in x.replace("\'", '"').replace('{','').replace('}','').split(', "')])))
    japic_df['総称名'] = japic_df.info_dict.apply(lambda x: BeautifulSoup(x['総称名']).text)
    japic_df['一般名'] = japic_df.info_dict.apply(lambda x: BeautifulSoup(x['一般名']).text if '一般名' in x.keys() else None)
    japic_df['欧文一般名'] = japic_df.info_dict.apply(lambda x: BeautifulSoup(x['欧文一般名']).text if '欧文一般名' in x.keys() else None)
    japic_df['薬効分類名'] = japic_df.info_dict.apply(lambda x: BeautifulSoup(x['薬効分類名']).text if '薬効分類名' in x.keys() else None)
    japic_df['薬効分類番号'] = japic_df.info_dict.apply(lambda x: BeautifulSoup(x['薬効分類番号']).text)
    japic_df['ATCコード'] = japic_df.info_dict.apply(lambda x: BeautifulSoup(x['ATCコード']).text if 'ATCコード' in x.keys() else None)
    japic_df['KEGG DRUG'] = japic_df.info_dict.apply(lambda x: x['KEGG DRUG'] if 'KEGG DRUG' in x.keys() else None)
    japic_df['KEGG DGROUP'] = japic_df.info_dict.apply(lambda x: x['KEGG DGROUP'] if 'KEGG DGROUP' in x.keys() else None)
    #japic_df['JAPIC'] = japic_df.info_dict.apply(lambda x: x['JAPIC'] if 'JAPIC' in x.keys() else None)
    japic_df = japic_df.drop('info_dict', axis = 1)
    
    japic_df.to_csv(data_folder+'rx_drug_overview_parsed.csv', index=False)
    return japic_df

def extract_ades(kegg_df, data_folder, type = 'rx'):
    ades_items, failed = [], []
    label_folder = data_folder + 'raw_{}/'.format(type)

    for japic_code in tqdm(kegg_df['kegg_product_id'].tolist()):
        file_path = label_folder+'{}.txt'.format(format_code(japic_code))
        with open(file_path) as f:
            s = BeautifulSoup(f, 'html.parser')

        try:
            #we get the title+content blocks
            items = s.find_all(class_=['contents-title', 'contents-block'])
            for i, item in enumerate(items):
                if 'contents-title' in str(item) and 'contents-block' not in str(item) and 'id' in str(item):
                    #find index of the title of the ade table (it starts with 11.2) and the next item in the list is the table.
                    if '11.2' in item.text:
                        ade_block = i+1
                        break
        except:
            try:
                #in another format, the title+content blocks are formatted slightly differently
                items = s.find_all(class_=['subtitle', 'block1'])
                for i, item in enumerate(items):
                    if 'subtitle' in str(item) and 'block1' not in str(item):
                        if 'その他の副作用' in item.text:
                            ade_block = i+1
                            break
            except:
                failed.append([japic_code, 'table fail'])

    try:
        ades = items[ade_block].find('table')
        ades = pd.read_html(str(ades))[0]
        ades.columns = ades.iloc[0]
        ades = ades.rename(columns={np.nan: 'category'}).drop(ades.index[0]).set_index('category')
        for row in ades.index:
            for col in ades.columns:
                if str(ades.loc[row, col]) != 'nan':
                    ades_items.append([japic_code, (row, col), ades.loc[row, col]])
    except:
        failed.append([japic_code, 'item fail'])

    ades_df = pd.DataFrame(ades_items, columns = ['japic_code', 'tags', 'ade'])
    ades_df.to_csv(data_folder+'{}_drug_ade_raw.csv'.format(type), index=False)

    failed_df = pd.DataFrame(failed, columns = ['japic_code', 'fail'])
    failed_df.to_csv(data_folder+'{}_drug_ade_raw_failed.csv'.format(type), index=False)

    return ades_df, failed_df
def extract_serious_ades(kegg_df, data_folder, type = 'rx'):

    serious_ade = []
    label_folder = data_folder + 'raw_{}/'.format(type)
    for japic_code in tqdm(kegg_df['kegg_product_id'].tolist()):
        file_path = label_folder+'{}.txt'.format(format_code(japic_code))
        with open(file_path) as f:
            s = BeautifulSoup(f, 'html.parser')

    labels = [i.text for i in s.find_all(['h4', 'h5'])]
    items = s.find_all(class_=['contents-title', 'contents-block'])
    item_text = [i.text for i in items]
    label_indexes = [item_text.index(l) if l in item_text else None for l in labels]
    label_dict = dict(zip(labels, label_indexes))

    if '11.1\u3000重大な副作用' in labels:
        next_label = labels[labels.index('11.1\u3000重大な副作用')+1]
        serious_items = items[label_dict['11.1\u3000重大な副作用']:label_dict[next_label]]
        serious_ade.append([japic_code, serious_items])
    else:
        labels = [i.text for i in s.find_all(['p', 'div'])]
        items = s.find_all(class_=['subtitle', 'block1'])
        if len(items) > 0 and '重大な副作用' in labels:
            item_text = [i.text for i in items]
            label_indexes = [item_text.index(l) if l in item_text else None for l in labels]
            label_dict = dict(zip(labels, label_indexes))
            try:
                next_label = labels[labels.index('その他の副作用')]
                serious_items = items[label_dict['重大な副作用']:label_dict[next_label]]
                serious_ade.append([japic_code, serious_items])
            except:
                serious_ade.append([japic_code, None])
        else:
            pass

    serious_ades_df = pd.DataFrame(serious_ade, columns = ['japic_code', 'serious_ade'])
    print(serious_ades_df.shape, len(serious_ades_df.japic_code.unique().tolist()))
    serious_ades_df.to_csv(data_folder+'{}_drug_serious_ade_raw.csv'.format(type), index=False)

    return serious_ades_df
def extract_special_pop_ades(kegg_df, data_folder, type = 'rx'):
    special_patients = []
    label_folder = data_folder + 'raw_{}/'.format(type)
    for japic_code in tqdm(kegg_df['kegg_product_id'].tolist()):
        file_path = label_folder+'{}.txt'.format(format_code(japic_code))
        with open(file_path) as f:
            s = BeautifulSoup(f, 'html.parser')

        labels = [i.text for i in s.find_all(['h4'])]
        items = s.find_all(class_=['contents-title', 'contents-block'])
        item_text = [i.text for i in items]
        label_indexes = [item_text.index(l) if l in item_text else None for l in labels]
        label_dict = dict(zip(labels, label_indexes))

        if '9. 特定の背景を有する患者に関する注意' in labels:
            next_label = labels[labels.index('9. 特定の背景を有する患者に関する注意')+1]
            serious_items = items[label_dict['9. 特定の背景を有する患者に関する注意']:label_dict[next_label]]
            special_patients.append([japic_code, serious_items])
        else:
            labels = [i.text for i in s.find_all(['p', 'div'])]
            items = s.find_all(class_=['subtitle', 'block1'])
            if len(items) > 0 and '特定の背景を有する患者に関する注意' in labels:
                item_text = [i.text for i in items]
                label_indexes = [item_text.index(l) if l in item_text else None for l in labels]
                label_dict = dict(zip(labels, label_indexes))
                try:
                    next_label = labels[labels.index('相互作用')]
                    serious_items = items[label_dict['特定の背景を有する患者に関する注意']:label_dict[next_label]]
                    special_patients.append([japic_code, serious_items])
                except:
                    try:
                        titles = s.find_all(['h4'])
                        titles_str = [i.text for i in titles]
                        if '使用上の注意' in titles_str:
                            items = s.find_all(['h4', 'h5', 'p', 'div'])
                            title_idx = items.index(titles[titles_str.index('使用上の注意')])
                            next_title_idx =  items.index(titles[titles_str.index('使用上の注意') + 1])
                            special_patients.append([japic_code, items[title_idx:next_title_idx]])
                    except:
                        special_patients.append([japic_code, None])
            else:
                special_patients.append([japic_code, None])
    special_patients = pd.DataFrame(special_patients, columns = ['japic_code', 'special_patients'])
    print(special_patients.shape, len(special_patients.japic_code.unique().tolist()))
    special_patients.to_csv(data_folder+'{}_drug_special_patients_raw.csv'.format(type), index=False)
    
    return special_patients

def extract_ddi(kegg_df, data_folder, type = 'rx'):
    ddi = []
    label_folder = data_folder + 'raw_{}/'.format(type)
    for japic_code in tqdm(kegg_df['kegg_product_id'].tolist()):
        file_path = label_folder+'{}.txt'.format(format_code(japic_code))
        with open(file_path) as f:
            s = BeautifulSoup(f, 'html.parser')

        labels = [i.text for i in s.find_all(['h4', 'h5'])]
        items = s.find_all(class_=['contents-title', 'contents-block'])
        item_text = [i.text for i in items]
        label_indexes = [item_text.index(l) if l in item_text else None for l in labels]
        label_dict = dict(zip(labels, label_indexes))

        if '10.1\u3000併用禁忌' in labels:
            next_label = labels[labels.index('10.1\u3000併用禁忌')+1]
            serious_items = items[label_dict['10.1\u3000併用禁忌']:label_dict[next_label]]
            ddi.append([japic_code, serious_items])
        else:
            labels = [i.text for i in s.find_all(['p', 'div'])]
            items = s.find_all(class_=['subtitle', 'block1'])
            if len(items) > 0 and '併用禁忌' in labels:
                item_text = [i.text for i in items]
                label_indexes = [item_text.index(l) if l in item_text else None for l in labels]
                label_dict = dict(zip(labels, label_indexes))
                try:
                    if '併用注意' in labels:
                    next_label = labels[labels.index('併用注意')]
                    else:
                    next_label = labels[labels.index('副作用')]
                    serious_items = items[label_dict['併用禁忌']:label_dict[next_label]]
                    ddi.append([japic_code, serious_items])
                except:
                    ddi.append([japic_code, None])
            else:
                pass
    
    ddi_df = pd.DataFrame(ddi, columns = ['japic_code', 'ddi'])
    print(ddi_df.shape, len(ddi_df.japic_code.unique().tolist()))
    ddi_df.to_csv(data_folder+'{}_drug_ddi_raw.csv'.format(type), index=False)
