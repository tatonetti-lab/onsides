# OnSIDES-INTL Database Generation Walkthrough

Here, we generate databases mirroring the OnSIDES database (which extracts ADE data from US FDA SPL drug labels) from UK (EMC), EU (EMA), and Japan (PMDA) drug labels. 

While we follow a similar ADE extraction/prediction philosophy to OnSIDES, as the raw label are formatted in a slightly different manner for each nation/region, the technical workflow is slightly adjusted to each nation. As such, we will describe the process of generating the databases for each individual database. Please skip to the details for the specific database you are interested in. 

If you are interested in how the OnSIDES database extracted from US FDA drug labels is generated, please refer to [OnSIDES](https://github.com/tatonetti-lab/onsides/blob/main/DATABASE.md)

## Step 0 : Preparing External Data Dependencies

To generate any of these databases, we require a number of API / downloaded files for mapping to standard vocabularies. Further details on how to prepare this suitably is provided [here](external_data/EXTERNAL_DATA.md). 

## OnSIDES-INTL Databases

- [OnSIDES-UK](onsides_uk/DATABASE_UK.md)
- [OnSIDES-EU](onsides_eu/DATABASE_EU.md)
- [OnSIDES-JP](onsides_uk/DATABASE_JP.md)

## Notes 

general notes : 
- each `data` subfolder in each of the onsides-intl folders (onsides-eu/jp/uk) houses all of the intermediate data generated during the process of database generation
- each `notebooks` subfolder contains the code required to construct the databases from scratch, mirroring the src code
- each `src` subfolder contains the python code to construct the databases from scratch
- if database generation is run on default settings, the final database output will be produced in a `final` subfolder for each databases' folder

technical notes : 
- all of the code can be run in a standard local environment, with the exception of the OnSIDES prediction model (which we recommend using a GPU for) 
- access to the internet is required to download the raw files and access the APIs for external. as such, this code may need to be configured to be able to run this on the cloud/on a server

in the works... 
- [] add boxed warnings 
- [] add special warnings for specific populations

pre-development, next-steps...
- [] tracking changes to labels
- [] integrate usage of the emc api instead of scraping the website for onsides-uk
- [] integrate usage of the ema api instead of scraping the website for onsides-eu 
- [] run by taking the updated files instead of running from scratch each time
- [] script to enable the training of a custom onsides model on each dataset instead of requiring the built onsides model
- [] allow the tweaking of the onsides model parameters for prediction
- [] streamline / integrate usage of scripts that are doing essentially the same function
- [] see if we can circumvent the dependency on the translation done with OpenAI-GPT3.5
