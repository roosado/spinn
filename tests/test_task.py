"""The frozen shared task, and the properties the comparison depends on.

The comparison table's premise is that both platforms are scored on **identical**
data. That is enforced by lifting photonn's test set verbatim rather than
regenerating it -- regenerating "the same" MNIST subset independently is how two
platforms end up scored on different data without anyone noticing.

These tests are the standing guard on that. If the fixture is ever regenerated and
one of these fails, the row in the comparison table is not comparable any more.
"""
from __future__ import annotations

import numpy as np

import os

import pytest

from spinn.task import (
    FIXTURES,
    N_CHANNELS,
    N_CLASSES,
    ROW_GRID,
    load_shared_task,
    one_hot,
)


def test_the_task_loads_with_both_splits():
    task = load_shared_task()
    assert task.train_images.shape == (20000, 6, 6)
    assert task.test_images.shape == (2000, 6, 6)
    assert task.train_labels.shape == (20000,)
    assert task.test_labels.shape == (2000,)


def test_thirty_six_channels_at_six_by_six():
    """36 modes matching photonn's mesh; a crossbar's counterpart is the mesh, not the stack."""
    assert load_shared_task().n_channels == N_CHANNELS == 36


def test_every_sample_is_unit_l2_and_non_negative():
    """Both facts are load-bearing for the crossbar's own input scaling.

    ``Crossbar.encode`` divides by the per-sample maximum to honour a read-voltage
    bound. That recovers exactly the L-infinity normalisation of the raw grid only
    because these are non-negative and differ from it by a positive scale.
    """
    task = load_shared_task()
    for images in (task.train_images, task.test_images):
        flat = images.reshape(len(images), -1)
        assert np.allclose(np.linalg.norm(flat, axis=1), 1.0)
        assert (flat >= 0).all()


def test_no_sample_is_entirely_blank():
    """A blank sample would divide by zero in the encode, and mean nothing anyway."""
    task = load_shared_task()
    for images in (task.train_images, task.test_images):
        assert (images.reshape(len(images), -1).max(axis=1) > 0).all()


def test_labels_cover_the_ten_classes():
    task = load_shared_task()
    for labels in (task.train_labels, task.test_labels):
        assert set(np.unique(labels)) == set(range(N_CLASSES))


def test_the_test_split_records_where_it_came_from():
    """Provenance travels with the data, so a later reader need not reconstruct it."""
    source = load_shared_task().source
    assert "modes=36" in source
    assert "test_acc=" in source, "the handoff's own record of what photonn scored"


def test_one_hot_is_one_hot():
    y = one_hot(np.array([0, 3, 9]))
    assert y.shape == (3, N_CLASSES)
    assert np.array_equal(y.sum(axis=1), np.ones(3))
    assert y[1, 3] == 1.0 and y[2, 9] == 1.0


# -- the other grids, for the array-size sweep ---------------------------------
#
# Only 6x6 is the shared task. The rest are the same 2,000 digits at another
# resolution, and what makes that true is checked here rather than assumed.

SWEEP_GRIDS = (8, 12, 18, 26)


@pytest.mark.parametrize("grid", SWEEP_GRIDS)
def test_another_grid_loads_its_test_split_without_the_train_split(grid):
    """The train split is gitignored at the larger grids, so a test must not need it."""
    task = load_shared_task(grid, train=False)
    assert task.test_images.shape == (2000, grid, grid)
    assert task.n_channels == grid * grid
    assert task.train_images is None and task.train_labels is None


@pytest.mark.parametrize("grid", SWEEP_GRIDS)
def test_another_grid_is_unit_l2_and_non_negative(grid):
    flat = load_shared_task(grid, train=False).test_images.reshape(2000, -1)
    assert np.allclose(np.linalg.norm(flat, axis=1), 1.0)
    assert (flat >= 0).all() and (flat.max(axis=1) > 0).all()


@pytest.mark.parametrize("grid", SWEEP_GRIDS)
def test_every_grid_is_the_same_two_thousand_digits(grid):
    """The labels are the part that can be compared without a downsampler.

    Bit-identical labels in the same order, at every grid, is what says these are
    the same draw. The images differ by construction. That the recipe reproduces the
    6x6 images exactly is checked where it is run, in
    ``tools/import_shared_task.py``, which refuses to emit a grid otherwise.
    """
    row = load_shared_task(ROW_GRID, train=False)
    other = load_shared_task(grid, train=False)
    assert np.array_equal(row.test_labels, other.test_labels)


@pytest.mark.parametrize("grid", SWEEP_GRIDS)
def test_another_grid_states_its_own_provenance(grid):
    source = load_shared_task(grid, train=False).source
    assert f"modes={grid * grid}" in source
    assert "subset_seed=0" in source


def test_a_train_split_that_is_absent_says_how_to_regenerate_it(tmp_path, monkeypatch):
    """Gitignored means it can be missing; the error has to be a fix, not a mystery."""
    import spinn.task as task_module

    monkeypatch.setattr(task_module, "FIXTURES", str(tmp_path))
    with pytest.raises(FileNotFoundError, match="import_shared_task.py --grid 8"):
        load_shared_task(8, train=False)


def test_a_grid_that_does_not_match_its_file_is_refused(tmp_path, monkeypatch):
    """A 12x12 file loaded as 8x8 would be a valid task at the wrong size, silently."""
    import shutil
    import spinn.task as task_module

    src = os.path.join(FIXTURES, "shared_task_12x12_test.npz")
    shutil.copy(src, tmp_path / "shared_task_8x8_test.npz")
    monkeypatch.setattr(task_module, "FIXTURES", str(tmp_path))
    with pytest.raises(ValueError, match="expected 8x8"):
        load_shared_task(8, train=False)
