"""The conversion from a tolerance edge to the series' comparison unit.

    effective bits = log2(operating range / sigma)

This is the one arithmetic every platform in the series shares, and it is the only
place where a mistake would make two correct measurements incomparable rather than
make one of them wrong. Hence its own file.

The consistency checks against ``exports/error_budget.json`` skip when the budget
has not been run, because ``exports/`` is gitignored and regenerable. They are
worth having anyway: they are what would catch the reported row drifting from the
run that produced it.
"""
from __future__ import annotations

import json
import math
import os

import numpy as np
import pytest

from apps import report_row
from apps.report_row import (
    BUDGET,
    HANDOFF,
    bits_from_sigma,
    bits_from_states,
    design_check,
)
from spinn.crossbar import Crossbar

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

budget = pytest.mark.skipif(
    not os.path.exists(BUDGET),
    reason="no error budget on disk; run spinn-hw/run_error_budget.m",
)

#: Regenerating the row needs the handoff as well as the budget -- it recomputes
#: the array read power from the weights and the test set, not just from the sweep.
row = pytest.mark.skipif(
    not (os.path.exists(BUDGET) and os.path.exists(HANDOFF)),
    reason="no budget or handoff on disk; exports/ is gitignored and regenerable",
)


# -- the unit ----------------------------------------------------------------


@pytest.mark.parametrize(
    "sigma, bits",
    [(0.5, 1.0), (0.25, 2.0), (0.0625, 4.0), (1.0 / 1024, 10.0)],
)
def test_a_sigma_of_one_over_two_to_the_n_is_n_bits(sigma, bits):
    """The definition, on values where it can be checked by eye."""
    assert bits_from_sigma(sigma) == pytest.approx(bits)


def test_the_conversion_needs_no_conductance_window():
    """Why the config key is a *relative* sigma.

    Every absolute conductance in this project is a design choice that a different
    junction would change. Quoting sigma against the window means the bit depth does
    not depend on that: the same fractional spread gives the same bits whatever
    window a junction is built to.
    """
    assert bits_from_sigma(0.035) == pytest.approx(-math.log2(0.035))


def test_the_design_check_on_the_recorded_window():
    """1 uS and 3 uS, worked by hand.

    R_AP = 1 MOhm and R_P = 333 kOhm, so TMR = (1e6 - 333.3e3) / 333.3e3 = 200%.
    At 3.4 kOhm um^2 the parallel state needs A = 3.4e3 / 333.3e3 = 1.02e-2 um^2,
    a disc 114 nm across. 0.1 V across 333.3 kOhm is 0.3 uA, which over that area
    is 0.3e-6 / 1.02e-10 cm^2 = 2.94e3 A/cm^2 -- 340 times below 1e6. And 1e6 A/cm^2
    through 3.4 kOhm um^2 is 1e10 A/m^2 * 3.4e-9 Ohm m^2 = 34 V.
    """
    d = design_check(1.0e-6, 3.0e-6, 0.1)
    assert d["r_ap"] == pytest.approx(1.0e6)
    assert d["r_p"] == pytest.approx(1.0e6 / 3)
    assert d["tmr"] == pytest.approx(2.0)
    assert d["pillar_nm"] == pytest.approx(114.0, abs=0.5)
    assert d["i_read"] == pytest.approx(0.3e-6)
    assert d["read_below_wall_motion"] == pytest.approx(340.0)
    assert d["write_through_barrier_v"] == pytest.approx(34.0)


def test_a_smaller_spread_is_more_bits():
    assert bits_from_sigma(0.01) > bits_from_sigma(0.1)


def test_a_differential_pair_is_worth_almost_a_bit_over_its_devices():
    """``2*states - 1`` effective weights, not ``states``.

    Using ``log2(states)`` would understate the scheme -- by a full bit at two
    states, which is exactly where the MTJ family sits.
    """
    assert bits_from_states(2, "differential") == pytest.approx(math.log2(3))
    assert bits_from_states(2, "offset") == pytest.approx(1.0)
    assert bits_from_states(7, "differential") == pytest.approx(math.log2(13))


def test_the_pairs_advantage_grows_towards_exactly_one_bit():
    """It approaches a bit, and is *smallest* at the bottom -- not the other way round.

    ``log2(2n-1) - log2(n)`` rises to 1 as ``n`` grows, because ``2n-1 -> 2n``.
    At two states it is only ``log2(3) - 1 = 0.585``, so the binary MTJ case gets
    the least out of the scheme -- which is worth knowing, since that is the case
    the scheme is most often argued for.
    """
    at_two = bits_from_states(2, "differential") - bits_from_states(2, "offset")
    at_many = bits_from_states(256, "differential") - bits_from_states(256, "offset")
    assert at_two == pytest.approx(math.log2(3) - 1.0)
    assert at_two < at_many < 1.0
    assert at_many == pytest.approx(1.0, abs=0.01)


# -- the power arithmetic ------------------------------------------------------


def test_array_read_power_is_the_sum_of_v_squared_g():
    """Checked against a hand-computed two-device case rather than itself."""
    from apps.report_row import array_read_power

    class _H:
        scheme = "differential"

        def crossbar(self):
            return Crossbar(2, 1, g_min=1.0e-6, g_max=3.0e-6, read_voltage=0.1)

    # weights [1, -1] -> g_pos = [3e-6, 1e-6], g_neg = [1e-6, 3e-6]
    # image [1.0, 0.5] -> V = [0.1, 0.05]
    # P = 0.01*(3e-6 + 1e-6) + 0.0025*(1e-6 + 3e-6) = 4e-8 + 1e-8 = 5e-8
    power = array_read_power(_H(), np.array([[1.0], [-1.0]]), np.array([[1.0, 0.5]]))
    assert power == pytest.approx(5.0e-8)


# -- the recorded budget --------------------------------------------------------


@pytest.fixture(scope="module")
def result():
    with open(BUDGET, encoding="utf-8") as fh:
        return json.load(fh)


@budget
def test_the_pass_mark_is_ninety_five_percent_of_ideal(result):
    """Declared before the sweeps ran; asserted here against what they used."""
    assert result["threshold"] == pytest.approx(0.95 * result["ideal"])


@budget
@pytest.mark.parametrize(
    "source", ["sigma_g_rel", "states_per_device", "wire_resistance_ohm"]
)
def test_every_source_bracketed_its_edge(result, source):
    """A ladder that never fails has found a too-narrow ladder, not an edge."""
    s = result[source]
    assert s["bracketed"], f"{source} did not bracket; widen the ladder and re-run"
    assert not math.isnan(s["lastHolding"])
    assert not math.isnan(s["firstFailing"])


@budget
@pytest.mark.parametrize(
    "source", ["sigma_g_rel", "states_per_device", "wire_resistance_ohm"]
)
def test_the_holds_flags_agree_with_the_pass_mark(result, source):
    s = result[source]
    expected = [m >= result["threshold"] for m in s["accMean"]]
    assert s["holds"] == expected


@budget
def test_the_deterministic_sources_really_have_no_spread(result):
    """Only source 1 is stochastic. A non-zero std here would mean it is not."""
    for source in ("states_per_device", "wire_resistance_ohm"):
        # Not exactly zero: MATLAB's std over identical values leaves float
        # residue around 1e-19. The claim is "no spread", not "no arithmetic".
        assert max(result[source]["accStd"]) < 1e-15


@budget
def test_the_stochastic_source_spreads_more_as_it_worsens(result):
    """A variation sweep whose spread did not grow would not be varying."""
    std = result["sigma_g_rel"]["accStd"]
    assert std[-1] > std[0] > 0


@budget
def test_conductance_variation_is_the_binding_source(result):
    """It demands more precision than the states knob, on the same window.

    Both are expressed as bits against the conductance window, so this is a
    like-for-like comparison rather than two numbers sharing a column. IR drop is
    deliberately excluded: it is a systematic, not a spread, so it has no sigma to
    take a log of.
    """
    sigma_bits = bits_from_sigma(result["sigma_g_rel"]["lastHolding"])
    state_bits = bits_from_states(
        int(result["states_per_device"]["lastHolding"]), result["scheme"]
    )
    assert sigma_bits > state_bits


@budget
def test_the_joint_run_is_not_worse_than_the_sum_of_the_independents(result):
    """Sub-additive, because accuracy saturates.

    A sample already misclassified by one source cannot be misclassified again by
    the next. Pinned so the sub-additivity is recognisable as expected rather than
    read later as evidence of something about the crossbar. A joint drop
    *exceeding* the sum would be the interesting case, and is not what happened.
    """
    assert result["joint"]["drop"] <= result["joint"]["sumOfIndependentDrops"] + 1e-12


@budget
def test_budgeting_every_source_to_its_own_edge_leaves_nothing_over(result):
    """The practical consequence, and the reason the joint run is reported at all."""
    assert not result["joint"]["holds"]
    assert result["joint"]["mean"] < result["threshold"]


# -- the committed row -------------------------------------------------------


@row
def test_the_committed_row_matches_what_report_row_produces_now():
    """The one test that compares against disk, and the reason it exists.

    ``docs/comparison_row.md`` is generated and does not look generated: it is
    prose with numbers in it, so the natural way to correct a sentence is to edit
    the file -- and the next ``python -m apps.report_row`` discards the edit without
    a word. The row is also this repository's single deliverable, published for a
    hub that refers to it rather than copying it, which makes a silently reverted
    correction the most expensive drift available here.

    The same bargain ``test_site_build.py`` and ``test_web_data.py`` make for the
    other two generated files that are committed.
    """
    path = os.path.join(REPO, "docs", "comparison_row.md")
    with open(path, encoding="utf-8", newline="") as fh:
        on_disk = fh.read()
    assert on_disk == report_row.render(), (
        "docs/comparison_row.md is not what apps.report_row.render() produces. The "
        "prose lives in apps/report_row.py; edit it there and re-run "
        "`python -m apps.report_row`."
    )
