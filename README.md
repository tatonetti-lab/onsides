# OnSIDES
A resource of adverse drug effects extracted from FDA structured product labels.

## V01

Initial release of the Onsides database of adverse reactions and boxed warnings extracted from the FDA structured product labels. All labels available to download from DailyMed (https://dailymed.nlm.nih.gov/dailymed/spl-resources-all-drug-labels.cfm) as of April 2022 were processed in this analysis. In total 2.7 million adverse reactions were extracted from 42,000 labels for just under 2,000 drug ingredients or combination of ingredients.

Onsides was created using the ClinicalBERT language model and 200 manually curated labels available from [Denmer-Fushman et al.](https://pubmed.ncbi.nlm.nih.gov/29381145/). The model achieves an F1 score of 0.86, AUROC of 0.88, and AUPR of 0.91 at extracting effects from the ADVERSE REACTIONS section of the label and an F1 score of 0.66, AUROC of 0.71, and AUPR of 0.60 at extracting effects from the BOXED WARNINGS section.

### Download

The data are available as a set of SQL tables or as flat files in CSV format.

#### SQL File
[onsides_v01_20220430.sql.gz](https://github.com/tatonetti-lab/onsides/releases/download/v01/onsides_v01_20220430.sql.gz) (81MB, md5:b386e9485e943120c9a783edf843d68e)

#### CSV Files
[onsides_v01_20220430.tar.gz](https://github.com/tatonetti-lab/onsides/releases/download/v01/onsides_v01_20220430.tar.gz) (81MB, md5:f73ded83cf5edc63447f6ca8b80add66)


### Description of Tables

Below is a brief description of the tables. See [`SCHEMA.md`](SCHEMA.md) for column descriptions and [`src/load_onsides_db.sql`](src/load_onsides_db.sql) for more details.

`adverse_reactions` - Main table of adverse reactions. This table includes adverse reactions extracted from the ADVERSE REACTIONS section of the most recent label for each ingredient or combination of ingredients. 94,029 rows.

`adverse_reactions_bylabel` - All extracted adverse reactions from the ADVERSE REACTIONS section of all labels. Each drug will have multiple labels over its lifetime (revisions, generic alternatives, etc.). This table contains the results of extracting adverse reactions from every label available for download from DailyMed. 2,764,338 rows.

`boxed_warnings` - Main table of boxed warnings. This table includes adverse reactions extracted from the BOXED WARNINGS section of the most recent label for each ingredient or combination of ingredients. 2,907 rows.

`boxed_warnings_bylabel` - All extracted adverse reactions from the BOXED WARNINGS section of all labels (including revisions, generics, etc). 67,984 rows.

`ingredients` - Active ingredients for each of the parsed labels. If the label is for a drug with a single active compound then there will be only a single row for that label.  If the label is for a combination of compounds then there will be multiple rows for that label. 52,646 rows.

`label_map` - Map between the xml_id (xml filename), zip_id (zip filename), and set_id (drug identifier). 45,989 rows.

`latest_labels_bydrug` - Most recent label (as determined from the zip filename for each drug or combination of drugs. 2,051 rows.

`rxnorm_map` - Map between set_id and rx_cui (product level) and also includes the structured product label version and a string description of the product. 443,620 rows.

`rxnorm_product_to_ingredient` - Map between the RxNorm product to the active ingredients in that product. 254,036 rows.

`rxnorm_to_setid` - Map between set_id and rx_cui. 141,915 rows.

### Replication, Retraining, and Improving the Model

*Prerequisites*

In addition to the cloned repository, a `data` subdirectory is required that contains three pieces of data.

1. A file that maps meddra preferred terms to lower level terms.
2. You will also need the manual annotations from Denmer-Fushman, et al paper and TAC.
3. The TAC labels in XML format with the Adverse Reactions, Boxed Warnings, and Warnings and Precautions sections parsed.

For your convenience, there is an example data directory download available with the minimum requirements available for [download](https://github.com/tatonetti-lab/onsides/releases/download/v01/data.zip).

Model training and evaluation is handled through the use of a helper script named `experiment_tracker.py`. There are several steps in the model training and evaluation pipeline and each has their own set of parameter options. The Experiment Tracker makes it straightforward to manage this process.

#### Model Training

Model Training consists of four steps: i) constructing the training data (`construct_training_data.py`), ii) fitting the BERT model (`fit_clinicalbert.py`), iii) generating probabilities for the example sentence fragments (`analyze_results.py`), and iv) aggregating the probabilities across sentence fragments at the adverse event term level (`compile_results.py`). The Experiment Tracker (`experiment_tracker.py`) will keep track of this entire process. It will track where each experiment is in this process and what commands need to be run to complete the experiment. Experiments are managed by editing the experiments entries in the `experiments.json` file. In each experiments entry, the parameters that are to be explored can be specified. Any parameters not specified are assumed to be the default values.

To track the status of the experiment run the script with the experiment identifier. For example:
```
python3 src/experiment_tracker.py --id 0
```

If any steps in the process of the experiment are incomplete, the script will print out a list of bash commands to the standard output that can be used to complete the experiment. For example you could run those commands with the following:

```
python3 src/experiment_tracker.py --id 0 | bash
```

If running on a GPU enabled machine, it may be beneficial to specify which GPU to use. The experiment tracker can automatically take care of this for you through the use of the CUDA_VISIBLE_DEVICES environment variable. This is set with the `--gpu` flag. For example:

```
python3 src/experiment_tracker.py --id 0 --gpu 1
```

You can monitor the status of all experiments that using the `--all` flag.

```
python3 src/experiment_tracker.py --all
```

#### Deployment Models

The `experiments.json` file can also be used to manage deployments. A deployment entry works the same as an experiment, except that only one set of parameters is used.

#### Evaluation

Each experiment has a corresponding Jupyter notebook for evaluation (See notebooks subdirectory). The files and parameters necessary to run the notebook are saved in the `analysis.json` file. The `analysis.json` file is automatically generated by the experiment tracker once an experiment is complete and should not be edited directly. Each of these notebooks is essentially identical with the only difference being which experiment is being evaluated. Therefore, to add a notebook for a new experiment copy an existing notebook, rename it, and edit the experiment ID in the third code block. The notebook will print ROC and PR curves as well as a table of summary performance statistics.

### Generating the OnSIDES Database

Generating the database is done in five steps: i) download and pre-process the structured product labels (`spl_processor.py`), ii) identify adverse reaction terms and construct feature sentence fragments (`construct_application_data.py`), iii) apply the model to score feature sentence fragments (`predict.py`), iv) compile the results into csv datafiles for each label section (`create_onsides_datafiles.py`), and v) create the SQL schema, load the raw data, and generate derivative tables (`load_onsides_db.py`).

See [DATABASE.md](DATABASE.md) for a step-by-step walkthrough.

### Caveats

The Onsides database is intended for research purposes only. The extraction process is far from perfect, side effects will be missed and some identified will be incorrect. Patients seeking health information should not trust these data and instead refer to the FDA's website (fda.gov) and consult their doctor.

The project is under active development. Validation of extracted information is yet to be independently verified and the data, methods, and statistics are subject to change at any time. Check back to this page for updates. If you would like to to contribute to the project or have ideas on how the methods, data, or evaluation can be improved please reach out to Dr. Tatonetti via [email]
(https://tatonettilab.org/people/) or [Twitter](http://twitter.com/nicktatonetti).

### Citation

A manuscript describing the data, methods, and results is in preparation. In the mean time, please reference the github repository. [![DOI](https://zenodo.org/badge/479583027.svg)](https://zenodo.org/badge/latestdoi/479583027)
