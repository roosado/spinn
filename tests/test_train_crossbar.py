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

import inspect
import os
import sys

import numpy as np
import pytest

from apps.train_crossbar import (
    EXPORTS,
    SCALE_CANDIDATES,
    calibrate_scale,
    cross_entropy,
    fit_to_window,
    learning_rate,
    main,
    output_dir,
    ratio_crossbar,
    ratio_dir,
    scale_dir,
    scale_to_window,
    softmax,
    train,
)
from spinn.crossbar import G_MAX, G_MIN, Crossbar, accuracy
from spinn.handoff import read_handoff
from spinn.task import load_shared_task, one_hot


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


# -- the array-size sweep's training rule --------------------------------------


def test_the_learning_rate_is_exactly_the_rows_own_at_36_inputs():
    """0.5 * 36 / 36, so the 6x6 array trains as it always did.

    Exact equality, not approx: the row's recorded weights must reproduce
    bit for bit, and a rate that differed in the last place would not.
    """
    assert learning_rate(36) == 0.5


def test_the_learning_rate_holds_the_step_in_the_input_norm_constant():
    """The step of a softmax regression goes with ||x||^2, which goes with the rows.

    Normalised inputs of ``n`` pixels have a squared norm that grows with ``n``,
    so ``lr * rows`` is what stays fixed. Unscaled, 676 inputs would oscillate and
    the ideal accuracy would be the optimiser's artefact.
    """
    for rows in (64, 144, 324, 676):
        assert learning_rate(rows) * rows == pytest.approx(0.5 * 36)
    assert learning_rate(676) < learning_rate(144) < learning_rate(36)


def test_the_rows_own_handoff_stays_where_it_was_and_the_rest_go_under_size():
    assert output_dir(6) == EXPORTS
    assert output_dir(12) == os.path.join(EXPORTS, "size", "g12")
    assert output_dir(8).endswith(os.path.join("size", "g08")), "zero-padded, so they sort"


def test_a_window_ratio_variant_lands_under_ratio_named_by_its_ratio():
    """``exports/ratio/r2p03``: a sensitivity, kept apart from the design's own handoff."""
    assert ratio_dir(2.03) == os.path.join(EXPORTS, "ratio", "r2p03")
    assert ratio_dir(1.85) == os.path.join(EXPORTS, "ratio", "r1p85")


def test_a_window_ratio_variant_holds_g_min_and_moves_only_g_max():
    """The design's off state stays put; only the on state follows the measured TMR.

    Under a spread proportional to conductance only the ratio reaches the accuracy,
    so which end is held is a choice about IR drop and power, which the variants are
    not run for. Holding g_min keeps the high-resistance state -- the one most
    devices sit in -- at the design's 1 MOhm.
    """
    cb = ratio_crossbar(36, 10, 2.03)
    assert cb.g_min == G_MIN
    assert cb.g_max == pytest.approx(2.03 * G_MIN)
    assert cb.ratio == pytest.approx(2.03)
    assert ratio_crossbar(36, 10, None).g_max == G_MAX, "no ratio is the design"


def test_a_ratio_variant_computes_exactly_what_the_design_does():
    """The window cancels in the ideal decode, so a variant's ideal is the design's."""
    rng = np.random.default_rng(3)
    images, w = rng.random((5, 36)), rng.uniform(-1, 1, (36, 10))
    assert np.allclose(ratio_crossbar(36, 10, 1.85).forward(images, w),
                       Crossbar(36, 10).forward(images, w))


# -- the calibrated scale --------------------------------------------------------
#
# The row maps max|w| to full scale. The calibrated variant puts full scale at c*max|w|
# instead and chooses c on the train set. It is a programming choice and not training,
# and the row keeps max|w|; these tests pin the choice and the handoff it writes.

ROW_IDEAL = os.path.join(EXPORTS, "crossbar_ideal.npz")

needs_row = pytest.mark.skipif(
    not os.path.exists(ROW_IDEAL),
    reason="exports/ is gitignored; run apps.train_crossbar first",
)


def _brute_force(w, x, y, states):
    """Every candidate's train accuracy, with the quantiser written out independently."""
    n = states - 1
    accs = []
    for c in SCALE_CANDIDATES:
        scaled = np.clip(w / (c * np.abs(w).max()), -1.0, 1.0)
        q = np.sign(scaled * n) * np.floor(np.abs(scaled * n) + 0.5) / n
        accs.append(accuracy(x @ q, y))
    return accs


def test_a_calibrated_variant_lands_under_scale_named_by_its_states():
    """``exports/scale/s5``: a sensitivity, kept apart from the design's own handoff."""
    assert scale_dir(5) == os.path.join(EXPORTS, "scale", "s5")
    assert scale_dir(3) == os.path.join(EXPORTS, "scale", "s3")


def test_the_candidates_are_exactly_0p30_to_1p00_in_steps_of_0p05():
    """Built from integers, so 0.35 is the literal 0.35 and not an accumulated step."""
    assert len(SCALE_CANDIDATES) == 15
    assert SCALE_CANDIDATES == tuple(k / 100 for k in range(30, 101, 5))
    assert SCALE_CANDIDATES[0] == 0.30 and SCALE_CANDIDATES[1] == 0.35
    assert SCALE_CANDIDATES[-1] == 1.0


def test_calibration_never_sees_test_data():
    """It takes the weights and the *train* arrays; nothing in its signature is a test set."""
    names = list(inspect.signature(calibrate_scale).parameters)
    assert names[:4] == ["weights", "x_train", "train_labels", "states"]
    assert not [n for n in names if "test" in n]


def test_calibration_picks_the_train_accuracy_maximiser_and_ties_go_to_the_larger_c():
    """Labels are the continuous array's own argmax, so quantisation is all that costs.

    Seed 16 is chosen because the best accuracy is reached at two candidates that are
    not neighbours -- 0.45 and 0.90 -- so "first maximum" and "last maximum" differ,
    and the precondition below fails loudly if the synthetic problem ever stops being
    a tie.
    """
    rng = np.random.default_rng(16)
    w = rng.normal(size=(8, 4))
    w[0, 0] = 5.0  # the outlier that sets the lattice at c = 1
    x = rng.random((60, 8))
    y = np.argmax(x @ w, axis=1)

    accs = _brute_force(w, x, y, 3)
    best = max(accs)
    tied = [c for c, a in zip(SCALE_CANDIDATES, accs) if a == best]
    assert len(tied) > 1, "the problem must contain a tie for this test to mean anything"
    assert accs[-1] < best, "and c = 1 must not already be the answer"

    assert calibrate_scale(w, x, y, 3) == max(tied)
    assert calibrate_scale(w, x, y, 3) > min(tied)


def test_when_every_candidate_ties_the_answer_is_c_equal_one():
    """The identity pattern quantises to itself at every c, so all fifteen tie."""
    w = np.eye(3)
    x = np.eye(3)
    y = np.arange(3)
    assert calibrate_scale(w, x, y, 2) == 1.0


def test_scaling_at_c_equal_one_is_the_rows_own_fit_to_the_window():
    w = np.array([[5.4, -2.0], [0.1, -0.3]])
    assert np.array_equal(scale_to_window(w, 1.0), fit_to_window(w)[0])


def test_scaling_below_one_clips_the_outliers_to_the_rails_and_nothing_else():
    w = np.array([[1.0, -1.0], [0.5, -0.25]])
    out = scale_to_window(w, 0.5)
    assert np.array_equal(out, np.array([[1.0, -1.0], [1.0, -0.5]]))


@needs_row
def test_the_calibrated_weights_quantise_exactly_as_the_search_saw_them():
    """On the row's own weights: in the window, full scale touched, same lattice point."""
    weights = np.load(ROW_IDEAL)["weights"]
    task = load_shared_task()
    full = Crossbar(36, 10)
    x_train = full.encode(task.train_images) / full.read_voltage
    cb = Crossbar(36, 10, states=5)

    c = calibrate_scale(weights, x_train, task.train_labels, 5)
    assert c in SCALE_CANDIDATES

    w_cal = np.clip(weights / c, -1.0, 1.0)
    assert np.abs(w_cal).max() == 1.0
    assert w_cal.min() >= -1.0 and w_cal.max() <= 1.0
    # The row's weights are already fitted, so max|w| is 1 and w / c is w / (c * max|w|).
    assert np.array_equal(w_cal, scale_to_window(weights, c))

    searched = cb.quantise_weights(np.clip(weights / (c * np.abs(weights).max()), -1.0, 1.0))
    assert np.array_equal(cb.quantise_weights(w_cal), searched)


def _run_main(monkeypatch, out_dir, *extra):
    argv = ["train_crossbar", "--quick", "--out-dir", str(out_dir), *extra]
    monkeypatch.setattr(sys, "argv", argv)
    main()


def test_the_calibrated_handoff_carries_clipped_weights_and_the_gain_times_c(
    monkeypatch, tmp_path, capsys
):
    """Same training as the row, so the calibrated gain is the row's gain times ``c``.

    ``--quick`` is five epochs, which is enough to pin the arithmetic and is not the
    row's accuracy. ``--out-dir`` keeps both runs out of ``exports/``.
    """
    row, cal = tmp_path / "row", tmp_path / "cal"
    _run_main(monkeypatch, row)
    _run_main(monkeypatch, cal, "--calibrate-states", "5")
    capsys.readouterr()

    zr, zc = np.load(row / "crossbar_ideal.npz"), np.load(cal / "crossbar_ideal.npz")
    c = float(zc["scale_c"])
    assert c in SCALE_CANDIDATES and int(zc["calibrated_states"]) == 5
    assert "scale_c" not in zr.files, "the row's record is unchanged"

    assert float(zc["readout_gain"]) == float(zr["readout_gain"]) * c
    assert np.array_equal(zc["weights"], np.clip(zr["weights"] / c, -1.0, 1.0))
    assert np.abs(zc["weights"]).max() == 1.0

    # The ideal recorded is the continuous accuracy of the clipped weights, through the array.
    task = load_shared_task(train=False)
    assert float(zc["ideal_accuracy"]) == accuracy(
        Crossbar(36, 10).forward(task.test_images, zc["weights"]), task.test_labels
    )

    h = read_handoff(cal / "crossbar_handoff.h5")
    assert h.constant("readout_gain") == float(zc["readout_gain"])
    assert h.constant("g_max_s") == G_MAX and h.constant("g_min_s") == G_MIN


def test_calibration_is_refused_off_the_rows_own_array(monkeypatch, tmp_path):
    """Like ``--ratio``: a sensitivity of the 36x10 row, and not of the size sweep."""
    monkeypatch.setattr(sys, "argv", ["train_crossbar", "--calibrate-states", "5",
                                      "--grid", "12", "--out-dir", str(tmp_path)])
    with pytest.raises(SystemExit, match="grid 6"):
        main()


def test_calibration_and_a_window_ratio_are_not_stacked(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "argv", ["train_crossbar", "--calibrate-states", "5",
                                      "--ratio", "2.03", "--out-dir", str(tmp_path)])
    with pytest.raises(SystemExit, match="--ratio"):
        main()
