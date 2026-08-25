#!/usr/bin/env python3
"""Train or score Campaign302's one frozen Alpha360 temporal Transformer."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import tempfile
from pathlib import Path

import numpy as np
import torch
from torch import nn


FEATURE_COUNT = 360
CHANNEL_COUNT = 6
SEQUENCE_LENGTH = 60
EMBEDDING_DIMENSION = 8
ATTENTION_HEADS = 2
ENCODER_LAYERS = 1
FEEDFORWARD_DIMENSION = 16
DROPOUT = 0.0
BATCH_SIZE = 512
PREDICTION_BATCH_SIZE = 4096
EPOCHS = 5
LEARNING_RATE = 0.001
WEIGHT_DECAY = 0.0001
GRADIENT_CLIP_L2_NORM = 5.0
RANDOM_STATE = 302
NUM_THREADS = 4


class Campaign302WorkerError(RuntimeError):
    """Reject a changed cross-runtime model or array contract."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_numpy(path: Path, values: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            np.save(handle, values, allow_pickle=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def fixed_environment() -> None:
    if torch.__version__ != "2.10.0":
        raise Campaign302WorkerError("torch version changed")
    torch.set_num_threads(NUM_THREADS)
    torch.manual_seed(RANDOM_STATE)
    np.random.seed(RANDOM_STATE)
    torch.use_deterministic_algorithms(True)


class SinusoidalPositionEncoding(nn.Module):
    """Fixed 60-position encoding with no fitted parameters."""

    def __init__(self) -> None:
        super().__init__()
        position = torch.arange(SEQUENCE_LENGTH, dtype=torch.float32).unsqueeze(1)
        divisor = torch.exp(
            torch.arange(0, EMBEDDING_DIMENSION, 2, dtype=torch.float32)
            * (-math.log(10000.0) / EMBEDDING_DIMENSION)
        )
        encoding = torch.zeros(
            (SEQUENCE_LENGTH, EMBEDDING_DIMENSION), dtype=torch.float32
        )
        encoding[:, 0::2] = torch.sin(position * divisor)
        encoding[:, 1::2] = torch.cos(position * divisor)
        self.register_buffer("encoding", encoding.unsqueeze(0), persistent=True)

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        return values + self.encoding


class FixedTemporalTransformer(nn.Module):
    """The single preregistered 60-by-6 Campaign302 architecture."""

    def __init__(self) -> None:
        super().__init__()
        self.embedding = nn.Linear(CHANNEL_COUNT, EMBEDDING_DIMENSION)
        self.position = SinusoidalPositionEncoding()
        layer = nn.TransformerEncoderLayer(
            d_model=EMBEDDING_DIMENSION,
            nhead=ATTENTION_HEADS,
            dim_feedforward=FEEDFORWARD_DIMENSION,
            dropout=DROPOUT,
            activation="gelu",
            batch_first=True,
            norm_first=False,
        )
        self.encoder = nn.TransformerEncoder(layer, num_layers=ENCODER_LAYERS)
        self.readout_norm = nn.LayerNorm(EMBEDDING_DIMENSION)
        self.readout = nn.Linear(EMBEDDING_DIMENSION, 1)

    def forward(self, matrix: torch.Tensor) -> torch.Tensor:
        if matrix.ndim != 2 or matrix.shape[1] != FEATURE_COUNT:
            raise Campaign302WorkerError("model input shape changed")
        sequence = matrix.reshape(-1, CHANNEL_COUNT, SEQUENCE_LENGTH).transpose(1, 2)
        encoded = self.encoder(self.position(self.embedding(sequence)))
        return self.readout(self.readout_norm(encoded[:, -1, :])).reshape(-1)


def validate_training_arrays(
    matrix: np.ndarray, target: np.ndarray, weight: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x = np.asarray(matrix, dtype=np.float32)
    y = np.asarray(target, dtype=np.float32).reshape(-1)
    w = np.asarray(weight, dtype=np.float32).reshape(-1)
    if not (
        x.ndim == 2
        and x.shape[1] == FEATURE_COUNT
        and len(x) == len(y) == len(w)
        and len(x) >= 1000
        and np.isfinite(x).all()
        and np.isfinite(y).all()
        and np.isfinite(w).all()
        and (w > 0).all()
        and math.isclose(float(w.sum()), 1.0, rel_tol=0.0, abs_tol=2e-6)
    ):
        raise Campaign302WorkerError("training array contract changed")
    return x, y, w / w.sum(dtype=np.float64)


def weighted_loss(
    model: FixedTemporalTransformer,
    matrix: torch.Tensor,
    target: torch.Tensor,
    weight: torch.Tensor,
) -> float:
    model.eval()
    numerator = 0.0
    with torch.no_grad():
        for begin in range(0, len(matrix), PREDICTION_BATCH_SIZE):
            end = min(begin + PREDICTION_BATCH_SIZE, len(matrix))
            residual = model(matrix[begin:end]) - target[begin:end]
            numerator += float(
                torch.sum(weight[begin:end] * residual.square()).cpu().item()
            )
    return numerator


def train(input_path: Path, model_path: Path, report_path: Path) -> dict[str, object]:
    fixed_environment()
    with np.load(input_path, allow_pickle=False) as payload:
        matrix, target, weight = validate_training_arrays(
            payload["matrix"], payload["target"], payload["weight"]
        )
    x = torch.from_numpy(matrix)
    y = torch.from_numpy(target)
    w = torch.from_numpy(weight)
    model = FixedTemporalTransformer()
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY
    )
    generator = torch.Generator(device="cpu").manual_seed(RANDOM_STATE)
    loss_curve: list[float] = []
    model.train()
    for _ in range(EPOCHS):
        order = torch.randperm(len(x), generator=generator)
        for begin in range(0, len(order), BATCH_SIZE):
            positions = order[begin : begin + BATCH_SIZE]
            prediction = model(x[positions])
            residual = prediction - y[positions]
            loss = torch.mean(w[positions] * len(x) * residual.square())
            if not torch.isfinite(loss):
                raise Campaign302WorkerError("nonfinite training loss")
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), GRADIENT_CLIP_L2_NORM)
            optimizer.step()
        loss_curve.append(weighted_loss(model, x, y, w))
    if not np.isfinite(loss_curve).all():
        raise Campaign302WorkerError("loss curve changed")

    model_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        prefix=f".{model_path.name}.", suffix=".tmp", dir=model_path.parent
    )
    os.close(descriptor)
    temporary = Path(name)
    try:
        torch.save(model.state_dict(), temporary)
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, model_path)
    finally:
        temporary.unlink(missing_ok=True)
    report: dict[str, object] = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign302_torch_worker_training",
        "status": "completed_fixed_five_epoch_training_without_validation_feedback",
        "training_rows": len(matrix),
        "feature_count": matrix.shape[1],
        "loss_curve": loss_curve,
        "model_sha256": file_sha256(model_path),
        "torch_version": torch.__version__,
        "random_state": RANDOM_STATE,
        "epochs": EPOCHS,
        "validation_return_feedback_used": False,
    }
    atomic_json(report_path, report)
    return report


def score(input_path: Path, model_path: Path, output_path: Path) -> dict[str, object]:
    fixed_environment()
    matrix = np.load(input_path, mmap_mode="r", allow_pickle=False)
    if not (
        matrix.ndim == 2
        and matrix.shape[1] == FEATURE_COUNT
        and np.isfinite(matrix).all()
    ):
        raise Campaign302WorkerError("score array contract changed")
    model = FixedTemporalTransformer()
    state = torch.load(model_path, map_location="cpu", weights_only=True)
    model.load_state_dict(state, strict=True)
    model.eval()
    result = np.empty(len(matrix), dtype=np.float64)
    with torch.no_grad():
        for begin in range(0, len(matrix), PREDICTION_BATCH_SIZE):
            end = min(begin + PREDICTION_BATCH_SIZE, len(matrix))
            batch = torch.from_numpy(np.asarray(matrix[begin:end], dtype=np.float32))
            result[begin:end] = model(batch).numpy().astype(np.float64, copy=False)
    if not np.isfinite(result).all():
        raise Campaign302WorkerError("model scores are nonfinite")
    atomic_numpy(output_path, result)
    return {
        "status": "completed_fixed_model_scoring",
        "rows": len(result),
        "output_sha256": file_sha256(output_path),
    }


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    subcommands = command.add_subparsers(dest="command", required=True)
    fit = subcommands.add_parser("train")
    fit.add_argument("--input", type=Path, required=True)
    fit.add_argument("--model", type=Path, required=True)
    fit.add_argument("--report", type=Path, required=True)
    predict = subcommands.add_parser("score")
    predict.add_argument("--input", type=Path, required=True)
    predict.add_argument("--model", type=Path, required=True)
    predict.add_argument("--output", type=Path, required=True)
    return command


def main() -> int:
    args = parser().parse_args()
    if args.command == "train":
        result = train(args.input, args.model, args.report)
    elif args.command == "score":
        result = score(args.input, args.model, args.output)
    else:
        raise Campaign302WorkerError(f"unsupported command: {args.command}")
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
