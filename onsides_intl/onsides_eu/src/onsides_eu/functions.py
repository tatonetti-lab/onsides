import argparse
import pandas as pd, numpy as np
import requests
import warnings
warnings.filterwarnings('ignore')
from glob import glob
from tqdm import tqdm
import apt
from bs4 import BeautifulSoup
##### specific functions #####
import tabula, camelot
import pypdf
import PyPDF2
import wget
from pypdf import PdfReader
