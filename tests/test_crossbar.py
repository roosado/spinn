"""The ideal crossbar, against cases small enough to work out by hand.

photonn's convention is a corresponding analytic test for every physics function,
and a crossbar makes that unusually cheap: a 2x2 array with four known
conductances has a column current you can compute on paper. The values below were
computed that way and then checked against the code, not read off it.

The headline is :func:`test_an_ideal_crossbar_computes_exactly_a_matrix_product`.
Both signed-weight schemes, at any conductance window and any read voltage, must
reduce exactly to ``normalised_input @ W``. That single identity pins the
programming map, the current summation and the decode against each other -- and it
is what makes the ideal number independent of which conductance window the design
chose, rather than merely believed to be.
"""
from __future__ import annotations

import numpy as np
import pytest

from spinn.crossbar import Crossbar, accuracy, predict

# The hand-worked example, used by several tests below.
#
#   g_min = 1e-6, g_max = 3e-6  ->  span = 2e-6,  read_voltage = 0.1
#   W = [[ 1.0, -1.0],
#        [ 0.0,  0.5]]
#   g_pos = g_min + (1+w)*1e-6 = [[3e-6, 1e-6], [2e-6, 2.5e-6]]
#   g_neg = g_min + (1-w)*1e-6 = [[1e-6, 3e-6], [2e-6, 1.5e-6]]
#   image [1.0, 0.5], peak 1.0  ->  V = [0.1, 0.05]
#   I_pos = [0.1*3e-6 + 0.05*2e-6,  0.1*1e-6 + 0.05*2.5e-6] = [4.00e-7, 2.25e-7]
#   I_neg = [0.1*1e-6 + 0.05*2e-6,  0.1*3e-6 + 0.05*1.5e-6] = [2.00e-7, 3.75e-7]
#   logits = (I_pos - I_neg) / (0.1 * 2e-6)                  = [1.0, -0.75]
HAND_W = np.array([[1.0, -1.0], [0.0, 0.5]])
HAND_IMAGE = np.array([[1.0, 0.5]])
HAND_G_POS = np.array([[3.0e-6, 1.0e-6], [2.0e-6, 2.5e-6]])
HAND_G_NEG = np.array([[1.0e-6, 3.0e-6], [2.0e-6, 1.5e-6]])
HAND_I_POS = np.array([[4.00e-7, 2.25e-7]])
HAND_I_NEG = np.array([[2.00e-7, 3.75e-7]])
HAND_LOGITS = np.array([[1.0, -0.75]])


@pytest.fixture
def bar():
    return Crossbar(n_inputs=2, n_outputs=2, g_min=1.0e-6, g_max=3.0e-6,
                    read_voltage=0.1)


# -- programming -------------------------------------------------------------


def test_the_two_rails_are_the_hand_computed_conductances(bar):
    g = bar.program(HAND_W)
    assert g.shape == (2, 2, 2)
    assert np.allclose(g[0], HAND_G_POS)
    assert np.allclose(g[1], HAND_G_NEG)


def test_a_differential_pair_encodes_the_weight_in_its_difference(bar):
    """``g_pos - g_neg == w * span`` exactly, which is the whole scheme."""
    w = np.array([[-1.0, -0.25], [0.4, 1.0]])
    g = Crossbar(2, 2).program(w)
    assert np.allclose(g[0] - g[1], w * Crossbar(2, 2).span)


def test_every_conductance_stays_inside_the_physical_window(bar):
    for scheme in ("differential", "offset"):
        cb = Crossbar(4, 3, scheme=scheme)
        g = cb.program(np.linspace(-2.0, 2.0, 12).reshape(4, 3))  # deliberately out of range
        assert g.min() >= cb.g_min - 1e-18
        assert g.max() <= cb.g_max + 1e-18


def test_an_offset_array_uses_one_device_per_weight_and_a_pair_uses_two():
    assert Crossbar(6, 5, scheme="offset").n_devices == 30
    assert Crossbar(6, 5, scheme="differential").n_devices == 60


# -- reading -----------------------------------------------------------------


def test_column_currents_are_the_hand_computed_sums(bar):
    v = bar.encode(HAND_IMAGE)
    assert np.allclose(v, [[0.1, 0.05]])
    i = bar.currents(v, bar.program(HAND_W))
    assert np.allclose(i[0], HAND_I_POS)
    assert np.allclose(i[1], HAND_I_NEG)


def test_the_decode_gives_the_hand_computed_logits(bar):
    assert np.allclose(bar.forward(HAND_IMAGE, HAND_W), HAND_LOGITS)


def test_an_ideal_crossbar_computes_exactly_a_matrix_product():
    """The identity both schemes must satisfy, at any window and any drive.

    An ideal crossbar is a matrix-vector multiply and nothing else. If this holds
    for a randomly chosen window, the design's choice of conductances cannot be
    influencing the ideal accuracy -- they cancel in the decode, exactly, rather
    than approximately or by convention.
    """
    rng = np.random.default_rng(20260908)
    images = rng.random((7, 3, 3))
    w = rng.uniform(-1.0, 1.0, size=(9, 4))
    for scheme in ("differential", "offset"):
        for g_min, g_max, volts in ((1e-6, 3e-6, 0.1), (2.5e-4, 9.0e-4, 1.7)):
            cb = Crossbar(9, 4, scheme=scheme, g_min=g_min, g_max=g_max,
                          read_voltage=volts)
            expected = (cb.encode(images) / volts) @ w
            assert np.allclose(cb.forward(images, w), expected), (scheme, g_min)


def test_the_offset_scheme_subtracts_a_pedestal_the_pair_never_draws():
    """Under one rail the column carries a baseline set by the inputs, not the weights.

    Here it is subtracted exactly, because this is the ideal model. In hardware it
    is a real current with real noise on it, and subtracting its mean downstream
    does not subtract that -- which is half the argument for the differential pair.
    """
    cb = Crossbar(2, 2, scheme="offset", g_min=1.0e-6, g_max=3.0e-6, read_voltage=0.1)
    v = cb.encode(HAND_IMAGE)
    zero_weights = np.zeros((2, 2))
    raw = cb.currents(v, cb.program(zero_weights))
    assert raw[0].min() > 0, "a real current flows even for an all-zero weight matrix"
    assert np.allclose(cb.decode(raw, v), 0.0), "and it decodes to exactly zero"


# -- the input scaling -------------------------------------------------------


def test_encoding_puts_the_largest_pixel_at_the_read_voltage():
    cb = Crossbar(4, 2, read_voltage=0.25)
    v = cb.encode(np.array([[0.2, 0.1, 0.05, 0.0], [0.9, 0.9, 0.0, 0.0]]))
    assert np.allclose(v.max(axis=1), 0.25)


def test_rescaling_a_unit_l2_sample_recovers_the_l_infinity_normalisation():
    """Why freezing photonn's L2-normalised grid costs this platform nothing.

    photonn normalises to unit optical power; a crossbar is bounded by a maximum
    read voltage. Both are per-sample positive scalings of the same non-negative
    vector, so one is exactly recoverable from the other.
    """
    rng = np.random.default_rng(11)
    raw = rng.random((5, 9))
    l2 = raw / np.linalg.norm(raw, axis=1, keepdims=True)
    cb = Crossbar(9, 2, read_voltage=1.0)
    assert np.allclose(cb.encode(l2), raw / raw.max(axis=1, keepdims=True))


def test_an_all_zero_sample_does_not_divide_by_zero():
    v = Crossbar(4, 2).encode(np.zeros((1, 4)))
    assert np.all(v == 0)


# -- the states knob ---------------------------------------------------------


def test_quantisation_snaps_devices_to_the_window_endpoints_at_two_states():
    cb = Crossbar(1, 3, states=2)
    g = cb.program(np.array([[-1.0, 0.9, 1.0]]))
    assert set(np.unique(g)) <= {cb.g_min, cb.g_max}


def test_quantisation_is_bounded_and_not_cyclic():
    """photonn's quantiser wraps to ``[0, 2*pi)``; conductance has ends, not a seam.

    A cyclic quantiser maps the largest weight onto the smallest. That is not a
    subtle error, but it would still return a plausible accuracy rather than fail.
    """
    cb = Crossbar(1, 2, states=4)
    g = cb.program(np.array([[1.0, -1.0]]))
    assert g[0, 0, 0] == pytest.approx(cb.g_max)
    assert g[0, 0, 1] == pytest.approx(cb.g_min)


def test_a_differential_pair_resolves_more_states_than_either_device_holds():
    """Two-state devices, three distinguishable weights.

    The effective weight is a *difference* of quantised conductances, so it
    resolves more finely than either device does. Quantising the weight instead of
    the devices would miss this and make error source 2 look worse than it is.
    """
    cb = Crossbar(1, 5, states=2)
    w = np.array([[-1.0, -0.4, 0.0, 0.4, 1.0]])
    g = cb.program(w)
    effective = (g[0] - g[1]) / cb.span
    assert sorted(set(np.round(effective[0], 12))) == [-1.0, 0.0, 1.0]


def test_the_ideal_case_does_not_quantise():
    cb = Crossbar(2, 2)
    assert cb.states is None
    w = np.array([[0.137, -0.42], [0.0, 0.999]])
    assert np.allclose(cb.program(w)[0] - cb.program(w)[1], w * cb.span)


# -- guards ------------------------------------------------------------------


@pytest.mark.parametrize(
    "kw",
    [
        dict(scheme="bipolar"),
        dict(g_min=3.0e-6, g_max=1.0e-6),
        dict(g_min=0.0),
        dict(states=1),
    ],
)
def test_a_nonsensical_configuration_is_refused(kw):
    with pytest.raises(ValueError):
        Crossbar(2, 2, **kw)


def test_a_weight_matrix_of_the_wrong_shape_is_refused():
    with pytest.raises(ValueError):
        Crossbar(2, 3).program(np.zeros((3, 2)))


def test_an_input_of_the_wrong_width_is_refused():
    with pytest.raises(ValueError):
        Crossbar(4, 2).encode(np.zeros((1, 5)))


# -- readout helpers ---------------------------------------------------------


def test_predict_and_accuracy():
    logits = np.array([[0.1, 0.9], [0.8, 0.2], [0.3, 0.7]])
    assert list(predict(logits)) == [1, 0, 1]
    assert accuracy(logits, [1, 0, 0]) == pytest.approx(2 / 3)
