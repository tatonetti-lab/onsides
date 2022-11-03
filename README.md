# OnSIDES

A resource of adverse drug effects extracted from FDA structured product labels.

## V02

*V02 update is currently in progress, this page will be frequently updated -NPT 2022-11-02*

Second release of the OnSIDES database of adverse reactions and boxed warnings extracted from the FDA structured product labels (SPLs). This version contains significant model improvements as well as updated labels. All labels available to download from DailyMed (https://dailymed.nlm.nih.gov/dailymed/spl-resources-all-drug-labels.cfm) as of November 2, 2022 were processed in this analysis. In total XXX million adverse reactions were extracted from XX,000 labels for just under X,000 drug ingredients or combination of ingredients.

OnSIDES was created using the [PubMedBERT language model](https://huggingface.co/microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract) and 200 manually curated labels available from [Denmer-Fushman et al.](https://pubmed.ncbi.nlm.nih.gov/29381145/). The model achieves an F1 score of 0.90, AUROC of 0.92, and AUPR of 0.94 at extracting effects from the ADVERSE REACTIONS section of the label. This constitutes an absolute increase of 4% in each of the performance metrics over V01. For the BOXED WARNINGS section, the model achieves a F1 score of 0.76, AUROC of 0.83, and AUPR of 0.77. This constitutes an absolute increase of 10-17% in the performance metrics over V01. Compared against the TAC reference standard using the official evaluation script the model achieves a F1 score of 0.85.

| Metric      | TAC (Best Model) | SIDER | OnSIDES V01 | OnSIDES V02 |
| ----------- | ---------------- | ----- | ----------- | ----------- |
| F1 Score    | 82.19            | 74.36 | 82.01       | 87.67       |
| Precision   | 80.69            | 43.49 | 88.76       | 93.65       |
| Recall      | 85.05            | 52.89 | 77.12       | 82.40       |

*Performance metrics in table are evaluated on the TAC gold standard test set.*

### Download

The data are available as a set of SQL tables or as flat files in CSV format.

#### CSV Files
[onsides_v02_20221102.tar.gz]

#### SQL File
[onsides_v02_20221102.sql.gz]

### Description of Tables

Below is a brief description of the tables. See [`SCHEMA.md`](SCHEMA.md) for column descriptions and [`src/load_onsides_db.sql`](src/load_onsides_db.sql) for more details.

`adverse_reactions` - Main table of adverse reactions. This table includes adverse reactions extracted from the ADVERSE REACTIONS section of the current active label for each product. XX,XXX rows.

`adverse_reactions_all_labels` - All extracted adverse reactions from the ADVERSE REACTIONS section of all labels. Each drug will have multiple labels over its lifetime (revisions, generic alternatives, etc.). This table contains the results of extracting adverse reactions from every label available for download from DailyMed. X,XXX,XXX rows.

`boxed_warnings` - Main table of boxed warnings. This table includes adverse reactions extracted from the BOXED WARNINGS section of the current active label for each drug product. X,XXX rows.

`boxed_warnings_all_labels` - All extracted adverse reactions from the BOXED WARNINGS section of all labels (including revisions, generics, etc). XX,XXX rows.

`ingredients` - Active ingredients for each of the parsed labels. If the label is for a drug with a single active compound then there will be only a single row for that label.  If the label is for a combination of compounds then there will be multiple rows for that label. XX,XXX rows.

`dm_spl_zip_files_meta_data` - Meta data provided by DailyMed that indicates which SPL version is the current for each Set ID.

`pharmacologic_class_mappings` -

`rxcui_setid_map` - Map between Set IDs and RxNorm product identifiers. XX,XXX rows.

`rxnorm_mappings` -

`rxnorm_to_setid` - Map between the RxNorm product to the active ingredients in that product. XXX,XXX rows.

### Replication, Retraining, and Improving the Model

*Prerequisites*

In addition to the cloned repository, a `data` subdirectory is required that contains three pieces of data.

1. A file that maps MedDRA preferred terms to lower level terms.
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

Generating the database is done in five steps: i) download and pre-process the structured product labels (`spl_processor.py`), ii) identify adverse reaction terms and construct feature sentence fragments (`construct_application_data.py`), iii) apply the model to score feature sentence fragments (`predict.py`), iv) compile the results into csv datafiles for each label section (`create_onsides_datafiles.py`), and v) integrate the results with standard vocabularies and build the csv files (`build_onsides.py`). All five steps are automated and managed through the Deployment Tracker (`deployment_tracker.py`).

See [DATABASE.md](DATABASE.md) for a step-by-step walkthrough.

### Caveats

The Onsides database is intended for research purposes only. The extraction process is far from perfect, side effects will be missed and some identified will be incorrect. Patients seeking health information should not trust these data and instead refer to the FDA's website (fda.gov) and consult their doctor.

The project is under active development. Validation of extracted information is yet to be independently verified and the data, methods, and statistics are subject to change at any time. Check back to this page for updates. If you would like to to contribute to the project or have ideas on how the methods, data, or evaluation can be improved please reach out to Dr. Tatonetti via [email](https://tatonettilab.org/people/) or [Twitter](http://twitter.com/nicktatonetti).

### Citation

A manuscript describing the data, methods, and results is in preparation. In the mean time, please reference the github repository. [![DOI](https://zenodo.org/badge/479583027.svg)](https://zenodo.org/badge/latestdoi/479583027)
