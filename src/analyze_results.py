import os
import sys
import torch
import pandas as pd
import numpy as np

sys.path.append(os.path.abspath("./src"))
import fit_clinicalbert as cb

model = cb.ClinicalBertClassifier()

np_random_seed = 222
random_state = 24
EPOCHS = 5
LR = 1e-06

model.load_state_dict(torch.load(f'./models/final_{np_random_seed}_{random_state}_{EPOCHS}_{LR}.pth'))

# loading and re-splitting the data
datapath = './data/clinical_bert_reference_set.txt'
df = pd.read_csv(datapath)

np.random.seed(np_random_seed)
df_train, df_val, df_test = np.split(df.sample(frac=1, random_state=random_state),
                                     [int(0.8*len(df)), int(0.9*len(df))])

print(len(df_train), len(df_val), len(df_test))

outputs = cb.evaluate(model, df_test)
npoutputs = [x.cpu().detach().numpy() for x in outputs]
predictions = np.vstack(npoutputs)

np.savetxt(f'./results/test_pred_{np_random_seed}_{random_state}_{EPOCHS}_{LR}.csv', predictions, delimiter=',')
