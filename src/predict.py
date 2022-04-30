"""
predict.py

# Files to predict on are very large. Will have to split the file first so
# that it doesn't take forever/use up all the memory on the system.
# NOTE: this split command cats the header row to each split file:
part=part2
section=AR
epochs=10
gpu=2
cd data/
gunzip output-$part-rx_method8_nwords125_clinical_bert_application_set_$section.txt.gz
tail -n +2 output-$part-rx_method8_nwords125_clinical_bert_application_set_$section.txt | split -d -C 100m - --filter='sh -c "{ head -n1 output-'$part'-rx_method8_nwords125_clinical_bert_application_set_'$section'.txt; cat; } > $FILE"' output-$part-rx_method8_nwords125_clinical_bert_application_set_$section\_split
gzip output-$part-rx_method8_nwords125_clinical_bert_application_set_$section.txt
cd ..

# then you can run with:
for f in data/*$part*_split*
do
    echo CUDA_VISIBLE_DEVICES=$gpu python3 src/predict.py --model models/bestepoch-bydrug-CB_8-$section-125_222_24_$epochs\_1e-06_256_32.pth --examples $f
done | bash

# when that is finished, recombine the results and then archive them
zcat results/*$part-rx-*.csv.gz | gzip > results/bestepoch-bydrug-CB-output-$part-rx_app8-$section\_ref8-$section\_222_24_10_1e-06_256_32.csv.gz
zcat results/bestepoch-bydrug-CB-output-$part-rx_app8-$section\_ref8-$section\_222_24_10_1e-06_256_32.csv.gz | wc -l
zcat data/output-$part-rx_method8_nwords125_clinical_bert_application_set_$section.txt.gz | wc -l

tar -czvf results/bestepoch-bydrug-CB-output-$part-rx-allparts_app8-$section\_ref8-$section\_222_24_10_1e-06_256_32.tar.gz results/*$part-rx-*.csv.gz
rm results/*$part-rx-*.csv.gz

rm data/*$part*_split*

"""

import os
import sys
import torch
import random
import argparse
import pandas as pd
import numpy as np

sys.path.append(os.path.abspath("./src"))
import fit_clinicalbert as cb

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--model', help='path to the model (pth) file', type=str, required=True)
    parser.add_argument('--examples', help='path to the file that contains the examples to make predict for', type=str, required=True)
    parser.add_argument('--batch-size', default=None, type=int, help='override the default batch size')
    args = parser.parse_args()

    model_filepath = args.model
    model_file = os.path.split(model_filepath)[-1]

    print(f"Loading model from {model_file}")
    model_file_noext = os.path.split(model_file)[-1].split('.')[0]

    if len(model_file_noext.split('_')) != 8:
        raise Exception("Model filename not in format expected: {prefix}_{refset}_{np_random_seed}_{random_state}_{EPOCHS}_{LR}_{max_length}_{batch_size}.pth")

    refset, refsection, refnwords = model_file_noext.split('_')[1].split('-')
    np_random_seed = int(model_file_noext.split('_')[2])
    random_state = int(model_file_noext.split('_')[3])
    EPOCHS = int(model_file_noext.split('_')[4])
    LR = model_file_noext.split('_')[5]
    max_length = int(model_file_noext.split('_')[6])
    batch_size = int(model_file_noext.split('_')[7])
    prefix = model_file_noext.split('_')[0]
    network = prefix.split('-')[2]

    print(f"Model")
    print(f"-------------------")
    print(f" prefix: {prefix}")
    print(f" network: {network}")
    print(f" refset: {refset}")
    print(f" refsection: {refsection}")
    print(f" refnwords: {refnwords}")
    print(f" np_random_seed: {np_random_seed}")
    print(f" random_state: {random_state}")
    print(f" EPOCHS: {EPOCHS}")
    print(f" LR: {LR}")
    print(f" max_length: {max_length}")
    print(f" batch_size: {batch_size}\n")

    ex_filename = os.path.split(args.examples)[-1].split('.')[0]
    ex_refset = int(ex_filename.split('_')[1].strip('method'))
    ex_nwords = ex_filename.split('_')[2].strip('nwords')
    ex_prefix = ex_filename.split('_')[0]
    ex_section = ex_filename.split('_')[7]

    if ex_nwords != refnwords:
        raise Exception(f"ERROR: There is an nwords mismatch between the model ({refnwords}) and the example data ({ex_nwords}).")

    if ex_section != refsection:
        print(f"WARNING: The examples section ({ex_section}) does not match the reference section ({refsection}))")

    is_split = False
    split_no = ''
    if ex_filename.find('split') != -1:
        is_split = True
        split_no = '-' + ex_filename.split('split')[1]

    results_path = f'./results/{prefix}-{ex_prefix}{split_no}_app{ex_refset}-{ex_section}_ref{refset}-{refsection}_{np_random_seed}_{random_state}_{EPOCHS}_{LR}_{max_length}_{batch_size}.csv.gz'

    print(f"Examples")
    print(f"-------------------")
    print(f" prefix: {ex_prefix}")
    print(f" refset: {ex_refset}")
    print(f" is_split: {is_split}")
    print(f" split_no: {split_no}")
    print(f" results path: {results_path}\n")

    if args.batch_size is None:
        # default is to use 2X the training batch size
        batch_size *= 2
        print(f"Setting prediction batch_size to 2X the training batch_size: {batch_size}")
    else:
        batch_size = args.batch_size
        print(f"Overriding batch_size to user defined: {batch_size}")

    if os.path.exists(results_path):
        print(f"  > Results file already exists, will not repeat evaluation. If you want to re-generate the results, delete the file and try again.")
        sys.exit(1)

    if network == 'CB':
        network_path = './models/Bio_ClinicalBERT/'
    elif network == 'PMB':
        network_path = './models/microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract/'
    else:
        raise Exception(f"ERROR: Unknown network: {network}")

    # initailize Dataset.tokenizer
    cb.Dataset.set_tokenizer(network_path)

    model = cb.ClinicalBertClassifier(network_path)
    model.load_state_dict(torch.load(model_filepath))

    # loading the example data
    df = pd.read_csv(args.examples)

    print(f"Evaluating example data...")
    outputs = cb.evaluate(model, df, max_length, batch_size, examples_only=True)
    npoutputs = [x.cpu().detach().numpy() for x in outputs]
    predictions = np.vstack(npoutputs)

    np.savetxt(results_path, predictions, delimiter=',')
