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

import os
import sys

import h5py
import numpy as np

PHOTONN = r"D:\Python\Photonn"
HANDOFF = os.path.join(PHOTONN, "exports", "mesh_phase3.h5")

#: photonn's `apps/train_mesh.py` defaults, so the subsets are the ones its own
#: numbers were produced against. `load_dataset` draws with default_rng(subset_seed).
N_TRAIN = 20000
SUBSET_SEED = 0
N_MODES = 36

OUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tests", "fixtures", "shared_task_6x6.npz",
)


def main() -> None:
    if PHOTONN not in sys.path:
        sys.path.insert(0, PHOTONN)
    try:
        from photonn.train import encode_modes, load_dataset
    except ModuleNotFoundError:
        raise SystemExit(
            "Run this with photonn's interpreter, which has photonn and torch:\n"
            f"  {PHOTONN}\\.venv\\Scripts\\python.exe tools/import_shared_task.py"
        )

    # The test set is lifted, never recomputed: it is the artefact photonn was
    # actually scored on, and recomputing it would reintroduce exactly the drift
    # this file exists to prevent.
    with h5py.File(HANDOFF, "r") as fh:
        test_images = fh["test_set/images"][:].astype("f4")
        test_labels = fh["test_set/labels"][:].astype("i4")
        provenance = str(fh.attrs["description"])

    g = int(round(N_MODES ** 0.5))
    assert test_images.shape[1:] == (g, g), test_images.shape
    norms = np.linalg.norm(test_images.reshape(len(test_images), -1), axis=1)
    assert np.allclose(norms, 1.0), "expected unit-L2 samples"

    train = load_dataset("mnist", subset=N_TRAIN, split="train", subset_seed=SUBSET_SEED)
    train_images = (
        encode_modes(train.images, n_modes=N_MODES)
        .abs().numpy().astype("f4").reshape(-1, g, g)
    )
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


if __name__ == "__main__":
    main()
