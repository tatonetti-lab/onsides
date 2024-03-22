## Raw Drug Label Datasets

To make further language model training / downstream analysis of drug label text more accessible (not limited to ADE analysis), we have formatted all of the text in drug labels publicly available for the UK, EU, and Japan as CSV and per-drug-label XML files. Each nation has a standardized drug label format, which we mirror in the XML files as much as possible, but make some alterations for ease of use in text mining, as described below. The standardized format for each nation / region is described briefly in the [LABELSCHEMA_INTL.md](LABELSCHEMA_INTL.md). 

<!--- check on where they should be kept --->
The files can be downloaded from [here](.tbd). 

---

### XML Files

The XML files are presented per-individual drug, and the structure is kept as consistent as possible. The structure follows

```
<drug_label>
    <drug_info>
        <product_id>...</product_id>
        <drug_name>...</drug_name>
        <ingredients>...</ingredients>
        <last_updated>...</last_updated>
        <company_title>...<company_title>
        <contact_items>...</contact_items>
    </drug_info>
    <drug_label_info>
        <section_id>..text..</section_id>
        ...
    </drug_label_info>
</drug_label>
```
----
### CSV Files

There are two CSV files per nation / region, which contain all of the information for all of the drugs | `drug_info.csv` and `drug_content.csv`. 

#### `drug_info.csv` 

each individual drug label is a row. 

| Column | Description | 
| --| ----------|
| product_id | id of the drug label. |
| drug_name | name of drug product. |
| ingredients | comma-separated list of ingredients in drug. |
| about | regulatory classification of drug. |
| last_updated | date of last update to drug label. |
| company_title | marketing / manufacturer of the drug. |
| contact_items | a dictionary of contact information related to the marketing / manufacturer of the drug. |


#### `drug_content.csv`

each section of a drug label is a row. 

| Column | Description | 
| -- | ----------|
| product_id | id of the drug label.
| section_id | id of the section. (used in XML files)
| section_title | title of the section. 
| section_content | all content in the section. here, it is kept in html format to preserve any formatting. simple code such as ```BeautifulSoup(x).text``` can be used to extract just the text from the section. |

---
### Generating these Files

If one wants to generate/adapt these files for each nation/region, the code to change the obtained raw data to XML/CSV files is located in each subfolder. They are currently provided as notebooks, but they may be adapted into scripts at a later date. 

- [EU : 1-1.data_to_xmlcsv.ipynb](./onsides_eu/notebooks/1-1.data_to_xmlcsv.ipynb)
- [UK : 1-1.data_to_xmlcsv.ipynb](./onsides_uk/notebooks/1-1.data_to_xmlcsv.ipynb)
- [JP : 1-1.data_to_xmlcsv.ipynb](./onsides_jp/notebooks/1-1.data_to_xmlcsv.ipynb)