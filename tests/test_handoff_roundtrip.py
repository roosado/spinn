"""The seam, proven by crossing it.

Python writes a handoff; MATLAB reads it back and rebuilds the array from the file
alone. The one assertion that matters is that MATLAB lands on **the same accuracy
Python recorded** -- because every way of getting this wrong produces a valid
array that simply is not the trained one:

- the weight matrix transposed (h5read reverses dimensions);
- each image flattened column-major instead of row-major, which is shape-valid
  and leaves no trace but a poorer number;
- the signed-weight scheme assumed rather than read, so an offset array is
  reconstructed as a differential one;
- ``readout_gain`` defaulted to 1.0, which does not change an argmax and so
  survives an accuracy check while corrupting every margin derived from it.

None of these raise. The accuracy comparison is the only detector, and it only
works against **trained** weights: random ones score chance either way, and the
test would pass while proving nothing. So the fixture trains briefly, and a
companion assertion checks that the transposed-input variant really does score
differently -- otherwise the headline check is passing for free.
"""
from __future__ import annotations

import os
import shutil

import numpy as np
import pytest

from apps.train_crossbar import fit_to_window, train
from conftest import json_runner
from spinn.crossbar import Crossbar, accuracy
from spinn.export import (
    OPERATING_POINT,
    SIGNED_SCHEMES,
    validate_handoff,
    write_handoff,
)
from spinn.handoff import read_handoff, read_test_set, read_weights
from spinn.task import N_CLASSES, load_shared_task, one_hot

HERE = os.path.dirname(os.path.abspath(__file__))

matlab = shutil.which("matlab")


def _operating_point(cb: Crossbar, gain: float) -> dict:
    return {
        "g_min_s": cb.g_min,
        "g_max_s": cb.g_max,
        "read_voltage_v": cb.read_voltage,
        "readout_gain": gain,
        "signed_scheme_code": SIGNED_SCHEMES[cb.scheme],
    }


@pytest.fixture(scope="module")
def trained():
    """A briefly-trained array, good enough to be sensitive to input ordering.

    Three epochs, which is nowhere near the recorded ideal accuracy and does not
    need to be: what this fixture has to provide is a weight matrix whose score
    depends on the inputs arriving in the right order.
    """
    task = load_shared_task()
    cb = Crossbar(task.n_channels, N_CLASSES)
    x = cb.encode(task.train_images) / cb.read_voltage
    y = one_hot(task.train_labels, N_CLASSES)
    raw = [w for _, _, w in train(x, y, epochs=3, lr=0.5, batch=128, seed=1)][-1]
    weights, gain = fit_to_window(raw)
    ideal = accuracy(cb.forward(task.test_images, weights), task.test_labels)
    assert ideal > 0.5, f"fixture must be well above chance to be sensitive; got {ideal}"
    return cb, weights, gain, ideal, task


@pytest.fixture(scope="module")
def handoff_path(trained, tmp_path_factory):
    cb, weights, gain, ideal, task = trained
    path = str(tmp_path_factory.mktemp("handoff") / "crossbar.h5")
    write_handoff(
        path,
        model_type="crossbar",
        parameters={"weights": weights},
        geometry={
            "n_rows": cb.n_inputs,
            "n_cols": cb.n_outputs,
            "devices_per_weight": cb.devices_per_weight,
        },
        operating_point=_operating_point(cb, gain),
        test_images=task.test_images,
        test_labels=task.test_labels,
        description="round-trip fixture",
        test_acc=ideal,
    )
    validate_handoff(path)
    return path


# -- the Python side ---------------------------------------------------------


def test_the_written_file_validates(handoff_path):
    validate_handoff(handoff_path)


def test_python_reads_back_what_it_wrote(handoff_path, trained):
    cb, weights, gain, ideal, _ = trained
    h = read_handoff(handoff_path)
    assert h.model_type == "crossbar"
    assert h.schema_version == "0.1.0"
    assert (h.n_rows, h.n_cols) == (cb.n_inputs, cb.n_outputs)
    assert h.scheme == cb.scheme
    assert h.n_devices == cb.n_devices
    assert h.test_acc == pytest.approx(ideal)
    assert h.constant("readout_gain") == pytest.approx(gain)
    assert np.allclose(read_weights(handoff_path), weights)


def test_the_handoff_alone_rebuilds_the_array(handoff_path, trained):
    """A reader must not need anything the file does not carry."""
    _, weights, _, ideal, _ = trained
    h = read_handoff(handoff_path)
    images, labels = read_test_set(handoff_path)
    rebuilt = h.crossbar()
    assert accuracy(rebuilt.forward(images, read_weights(handoff_path)), labels) == (
        pytest.approx(ideal)
    )


def test_a_missing_constant_raises_rather_than_defaulting(handoff_path):
    h = read_handoff(handoff_path)
    stripped = Handoff_without(h, "readout_gain")
    with pytest.raises(KeyError, match="readout_gain"):
        stripped.constant("readout_gain")


def Handoff_without(h, key):
    from dataclasses import replace

    return replace(h, operating_point={k: v for k, v in h.operating_point.items()
                                       if k != key})


def test_an_unknown_operating_point_key_is_refused(trained, tmp_path):
    cb, weights, gain, ideal, task = trained
    op = _operating_point(cb, gain)
    op["g_nominal_s"] = 2.0e-6
    with pytest.raises(ValueError, match="unrecognised key"):
        write_handoff(
            str(tmp_path / "bad.h5"), model_type="crossbar",
            parameters={"weights": weights},
            geometry={"n_rows": cb.n_inputs, "n_cols": cb.n_outputs,
                      "devices_per_weight": cb.devices_per_weight},
            operating_point=op, test_images=task.test_images[:4],
            test_labels=task.test_labels[:4],
        )


@pytest.mark.parametrize("dropped", sorted(OPERATING_POINT))
def test_every_required_constant_is_required(trained, tmp_path, dropped):
    """One test per manifest field, so adding a field adds its own guard."""
    cb, weights, gain, _, task = trained
    op = {k: v for k, v in _operating_point(cb, gain).items() if k != dropped}
    with pytest.raises(ValueError, match="missing"):
        write_handoff(
            str(tmp_path / "missing.h5"), model_type="crossbar",
            parameters={"weights": weights},
            geometry={"n_rows": cb.n_inputs, "n_cols": cb.n_outputs,
                      "devices_per_weight": cb.devices_per_weight},
            operating_point=op, test_images=task.test_images[:4],
            test_labels=task.test_labels[:4],
        )


def test_a_scheme_that_disagrees_with_the_device_count_is_refused(trained, tmp_path):
    """Two fields describing one fact, checked against each other at write time."""
    cb, weights, gain, _, task = trained
    with pytest.raises(ValueError, match="disagrees"):
        write_handoff(
            str(tmp_path / "mismatch.h5"), model_type="crossbar",
            parameters={"weights": weights},
            geometry={"n_rows": cb.n_inputs, "n_cols": cb.n_outputs,
                      "devices_per_weight": 1},          # says offset
            operating_point=_operating_point(cb, gain),  # says differential
            test_images=task.test_images[:4], test_labels=task.test_labels[:4],
        )


def test_weights_outside_the_window_are_refused(trained, tmp_path):
    """The failure mode that made the trainer wrong: weights that do not fit."""
    cb, weights, gain, _, task = trained
    with pytest.raises(ValueError, match=r"\[-1, 1\]"):
        write_handoff(
            str(tmp_path / "wide.h5"), model_type="crossbar",
            parameters={"weights": weights * 5.0},
            geometry={"n_rows": cb.n_inputs, "n_cols": cb.n_outputs,
                      "devices_per_weight": cb.devices_per_weight},
            operating_point=_operating_point(cb, gain),
            test_images=task.test_images[:4], test_labels=task.test_labels[:4],
        )


# -- the MATLAB side ---------------------------------------------------------

pytestmark_matlab = pytest.mark.skipif(
    matlab is None, reason="matlab not on PATH; the seam is checked from Python only"
)


@pytest.fixture(scope="module")
def crossed(handoff_path):
    if matlab is None:
        pytest.skip("matlab not on PATH")
    return json_runner(
        matlab, "-batch",
        f"cd('{HERE}'); handoff_runner('{handoff_path.replace(os.sep, '/')}')",
        marker="<<<JSON>>>",
    )


@pytestmark_matlab
def test_matlab_reads_the_geometry_and_the_scheme(crossed, trained):
    cb = trained[0]
    assert crossed["schema"] == "0.1.0"
    assert crossed["scheme"] == cb.scheme
    assert (crossed["nRows"], crossed["nCols"]) == (cb.n_inputs, cb.n_outputs)
    assert crossed["devicesPerWeight"] == cb.devices_per_weight
    assert crossed["nSamples"] == 2000


@pytestmark_matlab
def test_matlab_reproduces_the_accuracy_python_recorded(crossed):
    """The whole point of the plan.

    MATLAB rebuilds the array from the file alone -- weights, window, drive,
    scheme, gain -- and evaluates the frozen test set. Anything misread gives a
    different number here and nowhere else.
    """
    assert crossed["idealAcc"] == pytest.approx(crossed["recordedAcc"], abs=1e-12)


@pytestmark_matlab
def test_the_orientation_check_is_not_passing_for_free(crossed):
    """Flattening the images the other way must actually score differently.

    If this ever fails, the check above has stopped detecting anything: it would
    mean the array is insensitive to the order its inputs arrive in, and a
    column-major flatten would sail through.
    """
    assert crossed["transposedInputAcc"] != pytest.approx(crossed["idealAcc"], abs=1e-6)
    assert crossed["transposedInputAcc"] < crossed["idealAcc"]


# -- the config API ----------------------------------------------------------


@pytestmark_matlab
def test_the_crossbar_arch_exists_and_names_only_what_is_implemented(crossed):
    """Sources 4-7 get their keys when they get their implementations."""
    v = crossed["validate"]
    assert v["archKnown"]
    assert v["keys"] == ["sigma_g_rel", "states_per_device", "subset",
                         "wire_resistance_ohm"]


@pytestmark_matlab
def test_a_valid_crossbar_config_is_accepted(crossed):
    assert crossed["validate"]["goodAccepted"], crossed["validate"].get("goodError")


@pytestmark_matlab
def test_a_misspelled_key_is_rejected_with_the_nearest_suggestion(crossed):
    v = crossed["validate"]
    assert v["typoRejected"]
    assert v["typoIdentifier"] == "mc:validate_config:unknownField"
    assert "did you mean 'sigma_g_rel'?" in v["typoMessage"]


@pytestmark_matlab
def test_an_optical_key_is_not_accepted_by_the_crossbar_arch(crossed):
    """The harness is shared; the registries are not."""
    assert crossed["validate"]["opticalKeyRejected"]


@pytestmark_matlab
def test_every_key_catches_its_own_typo(crossed):
    """One key at a time, because one passing check does not cover three keys.

    A key present in the registry but misspelled in the ``+err`` function that
    reads it would sail through a single-key test. Each real key gets a plausible
    typo, and each must be both rejected and traced back to the key it meant.
    """
    v = crossed["validate"]
    assert v["eachTypoCaught"]
    assert v["eachTypoSuggests"]


# -- the error sources -------------------------------------------------------


@pytestmark_matlab
def test_conductance_variation_degrades_and_is_reproducible(crossed):
    s = crossed["sources"]
    assert s["variationAcc"] < s["ideal"], "a source wired up but not reaching the model"
    assert s["variationReproducible"], "seeds are recorded; they must mean something"
    assert s["variationSeedMatters"]
    assert s["variationStaysInWindow"], "a device cannot be programmed outside its states"


@pytestmark_matlab
def test_two_state_devices_still_give_three_effective_weights(crossed):
    """The differential pair resolving finer than either device, over the seam.

    This is the test that caught the modelling error. Rounding each rail
    independently gives a lattice of ``{-1, +1}`` -- a sign bit at twice the device
    count of an offset -- and the only symptom is this count coming back as two.
    """
    s = crossed["sources"]
    assert s["twoStateLevels"] == 2, "each device holds two states"
    assert s["latticeSize"] == 3, "their difference reaches three: -1, 0, +1"
    assert s["twoStateEffectiveWeights"] == 3, (
        "and the trained matrix actually uses all three; two would mean the pair "
        "had collapsed to a sign bit"
    )
    assert s["twoStateAcc"] < s["ideal"]


@pytestmark_matlab
def test_ir_drop_at_zero_resistance_is_exactly_the_ideal_sum(crossed):
    """Proves the override path is the same arithmetic, not a parallel one."""
    assert crossed["sources"]["irZeroMatchesIdeal"]


@pytestmark_matlab
def test_ir_drop_degrades_at_a_large_wire_resistance(crossed):
    s = crossed["sources"]
    assert s["irDropAcc"] < s["ideal"]


# -- the driver --------------------------------------------------------------


@pytestmark_matlab
def test_the_driver_satisfies_the_sweep_contract(crossed):
    sw = crossed["sweep"]
    assert sw["size"] == [3, 4], "one row per magnitude, one column per realization"
    assert sw["packFields"] == ["magnitudes", "accMean", "accStd", "threshold"]
    assert sw["packAccMean"] == pytest.approx(sw["meanByMagnitude"])


@pytestmark_matlab
def test_accuracy_falls_as_the_conductance_spread_grows(crossed):
    assert crossed["sweep"]["monotonic"], crossed["sweep"]["meanByMagnitude"]


@pytestmark_matlab
def test_a_sources_draw_does_not_depend_on_what_else_is_active(crossed):
    """The property the per-source seed offsets exist for.

    Plan 05 proposed checking this through "a joint run is the sum of the
    independent ones". That turns out to be the wrong instrument: accuracy
    saturates, so drops are sub-additive even when the seeding is perfect, and a
    sum-check would fail for reasons that have nothing to do with seeding.

    Tested directly instead. The same seed must produce the same perturbation
    whatever base conductances it is applied to -- otherwise a joint configuration
    is compared against draws the independent runs never saw.
    """
    sw = crossed["sweep"]
    assert sw["drawComparedCount"] > 100, "too few unclamped devices to conclude"
    assert sw["drawIndependentOfBase"]


@pytestmark_matlab
def test_a_deterministic_only_configuration_has_no_spread(crossed):
    """Correct, not broken: only source 1 is stochastic today.

    Pinned so that a zero standard deviation in a recorded budget is recognisable
    as the expected result rather than as a run that failed to vary.
    """
    sw = crossed["sweep"]
    assert sw["deterministicStd"] == 0.0
    assert sw["deterministicSeeds"] == [1, 2, 3], "seeds still advance per realization"
