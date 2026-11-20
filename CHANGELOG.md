# Changelog

## [Unreleased]

### Added

- Fine-tuned model published to HuggingFace as `tatonettilab/onsides-bert` (`scripts/upload_to_huggingface.py`)
- Separate license for the OnSIDES data (`LICENSE-DATA`)
- `CLAUDE.md` guidance for AI coding agents

## [3.2.1] - 2026-04-28

Code-only release; no data changes from 3.1.1.

### Fixed

- Foreign key violation in `vocab_rxnorm_ingredient_to_product` caused by a column order mismatch in the Postgres/MySQL schema (#82)

## [3.2.0] - 2026-04-28

Code-only release; no data changes from 3.1.1.

### Added

- Unified PubMedBERT model for all sections (AR, BW, WP) with per-section thresholds, replacing three separate models (TAC F1 89.87, up from 87.54; recall 94.68, up from 84.08)
- Web-based annotation tool (`onsides-annotate`) for building independent reference sets (#31)
- Independent hold-out evaluation set of 30 manually annotated FDA labels
- Training module with checkpoint/resume support (`onsides-train`) (#30)
- Training data construction and Snakemake experiment workflow driven by `experiments.json`, with a model registry (#81)
- Annotation curation-flag experiments (`onsides-compute-flags`); filtering did not improve performance (#26)
- Rebuilt Denmer-Fushman annotations with all sections and a characterization script (#27)

## [3.1.1] - 2026-04-22

Data release with April 2026 labels from all four sources (see the v3.1.1 GitHub release for counts).

### Added

- Versioning policy (`VERSIONING.md`)
- AI-assisted update guides (`HUMAN_UPDATE_GUIDE.md`, `AGENT_UPDATE_GUIDE.md`) and computational requirements in `UPDATE_INSTRUCTIONS.md`
- Per-rule log directives in key pipeline steps
- Scripts to reset US and JP downloads

### Changed

- BERT model paths are configurable instead of hardcoded

### Fixed

- BERT confidence threshold (`pred1 > 3.258`) was not applied before export, so the 3.1.0 CSV shipped ~20.5M low-confidence rows
- JP filename-too-long (`ENAMETOOLONG`) errors and crashes on labels without a side-effects section
- Non-UTF-8 bytes and filename case for UMLS `MRCONSO.RRF`
- `UNIQUE` constraint violation in the MedDRA vocabulary table
- Foreign key violations in vocabulary tables
- EU download rate limiting and a curl issue in downloads

## [3.1.0] - 2025-05-08

### Added

- Correct RxNorm paths between products and ingredients (per RxNav)
- Command line interface for generating the ZIP archive

### Fixed

- Erroneous product-to-ingredient mapping that led to products having thousands of ingredients
