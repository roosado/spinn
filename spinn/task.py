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

**Only 6x6 is the shared task.** ``load_shared_task(grid=g)`` also loads the same 2,000
test digits at 8, 12, 18 and 26, for the array-size sweep. photonn scored only the
36-mode mesh, so those grids are spinn-internal and nothing about them is comparable
to a photonn row; what ties them to the shared task is that ``tools/import_shared_task.py``
refuses to emit one unless its recipe first reproduces the 6x6 test set bit for bit.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np

FIXTURES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "fixtures"
)
FIXTURE = os.path.join(FIXTURES, "shared_task_6x6.npz")

#: The grid the comparison table rests on, and its channel count. Every other grid
#: exists for the array-size sweep only.
ROW_GRID = 6
N_CHANNELS = 36
N_CLASSES = 10


@dataclass(frozen=True)
class SharedTask:
    """Both splits of the frozen task, plus where they came from.

    ``train_images`` and ``train_labels`` are ``None`` when the train split was not
    asked for or is not on disk: at the larger grids it is regenerable rather than
    committed, and a test that needs only the test split should not need it.
    """

    train_images: np.ndarray | None   # (n, g, g) float32, unit-L2, non-negative
    train_labels: np.ndarray | None   # (n,) int32
    test_images: np.ndarray           # (2000, g, g) float32
    test_labels: np.ndarray           # (2000,) int32
    source: str                       # the handoff description the test split came from

    @property
    def n_channels(self) -> int:
        return int(np.prod(self.test_images.shape[1:]))

    @property
    def grid(self) -> int:
        return int(self.test_images.shape[1])


def _read(path: str, hint: str) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} is missing. {hint}")
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


def load_shared_task(grid: int = ROW_GRID, *, train: bool = True) -> SharedTask:
    """Load the frozen task at ``grid``, checking the properties everything assumes.

    The 6x6 task is one committed file. Every other grid is two: a committed test
    split and a gitignored train split, because the latter is tens of megabytes at
    the larger grids. Both come from ``tools/import_shared_task.py``.
    """
    regenerate = (
        "It is regenerated with photonn's interpreter:\n"
        f"  D:/Python/Photonn/.venv/Scripts/python.exe tools/import_shared_task.py "
        f"--grid {grid}"
    )
    if grid == ROW_GRID:
        z = _read(FIXTURE, "It is committed; if it has been removed, regenerate it. " + regenerate)
        test = train_z = z
    else:
        stem = os.path.join(FIXTURES, f"shared_task_{grid}x{grid}")
        test = _read(f"{stem}_test.npz", "It is committed. " + regenerate)
        train_z = _read(f"{stem}_train.npz", regenerate) if train else None

    task = SharedTask(
        train_images=train_z["train_images"] if train and train_z is not None else None,
        train_labels=train_z["train_labels"] if train and train_z is not None else None,
        test_images=test["test_images"],
        test_labels=test["test_labels"],
        source=bytes(test["source_description"]).decode("utf-8"),
    )
    if task.grid != grid or task.n_channels != grid * grid:
        raise ValueError(
            f"expected {grid}x{grid} = {grid * grid} channels; got {task.test_images.shape[1:]}"
        )
    if grid == ROW_GRID and task.n_channels != N_CHANNELS:
        raise ValueError(f"expected {N_CHANNELS} channels; got {task.n_channels}")
    return task


def one_hot(labels: np.ndarray, n_classes: int = N_CLASSES) -> np.ndarray:
    out = np.zeros((len(labels), n_classes), dtype="f8")
    out[np.arange(len(labels)), np.asarray(labels)] = 1.0
    return out
