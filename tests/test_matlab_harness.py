"""Tier 1, proven by running it: the inherited Monte Carlo harness.

Seven files came in from photonn byte-identical, verified with ``diff`` at copy
time and expected to work untouched. ``diff`` establishes what *should* work. This
is where four of them are actually executed.

The headline is ``mc.sweep``'s seed partitioning. Its own comment says it was
lifted out of the D2NN driver to stop two drivers drifting apart on how a sweep is
seeded, "which is the thing that would quietly make their tolerance tables
incomparable" -- and cross-platform comparability is the entire reason this repo
exists. Nothing checked it in either repo until now.

One ``matlab -batch`` invocation serves the whole module: startup is about 27
seconds, so a per-test invocation would put two minutes on the suite and the suite
would stop being run. See ``tests/matlab_runner.m``.
"""
from __future__ import annotations

import os
import shutil

import numpy as np
import pytest

from conftest import json_runner

HERE = os.path.dirname(os.path.abspath(__file__))

matlab = shutil.which("matlab")
pytestmark = pytest.mark.skipif(
    matlab is None, reason="matlab not on PATH; the as-built harness checks are skipped"
)


@pytest.fixture(scope="module")
def out():
    return json_runner(
        matlab, "-batch", f"cd('{HERE}'); matlab_runner", marker="<<<JSON>>>"
    )


# -- mc.validate_config ------------------------------------------------------
# The typo guard. A misspelled errorConfig field selects nothing, the run
# completes cleanly at every magnitude, and the flat curve reads as a tolerant
# design -- which for a project whose deliverable is a tolerance document is the
# worst failure available.


def test_a_valid_config_is_accepted(out):
    v = out["validate"]
    assert v["goodAccepted"], v.get("goodError", "")


def test_a_misspelled_field_is_rejected_and_the_nearest_key_suggested(out):
    v = out["validate"]
    assert v["typoRejected"], "a field no driver reads must not pass silently"
    assert v["identifier"] == "mc:validate_config:unknownField"
    assert "did you mean 'phase_sigma_rad'?" in v["message"], (
        "the suggestion is the load-bearing half: this failure is overwhelmingly "
        "a typo rather than an invention, so naming the intended key is what turns "
        "the error into a fix"
    )


def test_the_crossbar_arch_now_exists(out):
    """Replaces the guard that held the ordering until plan 04.

    Until the crossbar's parameterisation existed, ``mc.error_sources("crossbar")``
    raised, and a test here asserted that it did -- the keys are the config API and
    naming them early guarantees a rename. It now exists, so the guard becomes an
    assertion that it does. The keys themselves are checked at the seam, in
    ``test_handoff_roundtrip.py``, next to the code that reads them.
    """
    v = out["validate"]
    assert v["crossbarKnown"]
    assert "sigma_g_rel" in v["crossbarKeys"]


def test_an_unknown_architecture_is_still_rejected(out):
    """The registry is the selection mechanism, so it must not answer for anything."""
    v = out["validate"]
    assert v["unknownArchRejected"]
    assert v["archIdentifier"] == "mc:error_sources:badArch"


# -- mc.sweep ----------------------------------------------------------------


def test_sweep_partitions_seeds_as_its_own_comment_documents(out):
    """``sweep.m:5`` -- "Seeds are partitioned BASESEED + 100*i per magnitude".

    This is the property the whole comparison chapter rests on. Two drivers that
    seed differently produce tolerance tables that cannot be compared, and nothing
    about the failure announces itself: both runs complete, both look reasonable.
    """
    s = out["sweep"]
    expected = [s["baseSeed"] + 100 * i for i in range(1, s["nMag"] + 1)]
    assert s["seeds"] == expected, (
        f"seeds {s['seeds']} do not follow baseSeed + 100*i ({expected}); "
        "comparability with photonn is lost the moment this drifts"
    )


def test_no_two_magnitudes_share_a_draw(out):
    """The point of the offsets, stated as the property rather than the formula."""
    seeds = out["sweep"]["seeds"]
    assert len(set(seeds)) == len(seeds)


def test_sweep_returns_one_row_per_magnitude_and_one_column_per_realization(out):
    s = out["sweep"]
    assert s["size"] == [s["nMag"], s["nReal"]]


def test_sweep_passes_each_config_through_to_the_driver(out):
    """The stub's accuracy is a function of its config, so a mixed-up cfg shows up."""
    s = out["sweep"]
    acc = np.array(s["acc"])
    for i in range(s["nMag"]):
        expected = (i + 1) * 0.1 + np.arange(s["nReal"]) * 0.01
        assert np.allclose(acc[i], expected)


# -- mc.pack -----------------------------------------------------------------


def test_pack_produces_the_record_shape_every_source_takes(out):
    s = out["sweep"]
    assert s["packFields"] == ["magnitudes", "accMean", "accStd", "threshold"]
    assert s["packMagnitudes"] == [0.1, 0.2, 0.3, 0.4]
    assert s["packThreshold"] == 0.5


def test_pack_summarises_with_the_sample_standard_deviation(out):
    """MATLAB's ``std(acc, 0, 2)`` normalises by N-1; recomputed here rather than trusted."""
    s = out["sweep"]
    acc = np.array(s["acc"])
    assert np.allclose(s["packAccMean"], acc.mean(axis=1))
    assert np.allclose(s["packAccStd"], acc.std(axis=1, ddof=1))


# -- err.detector_noise ------------------------------------------------------
# The open Tier 1 question: it is written against per-region photon counts, and
# the crossbar's counterpart is charge at a sense amplifier. What is established
# here is that it runs and is dimensionally indifferent. Adapting it is plan 04's.


def test_detector_noise_runs_on_a_current_vector(out):
    d = out["detector"]
    assert d["size"] == [1, 4]
    assert d["allFinite"]
    assert d["nonNegative"], "a negative current out of a noise model is unphysical"


def test_detector_noise_is_reproducible_from_its_seed(out):
    d = out["detector"]
    assert d["reproducible"], "the MC driver records seeds; they have to mean something"
    assert d["seedChangesDraw"], "a seed that changes nothing is not a seed"


def test_detector_noise_stays_non_negative_with_the_adc_off(out):
    """Shot noise alone, at currents where sqrt(x) dwarfs x.

    A property of the Gaussian approximation to Poisson rather than of this repo,
    but it is the regime a crossbar sense amplifier sits in and the clamp is what
    keeps the result physical there.
    """
    d = out["detector"]
    assert d["quietNonNegative"]
    assert d["quietSize"] == [1, 4]
