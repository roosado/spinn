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
    DELIVERED_LEVELS,
    DELIVERED_LEVELS_TWO_PILLAR,
    DELIVERED_SIGMA_AREA,
    HANDOFF,
    IMEC_HEADLINE,
    IMEC_LEVEL_LABELS,
    IMEC_LEVELS_US,
    IMEC_P_SW_MEAN,
    IMEC_P_SW_MEDIANS,
    IMEC_SIGMA_MU,
    MEASURED_RATIOS,
    RATIO_BUDGETS,
    SCALE_BUDGET,
    SCALE_NPZ,
    WRITE_ATTEMPTS,
    WRITE_FAIL_BEST,
    WRITE_FAIL_WORST,
    attempts_monotone,
    attempts_verdicts,
    bits_from_sigma,
    bits_from_states,
    design_check,
    fewest_attempts,
    level_verdict,
    margin,
    rounds_to_zero,
    verdict_runs,
    write_bracket,
    write_edge_cells,
    write_edge_phrase,
    write_verdict_text,
)
from spinn.crossbar import Crossbar

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

budget = pytest.mark.skipif(
    not os.path.exists(BUDGET),
    reason="no error budget on disk; run spinn-hw/run_error_budget.m",
)



def _has_writes(path: str) -> bool:
    """Whether a budget on disk carries the write source -- older ones do not."""
    try:
        with open(path, encoding="utf-8") as fh:
            return "write_error_rate" in json.load(fh)
    except (OSError, ValueError):
        return False


#: Regenerating the row needs the handoff as well as the budget -- it recomputes
#: the array read power from the weights and the test set, not just from the sweep --
#: and, for the section on delivered levels, the calibrated variant and the write source
#: in both budgets.
row = pytest.mark.skipif(
    not (os.path.exists(HANDOFF) and os.path.exists(SCALE_NPZ)
         and _has_writes(BUDGET) and _has_writes(SCALE_BUDGET)),
    reason="no budget, handoff or calibrated variant with the write source on disk; "
           "exports/ is gitignored and regenerable",
)

#: The calibrated variant's budget, for the tests that read it.
variant = pytest.mark.skipif(
    not _has_writes(SCALE_BUDGET),
    reason=f"no calibrated variant with the write source at {SCALE_BUDGET}; run "
           f"apps.train_crossbar --calibrate-states {DELIVERED_LEVELS} and "
           "spinn-hw/run_error_budget.m",
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


# -- the margin rule -----------------------------------------------------------


def _ladder(mags, accs, threshold=0.7):
    holds = [a >= threshold for a in accs]
    last = max((i for i, h in enumerate(holds) if h), default=None)
    first = min((i for i, h in enumerate(holds) if not h), default=None)
    return {"magnitudes": mags, "accMean": accs, "holds": holds,
            "lastHolding": mags[last] if last is not None else float("nan"),
            "firstFailing": mags[first] if first is not None else float("nan")}


MAGS = [0.01, 0.02, 0.031, 0.035, 0.05, 0.063, 0.075]


def test_the_margin_holds_when_the_worse_end_of_the_bracket_holds():
    """And the margin is itself a bracket, because the edge is only between two rungs.

    Worse end 0.063 holds, the edge is between 0.075 (holds) and nothing: here the
    ladder fails at 0.075, so the edge lies between 0.063 and 0.075 and the margin is
    between log2(0.063/0.063) = 0 and log2(0.075/0.063) = 0.25 bits.
    """
    m = margin(_ladder(MAGS, [.75, .74, .73, .72, .71, .705, .69]), (0.031, 0.063))
    assert m["verdict"] == "holds"
    assert m["bits"] == pytest.approx((0.0, math.log2(0.075 / 0.063)))


def test_an_edge_beyond_the_ladder_leaves_the_margin_open_above():
    """Holding at every rung is a lower bound, not an edge -- and MATLAB writes it as null.

    ``jsonencode`` turns the NaN of "never failed" into ``null``, which arrives here as
    ``None``. The margin is then at least ``log2(top / worse end)`` and has no upper end.
    """
    s = _ladder(MAGS, [.75] * 7)
    s["firstFailing"] = None
    m = margin(s, (0.031, 0.063))
    assert m["verdict"] == "holds"
    assert m["bits"] == (pytest.approx(math.log2(0.075 / 0.063)), math.inf)


def test_the_margin_fails_when_the_better_end_fails():
    """Short by up to log2(0.031 / 0.02) bits: the edge is between 0.02 and 0.031."""
    m = margin(_ladder(MAGS, [.75, .71, .69, .68, .66, .64, .62]), (0.031, 0.063))
    assert m["verdict"] == "fails"
    assert m["short_bits"] == pytest.approx((0.0, math.log2(0.031 / 0.02)))


def test_the_margin_is_undetermined_when_the_bracket_straddles_the_edge():
    m = margin(_ladder(MAGS, [.75, .74, .73, .72, .71, .69, .68]), (0.031, 0.063))
    assert m["verdict"] == "undetermined"
    assert "bits" not in m and "short_bits" not in m


def test_a_delivered_end_off_the_ladder_is_refused_rather_than_interpolated():
    """The whole point of putting both ends on the ladder."""
    with pytest.raises(ValueError, match="not on the ladder"):
        margin(_ladder(MAGS, [.75] * 7), (0.031, 0.06))


def test_a_ladder_that_holds_at_the_worse_end_but_not_the_better_is_refused():
    with pytest.raises(ValueError, match="not monotone"):
        margin(_ladder(MAGS, [.75, .74, .69, .72, .71, .705, .69]), (0.031, 0.063))


def test_the_delivered_bracket_is_the_envelope_of_both_measured_sizes():
    """imec's two electrical CDs either side of this design's 114 nm pillar."""
    assert sorted(IMEC_SIGMA_MU) == [90, 127]
    every = [v for row in IMEC_SIGMA_MU.values() for v in row]
    assert DELIVERED_SIGMA_AREA == (min(every), max(every)) == (0.031, 0.063)
    assert 90 < design_check(1.0e-6, 3.0e-6, 0.1)["pillar_nm"] < 127


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
    "source", ["sigma_g_rel", "sigma_area_rel", "states_per_device", "wire_resistance_ohm"]
)
def test_every_source_bracketed_its_edge(result, source):
    """A ladder that never fails has found a too-narrow ladder, not an edge."""
    s = result[source]
    assert s["bracketed"], f"{source} did not bracket; widen the ladder and re-run"
    assert not math.isnan(s["lastHolding"])
    assert not math.isnan(s["firstFailing"])


@budget
@pytest.mark.parametrize(
    "source", ["sigma_g_rel", "sigma_area_rel", "states_per_device", "wire_resistance_ohm"]
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
    for source in ("sigma_g_rel", "sigma_area_rel"):
        std = result[source]["accStd"]
        assert std[-1] > std[0] > 0, source


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


@budget
def test_the_delivered_bracket_is_on_every_area_ladder(result):
    """Read off ladder points, as declared -- the design's run and both variants."""
    ladders = [result["sigma_area_rel"]["magnitudes"]]
    for path in RATIO_BUDGETS.values():
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                ladders.append(json.load(fh)["sigma_area_rel"]["magnitudes"])
    for mags in ladders:
        for end in DELIVERED_SIGMA_AREA:
            assert any(math.isclose(m, end) for m in mags), (end, mags)


@pytest.mark.parametrize(
    "m, bracket",
    [
        (1, (0.389, 0.495)),
        (2, (0.151321, 0.245025)),
        (3, (0.058864, 0.121287)),
        (4, (0.022898, 0.060037)),
        (5, (0.008907, 0.029718)),
        (6, (0.003465, 0.014711)),
    ],
)
def test_the_write_bracket_after_m_attempts_is_the_declared_one(m, bracket):
    """``[0.389^m, 0.495^m]``, to six places, as declared in docs/history.md (2026-10-06).

    Hard-coded, so a change to either constant or to the rounding is a failure here
    rather than a ladder that quietly moves.
    """
    assert write_bracket(m) == bracket
    assert m in WRITE_ATTEMPTS


def test_the_write_attempts_are_one_to_six():
    assert list(WRITE_ATTEMPTS) == [1, 2, 3, 4, 5, 6]


# -- delivered levels and write errors -----------------------------------------------

#: The row's states ladder, descending, and a write ladder built as the declared one is:
#: the eight round rates and both ends of every bracket.
STATES = [65, 33, 17, 9, 7, 5, 4, 3, 2]
RATES = sorted({1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2, 0.1, 0.3}
               | {e for m in WRITE_ATTEMPTS for e in write_bracket(m)})


def _writes(slope=0.5, base=0.75, threshold=0.69):
    """A write ladder whose accuracy falls linearly with the rate, holds to ~0.1."""
    return _ladder(RATES, [base - slope * r for r in RATES], threshold)


def test_a_delivered_level_count_that_holds_is_read_off_its_rung():
    s = _ladder(STATES, [.735, .735, .72, .72, .701, .66, .63, .50, .42], 0.6978)
    v = level_verdict(s, 7)
    assert v == {"levels": 7, "acc": .701, "verdict": "holds"}


def test_a_delivered_level_count_that_fails_is_read_off_its_rung():
    s = _ladder(STATES, [.735, .735, .72, .72, .701, .66, .63, .50, .42], 0.6978)
    assert level_verdict(s, 5) == {"levels": 5, "acc": .66, "verdict": "fails"}
    assert level_verdict(s, 3)["verdict"] == "fails"


def test_a_level_count_off_the_states_ladder_is_refused_rather_than_interpolated():
    s = _ladder(STATES, [.7] * 9, 0.6)
    with pytest.raises(ValueError, match="not on the states ladder"):
        level_verdict(s, 6)


def test_a_level_count_is_never_undetermined():
    """A count is one rung, so there is no bracket for it to straddle."""
    s = _ladder(STATES, [.735, .735, .72, .72, .701, .66, .63, .50, .42], 0.6978)
    assert {level_verdict(s, n)["verdict"] for n in STATES} <= {"holds", "fails"}


def test_the_attempts_are_judged_by_the_declared_rule_at_each_bracket():
    """Holds to 0.1, so m=3 straddles it: its better end holds and its worse end does not."""
    av = attempts_verdicts(_writes())
    assert [v["m"] for v in av] == list(WRITE_ATTEMPTS)
    assert [v["bracket"] for v in av] == [write_bracket(m) for m in WRITE_ATTEMPTS]
    assert [v["verdict"] for v in av] == [
        "fails", "fails", "undetermined", "holds", "holds", "holds"]
    assert av[3]["at_best"] == pytest.approx(0.75 - 0.5 * 0.022898)
    assert av[3]["at_worst"] == pytest.approx(0.75 - 0.5 * 0.060037)


def test_attempts_are_refused_on_a_ladder_that_lacks_a_bracket_end():
    """Both ends have to be rungs, or the verdict would be an interpolation."""
    mags = [r for r in RATES if r != 0.058864]
    with pytest.raises(ValueError, match="not on the ladder"):
        attempts_verdicts(_ladder(mags, [0.75 - 0.5 * r for r in mags], 0.69))


def test_attempts_survive_an_edge_beyond_the_ladder():
    """MATLAB writes "holds at every rung" as a null failing edge; every m then holds."""
    s = _ladder(RATES, [0.9] * len(RATES), 0.69)
    s["firstFailing"] = None
    av = attempts_verdicts(s)
    assert {v["verdict"] for v in av} == {"holds"}
    assert all(math.isinf(v["bits"][1]) for v in av)


def test_the_fewest_attempts_that_hold_is_the_first_that_does():
    av = attempts_verdicts(_writes())
    assert fewest_attempts(av) == 4
    assert attempts_monotone(av)


def test_no_attempts_that_hold_is_none_and_is_not_a_contradiction():
    av = attempts_verdicts(_writes(base=0.5))
    assert fewest_attempts(av) is None
    assert attempts_monotone(av)


def test_a_larger_number_of_attempts_that_stops_holding_is_flagged():
    """More attempts leave a smaller rate, so this is noise, and it must show."""
    verdicts = [{"m": 1, "verdict": "fails"}, {"m": 2, "verdict": "holds"},
                {"m": 3, "verdict": "undetermined"}, {"m": 4, "verdict": "holds"}]
    assert fewest_attempts(verdicts) == 2
    assert not attempts_monotone(verdicts)


def test_the_verdicts_by_attempts_collapse_into_runs():
    assert verdict_runs(attempts_verdicts(_writes())) == (
        "fails at m = 1–2, is undetermined at m = 3, holds at m = 4–6")
    assert verdict_runs([{"m": 1, "verdict": "holds"}]) == "holds at m = 1"


@pytest.mark.parametrize("name", ["holds", "fails", "undetermined"])
def test_a_write_verdict_is_a_word_and_never_bits(name):
    assert write_verdict_text(name) == f"**{name}**"
    assert write_verdict_text({"verdict": name, "bits": (1.0, 2.0)}) == f"**{name}**"


def test_a_write_verdict_that_is_not_a_verdict_is_refused():
    with pytest.raises(ValueError, match="not a verdict"):
        write_verdict_text("passes")


def test_a_write_ladders_edges_become_table_cells_with_their_accuracies():
    holds, fails = write_edge_cells(_writes())
    assert holds == f"r = 0.1 ({0.75 - 0.05:.4f})"
    assert fails == f"r = 0.121287 ({0.75 - 0.5 * 0.121287:.4f})"
    assert write_edge_phrase(_writes()) == "holds at r = 0.1 and fails at r = 0.121287"


def test_a_write_edge_beyond_the_ladder_is_said_as_edge_text_says_it():
    never_fails = _ladder(RATES, [0.9] * len(RATES), 0.69)
    never_fails["firstFailing"] = None
    holds, fails = write_edge_cells(never_fails)
    assert holds.startswith(f"r = {RATES[-1]:g} (")
    assert fails == f"holds at every rung to {RATES[-1]:g}"
    assert write_edge_phrase(never_fails) == f"holds at every rung to {RATES[-1]:g}"

    never_holds = _ladder(RATES, [0.5] * len(RATES), 0.69)
    never_holds["lastHolding"] = None
    holds, fails = write_edge_cells(never_holds)
    assert holds == "—"
    assert fails.startswith(f"fails at every rung from {RATES[0]:g} (")
    assert write_edge_phrase(never_holds) == f"fails at every rung from {RATES[0]:g}"


def test_a_weight_rounds_to_zero_strictly_below_half_a_step():
    """At five levels the step is 1/4, so half of it is 0.125 -- and 0.125 rounds up.

    Round half away from zero, as the array does, so the boundary weight is not zero.
    Checked against the array's own quantiser rather than against the formula.
    """
    w = np.array([[0.124, 0.125], [-0.1, 0.5], [-0.126, 0.0]])
    assert rounds_to_zero(w, 5) == (3, 6)
    q = Crossbar(3, 2, states=5).quantise_weights(w)
    assert int(np.sum(q == 0)) == 3


def test_the_pillar_counts_set_the_levels_and_the_pair_doubles_them_less_one():
    assert DELIVERED_LEVELS == len(IMEC_LEVELS_US) == len(IMEC_LEVEL_LABELS) == 5
    assert DELIVERED_LEVELS_TWO_PILLAR == 3
    assert Crossbar(1, 1, states=DELIVERED_LEVELS).representable_weights == 9


def test_imecs_five_levels_are_evenly_spaced_to_a_few_percent():
    """Why ``program()``'s even lattice is the paper's: the steps differ by under 4%."""
    g = np.array(IMEC_LEVELS_US)
    steps = np.diff(g)
    assert np.all(steps > 0)
    assert np.max(np.abs(steps / steps.mean() - 1.0)) < 0.04


def test_the_write_constants_are_one_minus_the_best_and_worst_intermediate_medians():
    """The two numbers the ladder is built from come from Fig. 11(a), not from each other."""
    inner = [p for k, p in IMEC_P_SW_MEDIANS.items() if k not in ("G1", "G5")]
    assert round(1.0 - max(inner), 6) == WRITE_FAIL_BEST
    assert round(1.0 - min(inner), 6) == WRITE_FAIL_WORST
    assert IMEC_P_SW_MEDIANS["G5"] == 1.0


def test_imecs_headline_is_a_mean_that_five_attempts_do_not_quite_reach():
    """(1 - 0.74)^5 is 1.19e-3: 1e-3 is strictly first met at six attempts."""
    n, rate = IMEC_HEADLINE
    assert (1.0 - IMEC_P_SW_MEAN) ** n == pytest.approx(1.19e-3, rel=0.01)
    assert (1.0 - IMEC_P_SW_MEAN) ** n > rate > (1.0 - IMEC_P_SW_MEAN) ** (n + 1)


def test_the_calibrated_variant_lives_under_its_own_directory():
    assert os.path.dirname(SCALE_BUDGET) == os.path.dirname(SCALE_NPZ)
    assert os.path.basename(os.path.dirname(SCALE_BUDGET)) == f"s{DELIVERED_LEVELS}"


def test_a_missing_calibrated_variant_is_refused_rather_than_left_out(monkeypatch, tmp_path):
    """The section is built on it; a document without it would look complete."""
    monkeypatch.setattr(report_row, "SCALE_BUDGET", str(tmp_path / "error_budget.json"))
    with pytest.raises(FileNotFoundError, match="calibrated variant"):
        report_row.load_scale()


def test_a_calibrated_budget_that_predates_the_write_source_is_refused(monkeypatch, tmp_path):
    path = tmp_path / "error_budget.json"
    path.write_text(json.dumps({"states_per_device": {}}), encoding="utf-8")
    npz = tmp_path / "crossbar_ideal.npz"
    np.savez(npz, calibrated_states=DELIVERED_LEVELS)
    monkeypatch.setattr(report_row, "SCALE_BUDGET", str(path))
    monkeypatch.setattr(report_row, "SCALE_NPZ", str(npz))
    with pytest.raises(KeyError, match="write_error_rate"):
        report_row.load_scale()


@budget
def test_the_write_bracket_is_on_the_write_ladder(result):
    """Both ends of every bracket are rungs, to the bit: read off, not interpolated.

    Exact float equality, not isclose. The ladder is built from the same two constants
    on each side, rounded to six places, so it either agrees to the bit or the two
    sides have drifted apart.
    """
    if "write_error_rate" not in result:
        pytest.skip("this budget predates the write source; re-run spinn-hw/run_error_budget.m")
    mags = result["write_error_rate"]["magnitudes"]
    assert mags == sorted(set(mags))
    for m in WRITE_ATTEMPTS:
        for end in write_bracket(m):
            assert end in mags, (m, end, mags)


@budget
def test_the_row_ran_its_write_source_at_the_fewest_states_it_holds_at(result):
    """Said in the row, so checked here: that is where the write source ran."""
    if "write_error_rate" not in result:
        pytest.skip("this budget predates the write source; re-run spinn-hw/run_error_budget.m")
    assert result["write_error_rate"]["states"] == result["states_per_device"]["lastHolding"]
    assert result["write_error_rate"]["threshold"] == result["threshold"]


@pytest.fixture(scope="module")
def scale():
    with open(SCALE_BUDGET, encoding="utf-8") as fh:
        return json.load(fh)


@budget
@variant
def test_the_calibrated_variant_is_judged_against_the_rows_own_pass_mark(result, scale):
    """The question is whether five levels carry this task to the row's standard."""
    assert scale["threshold"] == result["threshold"]
    assert scale["ownPassMark"] == pytest.approx(0.95 * scale["ideal"])
    assert scale["write_error_rate"]["threshold"] == result["threshold"]


@variant
def test_the_calibrated_variant_carries_only_the_two_sources_it_was_run_for(scale):
    assert {"states_per_device", "write_error_rate"} <= set(scale)
    assert not {"sigma_g_rel", "sigma_area_rel", "wire_resistance_ohm", "joint"} & set(scale)


@variant
def test_the_calibrated_variant_wrote_at_the_delivered_five_levels(scale):
    assert scale["write_error_rate"]["states"] == DELIVERED_LEVELS


@variant
def test_every_write_bracket_end_is_on_the_calibrated_variants_ladder(scale):
    mags = scale["write_error_rate"]["magnitudes"]
    for m in WRITE_ATTEMPTS:
        for end in write_bracket(m):
            assert end in mags, (m, end)


@variant
def test_both_delivered_level_counts_are_rungs_of_the_calibrated_states_ladder(scale):
    for n in (DELIVERED_LEVELS, DELIVERED_LEVELS_TWO_PILLAR):
        assert level_verdict(scale["states_per_device"], n)["levels"] == n


@variant
def test_the_variants_ideal_file_says_what_it_was_calibrated_for(scale):
    with np.load(SCALE_NPZ) as z:
        assert int(z["calibrated_states"]) == DELIVERED_LEVELS
        assert 0.0 < float(z["scale_c"]) <= 1.0
        assert float(z["ideal_accuracy"]) == scale["ideal"]
        assert float(np.abs(z["weights"]).max()) == pytest.approx(1.0)


@budget
@pytest.mark.parametrize("ratio", sorted(MEASURED_RATIOS))
def test_a_ratio_variant_is_the_same_array_in_another_window(result, ratio):
    """Same ideal, same pass mark, and the area source alone.

    The budget's own guard already refused to run if MATLAB could not rebuild the
    handoff's ideal; this checks the variant is the row's array and not another one,
    and that it carries no number nobody asked for.
    """
    path = RATIO_BUDGETS[ratio]
    if not os.path.exists(path):
        pytest.skip(f"no budget at {path}; exports/ is gitignored")
    with open(path, encoding="utf-8") as fh:
        variant = json.load(fh)
    assert variant["ideal"] == result["ideal"]
    assert variant["threshold"] == result["threshold"]
    assert "sigma_area_rel" in variant
    assert not {"sigma_g_rel", "states_per_device", "wire_resistance_ohm", "joint"} & set(variant)


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
