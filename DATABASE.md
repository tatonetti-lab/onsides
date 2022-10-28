# OnSIDES Database Generation Walkthrough

Generating the database is done in five steps:

1. download and pre-process the structured product labels (`spl_processor.py`)
2. identify adverse reaction terms and construct feature sentence fragments (`construct_application_data.py`)
3. apply the model to score feature sentence fragments (`predict.py`)
4. compile the results into csv datafiles for each label section (`create_onsides_datafiles.py`)
5. create the SQL schema, load the raw data, and generate derivative tables (`load_onsides_db.sql`)

## Step 1. Download and Pre-process the SPLs

The structured product labels (SPLs) are made available for download by DailyMed and updated
on a monthly, weekly, and daily basis at https://dailymed.nlm.nih.gov/dailymed/spl-resources-all-drug-labels.cfm.

We implemented a script to manage the download and pre-processing of these files assuming a
one-time bulk download of a full release of prescription labels, followed by periodic updates
(assumed to be monthly). The label files and the parsed text files are stored in the data
subdirectory at `./data/spl/rx/downloads/`.

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

## Step 2. Identify ADR terms and feature construction