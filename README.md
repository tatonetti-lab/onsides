# OnSIDES

### About OnSIDES

OnSIDES is a database of adverse drug events extracted from drug labels created by fine-tuning a [PubMedBERT language model](https://huggingface.co/microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract) on 200 manually curated labels available from [Denmer-Fushman et al.](https://pubmed.ncbi.nlm.nih.gov/29381145/). This comprehensive database will be updated quarterly, and currently contains more than 3.6 million drug-ADE pairs for 2,793 drug ingredients extracted from 46,686 labels, processed from all of the labels available to download from [DailyMed](https://dailymed.nlm.nih.gov/dailymed/spl-resources-all-drug-labels.cfm) as of November 2023. Additionally, we now provide a number of complementary databases constructed using a similar method - OnSIDES-INTL, adverse drug events extracted from drug labels of other nations/regions (Japan, UK, EU), and OnSIDES-PED, adverse drug events specifically noted for pediatric patients in drug labels. We have recently released a preprint on [medRxiv](https://www.medrxiv.org/content/10.1101/2024.03.22.24304724v1) with a full description of the data, methods and analyses. 

### Model Accuracy
Our fine-tuned language model achieves an F1 score of 0.90, AUROC of 0.92, and AUPR of 0.95 at extracting effects from the ADVERSE REACTIONS section of the FDA drug label. For the BOXED WARNINGS sections, the model achieves a F1 score of 0.71, AUROC of 0.85, and AUPR of 0.72. Compared against the reference standard using the official evaluation script for [TAC 2017](https://bionlp.nlm.nih.gov/tac2017adversereactions/), the model achieves a Micro-F1 score of 0.87 and a Macro-F1 of 0.85.

**Performance metrics evaluated against the TAC gold standard**

| Metric      | TAC (Best Model<sup>†</sup>) | SIDER 4.1 | OnSIDES v1.0.0 | OnSIDES v2/3.0.0 |
| ----------- | ---------------------------- | --------- | -------------- | -------------- |
| F1 Score    | 82.19                        | 74.36     | 82.01          | **87.54**      |
| Precision   | 80.69                        | 43.49     | 88.76          | **91.29**      |
| Recall      | **85.05**                    | 52.89     | 77.12          | 84.08          |

Further detailed model performance metrics can be found [here](./PERFORMANCE.md). 

Additionally, to evaluate the performance of the model when generating the additional OnSIDES-INTL and OnSIDES-PED datasets, we manually annotated the ADE mentions in 200 randomly sampled drug labels for each nation/category. This annotation data can be used to further train, fine-tune and improve language models related to large language models. It is described in further detail [here](./onsides_annot/ANNOTATION.md).

## Release Version 3.0.0 (coming soon)

The forthcoming third major release for OnSIDES contains a number of new datasets complementing the primary OnSIDES database. Additionally, OnSIDES has also been updated to reflect the latest updates to all drug labels.  

**[OnSIDES-INTL](./onsides_intl/ONSIDES_INTL.md)** (International):\
OnSIDES is now multi-national/multi-lingual! We have adapted the method to construct ADE databases extracted from UK, EU, and Japanese drug labels. Additionally, we provide the formatted text data from ~25,000 drug labels as CSV and XML files (described [here](./onsides_intl/ONSIDES_INTL.md))!

**[OnSIDES-PED]('./onsides_ped/ONSIDES_PED.md')** (Pediatrics):\
OnSIDES now includes patient population-specific ADEs! For the initial data release for this database, we have focused on pediatric-specific ADEs. We applied the OnSIDES method to the SPECIAL POPULATION section described in the drug labels, and we have extracted ADEs specifically noted for pediatric patients into a supplementary database. The tables for OnSIDES-PED are enclosed in the main OnSIDES database.

**[OnSIDES-ANNOT](./onsides_annot/ANNOTATION.md)** (Annotations):\
To better train and evaluate the model on the OnSIDES-INTL/PED datasets we've generated, we've manually annotated 200 sampled drug labels each for each subsection.

Additionally, we have added a number of **[projects](./projects/README.md)** to showcase potential use-cases of OnSIDES - predicting novel drug targets and indications from inter-drug adverse drug event profile similarities, analyzing enrichment of ADEs across drug classes, and predicting adverse events directly from chemical compound structures. 

<!--- UPDATE LINK ---->
More information about this release can be found [here](https://github.com/tatonetti-lab/onsides/releases/tag/v2.0.0-20231113).

## Download OnSIDES (latest release v2.1.0)

The latest database versions are available as a flat files in CSV format. Previous database versions can be
accessed under [Releases](https://github.com/tatonetti-lab/onsides/releases). A [DDL](src/sql/mysql/create_tables.sql) (`create_tables.sql`) is available to load the CSV files into a SQL schema.

<!--- UPDATE LINK ---->
### September 2024 Data Release 

The latest release of the database is [onsides_v2.1.0_20240925.tar.gz](https://github.com/tatonetti-lab/onsides/releases/tag/v2.1.0-20240925). (123MB)
<!--- add md5 --->

*Previous data releases can be found under the releases link to the right. Updated versions of the database will be completed quarterly, and will be described on this page.*

### Table Descriptions

Below is a brief description of the tables in the database. More details can be found in the [`SCHEMA`](SCHEMA.md) for column descriptions.

| Table  | Description | Rows | 
| --- | ----------- | --- | 
| `adverse_reactions` | Main table of adverse reactions. This table includes adverse reactions extracted from the ADVERSE REACTIONS section of the current active labels for each product and then grouped by ingredient(s) | 129,624 |
| `adverse_reactions_active_labels` | All extracted adverse reactions from the ADVERSE REACTIONS section of active versions of the label. | 3,061,873 | 
| `adverse_reactions_all_labels` | All extracted adverse reactions from the ADVERSE REACTIONS section of every available version of the label. As the database is updated in the future, ingredient will have multiple labels over its lifetime (revisions, generic alternatives, etc.). This table contains the results of extracting adverse reactions from every label available for download from DailyMed. | 3,610,120 |
| `boxed_warnings` | Main table of boxed warnings. This table includes adverse reactions extracted from the BOXED WARNINGS section of the current active label for each drug product and then grouped by ingredient(s). | 6,087 | 
| `boxed_warnings_active_labels` | All extracted adverse reactions from the BOXED WARNINGS section of all labels (including revisions, generics, etc) | 93,691 | 
| `boxed_warnings_all_labels` | All extracted adverse reactions from the BOXED WARNINGS section of all labels (including revisions, generics, etc) | 114,322 |
| `ingredients` | Active ingredients for each of the parsed labels. If the label is for a drug with a single active compound then there will be only a single row for that label.  If the label is for a combination of compounds then there will be multiple rows for that label. | 129,316 | 
| `dm_spl_zip_files_meta_data` | Meta data provided by DailyMed that indicates which SPL version is the current for each drug product (`set_id`). | 147,025 | 
| `rxnorm_mappings` | Mapping drug product `set_id`s to their RxNorm CUIs. | 456,932 | 
| `rxcui_setid_map` | Map from SetID to RxNorm product ids. | 147,087 | 
| `rxnorm_product_to_ingredient` | Map from RxNorm product ids to RxNorm ingredient ids. | 247,040 | 

## Generating the OnSIDES Database

### Training the Model

Training the model is done in five steps : 

0. Prepare a `data` subdirectory of files that contain three pieces of data. 
    - A file that maps MedDRA preferred terms to lower level terms.
    - The manual annotations from Denmer-Fushman, et al paper and TAC.
    - The TAC SPL labels in XML format with the Adverse Reactions, Boxed Warnings, and Warnings and Precautions sections parsed.

    For your convenience, there is an example data directory download available with the minimum requirements available for [download](https://github.com/tatonetti-lab/onsides/releases/download/v2.0.0/data.zip).
<!--- reformat the international data to call on files in this folder instead of its own data subdirectory--->
<!--- update the example data directory --->

1. constructing the training data (`construct_training_data.py`)
2. fitting the BERT model (`fit_clinicalbert.py`)
3. generating probabilities for the example sentence fragments (`analyze_results.py`)Shou
4. aggregating the probabilities across sentence fragments at the adverse event term level (`compile_results.py`)

The model we have trained can be downloaded from [here](https://github.com/tatonetti-lab/onsides/releases/tag/v2.0.0). It can be used in the downstream database compilation workflow described below. For further details on how the model is trained, see [MODEL TRAINING](./MODEL_TRAINING.md). 

### Compiling the Database

Once the model has been trained, generating the database is done in five steps: 
1. download and pre-process the structured product labels (`spl_processor.py`)
2. identify adverse reaction terms and construct feature sentence fragments (`construct_application_data.py`)
3. apply the model to score feature sentence fragments (`predict.py`)
4. compile the results into csv datafiles for each label section (`create_onsides_datafiles.py`)
5. integrate the results with standard vocabularies and build the csv files (`build_onsides.py`). 
All five steps are automated and managed through the Deployment Tracker (`deployment_tracker.py`).

See [DATABASE](DATABASE.md) for a step-by-step walkthrough.

## Limitations

OnSIDES is **strictly** intended for academic research purposes. The adverse drug event term extraction method is far from perfect - some side effects will be missed and some predicted as true adverse events will be incorrect. 

**Patients/healthcare professionals seeking health information should not trust or use this data, and instead refer to the information available from their regions' respective drug regulatory agencies, such as the [FDA](https://www.fda.gov/) (USA), [EMA](https://www.ema.europa.eu/en) (EU), [MHRA](https://www.gov.uk/government/organisations/medicines-and-healthcare-products-regulatory-agency) (UK), [PMDA](https://www.pmda.go.jp/english/) (Japan) and consult their healthcare providers for information.**

Additionally, this project is under active development. We are continuing to further conduct independent validation of the performance of the models used, and improve the extraction methodology. As such, the data, methods, and statistics are subject to change at any time. Any updates to the database will be reflected on this page/in this repository. 

If you would like to contribute to this project or have any suggestions on how the methods, data, or evaluation can be improved please reach out to Dr. Tatonetti via [email](https://tatonettilab.org/people/) or [Twitter](http://twitter.com/nicktatonetti).

## Citation

If you use the OnSIDES database, results, or methods in your work, please reference our preprint : 
> Tanaka, Y., Chen, H.Y., Belloni, P., Gisladottir, U., Kefeli, J., Patterson, J., Srinivasan, A., Zietz, M., Sirdeshmukh, G., Berkowitz, J., Larow Brown, K., Tatonetti, N. (2024). OnSIDES (ON-label SIDE effectS resource) Database : Extracting Adverse Drug Events from Drug Labels using Natural Language Processing Models.medRxiv. 10.1101/2024.03.22.24304724.
