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
    parser.add_argument('--skip-models', action='store_true', default=False)
    parser.add_argument('--replicate', type=int, default=0, help="use to run exact replicates of existing experiments, results and models will be saved in a replicates/rep[NUM] directory")

    args = parser.parse_args()

    expfh = open('./experiments.json')
    data = json.loads(expfh.read())
    expfh.close()

    #eprint(json.dumps(data["experiments"][args.id], indent=4))
    DATA_DIR = './data'
    RESULTS_DIR = './results'
    MODELS_DIR = './models'
    BASE_DIR = '.'
    if args.replicate != 0:
        RESULTS_DIR = f'./replicates/rep{args.replicate}/results'
        MODELS_DIR = f'./replicates/rep{args.replicate}/models'
        BASE_DIR = f'./replicates/rep{args.replicate}'

        if not os.path.exists('./replicates'):
            os.mkdir('./replicates')
        if not os.path.exists(f'./replicates/rep{args.replicate}'):
            os.mkdir(f'./replicates/rep{args.replicate}')

        for subdir in (RESULTS_DIR, MODELS_DIR):
            if not os.path.exists(subdir):
                os.mkdir(subdir)

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
        fn = f"{DATA_DIR}/ref{method}_nwords{nwords}_clinical_bert_reference_set_{section}.txt"
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
    #eprint(fit_clinicalbert_data)
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
        'Bio_ClinicalBERT': 'CB',
        'microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract': 'PMB',
        'bestepoch-bydrug-CB_0-AR-125_222_24_25_1e-06_256_32.pth': 'CB0',
        'bestepoch-bydrug-CB_0-BW-125_222_24_25_1e-06_256_32.pth': 'CB1'
    }

    fcbd_params_outputs = list()

    epochperf_files = list()

    for (method, nwords, section, reffn), max_length, batch_size, epochs, lr, ifexists, network in fcbd_iterator:

        if max_length == -1:
            max_length = 2**int(np.ceil(np.log2(2*nwords)))

        if batch_size == -1:
            batch_size = batch_size_estimate(max_length)

        network_path = os.path.join(MODELS_DIR, network)
        finalmodfn = f"{MODELS_DIR}/final-bydrug-{network_codes[network]}_{method}-{section}-{nwords}_222_24_{epochs}_{lr}_{max_length}_{batch_size}.pth"
        bestepochmodfn = f"{MODELS_DIR}/bestepoch-bydrug-{network_codes[network]}_{method}-{section}-{nwords}_222_24_{epochs}_{lr}_{max_length}_{batch_size}.pth"
        epochsfn = f"{RESULTS_DIR}/epoch-results-{network_codes[network]}_{method}-{section}-{nwords}_222_24_{epochs}_{lr}_{max_length}_{batch_size}.csv"

        epochperf_files.append(epochsfn)

        fcbd_params_outputs.append(('final', network, method, section, nwords, epochs, lr, max_length, batch_size, finalmodfn))
        fcbd_params_outputs.append(('bestepoch', network, method, section, nwords, epochs, lr, max_length, batch_size, bestepochmodfn))

        # eprint(method, nwords, section, reffn, max_length, batch_size, epoch, lr, ifexists, network)
        file_exists = os.path.exists(finalmodfn)
        bestepoch_file_exists = os.path.exists(bestepochmodfn)
        epochs_file_exists = os.path.exists(epochsfn)

        if not args.skip_models:
            eprint(f"  {finalmodfn}...{file_exists}")
            eprint(f"  {bestepochmodfn}...{bestepoch_file_exists}")
            eprint(f"  {epochsfn}...{epochs_file_exists}")

        if not args.skip_models and (not file_exists or not bestepoch_file_exists or not epochs_file_exists):
            if not file_exists:
                eprint(f"    NOT FOUND: final model file missing.")
            if not bestepoch_file_exists:
                eprint(f"    NOT FOUND: best epoch model file missing.")
            if not epochs_file_exists:
                eprint(f"    NOT FOUND: epoch results file missing.")

            command = f"python3 src/fit_clinicalbert.py --base-dir {BASE_DIR} --ref {reffn} --max-length {max_length} --batch-size {batch_size} --epochs {epochs} --learning-rate {lr} --ifexists {ifexists} --network {network_path}"
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

    ard_param_outputs = list()

    for (modeltype, network, method, section, nwords, epochs, lr, max_length, batch_size, modelfn), skip_train, _network in ard_iterator:

        network_path = os.path.join(MODELS_DIR, network)

        testmodresfn = f"{RESULTS_DIR}/{modeltype}-bydrug-{network_codes[network]}-test_{method}-{section}-{nwords}_222_24_{epochs}_{lr}_{max_length}_{batch_size}.csv"
        validmodresfn = f"{RESULTS_DIR}/{modeltype}-bydrug-{network_codes[network]}-valid_{method}-{section}-{nwords}_222_24_{epochs}_{lr}_{max_length}_{batch_size}.csv"

        test_file_exists = os.path.exists(testmodresfn)
        valid_file_exists = os.path.exists(validmodresfn)
        eprint(f"  {testmodresfn}...{test_file_exists}")
        eprint(f"  {validmodresfn}...{valid_file_exists}")

        if not test_file_exists or not valid_file_exists:
            skip_train_str = '' if not skip_train else '--skip-train '
            command = f"python3 src/analyze_results.py --base-dir {BASE_DIR} --model {modelfn} {skip_train_str}--network {network_path}"
            eprint(f"    NOT FOUND, create with: {command}")
            is_complete = False
            remaining_commands.append(command)

        ard_param_outputs.append((modeltype, network, method, section, nwords, epochs, lr, max_length, batch_size, [testmodresfn, validmodresfn]))

    eprint("")
    eprint("Checking for grouped results files...")
    compile_results_data = experiment.get("compile_results", defaults["compile_results"])

    crd_iterator = itertools.product(
        ard_param_outputs,
        compile_results_data.get("group-function", defaults["compile_results"]["group-function"])
    )

    grouped_files = {'final': list(), 'bestepoch': list()}

    for (modeltype, network, method, section, nwords, epochs, lr, max_length, batch_size, (testmodresfn, validmodresfn)), grpfun in crd_iterator:

        grpresfn = f"{RESULTS_DIR}/grouped-{grpfun}-{modeltype}-bydrug-{network_codes[network]}_{method}-{section}-{nwords}_222_24_{epochs}_{lr}_{max_length}_{batch_size}.csv"
        grouped_files[modeltype].append(grpresfn)

        file_exists = os.path.exists(grpresfn)
        eprint(f"  {grpresfn}...{file_exists}")

        if not file_exists:
            command = f"python3 src/compile_results.py --base-dir {BASE_DIR} --group-function {grpfun} --results {testmodresfn} {validmodresfn} --examples ./data/ref{method}_nwords{nwords}_clinical_bert_reference_set_{section}.txt"
            eprint(f"    NOT FOUND, create with: {command}")
            is_complete = False
            remaining_commands.append(command)

    eprint("")

    if not is_complete:
        eprint(f"EXPERIMENT IS INCOMPLETE: One or more files are missing. {len(remaining_commands)} commands need to be run. Printing them to standard output, pipe this script to bash to automatically run them.")
    for command in remaining_commands:
        if args.gpu == -1:
            print(command)
        else:
            print(f"CUDA_VISIBLE_DEVICES={args.gpu} " + command)
    else:
        eprint("EXPERIMENT IS COMPLETE!")

        eprint("Writing out analysis file...")
        if os.path.exists('analysis.json'):
            expfh = open('./analysis.json')
            analysis = json.loads(expfh.read())
            expfh.close()
        else:
            analysis = {"experiments": dict()}

        if type(experiment["factor"]["parameter"]) is list:
            factor_name = experiment["factor"]["script"]
            param_levels = list()

            for param in experiment["factor"]["parameter"]:
                factor_name += '.' + param
                param_levels.append(experiment[experiment["factor"]["script"]][param])

            factor_levels = list(itertools.product(*param_levels))

        else:
            factor_name = f'{experiment["factor"]["script"]}.{experiment["factor"]["parameter"]}'
            factor_levels = experiment[experiment["factor"]["script"]][experiment["factor"]["parameter"]]

        if not "labels" in experiment["factor"]:
            factor_labels = [f"{factor_name}:{l}" for l in factor_levels]
        else:
            factor_labels = experiment["factor"]["labels"]

        for modeltype in ('final', 'bestepoch'):
            if not len(factor_labels) == len(grouped_files[modeltype]):
                raise Exception(f"FAILED: The number of resulting grouped files for ({modeltype}) is not consistent with the experimental setup.")

        experiment_id = f"{args.id}"
        if args.replicate != 0:
            experiment_id = f"{args.id}R{args.replicate}"

        analysis["experiments"][experiment_id] = {
            "name": experiment["name"],
            "description": experiment["description"],
            "factor": factor_name,
            "levels": factor_levels,
            "labels": factor_labels,
            "final": grouped_files["final"],
            "bestepoch": grouped_files["bestepoch"],
            "epochperf": epochperf_files,
        }

        expfh = open('./analysis.json', 'w')
        expfh.write(json.dumps(analysis, indent=4))
        expfh.close()

        print("FINISHED.")
