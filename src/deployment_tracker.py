"""
deployment_tracker.py
Tool to automate the management of updating the OnSIDES database.

USAGE:
python3 src/deployment_tracker.py --release v2.0.0-AR

"""

import os
import sys
import csv
import json
import gzip
import tqdm
import argparse

from datetime import datetime

QUIET_MODE = False

def eprint(*args, **kwargs):
    if not QUIET_MODE:
        print(*args, file=sys.stderr, **kwargs)

def qprint(*args, **kwargs):
    if QUIET_MODE:
        print(*args, file=sys.stderr, **kwargs)

def load_json(filename):
    fh = open(filename)
    data = json.loads(fh.read())
    fh.close()
    return data

def save_json(filename, data):
    fh = open(filename, 'w')
    fh.write(json.dumps(data, indent=4))
    fh.close()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--release', help='ID for the release to deploy.', type=str, required=True)
    parser.add_argument('--gpu', help="GPU ID to use if on a CUDA-enabled machine.", type=str, required=False)
    parser.add_argument('--skip-spl-check', help="Skip the check for if the SPLs have been updated today.", action='store_true', required=False, default=False)
    args = parser.parse_args()

    use_gpu = False
    if args.gpu is not None:
        use_gpu = True

    #####
    # Step 0. Check that release is ready and available.
    #####

    eprint("Validating release settings and parameters are present... ", end='')

    releases = load_json('./releases.json')

    if not args.release in releases["releases"]:
        raise Exception(f"ERROR: Selected release ({args.release}) is not available in releases.json, use \n\npython3 src/experiment_tracker.py --id {args.release}\n\nto check it's status.")

    release_info = releases["releases"][args.release]
    if not os.path.exists(release_info['model_file']):
        raise Exception(f"PREREQUISITE ERROR: Model file is not present where expected. Rerun the experiment tracker\n\npython3 src/experiment_tracker.py --id {args.release}\n\nto check it's status and try again once complete.")

    experiments = load_json('./experiments.json')

    if not args.release in experiments["deployments"]:
        raise Exception(f"ERROR: Selected releases is not available in experiments.json, this is necessary to pull some parameter settings.")

    # Load some necessary parameter settings from the experiments file
    release_info["method"] = experiments['deployments'][args.release]['construct_training_data']['method'][0]
    release_info["nwords"] = experiments['deployments'][args.release]['construct_training_data']['nwords'][0]
    release_info["section"] = experiments['deployments'][args.release]['construct_training_data']['section'][0]

    model_data = os.path.splitext(os.path.basename(release_info['model_file']))[0].split('_')
    prefix = model_data[0]
    feature_params = model_data[1]
    training_params = '_'.join(model_data[2:])

    version, section = args.release.split('-')

    #print([prefix, feature_params, training_params])
    eprint("ok.")

    eprint(f"{json.dumps(release_info, indent=4)}")


    #####
    # Step 1. Check that spl_processor has been run today.
    #####
    eprint("Checking that the SPL Processor has been run today...", end='')

    if not os.path.exists('./spl.json'):
        raise Exception("PREREQUISITE ERROR: the spl labels must be downloaded and processed using the spl_process.py script before the deployment tracker is run. Initiate a full download of labels with \n\npython3 src/spl_processor.py --full\n\nOnce complete, rerun the deployment tracker.")

    spl_status = load_json('./spl.json')

    if not args.skip_spl_check and not spl_status['last_updated'] == datetime.now().strftime("%Y%d%m"):
        raise Exception("PREREQUISITE ERROR: The SPLs must be checked for updates immediately before the deployment tracker. Run with\n\npython3 src/spl_processor.py --update\n\nOnce complete re-run the deployment tracker.")

    eprint("ok.")

    #####
    # Step 2. Feature construction
    #####

    remaining_commands = list()
    spl_dir = os.path.join('data', 'spl', 'rx')

    labels_dirs = [os.path.join(spl_dir, labels_dir) for labels_dir in os.listdir(spl_dir) if os.path.isdir(os.path.join(spl_dir, labels_dir))]

    # TODO: Implement a tracking strategy so that we can tell when
    # TODO: files may be incomplete and require rerunning. For example,
    # TODO: if a process is terminated partway through, we would want to
    # TODO: be able to identify that and prompt for rerunning.
    # eprint("Checking for existing deployment process status files.")
    #
    # deploy_status = dict()
    # for labels_dir in labels_dirs:
    #     deploy_path = os.path.join(labels_dir, 'deployment_status.json')
    #     if not os.path.exists(deploy_path):
    #         deploy_status[labels_dir] = {
    #             'feature_construction_status', 'in_progress',
    #             'apply_model_status': 'in_progress',
    #             'compile_status': 'in_progress'
    #         }
    #         save_json(deploy_path, deploy_status[labels_dir])
    #     else:
    #         deploy_status[labels_dir] = load_json(deploy_path)

    eprint("Checking for sentence example files.")

    apply_params = list()

    for labels_dir in labels_dirs:

        sentences_fn = f"sentences-rx_method{release_info['method']}_nwords{release_info['nwords']}_clinical_bert_application_set_{release_info['section']}.txt.gz"
        apply_params.append((labels_dir, sentences_fn))

        eprint(f"  Checking for {os.path.join(labels_dir, sentences_fn)} ...", end='')
        if os.path.exists(os.path.join(labels_dir, sentences_fn)):
            eprint(f"ok.")
        else:
            eprint(f"missing. Generate with:")
            cmd = f"python3 src/construct_application_data.py --method {release_info['method']} --nwords {release_info['nwords']} --section {release_info['section']} --medtype rx --dir {labels_dir}"
            eprint(f"\n\t{cmd}\n")
            remaining_commands.append(cmd)

    ####
    # Step 3. Apply the model
    ####

    eprint("Checking for model output files.")

    compile_params = list()
    for labels_dir, sentences_fn in apply_params:

        output_fn = f"{prefix}-sentences-rx_ref{feature_params}_{training_params}.csv.gz"
        compile_params.append((labels_dir, sentences_fn, output_fn))

        eprint(f"  Checking for {os.path.join(labels_dir, output_fn)} ...", end="")
        if os.path.exists(os.path.join(labels_dir, output_fn)):
            eprint(f"ok.")
        else:
            eprint(f"missing. Generate with:")

            #eprint(os.path.getsize(f"{labels_dir}.zip"))
            # use the zip file we downloaded as a proxy for number of RX labels to process
            if os.path.getsize(f"{labels_dir}.zip") > (500*1024*1024):
                gpu = args.gpu if use_gpu else 0
                cmd = f"bash src/split_and_predict.sh {labels_dir} {release_info['method']} {release_info['nwords']} {release_info['section']} {gpu} {release_info['model_file']} {output_fn}"
            else:
                gpu_str = f"CUDA_VISIBLE_DEVICES={args.gpu} " if use_gpu else ""
                cmd = f"{gpu_str}python3 src/predict.py --model {release_info['model_file']} --examples {os.path.join(labels_dir, sentences_fn)}"

            eprint(f"\n\t{cmd}\n")
            remaining_commands.append(cmd)

    ####
    # Step 4. Compile results into a CSV
    ####

    for labels_dir, sentences_fn, output_fn in compile_params:

        compiled_fn = os.path.join("compiled", version, f"{section}.csv.gz")

        eprint(f"  Checking for {os.path.join(labels_dir, compiled_fn)} ...", end="")
        if os.path.exists(os.path.join(labels_dir, compiled_fn)):
            eprint(f"ok.")
        else:
            eprint(f"missing. Generate with:")
            cmd = f"python3 src/create_onsides_datafiles.py --release {args.release} --results {os.path.join(labels_dir, output_fn)} --examples {os.path.join(labels_dir, sentences_fn)}"
            eprint(f"\n\t{cmd}\n")
            remaining_commands.append(cmd)

    ####
    # Output necessary commands to finish to the standard out
    ####

    if len(remaining_commands) == 0:
        eprint("====================")
        eprint(f"Deployment {args.release} is complete. After all sections have been deployed, the final step is create the database files with:\n\n")
        eprint(f"python3 src/build_onsides.py --vocab ./data/omop/vocab_5.4 --release {version}")
        eprint(f"\nAssuming you have downloaded and extracted the OMOP vocabularies at ./data/omop/vocab_5.4. See DATABASE.md for details.")
    else:
        eprint("====================")
        eprint(f"Deployment is incomplete. There are {len(remaining_commands)} commands to run. These will be printed to standard out to facilitate piping to bash.\n\n")
        for cmd in remaining_commands:
            print(cmd)

if __name__ == '__main__':
    main()
