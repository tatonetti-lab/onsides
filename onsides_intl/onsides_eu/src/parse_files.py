import argparse
import pandas as pd, numpy as np
import os
import requests
import warnings
warnings.filterwarnings('ignore')
from glob import glob
from tqdm import tqdm
from bs4 import BeautifulSoup
##### specific functions #####
import tabula, camelot
import pypdf
import PyPDF2
import wget
from pypdf import PdfReader

def main():

    parser = argparse.ArgumentParser(description='download drug labels from EU website')
    parser.add_argument('--data_folder', required=True, help='Path to the data folder.')
    args = parser.parse_args()

    data_folder = args.data_folder

    pdfs = glob(data_folder+'raw/*_label.pdf')
    print('We have downloaded {} PDF drug label files.'.format(str(len(pdfs))))

    #from the PDF files, extract all text. This will be used to search for ADEs.
    isExist = os.path.exists(data_folder+'raw_txt')
    if not isExist:
        os.mkdir(data_folder+'raw_txt')
    
    for pdf in tqdm(pdfs):
        drug = pdf.split('/')[-1].split('_label.pdf')[0]
        pdf_file = open(pdf, 'rb')
        read_pdf = PyPDF2.PdfReader(pdf_file)
        n_pages = len(read_pdf.pages)
        p_text = ''
        for n in range(n_pages):
            page = read_pdf.pages[n]
            page_content = page.extract_text()
            p_text += page_content
        txt_drug = data_folder+'raw_txt/{}.txt'.format(drug)
        with open(txt_drug, 'w+') as f:
            f.write(p_text)
    
    #from the PDF files, extract all tables using Tabula. These will also be used to search for ADEs.
    isExist = os.path.exists(data_folder+'raw_tbl')
    if not isExist:
        os.mkdir(data_folder+'raw_tbl')

    for i, f in tqdm(enumerate(pdfs)): 
        try: 
            tables = tabula.read_pdf(f,pages='all', silent=True)
            for i, table in enumerate(tables):
                table.to_csv(data_folder+'raw_tbl/{d}_{i}.csv'.format(d = f.split('/')[-1].split('_')[0], i = str(i)), index=False)
        except:
            continue

if __name__ == "__main__":
    main()