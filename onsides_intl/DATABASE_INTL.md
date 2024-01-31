# OnSIDES-INTL Database Generation Walkthrough

On this page, we describe how each intl database is generated. 

## Step 0 : Preparing External Data Dependencies

<!--- eventually integrate this into the preparation for the main OnSIDES database--->
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

## Ongoing Development

in the works... 
- :construction: add extraction of boxed warnings 
- :construction: add extraction special warnings for specific populations
- :construction: integrate usage of the emc api instead of scraping the website for onsides-uk

pre-development, next-steps...
- :white_circle: tracking changes to labels
- :white_circle: integrate usage of the ema api instead of scraping the website for onsides-eu 
- :white_circle: run by taking the updated files instead of running from scratch each time
- :white_circle: script to enable the training of a custom onsides model on each dataset instead of requiring the built onsides model
- :white_circle: allow the tweaking of the onsides model parameters for prediction
- :white_circle: streamline / integrate usage of scripts that are doing essentially the same function
- :white_circle: see if we can circumvent the dependency on the translation done with GPT3.5, but may be easiest method. 
