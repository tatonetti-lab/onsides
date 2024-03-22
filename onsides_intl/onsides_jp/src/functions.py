import argparse
import os
import numpy as np
import pandas as pd
import requests
from tqdm import tqdm
from bs4 import BeautifulSoup
from glob import glob

def format_code(code):
    # This function takes in the code and prepends zeros to the left of the string to make it 8 characters.
    formatted_code = str(code).zfill(8)
    return formatted_code

def download_html(code, out_folder):
    # Grabs HTML from the KEGG website and downloads it into the designated raw file folder.
    r = requests.get('https://www.kegg.jp/medicus-bin/japic_med?japic_code={}'.format(code))
    # Encode (so Japanese characters don't break)
    r.encoding = r.apparent_encoding
    # Save raw HTML
    with open(out_folder + '{}.txt'.format(code), 'w') as f:
        f.write(r.text)