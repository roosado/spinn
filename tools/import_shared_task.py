"""Freeze the shared task, once, from photonn.

**Runs in photonn's venv, not this repo's**, and is not imported by anything here:

    D:/Python/Photonn/.venv/Scripts/python.exe tools/import_shared_task.py

This is the one deliberate exception to keeping the two repos independent, and it
is the right one. Regenerating "the same" MNIST subset independently is how two
platforms end up scored on different data without anyone noticing, and the
comparison table's whole premise is that the task is identical. It is frozen data,
not a duplicated result.

It is a one-off rather than a build step. `spinn` must never import `photonn` at
runtime; the output is committed and that is what the repo uses.

    python tools/import_shared_task.py            # the 6x6 task, as committed
    python tools/import_shared_task.py --grid 12  # the array-size sweep's other grids

The 6x6 task is the one the comparison table rests on. ``--grid g`` writes the same
digits at another resolution for ``docs/array_size.md``, and refuses to run unless the
recipe first reproduces the committed 6x6 test set bit for bit -- that check is what
makes "the same 2,000 digits at every size" a fact rather than an assumption.

What is written
---------------
``tests/fixtures/shared_task_6x6.npz``

- ``test_images``  (2000, 6, 6) float32 -- lifted **verbatim** from
  ``photonn/exports/mesh_phase3.h5``, the frozen set photonn's mesh was scored on.
  Not recomputed, so it cannot drift from what photonn actually used.
- ``test_labels``  (2000,) int32, likewise.
- ``train_images`` (20000, 6, 6) float32 -- MNIST train through photonn's own
  ``encode_modes``, the same function that produced the test set. Recomputed
  because the handoff carries no training data, and computed *here*, in photonn's
  venv, so the preprocessing is theirs rather than a reimplementation of theirs.
- ``train_labels`` (20000,) int32.

With ``--grid g`` (g != 6), two files instead of one, because the train split at a
large grid is tens of megabytes and the test split is not:

- ``shared_task_{g}x{g}_test.npz`` -- **committed**. The same 2,000 digits, photonn's
  ``load_dataset(subset=2000, split="test", subset_seed=0)`` through ``encode_modes``.
- ``shared_task_{g}x{g}_train.npz`` -- gitignored and regenerable, like ``exports/``.

On normalisation
----------------
``encode_modes`` L2-normalises each sample, because photonn's physical constraint
is optical power at the entrance. A crossbar's constraint is a maximum read
voltage -- an L-infinity bound.

That is not a problem, and the planning note that worried about it was wrong. The
images are non-negative and unit-L2, so dividing by the per-sample maximum
recovers exactly what L-infinity normalisation of the raw downsampled grid would
have given: for any positive scaling, ``s/max(s) == d/max(d)``. The normalisation
is a scale, and a scale is recoverable. An *offset* would not have been.

So the encoding stored here is the shared task, and each platform applies its own
input scaling on top of it.
"""
from __future__ import annotations

import argparse
import os
import sys

import h5py
import numpy as np

PHOTONN = r"D:\Python\Photonn"
HANDOFF = os.path.join(PHOTONN, "exports", "mesh_phase3.h5")

#: photonn's `apps/train_mesh.py` defaults, so the subsets are the ones its own
#: numbers were produced against. `load_dataset` draws with default_rng(subset_seed).
N_TRAIN = 20000
N_TEST = 2000
SUBSET_SEED = 0
N_MODES = 36
ROW_GRID = 6

FIXTURES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "fixtures"
)
OUT = os.path.join(FIXTURES, "shared_task_6x6.npz")


def _photonn():
    if PHOTONN not in sys.path:
        sys.path.insert(0, PHOTONN)
    try:
        from photonn.train import encode_modes, load_dataset
    except ModuleNotFoundError:
        raise SystemExit(
            "Run this with photonn's interpreter, which has photonn and torch:\n"
            f"  {PHOTONN}\\.venv\\Scripts\\python.exe tools/import_shared_task.py"
        )
    return encode_modes, load_dataset


def _encoded(encode_modes, dataset, grid: int) -> np.ndarray:
    """photonn's own encoding of a dataset at ``grid``: non-negative, unit-L2, float32."""
    return (
        encode_modes(dataset.images, n_modes=grid * grid)
        .abs().numpy().astype("f4").reshape(-1, grid, grid)
    )


def _lifted():
    """The 6x6 test set exactly as photonn's mesh was scored on it."""
    with h5py.File(HANDOFF, "r") as fh:
        images = fh["test_set/images"][:].astype("f4")
        labels = fh["test_set/labels"][:].astype("i4")
        provenance = str(fh.attrs["description"])
    g = int(round(N_MODES ** 0.5))
    assert images.shape[1:] == (g, g), images.shape
    norms = np.linalg.norm(images.reshape(len(images), -1), axis=1)
    assert np.allclose(norms, 1.0), "expected unit-L2 samples"
    return images, labels, provenance


def _test_recipe(encode_modes, load_dataset, grid: int):
    """The test split by recipe: photonn's draw, at any grid."""
    ds = load_dataset("mnist", subset=N_TEST, split="test", subset_seed=SUBSET_SEED)
    return _encoded(encode_modes, ds, grid), np.asarray(ds.labels, dtype="i4")


def _require_recipe_reproduces_the_lifted_set(encode_modes, load_dataset) -> None:
    """Refuse to emit another grid unless the recipe is *the* frozen 6x6 test set.

    Every other grid is claimed to be the same 2,000 digits at another resolution.
    That is only true if this recipe, at 6x6, gives back exactly what photonn's mesh
    was scored on -- images and labels, bit for bit.
    """
    lifted_images, lifted_labels, _ = _lifted()
    images, labels = _test_recipe(encode_modes, load_dataset, ROW_GRID)
    if not (np.array_equal(labels, lifted_labels) and np.array_equal(images, lifted_images)):
        raise SystemExit(
            "The recipe does not reproduce the frozen 6x6 test set, so another grid "
            "would not be the same digits. Stop and decide before going on."
        )
    print("recipe reproduces the frozen 6x6 test set exactly (images and labels)")


def freeze_row_grid() -> None:
    """The 6x6 task the comparison table rests on: lifted, never recomputed."""
    encode_modes, load_dataset = _photonn()

    # The test set is lifted, never recomputed: it is the artefact photonn was
    # actually scored on, and recomputing it would reintroduce exactly the drift
    # this file exists to prevent.
    test_images, test_labels, provenance = _lifted()
    g = ROW_GRID

    train = load_dataset("mnist", subset=N_TRAIN, split="train", subset_seed=SUBSET_SEED)
    train_images = _encoded(encode_modes, train, g)
    train_labels = np.asarray(train.labels, dtype="i4")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    np.savez_compressed(
        OUT,
        test_images=test_images,
        test_labels=test_labels,
        train_images=train_images,
        train_labels=train_labels,
        n_modes=np.int32(N_MODES),
        subset_seed=np.int32(SUBSET_SEED),
        source_handoff=np.bytes_(os.path.basename(HANDOFF)),
        source_description=np.bytes_(provenance),
    )
    size_kb = os.path.getsize(OUT) // 1024
    print(f"wrote {OUT} ({size_kb} KB)")
    print(f"  test  {test_images.shape} labels {np.bincount(test_labels).tolist()}")
    print(f"  train {train_images.shape}")
    print(f"  source: {provenance}")


def freeze_other_grid(g: int) -> None:
    """The same digits at grid ``g``, for the array-size sweep."""
    encode_modes, load_dataset = _photonn()
    _require_recipe_reproduces_the_lifted_set(encode_modes, load_dataset)

    test_images, test_labels = _test_recipe(encode_modes, load_dataset, g)
    norms = np.linalg.norm(test_images.reshape(len(test_images), -1), axis=1)
    assert np.allclose(norms, 1.0), "expected unit-L2 samples"

    train = load_dataset("mnist", subset=N_TRAIN, split="train", subset_seed=SUBSET_SEED)
    train_images = _encoded(encode_modes, train, g)
    train_labels = np.asarray(train.labels, dtype="i4")

    provenance = (
        f"photonn.train.load_dataset('mnist', subset={N_TEST}, split='test', "
        f"subset_seed={SUBSET_SEED}) through encode_modes(n_modes={g * g}); the same "
        f"recipe at 6x6 reproduces the mesh_phase3.h5 test set exactly | modes={g * g}"
    )
    common = dict(
        n_modes=np.int32(g * g),
        subset_seed=np.int32(SUBSET_SEED),
        source_description=np.bytes_(provenance),
    )
    stem = os.path.join(FIXTURES, f"shared_task_{g}x{g}")
    np.savez_compressed(
        f"{stem}_test.npz", test_images=test_images, test_labels=test_labels, **common
    )
    np.savez_compressed(
        f"{stem}_train.npz", train_images=train_images, train_labels=train_labels, **common
    )
    for kind, arr in (("test", test_images), ("train", train_images)):
        path = f"{stem}_{kind}.npz"
        print(f"wrote {path} ({os.path.getsize(path) // 1024} KB)  {arr.shape}")
    print(f"  test labels {np.bincount(test_labels).tolist()}")


def main() -> None:
    p = argparse.ArgumentParser(description="Freeze the shared task from photonn.")
    p.add_argument("--grid", type=int, default=ROW_GRID,
                   help="image grid g (rows = g*g); 6 is the comparison table's task")
    args = p.parse_args()
    if args.grid == ROW_GRID:
        freeze_row_grid()
    else:
        freeze_other_grid(args.grid)


if __name__ == "__main__":
    main()
