"""The shared task, frozen.

MNIST at 6x6 -- 36 channels, matching the mesh photonn built, because a crossbar
is an N-by-N matrix engine and the mesh is its like-for-like counterpart rather
than the diffractive stack.

The data is committed at ``tests/fixtures/shared_task_6x6.npz`` and was produced
once by ``tools/import_shared_task.py``, running in photonn's environment. The
test split is lifted verbatim from the handoff photonn's mesh was scored on; the
train split is MNIST train through photonn's own ``encode_modes``. Neither is
recomputed here, and ``spinn`` never imports ``photonn`` at runtime.

The samples are non-negative and unit-L2 -- photonn normalises to unit optical
power. A crossbar's constraint is a maximum read voltage instead, so
:meth:`spinn.crossbar.Crossbar.encode` rescales per sample. That is exact rather
than approximate: for a non-negative vector, ``s/max(s) == d/max(d)`` under any
positive scaling ``s = d/k``.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np

FIXTURE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tests", "fixtures", "shared_task_6x6.npz",
)

N_CHANNELS = 36
N_CLASSES = 10


@dataclass(frozen=True)
class SharedTask:
    """Both splits of the frozen task, plus where they came from."""

    train_images: np.ndarray   # (n, 6, 6) float32, unit-L2, non-negative
    train_labels: np.ndarray   # (n,) int32
    test_images: np.ndarray    # (2000, 6, 6) float32
    test_labels: np.ndarray    # (2000,) int32
    source: str                # the handoff description the test split came from

    @property
    def n_channels(self) -> int:
        return int(np.prod(self.test_images.shape[1:]))


def load_shared_task(path: str = FIXTURE) -> SharedTask:
    """Load the frozen task, checking the properties everything downstream assumes."""
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path} is missing. It is committed; if it has been removed, regenerate "
            "it with photonn's interpreter:\n"
            "  D:/Python/Photonn/.venv/Scripts/python.exe tools/import_shared_task.py"
        )
    with np.load(path, allow_pickle=False) as z:
        task = SharedTask(
            train_images=z["train_images"],
            train_labels=z["train_labels"],
            test_images=z["test_images"],
            test_labels=z["test_labels"],
            source=bytes(z["source_description"]).decode("utf-8"),
        )
    if task.n_channels != N_CHANNELS:
        raise ValueError(f"expected {N_CHANNELS} channels; got {task.n_channels}")
    return task


def one_hot(labels: np.ndarray, n_classes: int = N_CLASSES) -> np.ndarray:
    out = np.zeros((len(labels), n_classes), dtype="f8")
    out[np.arange(len(labels)), np.asarray(labels)] = 1.0
    return out
