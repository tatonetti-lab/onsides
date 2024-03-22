import argparse
import pandas as pd, numpy as np
import requests
import warnings
warnings.filterwarnings('ignore')
from glob import glob
from tqdm import tqdm
from bs4 import BeautifulSoup
##### specific functions #####
import tabula, camelot, os
import pypdf
import PyPDF2
import wget
from pypdf import PdfReader

def main():

    parser = argparse.ArgumentParser(description='download drug labels from EU EMA website')
    parser.add_argument('--data_folder', required=True, help='Path to the data folder.')
    args = parser.parse_args()

    data_folder = args.data_folder

    ## download table of drugs
    data_f = data_folder
    url = 'https://www.ema.europa.eu/sites/default/files/Medicines_output_european_public_assessment_reports.xlsx'
    wget.download(url, out = data_f)

    #read the table of drugs, and filter for human drugs
    df = pd.read_excel(data_folder+'Medicines_output_european_public_assessment_reports.xlsx', skiprows=8)
    df = df[df.Category == 'Human']
    print('Will download the raw files of {} drugs.'.format(str(df.shape[0])))
    
    #check if raw folder exists, if not, make it
    os.makedirs(data_folder+'raw', exist_ok=True)

    #download the raw files
    not_found = []
    for i, row in tqdm(df.iterrows()):
        med = row['Medicine name']
        url = row['URL'].split('/')[-1]
        url = 'https://www.ema.europa.eu/en/documents/product-information/{}-epar-product-information_en.pdf'.format(url)
        try:
            wget.download(url, out = data_folder+'data/raw/{}_label.pdf'.format(str(med).lower()))
        except:
            not_found.append(med)
    print('downloaded : {dl}, failed : {fail}, total : {tot}'.format(dl=str(df.shape[0]-len(not_found)), fail=len(not_found), tot=str(df.shape[0])))
    print('retry download')

    #retry download for failed files (sometimes the name format is wrong)
    not_found_2 = []
    for med in tqdm(not_found):
        if 'known as' in med or 'previously' in med:
            med_alt = med.split(' (')[0].replace(' ','-').lower()
        else:
            med_alt = med.replace(' ','-').replace('(','').replace(')','').lower()
        url = 'https://www.ema.europa.eu/en/documents/product-information/{}-epar-product-information_en.pdf'.format(med_alt)
        try:
            wget.download(url, out = data_folder+'raw/{}_label.pdf'.format(str(med).lower()))
        except:
            not_found_2.append(med)
    print('downloaded : {dl}, failed : {fail}, total : {tot}'.format(dl=str(df.shape[0]-len(not_found_2)), fail=len(not_found_2), tot=str(df.shape[0])))
    print('retry download')


if __name__ == "__main__":
    main()