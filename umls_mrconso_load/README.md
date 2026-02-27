# purpose
the purpose of this doc/folder is to serve as notes for loading a table from the UMLS MRCONSO file into a database.

# grants
```sql
GRANT USAGE ON SCHEMA umls TO rw_grp;

GRANT SELECT, INSERT, UPDATE, DELETE
ON TABLE umls.mrconso
TO rw_grp;
```

# qa
(base) |11:30:47|pentaho-secondary@triads-DL:[mrconso]> wc -l MRCONSO.RRF 
17390109 MRCONSO.RRF

cem_development_2026=# `select count(*) from umls.mrconso ;`
  count   
----------
 17390109

* also see readme at 