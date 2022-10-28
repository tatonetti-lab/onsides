# OnSIDES Database Generation Walkthrough

Generating the database is done in five steps:

1. download and pre-process the structured product labels (`spl_processor.py`)
2. identify adverse reaction terms and construct feature sentence fragments (`construct_application_data.py`)
3. apply the model to score feature sentence fragments (`predict.py`)
4. compile the results into csv datafiles for each label section (`create_onsides_datafiles.py`)
5. create the SQL schema, load the raw data, and generate derivative tables (`load_onsides_db.py`)

## Generate semi-automatically using Experiment Tracker

The steps above are detailed below. However, note that as with the experiments,
this process is assisted by the Experiment Tracker (`experiment_tracker.py`).

```
python3 src/experiment_tracker.py --deploy V02-AR
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
python3 src/construct_application_data.py --method 14 --nwords 60 --section AR --medtype rx --dir data/spl/rx/dm_spl_release_human_rx_part5
```

This will need to be run for each subdirectory of labels and for each section (Adverse Reactions,
Boxed Warnings, etc.). This script will create a sentences file at the directory path provided.
For example, the above command creates a file named:

```
data/spl/rx/dm_spl_release_human_rx_part5/sentences-rx_method14_nwords60_clinical_bert_application_set_AR.txt.gz
```

### Step 3. Apply the model to score ADR sentences

The trained model can be then applied to each of the feature files created in step 2 using
the `predict.py` script. The required parameters are the trained model path (`--model`) and
the path to the feature file generated in Step 2 (`--examples`). For example:

```
python3 src/predict.py --model models/bestepoch-bydrug-PMB_14-AR-60-all_222_24_25_1e-06_128_128.pth --examples data/spl/rx/dm_spl_release_human_rx_part5/sentences-rx_method14_nwords60_clinical_bert_application_set_AR.txt.gz
```

The resulting gzipped csv file of model outputs will be saved in the same directory
as the examples. For example, the above creates a file named:

```
data/spl/rx/dm_spl_release_human_rx_part5/bestepoch-bydrug-PMB-sentences-rx_app14-AR_ref14-AR_222_24_25_1e-06_128_128.csv.gz
```

####*Really Large Files*

This step can run into memory and compute time errors with very large sentence files. Most
of the parts of the full release download tend to cause issues. To avoid these errors and
speed up the process overall the sentence files can be split, processed individually, and
then recombined.

The following bash code snippet will split the file into 100 MB chunks, each with their
own header.

```
cd data/spl/rx/dm_spl_release_human_rx_part5/
mkdir -p splits
gunzip sentences-rx_method14_nwords60_clinical_bert_application_set_AR.txt.gz
tail -n +2 sentences-rx_method14_nwords60_clinical_bert_application_set_AR.txt | split -d -C 100m - --filter='sh -c "{ head -n1 sentences-rx_method14_nwords60_clinical_bert_application_set_AR.txt; cat; } > $FILE"' splits/sentences-rx_method14_nwords60_clinical_bert_application_set_AR_split
gzip sentences-rx_method14_nwords60_clinical_bert_application_set_AR.txt
cd -
```

Then run `predict.py` on each split:

```
for f in data/spl/rx/dm_spl_release_human_rx_part5/splits/*
do
  echo python3 src/predict.py --model models/bestepoch-bydrug-PMB_14-AR-60-all_222_24_25_1e-06_128_128.pth --examples $f
done | bash
```

Finally, recombine the results and archive them:

```
cd data/spl/rx/dm_spl_release_human_rx_part5/
zcat splits/*.csv.gz | gzip > bestepoch-bydrug-PMB-sentences-rx_app14-AR-60-all_ref14-AR_222_24_25_1e-06_128_128.csv.gz
rm -rf splits
cd -
```

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
python3 src/create_onsides_datafiles.py --release V02-AR --results data/spl/rx/dm_spl_release_human_rx_part5/bestepoch-bydrug-PMB-sentences-rx_app14-AR_ref14-AR-60-all_222_24_25_1e-06_128_128.csv.gz --examples data/spl/rx/dm_spl_release_human_rx_part5/sentences-rx_method14_nwords60_clinical_bert_application_set_AR.txt.gz
```

Which will create a "compiled" file in the labels directory:

```
data/spl/rx/dm_spl_release_human_rx_part5/compiled_bestepoch-bydrug-PMB-sentences-rx_app14-AR_ref14-AR-60-all_222_24_25_1e-06_128_128.csv.gz
```

### Step 5.
