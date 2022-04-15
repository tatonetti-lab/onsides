import os
import sys
import torch
import random
import argparse
import pandas as pd
import numpy as np

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=str, required=True)

    args = parser.parse_args()

    model_filepath = args.model
    model_file = os.path.split(model_filepath)[-1]

    print(f"Loading model from {model_file}")

    if len(model_file.split('_')) != 6:
        raise Exception("Model filename not in format expected: {prefix}_{refset}_{np_random_seed}_{random_state}_{EPOCHS}_{LR}.pth")

    refset = int(model_file.split('_')[1])
    np_random_seed = int(model_file.split('_')[2])
    random_state = int(model_file.split('_')[3])
    EPOCHS = int(model_file.split('_')[4])
    LR = model_file.split('_')[5].split('.')[0]
    
    prefix = model_file.split('_')[0]

    print(f" prefix: {prefix}")
    print(f" refset: {refset}")
    print(f" np_random_seed: {np_random_seed}")
    print(f" random_state: {random_state}")
    print(f" EPOCHS: {EPOCHS}")
    print(f" LR: {LR}")

    sys.path.append(os.path.abspath("./src"))
    import fit_clinicalbert as cb

    model = cb.ClinicalBertClassifier()
    model.load_state_dict(torch.load(model_file))

    # loading and re-splitting the data
    datapath = f'../data/ref{refset}_clinical_bert_reference_set.txt'
    df = pd.read_csv(datapath)

    # randomly select by drug/label
    druglist = sorted(set(df['drug']))

    random.seed(np_random_seed)
    random.shuffle(druglist)

    drugs_train, drugs_val, drugs_test = np.split(druglist, [int(0.8*len(druglist)), int(0.9*len(druglist))])

    print(f"Split labels in train, val, test by drug:")
    print(len(drugs_train), len(drugs_val), len(drugs_test))

    df_train = df[df['drug'].isin(drugs_train)]
    df_val = df[df['drug'].isin(drugs_val)]
    df_test = df[df['drug'].isin(drugs_test)]

    print(len(df_train), len(df_val), len(df_test))

    print(f"Evaluating testing data...")
    outputs = cb.evaluate(model, df_test)
    npoutputs = [x.cpu().detach().numpy() for x in outputs]
    predictions = np.vstack(npoutputs)

    np.savetxt(f'./results/{prefix}-test_{refset}_{np_random_seed}_{random_state}_{EPOCHS}_{LR}.csv', predictions, delimiter=',')

    print(f"Evaluating validation data...")
    outputs = cb.evaluate(model, df_val)
    npoutputs = [x.cpu().detach().numpy() for x in outputs]
    predictions = np.vstack(npoutputs)

    np.savetxt(f'./results/{prefix}-valid_{refset}_{np_random_seed}_{random_state}_{EPOCHS}_{LR}.csv', predictions, delimiter=',')

    print(f"Evaluating training data...")
    outputs = cb.evaluate(model, df_train)
    npoutputs = [x.cpu().detach().numpy() for x in outputs]
    predictions = np.vstack(npoutputs)

    np.savetxt(f'./results/{prefix}-train_{refset}_{np_random_seed}_{random_state}_{EPOCHS}_{LR}.csv', predictions, delimiter=',')
