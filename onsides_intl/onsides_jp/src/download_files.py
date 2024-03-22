import argparse
import os
import numpy as np
import pandas as pd
import requests
from tqdm import tqdm
from bs4 import BeautifulSoup
from glob import glob
from functions import format_code, download_html

def make_rx_datatable(data_folder):
    # Make datatable of all drugs available (RX)
    kegg_url_init = 'https://www.kegg.jp/medicus-bin/search_drug?display=med&page=1&uid=1685277724113953'
    r = requests.get(kegg_url_init)
    r.encoding = r.apparent_encoding
    soup = BeautifulSoup(r.text, 'html.parser')
    # Get number of individual rx drugs
    rx_num = int(soup.find('li', class_='med on').text.split('(')[-1].replace(')',''))
    # Get number of rx drug pages to parse
    rx_page_num = int(np.ceil(int(rx_num)/40))
    print(rx_num, rx_page_num)

    kegg_rx_drug_list = []
    for i in tqdm(range(int(rx_page_num))):
        page_num = i+1
        kegg_url_page = 'https://www.kegg.jp/medicus-bin/search_drug?display=med&page={}&uid=1685277724113953'.format(page_num)
        r = requests.get(kegg_url_page)
        r.encoding = r.apparent_encoding
        page_soup = BeautifulSoup(r.text, 'html.parser')
        drug_table_rows = page_soup.find('table', class_='list1').find_all('tr')
        for row in drug_table_rows[1:]: # Skip header
            kegg_rx_drug_list.append(row.find_all('td')) # Split into each cell

    kegg_rx_drug_df = pd.DataFrame(kegg_rx_drug_list, columns=['product', 'ingredient', 'indication', 'kegg_drug_id'])
    kegg_rx_drug_df['kegg_product_id'] = kegg_rx_drug_df['product'].apply(lambda x: x.find('a', href=True)['href'].split('japic_code=')[-1])
    kegg_rx_drug_df['product'] = kegg_rx_drug_df['product'].apply(lambda x: x.text.strip())
    kegg_rx_drug_df['ingredient'] = kegg_rx_drug_df.ingredient.apply(lambda x: ';'.join(x.text.split('\n')))
    kegg_rx_drug_df['indication'] = kegg_rx_drug_df.indication.apply(lambda x: x.text)
    kegg_rx_drug_df['kegg_drug_id'] = kegg_rx_drug_df.kegg_drug_id.apply(lambda x: x.text)

    kegg_rx_drug_df.to_csv(os.path.join(data_folder, 'kegg_rx_drug_data.csv'), index=False, encoding='utf-8-sig')

def make_otc_datatable(data_folder):
    # Make datatable of all drugs available (OTC) - currently not used
    kegg_url_init = 'https://www.kegg.jp/medicus-bin/search_drug?display=otc&page=1&uid=1685277724113953'
    r = requests.get(kegg_url_init)
    r.encoding = r.apparent_encoding
    soup = BeautifulSoup(r.text, 'html.parser')
    # Get number of individual otc drugs
    otc_num = int(soup.find('li', class_='otc on').text.split('(')[-1].replace(')',''))
    # Get number of otc drug pages to parse
    otc_page_num = int(np.ceil(int(otc_num)/40))
    print(otc_num, otc_page_num)

    kegg_otc_drug_list = []
    for i in tqdm(range(int(otc_page_num))):
         page_num = i + 1
         kegg_url_page = 'https://www.kegg.jp/medicus-bin/search_drug?display=otc&page={}&uid=1685277724113953'.format(page_num)
         r = requests.get(kegg_url_page)
         r.encoding = r.apparent_encoding
         page_soup = BeautifulSoup(r.text, 'html.parser')
         drug_table = page_soup.find('table', class_='list1')
         if drug_table is not None:
             drug_table_rows = drug_table.find_all('tr')
             for row in drug_table_rows[1:]:  # Skip header
                 kegg_otc_drug_list.append(row.find_all('td'))  # Split into each cell
         else:
             # Handle the case when the table is not found
             print(f"Table 'list1' not found on page {page_num}. Skipping...")

    kegg_otc_drug_df = pd.DataFrame(kegg_otc_drug_list, columns=['product', 'company', 'indication', 'risk_level'])
    kegg_otc_drug_df['kegg_product_id'] = kegg_otc_drug_df['product'].apply(lambda x: x.find('a', href=True)['href'].split('japic_code=')[-1])
    kegg_otc_drug_df['product'] = kegg_otc_drug_df['product'].apply(lambda x: x.text.strip())
    kegg_otc_drug_df['company'] = kegg_otc_drug_df.company.apply(lambda x: x.text)
    kegg_otc_drug_df['indication'] = kegg_otc_drug_df.indication.apply(lambda x: x.text)
    kegg_otc_drug_df['risk_level'] = kegg_otc_drug_df.risk_level.apply(lambda x: x.text)

    kegg_otc_drug_df.to_csv(os.path.join(data_folder, 'kegg_otc_drug_data.csv'), index=False)

def download_html(data_folder, type = 'rx'):
    #read in drug table csv file
    if type == 'rx':
        kegg_df = pd.read_csv(os.path.join(data_folder, 'kegg_rx_drug_data.csv'))
        isExist = os.path.exists(data_folder+'raw_rx')
        if not isExist:
            os.mkdir(data_folder+'raw_rx')
        raw_file_folder = os.path.join(data_folder, 'raw_rx/')
    elif type == 'otc':
        kegg_df = pd.read_csv(os.path.join(data_folder, 'kegg_otc_drug_data.csv'))
        isExist = os.path.exists(data_folder+'raw_otc')
        if not isExist:
            os.mkdir(data_folder+'raw_otc')
        raw_file_folder = os.path.join(data_folder, 'raw_otc/')
    
    for code in tqdm(kegg_df.kegg_product_id.tolist()):
        # Iterate through codes, download each drug HTML file
        japic_code = format_code(code)
        download_html(japic_code, out_folder=raw_file_folder)

    # Check if all files have been downloaded properly (sometimes the internet connection fails)
    error_codes = []
    for code in tqdm(kegg_df['kegg_product_id'].tolist()):
        japic_code = format_code(code)
        file_path = os.path.join(raw_file_folder, '{}.txt'.format(japic_code))
        with open(file_path) as f:
            s = BeautifulSoup(f, 'html.parser')
        try:
            if s.find('title').text == '403 Forbidden':
                error_codes.append(japic_code)
                # Redownload, try to replace file with the correct one
                download_html(japic_code, out_folder=raw_file_folder)
        except:
            pass

    # Check the number of total files - should be 14,196 (as of May 28th)
    file_count = len(glob(raw_file_folder + '/*.txt'))
    print("Files in KEGG database : {kegg}\nTotal number of files : {dl}".format(kegg = str(kegg_df.shape[0]), dl=file_count))

def main():
    parser = argparse.ArgumentParser(description='download drug labels from KEGG website')
    parser.add_argument('--data_folder', required=True, help='Path to the data folder.')
    args = parser.parse_args()

    data_folder = args.data_folder
    
    #make the datatables for Rx and OTC drugs to get the lists of drug labels available
    make_rx_datatable(data_folder)
    make_otc_datatable(data_folder)

    # Download all raw HTML files of drugs (RX) (slow process : about 5.5hrs for ~14,000 drug labels)
    # Input: kegg_rx_drug_data.csv
    # Output: folder (/raw/) filled with individual HTML drug
    download_html(data_folder, type = 'rx')
    download_html(data_folder, type = 'otc')

if __name__ == "__main__":
    main()
