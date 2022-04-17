"""
predict.py

# Files to predict on are very large. Will have to split the file first so
# that it doesn't take forever/use up all the memory on the system.
# NOTE: this split command cats the header row to each split file:
tail -n +2 output-part4_app0_clinical_bert_application_set.txt| split -d -C 100m - --filter='sh -c "{ head -n1 output-part4_app0_clinical_bert_application_set.txt; cat; } > $FILE"' output-part4_app0_clinical_bert_application_set_split

# then you can run with:
for f in data/*_split*
do
    CUDA_VISIBLE_DEVICES=3 python3 src/predict.py --model models/final-bydrug_0_222_24_25_1e-06.pth --examples $f
done
"""

import os
import sys
import torch
import random
import argparse
import pandas as pd
import numpy as np

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--model', help='path to the model (pth) file', type=str, required=True)
    parser.add_argument('--examples', help='path to the file that contains the examples to make predict for', type=str, required=True)

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
    print(f"Model")
    print(f"-------------------")
    print(f" prefix: {prefix}")
    print(f" refset: {refset}")
    print(f" np_random_seed: {np_random_seed}")
    print(f" random_state: {random_state}")
    print(f" EPOCHS: {EPOCHS}")
    print(f" LR: {LR}\n")

    ex_filename = os.path.split(args.examples)[-1]
    ex_refset = int(ex_filename.split('_')[1].strip('app'))
    ex_prefix = ex_filename.split('_')[0]

    is_split = False
    split_no = ''
    if ex_filename.find('split') != -1:
        is_split = True
        split_no = '-' + ex_filename.split('split')[1]

    results_path = f'./results/{prefix}-{ex_prefix}{split_no}_app{ex_refset}_ref{refset}_{np_random_seed}_{random_state}_{EPOCHS}_{LR}.csv'

    print(f"Examples")
    print(f"-------------------")
    print(f" prefix: {ex_prefix}")
    print(f" refset: {ex_refset}")
    print(f" is_split: {is_split}")
    print(f" split_no: {split_no}")
    print(f" results path: {results_path}\n")

    if os.path.exists(results_path):
        print(f"  > Results file already exists, will not repeat evaluation. If you want to re-generate the results, delete the file and try again.")
        sys.exit(1)


    sys.path.append(os.path.abspath("./src"))
    import fit_clinicalbert as cb

    model = cb.ClinicalBertClassifier()
    model.load_state_dict(torch.load(model_filepath))

    # loading the example data
    df = pd.read_csv(args.examples)

    print(f"Evaluating example data...")
    outputs = cb.evaluate(model, df, examples_only=True)
    npoutputs = [x.cpu().detach().numpy() for x in outputs]
    predictions = np.vstack(npoutputs)

    np.savetxt(results_path, predictions, delimiter=',')
