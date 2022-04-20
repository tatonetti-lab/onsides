"""
experiment_tracker.py

Keep track of the experiments we are running, which parameters are being tested, and
where we are in generating the data.
"""

import os
import sys
import json
import argparse
import itertools

import numpy as np

from fit_clinicalbert import batch_size_estimate

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--id', type=str, required=True)
    parser.add_argument('--gpu', type=int, help="if you want to prepend the output commands with the specific gpu, specify a gpu number here.", default=-1)

    args = parser.parse_args()

    expfh = open('./experiments.json')
    data = json.loads(expfh.read())

    #eprint(json.dumps(data["experiments"][args.id], indent=4))

    if not args.id in data["experiments"]:
        raise Exception(f"ERROR: Could not find an experiment with id={args.id} in experiments.json.")

    defaults = data["defaults"]
    experiment = data["experiments"][args.id]
    is_complete = True
    remaining_commands = list()

    eprint(f"Experiment {args.id} loaded.")
    eprint(f'  Name: {experiment["name"]}')
    eprint(f'  Description: {experiment["description"]}')
    eprint(f"-------------------------------------------")

    eprint("")
    eprint("Checking for training data...")

    construct_training_data = experiment.get("construct_training_data", defaults["construct_training_data"])

    ctd_iterator = itertools.product(
        construct_training_data.get("method", defaults["construct_training_data"]["method"]),
        construct_training_data.get("nwords", defaults["construct_training_data"]["nwords"]),
        construct_training_data.get("section", defaults["construct_training_data"]["section"])
    )

    ctd_params_outputs = list()

    for method, nwords, section in ctd_iterator:
        fn = f"./data/ref{method}_nwords{nwords}_clinical_bert_reference_set_{section}.txt"
        ctd_params_outputs.append((method, nwords, section, fn))

        file_exists = os.path.exists(fn)
        eprint(f"  {fn}...{file_exists}")
        if not file_exists:
            command = f"python3 src/construct_training_data.py --method {method} --nwords {nwords} --section {section}"
            eprint(f"    NOT FOUND, create with: {command}")
            is_complete = False
            remaining_commands.append(command)

    eprint("")
    eprint("Checking for model output...")
    fit_clinicalbert_data = experiment.get("fit_clinicalbert", defaults["fit_clinicalbert"])

    fcbd_iterator = itertools.product(
        ctd_params_outputs,
        fit_clinicalbert_data.get("max-length", defaults["fit_clinicalbert"]["max-length"]),
        fit_clinicalbert_data.get("batch-size", defaults["fit_clinicalbert"]["batch-size"]),
        fit_clinicalbert_data.get("epochs", defaults["fit_clinicalbert"]["epochs"]),
        fit_clinicalbert_data.get("learning-rate", defaults["fit_clinicalbert"]["learning-rate"]),
        fit_clinicalbert_data.get("ifexists", defaults["fit_clinicalbert"]["ifexists"]),
        fit_clinicalbert_data.get("network", defaults["fit_clinicalbert"]["network"]),
    )
    network_codes = {
        'models/Bio_ClinicalBERT/': 'CB',
        'models/microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract/': 'PMB'
    }

    fcbd_params_outputs = list()

    for (method, nwords, section, reffn), max_length, batch_size, epochs, lr, ifexists, network in fcbd_iterator:

        if max_length == -1:
            max_length = 2**int(np.ceil(np.log2(2*nwords)))

        if batch_size == -1:
            batch_size = batch_size_estimate(max_length)

        finalmodfn = f"./models/final-bydrug-{network_codes[network]}_{method}-{section}-{nwords}_222_24_{epochs}_{lr}_{max_length}_{batch_size}.pth"
        bestepochmodfn = f"./models/bestepoch-bydrug-{network_codes[network]}_{method}-{section}-{nwords}_222_24_{epochs}_{lr}_{max_length}_{batch_size}.pth"
        epochsfn = f"./results/epoch-results-{network_codes[network]}_{method}-{section}-{nwords}_222_24_{epochs}_{lr}_{max_length}_{batch_size}.csv"

        fcbd_params_outputs.append(('final', network, method, section, nwords, epochs, lr, max_length, batch_size, finalmodfn))
        fcbd_params_outputs.append(('bestepoch', network, method, section, nwords, epochs, lr, max_length, batch_size, bestepochmodfn))

        # eprint(method, nwords, section, reffn, max_length, batch_size, epoch, lr, ifexists, network)
        file_exists = os.path.exists(finalmodfn)
        bestepoch_file_exists = os.path.exists(bestepochmodfn)
        epochs_file_exists = os.path.exists(epochsfn)

        eprint(f"  {finalmodfn}...{file_exists}")
        eprint(f"  {bestepochmodfn}...{bestepoch_file_exists}")
        eprint(f"  {epochsfn}...{epochs_file_exists}")

        if not file_exists or not bestepoch_file_exists or not epochs_file_exists:
            if not file_exists:
                eprint(f"    NOT FOUND: final model file missing.")
            if not bestepoch_file_exists:
                eprint(f"    NOT FOUND: best epoch model file missing.")
            if not epochs_file_exists:
                eprint(f"    NOT FOUND: epoch results file missing.")

            command = f"python3 src/fit_clinicalbert.py --ref {reffn} --max_length {max_length} --batch_size {batch_size} --epochs {epochs} --learning-rate {lr} --ifexists {ifexists} --network {network}"
            eprint(f"    Create with: {command}")
            is_complete = False
            remaining_commands.append(command)

    eprint("")
    eprint("Checking for results files...")
    analyze_results_data = experiment.get("analyze_results", defaults["analyze_results"])

    ard_iterator = itertools.product(
        fcbd_params_outputs,
        analyze_results_data.get("skip-train", defaults["analyze_results"]["skip-train"]),
        analyze_results_data.get("network", defaults["analyze_results"]["network"])
    )

    for (modeltype, network, method, section, nwords, epochs, lr, max_length, batch_size, modelfn), skip_train, _network in ard_iterator:

        testmodresfn = f"./results/{modeltype}-bydrug-{network_codes[network]}-test_{method}-{section}-{nwords}_222_24_{epochs}_{lr}_{max_length}_{batch_size}.csv"
        validmodresfn = f"./results/{modeltype}-bydrug-{network_codes[network]}-valid_{method}-{section}-{nwords}_222_24_{epochs}_{lr}_{max_length}_{batch_size}.csv"

        test_file_exists = os.path.exists(testmodresfn)
        valid_file_exists = os.path.exists(validmodresfn)
        eprint(f"  {testmodresfn}...{test_file_exists}")
        eprint(f"  {validmodresfn}...{valid_file_exists}")

        if not test_file_exists or not valid_file_exists:
            skip_train_str = '' if not skip_train else '--skip-train '
            command = f"python3 src/analyze_results.py --model {modelfn} {skip_train_str}--network {network}"
            eprint(f"    NOT FOUND, create with: {command}")
            is_complete = False
            remaining_commands.append(command)

    eprint("")

    if not is_complete:
        eprint("EXPERIMENT IS INCOMPLETE: One or more files are missing. The following command need to be run:")
        for command in remaining_commands:
            if args.gpu == -1:
                print(command)
            else:
                print(f"CUDA_VISIBLE_DEVICES={args.gpu} " + command)
    else:
        eprint("EXPERIMENT IS COMPLETE!")
