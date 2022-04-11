"""
Use clinical bert to classify terms as events or not_events.

"""

import pandas as pd

datapath = './data/meddra_llt_pt_map.txt'
df = pd.read_csv(datapath)
print(df.head())
