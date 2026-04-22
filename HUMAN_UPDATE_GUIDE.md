# OnSIDES Data Update Guide for Human Operators

This guide explains how to produce a new OnSIDES data release using an AI coding
agent (e.g. Claude Code) as your assistant. The agent handles error diagnosis, code
fixes, and validation; you handle running commands and making judgment calls.

## Prerequisites

Before starting, make sure you have:

- [ ] Access to this repository (`tatonetti-lab/onsides`)
- [ ] A machine with a GPU (for BERT scoring in the evaluate step)
- [ ] `uv` installed (Python package manager)
- [ ] `nix` installed (provides pandoc, duckdb, sqlite3, and other system tools)
- [ ] A UMLS license and the full `MRCONSO.RRF` file (several GB, ~17M rows)
- [ ] OMOP CDM vocabulary files (`CONCEPT.csv`, `CONCEPT_RELATIONSHIP.csv`)
- [ ] The trained BERT model files (PubMedBERT + OnSIDES weights)
- [ ] `screen` or `tmux` for long-running jobs

## How the workflow works

The data update pipeline has 8 steps. Some take seconds, others take days. The agent
knows the pipeline in detail (via `AGENT_UPDATE_GUIDE.md`) and can diagnose and fix
most errors that arise. Your job is to:

1. **Run commands** the agent suggests (it cannot run long jobs itself).
2. **Report back** when commands finish or fail — paste the error output.
3. **Make decisions** the agent can't (e.g. "should we re-download everything?" or
   "is this row count reasonable?").

The agent tracks progress across conversations using its memory system, so you can
close a session and pick up where you left off.

## Getting started

### 1. Start the agent

Open Claude Code in the repo directory:

```bash
cd /path/to/onsides
claude
```

Tell the agent what you're doing:

> "I'm starting a new data release for OnSIDES. Let's work through the update
> pipeline. Please read AGENT_UPDATE_GUIDE.md for instructions."

### 2. Environment setup

The agent will guide you through preparing the environment. The key commands:

```bash
uv sync                     # Install Python dependencies
nix develop                 # Enter the nix shell (provides pandoc, duckdb, etc.)
```

**Important**: All Snakemake commands must be run inside `nix develop`. If you see
"command not found" errors for `pandoc` or `duckdb`, you're outside the nix shell.

### 3. Place external data files

These cannot be downloaded automatically and must be obtained manually:

| File | Place at | Notes |
|------|----------|-------|
| UMLS MRCONSO | `data/MRCONSO.RRF` | Must be the **full** file, not a sample. Requires UMLS license. |
| OMOP CONCEPT | `data/omop_vocab/CONCEPT.csv` | From OMOP CDM vocabulary download |
| OMOP CONCEPT_RELATIONSHIP | `data/omop_vocab/CONCEPT_RELATIONSHIP.csv` | Same source |
| BERT model | `models/microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract/` | Symlinks OK |
| BERT weights | `models/bestepoch-bydrug-PMB_14-ALL-125-all_222_24_25_1e-06_256_32.pth` | Symlinks OK |

Ask the agent to verify the files are in place before proceeding.

### 4. Run the pipeline

Work through each step by telling the agent you're ready, running the command it
provides, and reporting the result. Here's the typical flow:

#### Downloads (Step 4) — hours to days

```bash
# Run each in a screen session. EU and JP need --keep-going and multiple re-runs.
snakemake -s snakemake/us/download/Snakefile --resources jobs=1
snakemake -s snakemake/uk/download/Snakefile --resources jobs=1
snakemake -s snakemake/eu/download/Snakefile --resources jobs=1 --keep-going
snakemake -s snakemake/jp/download/Snakefile --resources jobs=1 --keep-going
```

Re-run EU and JP until Snakemake says there's nothing to do. These servers are flaky.

#### Parse (Step 5) — hours

```bash
snakemake -s snakemake/us/parse/Snakefile
snakemake -s snakemake/uk/parse/Snakefile
snakemake -s snakemake/eu/parse/Snakefile
snakemake -s snakemake/jp/parse/Snakefile --keep-going
```

After all four complete, ask the agent to run the parse checkpoint validation. It
will check that all four regional parquet files have non-zero row counts.

#### Evaluate (Step 6) — days

```bash
snakemake -s snakemake/onsides/evaluate/Snakefile
```

This is the longest step (GPU-bound BERT scoring). Run it in a screen session.

#### Export (Step 7) — minutes

```bash
snakemake -s snakemake/onsides/export/Snakefile
```

#### Build zip (Step 8) — seconds

```bash
build-zip --version vX.Y.Z
```

### 5. Handle errors

When a command fails:

1. **Paste the error output** to the agent. Include the full traceback if visible.
2. **Let the agent investigate.** It will read Snakemake logs, check rule-specific
   log files, and diagnose the issue.
3. **The agent will fix code if needed** and tell you to re-run. Before re-running,
   it may ask you to delete stale intermediate files (like `duck.db`).
4. **If the same error repeats**, paste the new output — the fix may have been
   incomplete or a different issue may have surfaced.

Common error patterns the agent knows how to handle:
- `ENAMETOOLONG` — Japanese filename truncation issues
- `MissingInputException` — files not yet generated or still zipped
- `UNIQUE constraint failed` — duplicate keys in vocabulary tables
- `Invalid unicode` — non-English UMLS rows in MRCONSO.RRF
- `command not found: pandoc/duckdb` — not in the nix shell
- `Matching 0 terms` — stale empty parquet files from a prior failed run

### 6. Create the release

Once the zip is built, tell the agent to:
1. Commit any code changes made during the pipeline run.
2. Push to the remote.
3. Create a GitHub release with the zip attached.

The agent will draft release notes covering data coverage, database statistics, and
any pipeline fixes made during the run.

## Tips

- **Use `screen` or `tmux`** for steps 4-6. These run for hours or days.
- **Don't close the nix shell** between commands — you'll lose pandoc/duckdb from
  PATH.
- **Re-runs are safe.** Snakemake is idempotent. If a step partially completes, just
  re-run it and it will pick up where it left off (unless stale output files confuse
  it — the agent knows when to clean these up).
- **The agent remembers progress** across conversations. If you need to stop and
  resume later, just tell the new agent session to check its memory for update
  progress.
- **Check row counts** at each checkpoint. The agent will tell you what's expected,
  but use your domain knowledge to flag anything surprising.
- **Version numbering**: See `VERSIONING.md`. Code versions follow semver
  (`major.minor.patch`); data releases append a date (`3.1.1-20260422`).
