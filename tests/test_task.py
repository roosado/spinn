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

from spinn.task import N_CHANNELS, N_CLASSES, load_shared_task, one_hot


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
