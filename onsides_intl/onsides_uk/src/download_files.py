import numpy as np
import pandas as pd
import requests
from tqdm import tqdm
import ast, wget, os
from glob import glob
from time import sleep
from bs4 import BeautifulSoup
import argparse

def main():
    parser = argparse.ArgumentParser(description='download drug labels from EU EMA website')
    parser.add_argument('--data_folder', required=True, help='Path to the data folder.', default='./data/')
    args = parser.parse_args()
    data_folder = args.data_folder

    #scrape the MHRA website to build a list of ingredients in alphabetical order. 
    ingredient_list = []
    for l in tqdm(['0-9', '', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']):
        url = 'https://www.medicines.org.uk/emc/browse-ingredients/{}'.format(l)
        r = requests.get(url).text
        s = BeautifulSoup(r)
        drugs = s.find(class_='browse-results')
        for d in drugs.find_all('a', href=True):
            drug_id = d['href']
            drug_name = d.text
            ingredient_list.append([drug_id, drug_name])
    ingredient_df = pd.DataFrame(ingredient_list, columns = ['ingredient_id', 'ingredient_name'])
    ingredient_df.to_csv(data_folder+'ingredient_data.csv', index=False)
    print('scraped {} ingredients'.format(str(ingredient_df.shape[0])))


    #scrape the Medicines.org.uk website to build a list of products
    product_list = []
    redo = []
    for ingredient_id, ingredient_name in tqdm(zip(ingredient_df.ingredient_id, ingredient_df.ingredient_name)):
        url = 'https://www.medicines.org.uk{}?offset=1&limit=200'.format(ingredient_id)
        r = requests.get(url).text
        s = BeautifulSoup(r)
        #number of items
        item_num = s.find(class_='search-results-header').find('span').text.replace(' products found','').replace(' product found','')
        #make table of items
        product_data = s.find_all(class_='search-results-product')
        for i in product_data:
            product_id = i.find(class_='search-results-product-info-title-link emc-link', href=True)['href']
            product_name = i.find(class_='search-results-product-info-title-link emc-link').text
            active_ingredients = i.find(class_="search-results-product-info-type emc-text-default").text
            company_name = i.find(class_="search-results-product-info-company").text
            product_list.append([ingredient_id, ingredient_name, product_id, product_name, active_ingredients, company_name])
        if int(item_num) > 200:
            redo.append([ingredient_id, ingredient_name])
    drug_df = pd.DataFrame(product_list, columns = ['ingredient_id', 'ingredient_name', 'product_id', 'product_name', 'active_ingredients', 'company_name'])
    drug_df.to_csv(data_folder+'drug_data.csv', index=False)
    print('scraped {} products'.format(str(drug_df.shape[0])))

    #check if raw folder exists, if not, make it
    os.makedirs(data_folder+'raw', exist_ok=True)

    #download the text from the product pages.
    drug_df = pd.read_csv(data_folder+'drug_data.csv')
    print('start the download for {} products'.format(str(drug_df.shape[0])))
    for product in tqdm(drug_df.product_id.unique().tolist()):
        url = 'https://www.medicines.org.uk{}'.format(product)
        r = requests.get(url)
        #save raw html
        f = open(data_folder+'raw/{}.txt'.format(product.split('/')[-2]), 'w')
        f.write(r.text)
        f.close()
    
    #retry for failed downloads
    redo = []
    for product in tqdm(drug_df.product_id.unique().tolist()):
        f = (data_folder+'raw/{}.txt'.format(product.split('/')[-2]))
        try:
            with open(f) as fi:
                s = BeautifulSoup(fi, 'html.parser')
            if s.find('title').text == 'emc - are you human?':
                ##retry
                url = 'https://www.medicines.org.uk{}'.format(product)
                r = requests.get(url)
                s = BeautifulSoup(r.text, 'html.parser')
                if s.find('title').text != 'emc - are you human?':
                    #save raw html
                    f = open(data_folder+'raw/{}.txt'.format(product.split('/')[-2]), 'w')
                    f.write(r.text)
                    f.close()
                    redo.append([product, 'done'])
                else:
                    redo.append([product, 'failed'])
        except:
            ##retry
            url = 'https://www.medicines.org.uk{}'.format(product)
            r = requests.get(url)
            s = BeautifulSoup(r.text, 'html.parser')
            if s.find('title').text != 'emc - are you human?':
                #save raw html
                f = open(data_folder+'raw/{}.txt'.format(product.split('/')[-2]), 'w')
                f.write(r.text)
                f.close()
                redo.append([product, 'done'])
            else:
                redo.append([product, 'failed'])

if __name__ == "__main__":
    main()