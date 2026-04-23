"""
train.py

Fine-tune PubMedBERT (ClinicalBertClassifier) to classify adverse drug events.
Supports resuming from a checkpoint for interrupted runs.

Usage:
    onsides-train --ref data/refs/ref14_nwords125_clinical_bert_reference_set_ALL.txt \\
                  --network models/microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract
"""

import argparse
import csv
import logging
import os
import random
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from pydantic import BaseModel
from torch import nn
from torch.optim import Adam
from tqdm import tqdm

from onsides.clinicalbert import ClinicalBertClassifier, Dataset

logger = logging.getLogger(__name__)

LABELS = {"not_event": 0, "is_event": 1}

NETWORK_CODES = {
    "Bio_ClinicalBERT": "CB",
    "BiomedNLP-PubMedBERT": "PMB",
}

NETWORK_PATHS = {
    "CB": Path("models/Bio_ClinicalBERT"),
    "PMB": Path("models/microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract"),
}

DEFAULT_RANDOM_SEED = 222
DEFAULT_EPOCHS = 25
DEFAULT_LEARNING_RATE = 1e-6
EARLY_STOPPING_PATIENCE = 4


class TrainingConfig(BaseModel):
    """Serializable training configuration stored in checkpoints."""

    ref_path: str
    network_path: str
    network_code: str
    refset: int
    refsection: str
    refnwords: int
    refsource: str
    np_random_seed: int
    split_method: str
    epochs: int
    learning_rate: float
    max_length: int
    batch_size: int
    pretrained_state: str | None = None


class EpochMetrics(BaseModel):
    """Metrics for a single training epoch."""

    epoch: int
    train_loss: float
    train_accuracy: float
    valid_loss: float
    valid_accuracy: float
    epoch_time: float
    epoch_saved: bool


def batch_size_estimate(max_length: int) -> int:
    """Estimate batch size from max_length using fitted log-log relationship.

    Based on runs on P100 GPUs with 16GB memory.
    """
    log_bs = -1.2209302325581395 * np.log(max_length) + 10.437506963082898
    bs = np.exp(log_bs)
    power = np.log2(bs)
    return int(2 ** round(power))


def resolve_network(network_arg: str) -> tuple[str, Path, Path | None]:
    """Parse network argument into (code, base_model_path, pretrained_state_path).

    If network_arg is a .pth file, it's treated as a pretrained state to load,
    and the base network is inferred from the filename.
    """
    if network_arg.endswith(".pth"):
        pretrained_state = Path(network_arg)
        network_code = pretrained_state.stem.split("_")[0].split("-")[-1]
        if network_code not in NETWORK_PATHS:
            raise ValueError(
                f"Unknown network code '{network_code}' in pretrained state filename"
            )
        return network_code, NETWORK_PATHS[network_code], pretrained_state

    for key, code in NETWORK_CODES.items():
        if key in network_arg:
            return code, Path(network_arg), None

    raise ValueError(f"Cannot determine network type from: {network_arg}")


def load_reference_data(ref_path: Path, source: str = "all") -> pd.DataFrame:
    """Load reference data CSV, optionally filtering by source method."""
    df = pd.read_csv(ref_path)

    required_cols = {"class", "string", "drug"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(
            f"Reference data is missing required columns: {missing}"
        )

    if "source_method" not in df.columns:
        if source != "exact":
            raise ValueError(
                f"Invalid source '{source}' for old reference file format. "
                "Must be 'exact'."
            )
        return df

    if source == "all":
        return df
    if source in ("exact", "deepcadrme"):
        return df[df["source_method"] == source].copy()
    raise ValueError(f"Unexpected value for --refsource: {source}")


def split_train_val_test(
    df: pd.DataFrame, seed: int, method: str
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split reference data by drug into train/val/test sets."""
    druglist = sorted(set(df["drug"]))
    random.seed(seed)
    random.shuffle(druglist)
    np.random.seed(seed)

    if method == "TAC":
        if "tac" not in df.columns:
            raise ValueError(
                "'tac' column not found in reference data for TAC split."
            )
        train_drugs = sorted(set(df[df["tac"] == "train"]["drug"]))
        drugs_train, drugs_val = np.split(
            train_drugs, [int(0.9 * len(train_drugs))]
        )
        drugs_test = sorted(set(df[df["tac"] == "test"]["drug"]))
    elif int(method) == 24:
        drugs_train, drugs_val, drugs_test = np.split(
            druglist, [int(0.8 * len(druglist)), int(0.9 * len(druglist))]
        )
    else:
        raise ValueError(f"Unknown split method: {method}")

    logger.info(
        f"Split by drug: train={len(drugs_train)}, "
        f"val={len(drugs_val)}, test={len(drugs_test)}"
    )

    return (
        df[df["drug"].isin(drugs_train)].copy(),
        df[df["drug"].isin(drugs_val)].copy(),
        df[df["drug"].isin(drugs_test)].copy(),
    )


def build_filename_params(config: TrainingConfig) -> str:
    """Build the parameter portion of model filename for compatibility."""
    return (
        f"{config.refset}-{config.refsection}-{config.refnwords}-{config.refsource}_"
        f"{config.np_random_seed}_{config.split_method}_{config.epochs}_"
        f"{config.learning_rate}_{config.max_length}_{config.batch_size}"
    )


def _atomic_torch_save(obj: object, path: Path) -> None:
    """Write a torch save file atomically via temp file + rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path_str = tempfile.mkstemp(
        dir=path.parent, suffix=".tmp", prefix=path.stem
    )
    os.close(tmp_fd)
    tmp_path = Path(tmp_path_str)
    try:
        torch.save(obj, tmp_path)
        tmp_path.replace(path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise


def save_checkpoint(
    path: Path,
    model: ClinicalBertClassifier,
    optimizer: Adam,
    epoch: int,
    best_val_loss: float | None,
    epochs_since_best: int,
    metrics_history: list[EpochMetrics],
    config: TrainingConfig,
) -> None:
    """Save a training checkpoint that can be used to resume."""
    checkpoint = {
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "epoch": epoch,
        "best_val_loss": best_val_loss,
        "epochs_since_best": epochs_since_best,
        "metrics_history": [m.model_dump() for m in metrics_history],
        "training_config": config.model_dump(),
    }
    _atomic_torch_save(checkpoint, path)
    logger.info(f"Checkpoint saved to {path}")


def load_checkpoint(path: Path) -> dict:
    """Load a training checkpoint."""
    if not path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {path}")
    checkpoint = torch.load(path, weights_only=False)
    required_keys = {
        "model_state_dict",
        "optimizer_state_dict",
        "epoch",
        "best_val_loss",
        "epochs_since_best",
        "metrics_history",
        "training_config",
    }
    missing = required_keys - set(checkpoint.keys())
    if missing:
        raise ValueError(f"Checkpoint is missing keys: {missing}")
    return checkpoint


def save_epoch_results(path: Path, metrics: list[EpochMetrics]) -> None:
    """Write epoch metrics to CSV in the legacy format."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "epoch",
            "train_loss",
            "train_accuracy",
            "valid_loss",
            "valid_accuracy",
            "epoch_time",
            "epoch_saved",
        ])
        for m in metrics:
            writer.writerow([
                m.epoch,
                m.train_loss,
                m.train_accuracy,
                m.valid_loss,
                m.valid_accuracy,
                m.epoch_time,
                m.epoch_saved,
            ])


def train(
    model: ClinicalBertClassifier,
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    config: TrainingConfig,
    bestepoch_path: Path,
    checkpoint_path: Path,
    resume_from: dict | None = None,
) -> list[EpochMetrics]:
    """Train the model with early stopping and per-epoch checkpointing.

    If resume_from is provided, training continues from the checkpoint state.
    """
    # Prepare datasets
    train_texts = train_df["string"].tolist()
    train_labels = [LABELS[c] for c in train_df["class"]]
    val_texts = val_df["string"].tolist()
    val_labels = [LABELS[c] for c in val_df["class"]]

    tokenizer_path = Path(config.network_path)
    train_dataset = Dataset(
        train_texts, tokenizer_path, config.max_length, train_labels
    )
    val_dataset = Dataset(
        val_texts, tokenizer_path, config.max_length, val_labels
    )

    train_loader = torch.utils.data.DataLoader(
        train_dataset, batch_size=config.batch_size, shuffle=True
    )
    val_loader = torch.utils.data.DataLoader(
        val_dataset, batch_size=config.batch_size
    )

    # Device setup
    use_cuda = torch.cuda.is_available()
    device = torch.device("cuda" if use_cuda else "cpu")
    logger.info(f"Using device: {device}")

    criterion = nn.CrossEntropyLoss()
    optimizer = Adam(model.parameters(), lr=config.learning_rate)

    if use_cuda:
        model = model.cuda()
        criterion = criterion.cuda()

    # Resume state or start fresh
    start_epoch = 0
    best_val_loss: float | None = None
    epochs_since_best = 0
    metrics_history: list[EpochMetrics] = []

    if resume_from is not None:
        optimizer.load_state_dict(resume_from["optimizer_state_dict"])
        start_epoch = resume_from["epoch"] + 1
        best_val_loss = resume_from["best_val_loss"]
        epochs_since_best = resume_from["epochs_since_best"]
        metrics_history = [
            EpochMetrics(**m) for m in resume_from["metrics_history"]
        ]
        logger.info(
            f"Resuming from epoch {start_epoch + 1} "
            f"(best_val_loss={best_val_loss:.6f})"
        )

    # Training loop
    skip_training = config.epochs == 0
    effective_epochs = max(config.epochs, 1)

    for epoch_num in range(start_epoch, effective_epochs):
        epoch_start = time.time()
        total_loss_train = 0.0
        total_acc_train = 0
        epochs_since_best += 1
        saved_model = False

        # Training pass
        model.train()
        for train_input, train_label in tqdm(
            train_loader, desc=f"Epoch {epoch_num + 1}/{effective_epochs}"
        ):
            if skip_training:
                break

            train_label = train_label.to(device)
            mask = train_input["attention_mask"].to(device)
            input_id = train_input["input_ids"].squeeze(1).to(device)

            output = model(input_id, mask)
            batch_loss = criterion(output, train_label)
            total_loss_train += batch_loss.item()
            total_acc_train += (output.argmax(dim=1) == train_label).sum().item()

            model.zero_grad()
            batch_loss.backward()
            optimizer.step()

        # Validation pass
        model.eval()
        total_loss_val = 0.0
        total_acc_val = 0
        with torch.no_grad():
            for val_input, val_label in val_loader:
                val_label = val_label.to(device)
                mask = val_input["attention_mask"].to(device)
                input_id = val_input["input_ids"].squeeze(1).to(device)

                output = model(input_id, mask)
                batch_loss = criterion(output, val_label)
                total_loss_val += batch_loss.item()
                total_acc_val += (output.argmax(dim=1) == val_label).sum().item()

        # Check for best epoch
        val_loss_norm = total_loss_val / len(val_df)
        if best_val_loss is None or val_loss_norm < best_val_loss:
            best_val_loss = val_loss_norm
            _atomic_torch_save(model.state_dict(), bestepoch_path)
            saved_model = True
            epochs_since_best = 0

        epoch_metrics = EpochMetrics(
            epoch=epoch_num + 1,
            train_loss=total_loss_train / len(train_df),
            train_accuracy=total_acc_train / len(train_df),
            valid_loss=val_loss_norm,
            valid_accuracy=total_acc_val / len(val_df),
            epoch_time=time.time() - epoch_start,
            epoch_saved=saved_model,
        )
        metrics_history.append(epoch_metrics)

        logger.info(
            f"Epoch {epoch_num + 1} | "
            f"Train Loss: {epoch_metrics.train_loss:.4f} | "
            f"Train Acc: {epoch_metrics.train_accuracy:.4f} | "
            f"Val Loss: {epoch_metrics.valid_loss:.4f} | "
            f"Val Acc: {epoch_metrics.valid_accuracy:.4f}"
            + (" | Saved best" if saved_model else "")
        )

        # Save checkpoint after every completed epoch
        save_checkpoint(
            checkpoint_path,
            model,
            optimizer,
            epoch_num,
            best_val_loss,
            epochs_since_best,
            metrics_history,
            config,
        )

        # Early stopping
        logger.info(
            f"Epochs since best: {epochs_since_best} "
            f"(stopping at {EARLY_STOPPING_PATIENCE})"
        )
        if epochs_since_best >= EARLY_STOPPING_PATIENCE:
            logger.info(
                f"Early stopping at epoch {epoch_num + 1} "
                f"({EARLY_STOPPING_PATIENCE} epochs without improvement)"
            )
            break

    return metrics_history


def _parse_ref_metadata(ref_path: Path) -> tuple[int, str, int]:
    """Extract refset, refsection, refnwords from reference filename.

    Expected format: ref{method}_nwords{N}_...__{section}.txt
    """
    basename = ref_path.stem
    parts = basename.split("_")

    refset = int(parts[0].removeprefix("ref"))
    refnwords = int(parts[1].removeprefix("nwords"))
    refsection = parts[-1]

    return refset, refsection, refnwords


def main() -> None:
    """CLI entry point for onsides-train."""
    parser = argparse.ArgumentParser(
        description="Fine-tune PubMedBERT for adverse drug event classification."
    )
    parser.add_argument(
        "--ref", type=Path, help="Path to reference CSV"
    )
    parser.add_argument(
        "--network",
        default="models/microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract",
        type=str,
        help="Path to pretrained model or .pth state",
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=-1,
        help="Max token length (default: auto from nwords)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=-1,
        help="Batch size (default: auto-estimated)",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=DEFAULT_EPOCHS,
        help=f"Max training epochs (default: {DEFAULT_EPOCHS})",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=DEFAULT_LEARNING_RATE,
        help=f"Learning rate (default: {DEFAULT_LEARNING_RATE})",
    )
    parser.add_argument(
        "--refsource",
        type=str,
        default="all",
        choices=["all", "exact", "deepcadrme"],
        help="Restrict reference data by source",
    )
    parser.add_argument(
        "--split-method",
        type=str,
        default="24",
        help="Data split method: '24' (80/10/10) or 'TAC'",
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path("."),
        help="Base directory for models/ and results/",
    )
    parser.add_argument(
        "--ifexists",
        type=str,
        default="quit",
        choices=["quit", "replicate", "overwrite"],
        help="What to do if model already exists",
    )
    parser.add_argument(
        "--resume",
        type=Path,
        default=None,
        help="Path to checkpoint file to resume training from",
    )

    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    )

    if args.resume:
        _run_resume(args)
    else:
        if args.ref is None:
            parser.error("--ref is required for a fresh training run")
        _run_fresh(args)


def _run_resume(args: argparse.Namespace) -> None:
    """Resume training from a checkpoint."""
    logger.info(f"Loading checkpoint from {args.resume}")
    checkpoint = load_checkpoint(args.resume)
    config = TrainingConfig(**checkpoint["training_config"])

    logger.info(f"Resuming training with config: {config.model_dump()}")

    # Reload reference data with same parameters
    ref_path = Path(config.ref_path)
    if not ref_path.exists():
        raise FileNotFoundError(
            f"Reference data not found at {ref_path}. "
            "The same reference file used for the original run is required."
        )
    df = load_reference_data(ref_path, config.refsource)
    df_train, df_val, df_test = split_train_val_test(
        df, config.np_random_seed, config.split_method
    )

    # Recreate model and load checkpoint state
    network_path = Path(config.network_path)
    model = ClinicalBertClassifier(network_path)
    model.load_state_dict(checkpoint["model_state_dict"])

    # Set random seed for reproducibility
    torch.manual_seed(config.np_random_seed)

    # Build file paths
    base_dir = args.base_dir
    filename_params = build_filename_params(config)
    bestepoch_path = (
        base_dir / "models" / f"bestepoch-bydrug-{config.network_code}_{filename_params}.pth"
    )
    checkpoint_path = (
        base_dir / "models" / f"checkpoint-bydrug-{config.network_code}_{filename_params}.ckpt.pt"
    )

    # Train
    metrics = train(
        model, df_train, df_val, config,
        bestepoch_path, checkpoint_path,
        resume_from=checkpoint,
    )

    # Save final model and results
    _save_final(model, config, metrics, base_dir, filename_params, df_test, network_path)


def _run_fresh(args: argparse.Namespace) -> None:
    """Start a fresh training run."""
    # Parse reference file metadata
    refset, refsection, refnwords = _parse_ref_metadata(args.ref)
    logger.info(
        f"Reference set: method={refset}, section={refsection}, "
        f"nwords={refnwords}, source={args.refsource}"
    )

    # Resolve network
    network_code, network_path, pretrained_state = resolve_network(args.network)

    # Auto-calculate max_length
    if args.max_length == -1:
        max_length = 2 ** int(np.ceil(np.log2(2 * refnwords)))
        logger.info(
            f"Auto max_length={max_length} from nwords={refnwords}"
        )
    else:
        max_length = args.max_length
        if max_length < 2 * refnwords:
            logger.warning(
                f"max_length ({max_length}) < 2*nwords ({2 * refnwords}): "
                "significant truncation expected"
            )

    # Auto-calculate batch_size
    if args.batch_size == -1:
        batch_size = batch_size_estimate(max_length)
        logger.info(f"Auto batch_size={batch_size} from max_length={max_length}")
    else:
        batch_size = args.batch_size
        est = batch_size_estimate(max_length)
        if batch_size > est:
            logger.warning(
                f"Batch size ({batch_size}) > estimated safe size ({est}): "
                "may run into memory issues"
            )

    # Build config
    config = TrainingConfig(
        ref_path=str(args.ref),
        network_path=str(network_path),
        network_code=network_code,
        refset=refset,
        refsection=refsection,
        refnwords=refnwords,
        refsource=args.refsource,
        np_random_seed=DEFAULT_RANDOM_SEED,
        split_method=args.split_method,
        epochs=args.epochs,
        learning_rate=args.learning_rate,
        max_length=max_length,
        batch_size=batch_size,
        pretrained_state=str(pretrained_state) if pretrained_state else None,
    )

    # Build file paths
    base_dir = args.base_dir
    filename_params = build_filename_params(config)
    final_model_path = (
        base_dir / "models" / f"final-bydrug-{network_code}_{filename_params}.pth"
    )
    bestepoch_path = (
        base_dir / "models" / f"bestepoch-bydrug-{network_code}_{filename_params}.pth"
    )
    checkpoint_path = (
        base_dir / "models" / f"checkpoint-bydrug-{network_code}_{filename_params}.ckpt.pt"
    )

    # Check for existing model
    if final_model_path.exists():
        logger.info(f"Found existing model at {final_model_path}")
        if args.ifexists == "quit":
            logger.info("Quitting. Use --ifexists replicate to run a replicate.")
            sys.exit(1)
        elif args.ifexists == "replicate":
            models_dir = base_dir / "models"
            reps = [
                f
                for f in models_dir.iterdir()
                if filename_params in f.name
                and "bestepoch" not in f.name.lower()
                and "checkpoint" not in f.name.lower()
            ]
            filename_params = f"{filename_params}_rep{len(reps)}"
            final_model_path = (
                models_dir / f"final-bydrug-{network_code}_{filename_params}.pth"
            )
            bestepoch_path = (
                models_dir / f"bestepoch-bydrug-{network_code}_{filename_params}.pth"
            )
            checkpoint_path = (
                models_dir / f"checkpoint-bydrug-{network_code}_{filename_params}.ckpt.pt"
            )
            logger.info(f"Running replicate: {final_model_path.name}")
        elif args.ifexists == "overwrite":
            logger.info("Overwriting existing model.")

    # Load and split data
    df = load_reference_data(args.ref, args.refsource)
    logger.info(f"Loaded {len(df)} examples from {args.ref}")

    df_train, df_val, df_test = split_train_val_test(
        df, DEFAULT_RANDOM_SEED, args.split_method
    )
    logger.info(
        f"Split sizes: train={len(df_train)}, "
        f"val={len(df_val)}, test={len(df_test)}"
    )

    # Initialize model
    model = ClinicalBertClassifier(network_path)

    if pretrained_state is not None:
        logger.info(f"Loading pretrained state from {pretrained_state}")
        model.load_state_dict(torch.load(pretrained_state, weights_only=True))

    # Set random seed
    torch.manual_seed(DEFAULT_RANDOM_SEED)

    # Train
    metrics = train(
        model, df_train, df_val, config,
        bestepoch_path, checkpoint_path,
    )

    # Save final model and results
    _save_final(model, config, metrics, base_dir, filename_params, df_test, network_path)


def _save_final(
    model: ClinicalBertClassifier,
    config: TrainingConfig,
    metrics: list[EpochMetrics],
    base_dir: Path,
    filename_params: str,
    df_test: pd.DataFrame,
    network_path: Path,
) -> None:
    """Save the final model, epoch results, and run test evaluation."""
    # Save final model
    final_model_path = (
        base_dir / "models" / f"final-bydrug-{config.network_code}_{filename_params}.pth"
    )
    torch.save(model.state_dict(), final_model_path)
    logger.info(f"Final model saved to {final_model_path}")

    # Save epoch results CSV
    results_path = (
        base_dir / "results" / f"epoch-results-{config.network_code}_{filename_params}.csv"
    )
    save_epoch_results(results_path, metrics)
    logger.info(f"Epoch results saved to {results_path}")

    # Evaluate on test set using best-epoch model
    bestepoch_path = (
        base_dir / "models" / f"bestepoch-bydrug-{config.network_code}_{filename_params}.pth"
    )
    if bestepoch_path.exists():
        logger.info("Evaluating best-epoch model on test set...")
        loaded_model = ClinicalBertClassifier(network_path)
        state_dict = torch.load(bestepoch_path, weights_only=True)
        loaded_model.load_state_dict(state_dict)

        from onsides.clinicalbert import evaluate

        test_texts = df_test["string"].tolist()
        evaluate(
            loaded_model,
            network_path,
            test_texts,
            max_length=config.max_length,
            batch_size=config.batch_size * 2,
        )

    logger.info("Training complete.")
