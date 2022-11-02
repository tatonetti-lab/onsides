# OnSIDES Database Generation Walkthrough

Generating the database is done in five steps:

1. download and pre-process the structured product labels (`spl_processor.py`)
2. identify adverse reaction terms and construct feature sentence fragments (`construct_application_data.py`)
3. apply the model to score feature sentence fragments (`predict.py`)
4. compile the results into csv datafiles for each label section (`create_onsides_datafiles.py`)
5. integrate the results with standard vocabularies and build the csv files (`build_onsides.py`)

## Generate semi-automatically using Deployment Tracker

The steps above are detailed below. However, note that as with the experiments,
this process is assisted by the Deployment Tracker (`demployment_tracker.py`). The
Deployment Tracker will walk through the process checking for the necessary files. If
any are missing it will print the command used to generate them to the standard output.
Some steps (SPL Processing) need to be performed before running the tracker. In this case
the tracker confirms a recent run and prompts the user to re-run if potentially out of date.

To run the Deployment Tracker:

```
python3 src/deployment_tracker.py --release V02-AR
```

For convenience the remaining commands can be piped to bash as follows:

```
python3 src/deployment_tracker.py --release V02-AR | bash
```

If on a GPU-enabled machine, the `--gpu` flag can be used to specify which
gpu to use for the steps that require it.

```
python3 src/deployment_tracker.py --release V02-AR --gpu 2
```

## Generate by running each step manually

### Step 1. Download and Pre-process the SPLs

The structured product labels (SPLs) are made available for download by DailyMed and updated
on a monthly, weekly, and daily basis at https://dailymed.nlm.nih.gov/dailymed/spl-resources-all-drug-labels.cfm.

We implemented a script to manage the download and pre-processing of these files assuming a
one-time bulk download of a full release of prescription labels, followed by periodic updates
(assumed to be monthly). The prescriptin drug label files and the parsed text files are stored
in the data subdirectory at `./data/spl/rx/`.

To initiate a full release download, run `spl_processor.py` as follows:

```
python3 src/spl_processor.py --full
```

The latest full release of the prescription drug labels will be downloaded, checksum verified,
and then pre-processed into json files.

To make a periodic update, run `spl_processor.py` as follows:

```
python3 src/spl_processor.py --update
```

The processor will check the dates of the downloaded full release as well as any updates
and look for additional available updates. If any are available, it will download the files,
checksum verify them, and then pre-process them into json files.

### Step 2. Identify ADR terms and feature construction

To identify the ADR terms and construct the feature sentences, use the `construct_application_data.py`
script. The feature method (`--method`), number of words (`--nwords`), label section (`--section`),
label medicine type (`--medtype`), and the directory of the parsed label json files (`--dir`) are
all required parameters. For example:

```
python3 src/construct_application_data.py --method 14 --nwords 125 --section AR --medtype rx --dir data/spl/rx/dm_spl_release_human_rx_part5
```

This will need to be run for each subdirectory of labels and for each section (Adverse Reactions,
Boxed Warnings, etc.). This script will create a sentences file at the directory path provided.
For example, the above command creates a file named:

```
data/spl/rx/dm_spl_release_human_rx_part5/sentences-rx_method14_nwords125_clinical_bert_application_set_AR.txt.gz
```

### Step 3. Apply the model to score ADR sentences

The trained model can be then applied to each of the feature files created in step 2 using
the `predict.py` script. The required parameters are the trained model path (`--model`) and
the path to the feature file generated in Step 2 (`--examples`). For example:

```
python3 src/predict.py --model ./models/final-bydrug-PMB_14-AR-125-all_222_24_25_1e-05_256_32.pth --examples data/spl/rx/dm_spl_release_human_rx_part5/sentences-rx_method14_nwords125_clinical_bert_application_set_AR.txt.gz
```

The resulting gzipped csv file of model outputs will be saved in the same directory
as the examples. For example, the above creates a file named:

```
data/spl/rx/dm_spl_release_human_rx_part5/final-bydrug-PMB-sentences-rx_ref14-AR-125-all_222_24_25_1e-05_256_32.csv.gz
```

#### Really Large Files

This step can run into memory and compute time errors with very large sentence files. Most
of the parts of the full release download tend to cause issues. To avoid these errors and
speed up the process overall the sentence files can be split, processed individually, and
then recombined.

The following bash code snippet shows how this can be done using the full release part5
as of Oct 2022. The part5 file will split the file into 100 MB chunks, each with their
own header.

```
cd data/spl/rx/dm_spl_release_human_rx_part5/
mkdir -p splits
gunzip sentences-rx_method14_nwords125_clinical_bert_application_set_AR.txt.gz
tail -n +2 sentences-rx_method14_nwords125_clinical_bert_application_set_AR.txt | split -d -C 100m - --filter='sh -c "{ head -n1 sentences-rx_method14_nwords125_clinical_bert_application_set_AR.txt; cat; } > $FILE"' splits/sentences-rx_method14_nwords125_clinical_bert_application_set_AR_split
gzip sentences-rx_method14_nwords125_clinical_bert_application_set_AR.txt
cd -
```

Then run `predict.py` on each split:

```
for f in data/spl/rx/dm_spl_release_human_rx_part5/splits/*
do
  echo python3 src/predict.py --model ./models/final-bydrug-PMB_14-AR-125-all_222_24_25_1e-05_256_32.pth --examples $f
done | bash
```

Finally, recombine the results and archive them:

```
cd data/spl/rx/dm_spl_release_human_rx_part5/
zcat splits/*.csv.gz | gzip > final-bydrug-PMB-sentences-rx_app14-AR-125-all_ref14-AR_222_24_25_1e-05_256_32.csv.gz
rm -rf splits
cd -
```

This process will have to be done for each part of a full release and for each
update available. Reminder note that the Deployment Tracker (`deployment_tracker.py`)
script will automate this process for you (See above for how to run).

### Step 4. Compile results into CSV files

The previous step produced scores for each ADR mention in each label. However, a single ADR
is often mentioned multiple times per label. We collapse these different instances down into
a single score using an aggregation function (e.g. mean) and produce files that we can
then load into an SQL database. We do this using `create_onsides_datafiles.py`. There are
three required parameters to this script: the path to the results file (`--results`), the
path to the sentences file (`--examples`), and which deployment release was used to generate
the scores (`--release`). The releases available can be found in the `experiments.json` file
under `deployments`.

To compile the results for `AR-V02`, for example:

```
python3 src/create_onsides_datafiles.py --release V02-AR --results data/spl/rx/dm_spl_release_human_rx_part5/final-bydrug-PMB-sentences-rx_ref14-AR-125-all_222_24_25_1e-05_256_32.csv.gz --examples data/spl/rx/dm_spl_release_human_rx_part5/sentences-rx_method14_nwords125_clinical_bert_application_set_AR.txt.gz
```

Which will create a "compiled" file in the labels directory:

```
data/spl/rx/dm_spl_release_human_rx_part5/compiled/V02/AR.csv.gz
```

### Step 5. Collate and integrate with standard vocabularies and build database files

To build the final version of the OnSIDES database files we leverage the standard
vocabularies in the OMOP Common Data Model (CDM). These can be downloaded using the
ATHENA tool made available from OHDSI.org. See https://www.ohdsi.org/data-standardization/
for more information. In this implementation we use OMOP CDM v5.4. Download the vocabularies
through ATHENA (including MedDRA, which will require a EULA) and save them into a
subdirectory of `./data`.

The files are built by running the `build_onsides.py` script with the path to the download
vocabularies (`--vocab`) and the version number (`--version`). All sections which have a trained
model specified in the `experiments.json` file for the provided version will be collated.

```
python3 src/build_onsides.py --vocab ./data/omop/vocab_5.4 --version V02
```

The `build_onsides.py` script will iterate through each of the SPL subdirectories looking
for available compiled results files (results of Step 4). If any subdirectories are missing
the compiled results, the script throw an error and halt execution.

Once completed, the results will be saved to the `releases` subdirectory by the version
number and the date in `YYYYMMDD` format.

```
./releases/V02/20221029/
```
