# Versioning

OnSIDES uses two versioning layers: one for the **code** (the pipeline that generates the data) and one for the **data releases** (the database files published to users).

## Code Versioning

Code versions follow `major.minor.patch` format, inspired by [Semantic Versioning](https://semver.org) but adapted for a data pipeline where the "API" is the database schema and output data.

- **Major** — Changes in *what* we extract or *how* we extract it. For example, adding new label sections, changing ADE extraction methodology, or reorganizing how products are represented. These will almost always change the database schema.
- **Minor** — Improvements to extraction *quality* that may change the database structure or output, but don't represent a fundamental shift in methodology. For example, upgrading the scoring model, fixing bugs that affect output data, or adding new vocabulary mappings.
- **Patch** — Code-only fixes that do not affect the output data or database schema. For example, fixing a download retry bug, improving logging, or updating documentation.

## Data Release Versioning

Data releases are published periodically (target: quarterly) using the code version plus a date suffix:

```
<code_version>-<YYYYMMDD>
```

For example, `3.1.0-20260325` is a data release generated on March 25, 2026 using code version 3.1.0.

The same code version can produce multiple data releases as source label databases (DailyMed, EMA, EMC, KEGG) are updated over time. The date identifies which snapshot of source data was used.

## Examples

| Version | What changed |
|---------|-------------|
| 2.0.0 → 3.0.0 | Added international labels (EU, UK, JP); restructured database to support multiple sources |
| 3.0.0 → 3.1.0 | Fixed product-to-ingredient mapping; added correct RxNorm paths |
| 3.1.0-20250508 → 3.1.0-20260325 | Same pipeline, updated with latest labels from all sources |
