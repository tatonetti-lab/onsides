"""Tests for onsides.train module."""

import csv
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import torch
from torch.optim import Adam

from onsides.train import (
    EpochMetrics,
    TrainingConfig,
    batch_size_estimate,
    build_filename_params,
    load_checkpoint,
    load_reference_data,
    resolve_network,
    save_checkpoint,
    save_epoch_results,
    split_train_val_test,
)


class TestBatchSizeEstimate:
    def test_known_values(self):
        # max_length=256 should give batch_size=32 (used in production)
        assert batch_size_estimate(256) == 32

    def test_larger_max_length_gives_smaller_batch(self):
        assert batch_size_estimate(512) < batch_size_estimate(256)

    def test_result_is_power_of_two(self):
        for ml in [64, 128, 256, 512, 1024]:
            bs = batch_size_estimate(ml)
            assert bs > 0
            assert (bs & (bs - 1)) == 0, f"{bs} is not a power of two"


class TestResolveNetwork:
    def test_pubmedbert_path(self):
        code, path, state = resolve_network(
            "models/microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract"
        )
        assert code == "PMB"
        assert "PubMedBERT" in str(path)
        assert state is None

    def test_clinicalbert_path(self):
        code, path, state = resolve_network("models/Bio_ClinicalBERT")
        assert code == "CB"
        assert "ClinicalBERT" in str(path)
        assert state is None

    def test_pretrained_state_pth(self):
        code, path, state = resolve_network(
            "models/bestepoch-bydrug-PMB_14-ALL-125-all_222_24_25_1e-06_256_32.pth"
        )
        assert code == "PMB"
        assert state is not None
        assert state.suffix == ".pth"

    def test_unknown_network_raises(self):
        with pytest.raises(ValueError, match="Cannot determine"):
            resolve_network("models/some_unknown_model")

    def test_unknown_code_in_pth_raises(self):
        with pytest.raises(ValueError, match="Unknown network code"):
            resolve_network("bestepoch-bydrug-XYZ_params.pth")


class TestBuildFilenameParams:
    def test_format(self):
        config = TrainingConfig(
            ref_path="data/ref.txt",
            network_path="models/PMB",
            network_code="PMB",
            refset=14,
            refsection="ALL",
            refnwords=125,
            refsource="all",
            np_random_seed=222,
            split_method="24",
            epochs=25,
            learning_rate=1e-06,
            max_length=256,
            batch_size=32,
        )
        result = build_filename_params(config)
        assert result == "14-ALL-125-all_222_24_25_1e-06_256_32"

    def test_different_params(self):
        config = TrainingConfig(
            ref_path="data/ref.txt",
            network_path="models/CB",
            network_code="CB",
            refset=0,
            refsection="AR",
            refnwords=60,
            refsource="exact",
            np_random_seed=222,
            split_method="TAC",
            epochs=10,
            learning_rate=2.5e-05,
            max_length=128,
            batch_size=64,
        )
        result = build_filename_params(config)
        assert "0-AR-60-exact" in result
        assert "TAC" in result


class TestTrainingConfigRoundtrip:
    def test_serialize_deserialize(self):
        config = TrainingConfig(
            ref_path="data/ref.txt",
            network_path="models/PMB",
            network_code="PMB",
            refset=14,
            refsection="ALL",
            refnwords=125,
            refsource="all",
            np_random_seed=222,
            split_method="24",
            epochs=25,
            learning_rate=1e-06,
            max_length=256,
            batch_size=32,
        )
        data = config.model_dump()
        restored = TrainingConfig(**data)
        assert config == restored

    def test_with_pretrained_state(self):
        config = TrainingConfig(
            ref_path="data/ref.txt",
            network_path="models/PMB",
            network_code="PMB",
            refset=14,
            refsection="BW",
            refnwords=125,
            refsource="all",
            np_random_seed=222,
            split_method="TAC",
            epochs=25,
            learning_rate=2.5e-05,
            max_length=256,
            batch_size=32,
            pretrained_state="models/bestepoch-bydrug-PMB_14-ALL-125-all_222_24_25_1e-06_256_32.pth",
        )
        data = config.model_dump()
        restored = TrainingConfig(**data)
        assert restored.pretrained_state == config.pretrained_state


class TestLoadReferenceData:
    def _make_ref_csv(self, tmp_path: Path, with_source_method: bool = True):
        rows = []
        for drug in ["DRUG_A", "DRUG_B", "DRUG_C"]:
            for cls in ["is_event", "not_event"]:
                row = {
                    "section": "AR",
                    "drug": drug,
                    "tac": "train",
                    "meddra_id": 10000001,
                    "pt_meddra_id": 10000001,
                    "class": cls,
                    "pt_meddra_term": "headache",
                    "found_term": "headache",
                    "string": f"context for {drug} {cls}",
                }
                if with_source_method:
                    row["source_method"] = "exact" if cls == "is_event" else "deepcadrme"
                rows.append(row)

        df = pd.DataFrame(rows)
        path = tmp_path / "ref.csv"
        df.to_csv(path, index=False)
        return path

    def test_load_all(self, tmp_path):
        path = self._make_ref_csv(tmp_path)
        df = load_reference_data(path, "all")
        assert len(df) == 6

    def test_filter_exact(self, tmp_path):
        path = self._make_ref_csv(tmp_path)
        df = load_reference_data(path, "exact")
        assert all(df["source_method"] == "exact")

    def test_filter_deepcadrme(self, tmp_path):
        path = self._make_ref_csv(tmp_path)
        df = load_reference_data(path, "deepcadrme")
        assert all(df["source_method"] == "deepcadrme")

    def test_missing_columns_raises(self, tmp_path):
        path = tmp_path / "bad.csv"
        pd.DataFrame({"x": [1]}).to_csv(path, index=False)
        with pytest.raises(ValueError, match="missing required columns"):
            load_reference_data(path)

    def test_old_format_exact_ok(self, tmp_path):
        path = self._make_ref_csv(tmp_path, with_source_method=False)
        df = load_reference_data(path, "exact")
        assert len(df) == 6

    def test_old_format_non_exact_raises(self, tmp_path):
        path = self._make_ref_csv(tmp_path, with_source_method=False)
        with pytest.raises(ValueError, match="Invalid source"):
            load_reference_data(path, "all")


class TestSplitTrainValTest:
    def _make_df(self, n_drugs=20):
        rows = []
        for i in range(n_drugs):
            drug = f"DRUG_{i:03d}"
            for cls in ["is_event", "not_event"]:
                rows.append({
                    "drug": drug,
                    "class": cls,
                    "string": f"context {drug} {cls}",
                })
        return pd.DataFrame(rows)

    def test_split_24_sizes(self):
        df = self._make_df(20)
        train, val, test = split_train_val_test(df, 222, "24")
        # 20 drugs: 16 train, 2 val, 2 test
        assert len(set(train["drug"])) == 16
        assert len(set(val["drug"])) == 2
        assert len(set(test["drug"])) == 2

    def test_split_deterministic(self):
        df = self._make_df(20)
        train1, val1, test1 = split_train_val_test(df, 222, "24")
        train2, val2, test2 = split_train_val_test(df, 222, "24")
        assert list(train1["drug"]) == list(train2["drug"])
        assert list(val1["drug"]) == list(val2["drug"])
        assert list(test1["drug"]) == list(test2["drug"])

    def test_different_seed_different_split(self):
        df = self._make_df(20)
        train1, _, _ = split_train_val_test(df, 222, "24")
        train2, _, _ = split_train_val_test(df, 999, "24")
        assert list(train1["drug"]) != list(train2["drug"])

    def test_no_drug_overlap(self):
        df = self._make_df(20)
        train, val, test = split_train_val_test(df, 222, "24")
        train_drugs = set(train["drug"])
        val_drugs = set(val["drug"])
        test_drugs = set(test["drug"])
        assert train_drugs.isdisjoint(val_drugs)
        assert train_drugs.isdisjoint(test_drugs)
        assert val_drugs.isdisjoint(test_drugs)

    def test_tac_split(self):
        rows = []
        for i in range(20):
            drug = f"DRUG_{i:03d}"
            tac = "train" if i < 10 else "test"
            rows.append({
                "drug": drug,
                "tac": tac,
                "class": "is_event",
                "string": f"context {drug}",
            })
        df = pd.DataFrame(rows)
        train, val, test = split_train_val_test(df, 222, "TAC")
        # 10 train drugs split 90/10 -> 9 train, 1 val; 10 test
        assert len(set(train["drug"])) == 9
        assert len(set(val["drug"])) == 1
        assert len(set(test["drug"])) == 10

    def test_tac_missing_column_raises(self):
        df = self._make_df(10)
        with pytest.raises(ValueError, match="tac"):
            split_train_val_test(df, 222, "TAC")


class TestCheckpointRoundtrip:
    def _make_config(self):
        return TrainingConfig(
            ref_path="data/ref.txt",
            network_path="models/PMB",
            network_code="PMB",
            refset=14,
            refsection="ALL",
            refnwords=125,
            refsource="all",
            np_random_seed=222,
            split_method="24",
            epochs=25,
            learning_rate=1e-06,
            max_length=256,
            batch_size=32,
        )

    def test_roundtrip(self, tmp_path):
        # Create a minimal model (just the linear layer, skip BERT for speed)
        model = torch.nn.Module()
        model.linear = torch.nn.Linear(10, 2)
        # We can't use ClinicalBertClassifier without downloading BERT weights,
        # but we can test the checkpoint mechanism with any nn.Module
        optimizer = Adam(model.parameters(), lr=1e-6)

        config = self._make_config()
        metrics = [
            EpochMetrics(
                epoch=1,
                train_loss=0.5,
                train_accuracy=0.7,
                valid_loss=0.4,
                valid_accuracy=0.75,
                epoch_time=120.0,
                epoch_saved=True,
            )
        ]

        path = tmp_path / "test.ckpt.pt"

        # Use the raw save logic since save_checkpoint expects ClinicalBertClassifier
        checkpoint = {
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "epoch": 0,
            "best_val_loss": 0.4,
            "epochs_since_best": 0,
            "metrics_history": [m.model_dump() for m in metrics],
            "training_config": config.model_dump(),
        }
        torch.save(checkpoint, path)

        loaded = load_checkpoint(path)
        assert loaded["epoch"] == 0
        assert loaded["best_val_loss"] == 0.4
        assert loaded["epochs_since_best"] == 0

        restored_config = TrainingConfig(**loaded["training_config"])
        assert restored_config == config

        restored_metrics = [EpochMetrics(**m) for m in loaded["metrics_history"]]
        assert len(restored_metrics) == 1
        assert restored_metrics[0].train_loss == 0.5

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_checkpoint(tmp_path / "nonexistent.ckpt.pt")

    def test_missing_keys_raises(self, tmp_path):
        path = tmp_path / "bad.ckpt.pt"
        torch.save({"model_state_dict": {}}, path)
        with pytest.raises(ValueError, match="missing keys"):
            load_checkpoint(path)


class TestSaveEpochResults:
    def test_csv_format(self, tmp_path):
        metrics = [
            EpochMetrics(
                epoch=1,
                train_loss=0.5,
                train_accuracy=0.7,
                valid_loss=0.4,
                valid_accuracy=0.75,
                epoch_time=120.0,
                epoch_saved=True,
            ),
            EpochMetrics(
                epoch=2,
                train_loss=0.3,
                train_accuracy=0.8,
                valid_loss=0.35,
                valid_accuracy=0.82,
                epoch_time=115.0,
                epoch_saved=True,
            ),
        ]

        path = tmp_path / "results" / "epoch-results.csv"
        save_epoch_results(path, metrics)

        with open(path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 2
        assert set(rows[0].keys()) == {
            "epoch", "train_loss", "train_accuracy",
            "valid_loss", "valid_accuracy", "epoch_time", "epoch_saved",
        }
        assert rows[0]["epoch"] == "1"
        assert rows[1]["epoch"] == "2"

    def test_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "deep" / "nested" / "results.csv"
        save_epoch_results(path, [])
        assert path.exists()
