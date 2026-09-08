"""The training arithmetic, and the one step of it that is a physics claim.

Almost all of this file is ordinary: a softmax, a cross-entropy, a gradient step.
The part worth testing hard is :func:`fit_to_window`, because it encodes a claim
about the hardware -- that the conductance window bounds the weight pattern's
*shape* and not its scale, since a positive global factor on the column currents
cannot change an argmax.

That claim replaced a wrong one. The first version of the trainer projected onto
``[-1, 1]`` after every gradient step, which sounds more physical and is not: it
clips inside the descent, distorting the direction rather than the reachable set.
It cost 5.7 points of accuracy and parked 27% of the weights on the window edge.
The test below is what would have caught it.
"""
from __future__ import annotations

import numpy as np
import pytest

from apps.train_crossbar import cross_entropy, fit_to_window, softmax, train
from spinn.crossbar import Crossbar, accuracy
from spinn.task import one_hot


def test_softmax_is_a_distribution_and_survives_large_logits():
    z = np.array([[1.0, 2.0, 3.0], [1000.0, 1000.0, 1000.0]])
    p = softmax(z)
    assert np.allclose(p.sum(axis=1), 1.0)
    assert np.isfinite(p).all(), "the max-subtraction is what keeps this finite"
    assert np.allclose(p[1], 1 / 3)


def test_cross_entropy_is_zero_for_a_confident_correct_prediction():
    assert cross_entropy(np.array([[1.0, 0.0]]), np.array([[1.0, 0.0]])) < 1e-9


def test_cross_entropy_does_not_blow_up_on_a_confident_wrong_one():
    """The epsilon: log(0) is -inf, and one such sample would poison a whole epoch."""
    assert np.isfinite(cross_entropy(np.array([[0.0, 1.0]]), np.array([[1.0, 0.0]])))


# -- the window ---------------------------------------------------------------


def test_fitting_to_the_window_puts_every_weight_inside_it():
    w = np.array([[5.4, -2.0], [0.1, -0.3]])
    fitted, gain = fit_to_window(w)
    assert np.abs(fitted).max() == pytest.approx(1.0)
    assert gain == pytest.approx(5.4)


def test_the_gain_reconstructs_the_trained_weights():
    """It has to cross the handoff: without it MATLAB rebuilds mis-scaled logits."""
    w = np.array([[5.4, -2.0], [0.1, -0.3]])
    fitted, gain = fit_to_window(w)
    assert np.allclose(fitted * gain, w)


def test_fitting_to_the_window_cannot_change_a_prediction():
    """The claim the procedure rests on, tested rather than asserted.

    A positive global scale on every logit leaves the argmax alone. If this ever
    fails, training unconstrained and rescaling afterwards is not free and the
    recorded ideal accuracy is wrong.
    """
    rng = np.random.default_rng(4)
    x = rng.normal(size=(200, 12))
    w = rng.normal(scale=3.0, size=(12, 10))
    fitted, _ = fit_to_window(w)
    assert np.array_equal(np.argmax(x @ w, axis=1), np.argmax(x @ fitted, axis=1))


def test_all_zero_weights_are_refused_rather_than_dividing_by_zero():
    with pytest.raises(ValueError):
        fit_to_window(np.zeros((3, 3)))


# -- the loop ------------------------------------------------------------------


def test_training_reduces_the_loss_on_a_separable_problem():
    rng = np.random.default_rng(0)
    x = np.concatenate([rng.normal(1.0, 0.2, (60, 4)), rng.normal(-1.0, 0.2, (60, 4))])
    y = one_hot(np.array([0] * 60 + [1] * 60), 2)
    losses = [loss for _, loss, _ in
              train(x, y, epochs=12, lr=0.5, batch=16, seed=1)]
    assert losses[-1] < losses[0]


def test_training_is_reproducible_from_its_seed():
    rng = np.random.default_rng(2)
    x, y = rng.normal(size=(80, 5)), one_hot(rng.integers(0, 3, 80), 3)
    kw = dict(epochs=4, lr=0.3, batch=16)
    a = [w.copy() for _, _, w in train(x, y, seed=7, **kw)][-1]
    b = [w.copy() for _, _, w in train(x, y, seed=7, **kw)][-1]
    assert np.array_equal(a, b), "seeds are fixed and recorded; they must mean something"


def test_the_trained_map_is_what_the_array_computes():
    """End to end: the linear map the loop trains *is* the crossbar, not a stand-in.

    If these ever diverge, the training shortcut and the physical decode have
    drifted, and the recorded accuracy describes neither.
    """
    rng = np.random.default_rng(3)
    images = rng.random((40, 3, 3))
    cb = Crossbar(9, 4)
    x = cb.encode(images) / cb.read_voltage
    y = one_hot(rng.integers(0, 4, 40), 4)
    weights = [w for _, _, w in train(x, y, epochs=6, lr=0.4, batch=10, seed=5)][-1]
    fitted, _ = fit_to_window(weights)
    assert np.allclose(cb.forward(images, fitted), x @ fitted)
    assert accuracy(cb.forward(images, fitted), np.argmax(y, axis=1)) == accuracy(
        x @ fitted, np.argmax(y, axis=1)
    )
