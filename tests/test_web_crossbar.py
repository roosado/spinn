"""The browser's copy of the physics, pinned to the recorded measurement.

``apps/web/crossbar.js`` is a third implementation of arithmetic that already
exists in ``spinn/crossbar.py`` and in ``spinn-hw/+model`` plus ``spinn-hw/+err``.
A third copy is normally where you stop and extract a shared one, and that is not
available here: the seam between the two existing copies is one-directional by
design, and neither Python nor MATLAB runs in a reader's browser.

So the copy is not trusted, it is pinned. Every magnitude in
``exports/error_budget.json`` that does not involve a random draw is recomputed by
the JavaScript and compared against what MATLAB recorded -- nine quantisation
levels, nine wire resistances, and the ideal. That is the whole justification for
the widgets on the site claiming to show the real machine.

**The three-sample discrepancy is expected and is documented here rather than
tolerated silently.** At coarse quantisation the weight lattice is small enough
that some digits produce two exactly equal column currents, and which column wins
is then decided by the order the additions happened in -- MATLAB's matrix multiply
and this loop sum in different orders. Three magnitudes on the states ladder move
by exactly one sample of two thousand for that reason. It is not a difference in
the physics, and the page says so where a reader could otherwise compare two
numbers and find them one digit apart.
"""
from __future__ import annotations

import os
import shutil

import pytest

from conftest import json_runner

HERE = os.path.dirname(os.path.abspath(__file__))
RUNNER = os.path.join(HERE, "crossbar_runner.js")

node = shutil.which("node")
pytestmark = pytest.mark.skipif(node is None, reason="node not on PATH")

#: One sample of two thousand. See the module docstring: exactly the size of a
#: tie broken differently, and small enough that a real divergence in the physics
#: could not hide underneath it -- the next-smallest disagreement any of these
#: sweeps produces is thirty times larger.
ONE_SAMPLE = 1 / 2000 + 1e-12


@pytest.fixture(scope="module")
def out():
    return json_runner(node, RUNNER)


def test_the_browser_reproduces_the_ideal_accuracy_exactly(out):
    """No error source, no random draw, no tie: this one has to be to the digit.

    Against the accuracy the generated module carries rather than against
    ``exports/``, which is gitignored: the recorded 0.7345 travels into the browser
    inside ``data.js``, and ``test_web_data.py`` is what holds that value to the
    export it came from wherever the export exists.
    """
    assert out["idealComputed"] == out["ideal"]


def test_the_geometry_survived_the_crossing(out):
    assert (out["rows"], out["cols"], out["n"]) == (36, 10, 2000)


def test_every_quantisation_magnitude_matches_matlab_to_one_sample(out):
    off = [(e["magnitude"], e["computed"], e["recorded"]) for e in out["states"]
           if abs(e["computed"] - e["recorded"]) > ONE_SAMPLE]
    assert not off, f"states magnitudes off by more than one sample: {off}"


def test_the_states_ladder_is_mostly_exact(out):
    """The ties are a handful of magnitudes, not a drift across the ladder.

    If a rounding convention or an encode had actually diverged, every magnitude
    would move, not three of the coarsest.
    """
    exact = [e for e in out["states"] if e["computed"] == e["recorded"]]
    assert len(exact) >= len(out["states"]) - 3


def test_every_wire_resistance_matches_matlab_to_the_sample(out):
    """Source 3 has no random draw and no coarse lattice, so it has no excuse.

    This is the strongest single check in the file: IR drop is the one source whose
    result depends on the absolute conductance window and the read voltage, so
    reproducing all nine magnitudes says the operating point crossed into the
    browser intact as well as the arithmetic.

    Not asserted with ``==``. The recorded file carries values like
    ``0.0030000000000000005``, because MATLAB averages twenty identical
    realisations and the accumulation lands a few units in the last place off the
    exact ratio. That is a representation artefact of the mean, not a digit
    classified differently, and 1e-9 is four hundred thousand times smaller than
    the one sample in two thousand that would be.
    """
    off = [(e["magnitude"], e["computed"], e["recorded"]) for e in out["wire"]
           if abs(e["computed"] - e["recorded"]) > 1e-9]
    assert not off, f"wire magnitudes disagree: {off}"


def test_conductance_variation_lands_inside_the_recorded_spread(out):
    """A different generator, so the stream differs and the distribution must not."""
    bad = []
    for e in out["sigma"]:
        # One recorded standard deviation, plus a floor for the magnitudes where the
        # sweep's own spread is smaller than a couple of samples.
        tol = max(e["recordedStd"], 0.004)
        if abs(e["mean"] - e["recorded"]) > tol:
            bad.append((e["magnitude"], e["mean"], e["recorded"], tol))
    assert not bad, f"sigma means outside the recorded spread: {bad}"


def test_rounding_is_half_away_from_zero_not_javascripts_default(out):
    """``Math.round(-2.5)`` is -2, which is a third convention again.

    Python rounds half to even, MATLAB half away from zero, JavaScript half towards
    positive infinity. Both existing implementations agreed on away-from-zero after
    plan 04 found the disagreement; this is the third side of that seam.
    """
    assert out["rounding"] == [-3, -2, -1, 1, 2, 3]


def test_the_images_decoded_out_of_the_sparse_block(out):
    """Every sample keeps a peak of exactly one, which is what the encode assumes."""
    assert out["images"]["peakExactlyOne"] == 2000
    assert out["images"]["aboveOne"] == 0
    # About a quarter of a 6x6 digit is ink; the sparse format is only worth its
    # decoder while that stays true.
    assert 0.2 < out["images"]["nonZero"] / (2000 * 36) < 0.35


@pytest.mark.parametrize("states", ["2", "3", "5"])
def test_a_pair_reaches_twice_the_states_less_one(out, states):
    """The bug plan 04 caught, asserted on the third implementation.

    Rounding each rail independently collapses the lattice to a sign bit -- three
    values where there should be five, at twice the device count of an offset. The
    symptom is only ever a lattice with the wrong number of levels in it.
    """
    entry = out["lattice"][states]
    assert entry["reached"] == entry["expected"]
