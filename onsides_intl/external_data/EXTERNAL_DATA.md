# External Data

In order to map the adverse events and drugs listed in the OnSIDES database, we rely on a number of standard vocabularies - RxNorm for drugs, MedDRA for events. While some of these can be accessed via APIs, some are more easily accessible through downloaded files, which will be expected to reside in this folder when OnSIDES-INTL is run to build the databases. 

Here, we will briefly describe the steps needed to access these databases. (While vocabulary access is free, users are expected to register accordingly.)

### List of Standard Vocabularies
- UMLS (for drug+event ids, download)
- OHDSI Athena (for drug+event ids, download)
- RxNorm (for drug ids, accessed via NLM API)

### UMLS

- Download the `MRCONSO.RFF` file from [here](https://www.nlm.nih.gov/research/umls/licensedcontent/umlsknowledgesources.html)
- If you have (or register for) an NIH UMLS API, you can programmatically download the file also. (details to obtain an API key can be obtained [here](https://documentation.uts.nlm.nih.gov/rest/authentication.html))
- The [build_umls_database](build_umls_database.ipynb) notebook can be used to prepare the UMLS datasets for each vocabulary (and other vocabularies of your choice). 

- ###TODO : Make the notebook into a python script - but needs to be highly customised anyway?

### OHDSI Athena

- Accessible [here](https://athena.ohdsi.org/search-terms/start)
- From downloads tab, download a RxNorm / RxNorm Extension / ATC code table (for drugs). 

- ###TODO : Add urther details
