"""
experiment_tracker.py

Keep track of the experiments we are running, which parameters are being tested, and
where we are in generating the data.

EXAMPLES

To check status of all of the experiments. Use the skip models flag if you are not
on a machine ready to train the neural networks (GPU ready).
```
python3 src/experiment_tracker.py --all [--skip-models]
```

To check the status of a specific experiment. Use the skip models flag if you are not
on a machine ready to train the neural networks (GPU ready).
```
python3 src/experiment_tracker.py --id 0 [--skip-models]
```

"""

import os
import sys
import json
import psutil
import argparse
import itertools

import numpy as np

from fit_clinicalbert import batch_size_estimate

QUIET_MODE = False

def eprint(*args, **kwargs):
    if not QUIET_MODE:
        print(*args, file=sys.stderr, **kwargs)

def qprint(*args, **kwargs):
    if QUIET_MODE:
        print(*args, file=sys.stderr, **kwargs)

def tracker(args_id, args, data, replicate, clean_experiment):

    #DATA_DIR = './data'
    REFS_DIR = './data/refs'
    RESULTS_DIR = './results'
    MODELS_DIR = './models'
    BASE_DIR = '.'
    if replicate != 0:
        RESULTS_DIR = f'./replicates/rep{replicate}/results'
        MODELS_DIR = f'./replicates/rep{replicate}/models'
        BASE_DIR = f'./replicates/rep{replicate}'

        if not os.path.exists('./replicates'):
            os.mkdir('./replicates')
        if not os.path.exists(f'./replicates/rep{replicate}'):
            os.mkdir(f'./replicates/rep{replicate}')

        for subdir in (RESULTS_DIR, MODELS_DIR):
            if not os.path.exists(subdir):
                os.mkdir(subdir)

    defaults = data["defaults"]
    is_deployment = False

    if args_id in data["experiments"]:
        experiment = data["experiments"][args_id]
    elif args_id in data["deployments"]:
        experiment = data["deployments"][args_id]
        is_deployment = True
    else:
        raise Exception(f"ERROR: Could not find an experiment or deployment with id={args_id} in experiments.json.")

    if (args.skip_models or args.skip_deployments) and is_deployment:
        eprint(f"Deployments must not have the --skip-models flag. Skipping deployment {args_id}.")
        return

    is_complete = True
    remaining_commands = list()
    output_files = list()


    if replicate == 0:
        eprint(f"Experiment {args_id} loaded.")
    else:
        eprint(f"Experiment {args_id}, Replicate {replicate} loaded.")

    eprint(f'  Name: {experiment["name"]}')
    eprint(f'  Description: {experiment["description"]}')
    eprint(f"-------------------------------------------")

    eprint("")
    eprint("Checking for training data...")

    repexpstr = 'Experiment' if replicate == 0 else 'Replicate'
    repexpidstr = args_id if replicate == 0 else f'{args_id}R{replicate}'

    qprint(f"Loaded {repexpstr:10} {repexpidstr:11s} ({experiment['name'][:50]:50s}), checking status...", end='')

    construct_training_data = experiment.get("construct_training_data", defaults["construct_training_data"])

    ctd_iterator = itertools.product(
        construct_training_data.get("method", defaults["construct_training_data"]["method"]),
        construct_training_data.get("nwords", defaults["construct_training_data"]["nwords"]),
        construct_training_data.get("section", defaults["construct_training_data"]["section"])
    )

    ctd_params_outputs = list()

    for method, nwords, section in ctd_iterator:
        fn = f"{REFS_DIR}/ref{method}_nwords{nwords}_clinical_bert_reference_set_{section}.txt"
        ctd_params_outputs.append((method, nwords, section, fn))

        file_exists = os.path.exists(fn)
        if not args.skip_refs:
            eprint(f"  {fn} ...{file_exists}")

        if not args.skip_refs and not file_exists:
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
        fit_clinicalbert_data.get("refsource", defaults["fit_clinicalbert"]["refsource"]),
        fit_clinicalbert_data.get("split-method", defaults["fit_clinicalbert"]["split-method"])
    )
    network_codes = {
        'Bio_ClinicalBERT': 'CB',
        'microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract': 'PMB',
        'bestepoch-bydrug-CB_0-AR-125-all_222_24_25_1e-06_256_32.pth': 'CB0',
        'bestepoch-bydrug-CB_0-BW-125-all_222_24_25_1e-06_256_32.pth': 'CB1',
        'bestepoch-bydrug-CB_0-ALL-125-all_222_24_25_1e-06_256_32.pth': 'CB2',
        'bestepoch-bydrug-PMB_0-AR-125-all_222_24_25_1e-06_256_32.pth': 'PMB0',
        'bestepoch-bydrug-PMB_0-BW-125-all_222_24_25_1e-06_256_32.pth': 'PMB1',
        'bestepoch-bydrug-PMB_0-ALL-125-all_222_24_25_1e-06_256_32.pth': 'PMB2'
    }

    fcbd_params_outputs = list()

    epochperf_files = list()
    model_files = {'final': list(), 'bestepoch': list()}

    for (method, nwords, section, reffn), max_length, batch_size, epochs, lr, ifexists, network, refsource, split_method in fcbd_iterator:

        if max_length == -1:
            max_length = 2**int(np.ceil(np.log2(2*nwords)))

        if batch_size == -1:
            batch_size = batch_size_estimate(max_length)

        network_path = os.path.join(MODELS_DIR, network)
        finalmodfn = f"{MODELS_DIR}/final-bydrug-{network_codes[network]}_{method}-{section}-{nwords}-{refsource}_222_{split_method}_{epochs}_{lr}_{max_length}_{batch_size}.pth"
        bestepochmodfn = f"{MODELS_DIR}/bestepoch-bydrug-{network_codes[network]}_{method}-{section}-{nwords}-{refsource}_222_{split_method}_{epochs}_{lr}_{max_length}_{batch_size}.pth"
        epochsfn = f"{RESULTS_DIR}/epoch-results-{network_codes[network]}_{method}-{section}-{nwords}-{refsource}_222_{split_method}_{epochs}_{lr}_{max_length}_{batch_size}.csv"

        output_files.append(finalmodfn)
        output_files.append(bestepochmodfn)
        output_files.append(epochsfn)

        epochperf_files.append(epochsfn)

        fcbd_params_outputs.append(('final', network, method, section, nwords, refsource, split_method, epochs, lr, max_length, batch_size, finalmodfn))
        fcbd_params_outputs.append(('bestepoch', network, method, section, nwords, refsource, split_method, epochs, lr, max_length, batch_size, bestepochmodfn))

        # eprint(method, nwords, refsource, section, reffn, max_length, batch_size, epoch, lr, ifexists, network)
        file_exists = os.path.exists(finalmodfn)
        bestepoch_file_exists = os.path.exists(bestepochmodfn)
        epochs_file_exists = os.path.exists(epochsfn)

        model_files['final'].append(finalmodfn)
        model_files['bestepoch'].append(bestepochmodfn)

        if not args.skip_models:
            eprint(f"  {finalmodfn} ...{file_exists}")
            eprint(f"  {bestepochmodfn} ...{bestepoch_file_exists}")
            eprint(f"  {epochsfn} ...{epochs_file_exists}")

        if not args.skip_models and (not file_exists or not bestepoch_file_exists or not epochs_file_exists):
            if not file_exists:
                eprint(f"    NOT FOUND: final model file missing.")
            if not bestepoch_file_exists:
                eprint(f"    NOT FOUND: best epoch model file missing.")
            if not epochs_file_exists:
                eprint(f"    NOT FOUND: epoch results file missing.")

            command = f"python3 src/fit_clinicalbert.py --base-dir {BASE_DIR} --ref {reffn} --refsource {refsource} --split-method {split_method} --max-length {max_length} --batch-size {batch_size} --epochs {epochs} --learning-rate {lr} --ifexists {ifexists} --network {network_path}"
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

    for (modeltype, network, method, section, nwords, refsource, split_method, epochs, lr, max_length, batch_size, modelfn), skip_train, _network in ard_iterator:

        network_path = os.path.join(MODELS_DIR, network)

        testmodresfn = f"{RESULTS_DIR}/{modeltype}-bydrug-{network_codes[network]}-test_{method}-{section}-{nwords}-{refsource}_222_{split_method}_{epochs}_{lr}_{max_length}_{batch_size}.csv"
        validmodresfn = f"{RESULTS_DIR}/{modeltype}-bydrug-{network_codes[network]}-valid_{method}-{section}-{nwords}-{refsource}_222_{split_method}_{epochs}_{lr}_{max_length}_{batch_size}.csv"

        output_files.append(testmodresfn)
        output_files.append(validmodresfn)

        test_file_exists = os.path.exists(testmodresfn)
        valid_file_exists = os.path.exists(validmodresfn)
        eprint(f"  {testmodresfn} ...{test_file_exists}")
        eprint(f"  {validmodresfn} ...{valid_file_exists}")

        if not test_file_exists or not valid_file_exists:
            skip_train_str = '' if not skip_train else '--skip-train '
            command = f"python3 src/analyze_results.py --base-dir {BASE_DIR} --model {modelfn} {skip_train_str}--network {network_path}"
            eprint(f"    NOT FOUND, create with: {command}")
            is_complete = False
            remaining_commands.append(command)

        ard_param_outputs.append((modeltype, network, method, section, nwords, refsource, split_method, epochs, lr, max_length, batch_size, [testmodresfn, validmodresfn]))

    eprint("")
    eprint("Checking for grouped results files...")
    compile_results_data = experiment.get("compile_results", defaults["compile_results"])

    crd_iterator = itertools.product(
        ard_param_outputs,
        compile_results_data.get("group-function", defaults["compile_results"]["group-function"])
    )

    grouped_files = {'final': list(), 'bestepoch': list()}

    for (modeltype, network, method, section, nwords, refsource, split_method, epochs, lr, max_length, batch_size, (testmodresfn, validmodresfn)), grpfun in crd_iterator:

        grpresfn = f"{RESULTS_DIR}/grouped-{grpfun}-{modeltype}-bydrug-{network_codes[network]}_{method}-{section}-{nwords}-{refsource}_222_{split_method}_{epochs}_{lr}_{max_length}_{batch_size}.csv"
        grouped_files[modeltype].append(grpresfn)

        output_files.append(grpresfn)

        file_exists = os.path.exists(grpresfn)
        eprint(f"  {grpresfn} ...{file_exists}")

        if not file_exists:
            command = f"python3 src/compile_results.py --base-dir {BASE_DIR} --group-function {grpfun} --results {testmodresfn} {validmodresfn} --examples {REFS_DIR}/ref{method}_nwords{nwords}_clinical_bert_reference_set_{section}.txt"
            eprint(f"    NOT FOUND, create with: {command}")
            is_complete = False
            remaining_commands.append(command)

    eprint("")

    if clean_experiment:
        eprint(f"CLEANING MODE: To clean out the files from this experiment, pipe the following commands to bash.")
        for fn in output_files:
            if os.path.exists(fn):
                print(f"rm {fn}")

        return

    if not is_complete:
        eprint(f"EXPERIMENT IS INCOMPLETE: One or more files are missing. {len(remaining_commands)} commands need to be run.")
        eprint(f"Checking to see if any commands are currently running...")
        exploded_commands = set([tuple(cmd.split()) for cmd in remaining_commands])
        running_commands = set()
        for p in psutil.pids():
            try:
                proc = psutil.Process(p)
                running_commands.add(tuple(proc.cmdline()))
            except psutil.AccessDenied:
                pass
            except psutil.NoSuchProcess:
                pass

        for cmd in (running_commands & exploded_commands):
            eprint(f"  Found running: {proc} {' '.join(cmd)}")

        eprint("Printing the remaining commands to standard output, pipe this script to bash to automatically run them.")

        nrunning = len(running_commands & exploded_commands)
        runningstr = '' if nrunning == 0 else f', {nrunning:2} currently running.'
        qprint(f" [  Incomplete  ] {len(remaining_commands):2} commands remaining{runningstr}")

        if not QUIET_MODE:
            for command in remaining_commands:
                if tuple(command.split()) in running_commands:
                    continue

                if args.gpu == -1:
                    print(command)
                else:
                    print(f"CUDA_VISIBLE_DEVICES={args.gpu} " + command)
    else:
        if is_deployment:
            eprint("DEPLOYMENT IS READY.")
            qprint(" [     Ready    ]")

            if args.skip_models:
                eprint("Writing release information requires --skip-models to be False.")
            else:
                eprint("Writing out releases file...")
                if os.path.exists('./releases.json'):
                    expfh = open('./releases.json')
                    releases = json.loads(expfh.read())
                    expfh.close()
                else:
                    releases = {"releases": dict()}

                if len(model_files[experiment["model"]]) != 1:
                    raise Exception(f"ERROR: Deployment has more than one model file available for {experiment['model']}. There should be only one.")

                experiment_id = f"{args_id}"
                releases["releases"][experiment_id] = {
                    "name": experiment["name"],
                    "description": experiment["description"],
                    "threshold": experiment["threshold"],
                    "model": experiment["model"],
                    "model_file": model_files[experiment["model"]][0]
                }

                expfh = open('./releases.json', 'w')
                expfh.write(json.dumps(releases, indent=4))
                expfh.close()

                eprint("FINISHED.")
        else:

            eprint("EXPERIMENT IS COMPLETE!")
            qprint(" [   Complete   ]")

            eprint("Writing out analysis file...")
            if os.path.exists('analysis.json'):
                expfh = open('./analysis.json')
                analysis = json.loads(expfh.read())
                expfh.close()
            else:
                analysis = {"experiments": dict()}

            factor_scripts = list()
            factor_params = list()
            #print(experiment)
            # TODO: Labels are not working correctly when there are multiple scripts. Eg. Experiment 10B.
            if type(experiment["factor"]["script"]) is list:
                factor_scripts = experiment["factor"]["script"]
                # if factor_scripts is a list then factor_params must be a
                # list of lists and the number of lists must match the length
                # of the factor_scripts list.
                if not type(experiment["factor"]["parameter"]) is list:
                    raise Exception(f'factor:script is list, factor:parameter must be list as well. Error on experiment: {experiment}')

                if not type(experiment["factor"]["parameter"][0] is list):
                    raise Exception(f'factor:script is list, factor:parameter must be list of lists. Error on experiment: {experiment}')

                factor_params = experiment["factor"]["parameter"]
            else:
                factor_scripts.append(experiment["factor"]["script"])
                if type(experiment["factor"]["parameter"]) is list:
                    if type(experiment["factor"]["parameter"][0]) is list:
                        factor_params = experiment["factor"]["parameter"]
                    elif type(experiment["factor"]["parameter"][0]) is str:
                        factor_params.append(experiment["factor"]["parameter"])
                    else:
                        raise Exception("Unexpected type.")
                elif type(experiment["factor"]["parameter"]) is str:
                    factor_params.append([experiment["factor"]["parameter"]])
                else:
                    raise Exception("Unexpected type.")

            factor_name = ''
            factor_levels = list()

            for factor_script_idx, factor_script in enumerate(factor_scripts):
                if type(experiment["factor"]["parameter"]) is list:
                    factor_name = str(experiment["factor"]["script"])
                    param_levels = list()

                    #print(factor_params)
                    #print(factor_scripts)
                    #print(factor_script_idx)
                    for param in factor_params[factor_script_idx]:
                        factor_name += '.' + param
                        param_levels.append(experiment[factor_script][param])

                    param_levels.reverse()
                    factor_levels.extend( list(itertools.product(*param_levels)) )

                else:
                    factor_name += f'{experiment["factor"]["script"]}.{experiment["factor"]["parameter"]}.'
                    factor_levels.extend( experiment[experiment["factor"]["script"]][experiment["factor"]["parameter"]] )

            if not "labels" in experiment["factor"]:
                factor_labels = [f"{factor_name}:{l}" for l in factor_levels]
            else:
                factor_labels = experiment["factor"]["labels"]

            for modeltype in ('final', 'bestepoch'):
                if not len(factor_labels) == len(grouped_files[modeltype]):
                    raise Exception(f"FAILED: The number of resulting grouped files for ({modeltype}) is not consistent with the experimental setup.")

            experiment_id = f"{args_id}"
            if replicate != 0:
                experiment_id = f"{args_id}R{replicate}"

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

            eprint("FINISHED.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--id', type=str)
    parser.add_argument('--gpu', type=int, help="if you want to prepend the output commands with the specific gpu, specify a gpu number here.", default=-1)
    parser.add_argument('--skip-models', action='store_true', default=False)
    parser.add_argument('--skip-refs', action='store_true', default=False)
    parser.add_argument('--skip-deployments', action='store_true', default=False)
    parser.add_argument('--results-only', action='store_true', default=False)
    parser.add_argument('--replicate', type=int, default=0, help="use to run exact replicates of existing experiments, results and models will be saved in a replicates/rep[NUM] directory")
    parser.add_argument('--quiet', action='store_true', default=False)
    parser.add_argument('--all', action='store_true', default=False)
    parser.add_argument('--clean', action='store_true', default=False)

    args = parser.parse_args()

    if args.id is None and not args.all:
        raise Exception(f"ERROR: No experiment id provided. If you would like to check on all experiments use the --all flag.")

    if args.all and args.clean:
        raise Exception(f"ERROR: Cannot clean all experiments. An experiment must be chosen with the --id argument.")

    QUIET_MODE = args.quiet

    if args.results_only:
        args.skip_models = True
        args.skip_refs = True

    expfh = open('./experiments.json')
    data = json.loads(expfh.read())
    expfh.close()

    #eprint(json.dumps(data["experiments"][args.id], indent=4))
    if args.all:
        experiment_ids = [(exp_id, 0) for exp_id in data["experiments"].keys()]
        for exp_id in data["replicates"].keys():
            for replicate in data["replicates"][exp_id]:
                experiment_ids.append((exp_id, replicate))

        for dep_id in data["deployments"].keys():
            experiment_ids.append((dep_id, 0))

        QUIET_MODE = True
    else:
        experiment_ids = [(args.id, args.replicate),]

    for exp_id, replicate in experiment_ids:
        tracker(exp_id, args, data, replicate, args.clean)

    if args.all:
        qprint("Updated analysis.json for any completed experiments.")
