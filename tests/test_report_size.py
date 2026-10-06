"""The array-size sweep, and the one place its conclusions can be checked against disk.

Two kinds of test here. The first are arithmetic on the report's own logic -- the
ladder, the bracket in size -- and need nothing on disk. The second compare the recorded
budgets at every size to the properties the sweep was declared to have; those skip when
``exports/size/`` is absent, because ``exports/`` is gitignored and regenerable, the same
bargain ``test_report_row.py`` makes.

What is *not* asserted anywhere is a value the sweep produced. The edges are results, not
requirements. What is asserted is that they were produced by the protocol that was
declared before the run.
"""
from __future__ import annotations

import json
import math
import os

import pytest

from apps import report_size
from apps.report_row import (
    DELIVERED_LEVELS,
    DELIVERED_LEVELS_TWO_PILLAR,
    DELIVERED_SIGMA_AREA,
    WRITE_ATTEMPTS,
    write_bracket,
)
from apps.report_size import (
    CITED_OHM,
    GRIDS,
    OUT,
    WIRE_LADDER,
    _path,
    at,
    bracket_in_size,
    delivered_at,
    fewest_text,
)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROW_BUDGET = os.path.join(REPO, "exports", "error_budget.json")

sizes_on_disk = pytest.mark.skipif(
    not all(os.path.exists(_path(g, "error_budget.json")) and
            os.path.exists(_path(g, "crossbar_handoff.h5")) for g in GRIDS),
    reason="no size sweep on disk; run apps.train_crossbar --grid g and "
           "spinn-hw/run_size_sweep.m (exports/ is gitignored)",
)


def _sizes_have_writes() -> bool:
    """Whether every size's budget on disk carries the write source -- older ones do not."""
    try:
        for g in GRIDS:
            with open(_path(g, "error_budget.json"), encoding="utf-8") as fh:
                if "write_error_rate" not in json.load(fh):
                    return False
    except (OSError, ValueError):
        return False
    return True


#: The tests that read the write source at every size skip, with the reason, on budgets
#: recorded before it existed.
writes_on_disk = pytest.mark.skipif(
    not _sizes_have_writes(),
    reason="the size budgets on disk predate the write source; re-run "
           "spinn-hw/run_size_sweep.m (exports/ is gitignored)",
)


# -- the ladder ----------------------------------------------------------------


def test_the_ladder_contains_both_cited_wire_values_exactly():
    """That is what makes "does cited wiring hold at this size" a ladder point.

    If either were off the ladder the size limit would be read off an interpolation,
    which is the one thing the sweep declared it would not do.
    """
    for ohm in CITED_OHM:
        assert any(math.isclose(m, ohm, rel_tol=1e-12) for m in WIRE_LADDER), ohm


def test_the_ladder_is_fifteen_magnitudes_a_third_of_a_decade_apart():
    assert len(WIRE_LADDER) == 15
    assert WIRE_LADDER[0] == pytest.approx(0.02)
    assert WIRE_LADDER[-1] == pytest.approx(928.3, abs=0.1)
    for a, b in zip(WIRE_LADDER, WIRE_LADDER[1:]):
        assert b / a == pytest.approx(10.0 ** (1.0 / 3.0))


def test_the_cited_values_are_the_two_the_row_cites():
    assert CITED_OHM == (2.0, 20.0)


def test_at_reads_a_ladder_point_and_refuses_one_that_is_not_there():
    mags, vals = [1.0, 2.0, 20.0], [0.9, 0.8, 0.5]
    assert at(mags, vals, 20.0) == 0.5
    with pytest.raises(KeyError, match="not on the ladder"):
        at(mags, vals, 3.0)


def test_at_survives_matlab_writing_a_one_element_array_as_a_scalar():
    assert at(2.0, 0.8, 2.0) == 0.8


# -- the bracket in size ---------------------------------------------------------

SIZES = [36, 64, 144, 324, 676]


def test_a_bracket_is_the_last_size_that_holds_and_the_first_that_fails():
    br = bracket_in_size(SIZES, [True, True, True, False, False])
    assert (br["status"], br["last"], br["first_fail"]) == ("bracket", 144, 324)
    assert br["monotone"]


def test_holding_everywhere_is_no_edge_and_is_said_to_be_the_range():
    """Not a result: a property of how far the sweep went."""
    br = bracket_in_size(SIZES, [True] * 5)
    assert br["status"] == "holds_everywhere"
    assert br["first_fail"] is None and br["last"] == 676


def test_failing_at_the_smallest_size_is_no_edge_either():
    br = bracket_in_size(SIZES, [False, False, False, False, False])
    assert br["status"] == "fails_everywhere"
    assert br["last"] is None and br["first_fail"] == 36


def test_holding_again_after_failing_is_flagged_and_the_first_failure_is_kept():
    br = bracket_in_size(SIZES, [True, True, False, True, False])
    assert (br["last"], br["first_fail"]) == (64, 144)
    assert not br["monotone"], "the bracket is real but the range must not read as monotone"


# -- delivered levels and write errors --------------------------------------------------

STATES = [65, 33, 17, 9, 7, 5, 4, 3, 2]
RATES = sorted({1e-4, 3e-4, 1e-3, 3e-3, 1e-2, 3e-2, 0.1, 0.3}
               | {e for m in WRITE_ATTEMPTS for e in write_bracket(m)})


def _sweep(mags, accs, threshold):
    holds = [a >= threshold for a in accs]
    last = max((i for i, h in enumerate(holds) if h), default=None)
    first = min((i for i, h in enumerate(holds) if not h), default=None)
    return {"magnitudes": mags, "accMean": accs, "holds": holds,
            "lastHolding": None if last is None else mags[last],
            "firstFailing": None if first is None else mags[first]}


def _size(five_acc, three_acc, write_accs, rows=144, states=DELIVERED_LEVELS, threshold=0.8):
    """A size's budget as far as delivered_at reads it."""
    accs = [0.9] * 5 + [five_acc, 0.5, three_acc, 0.4]
    write = _sweep(RATES, write_accs, threshold)
    write["states"] = states
    return {"rows": rows, "states_per_device": _sweep(STATES, accs, threshold),
            "write_error_rate": write}


def test_where_five_levels_fail_no_attempts_are_judged():
    """The array fails before a write can matter, so there is nothing to bracket."""
    x = delivered_at(_size(0.7, 0.5, [0.7] * len(RATES), rows=36))
    assert x["five"]["verdict"] == "fails" and x["three"]["verdict"] == "fails"
    assert x["writes"] is None and x["fewest"] is None


def test_where_five_levels_hold_the_write_ladder_is_read_for_its_edge_and_its_attempts():
    accs = [0.9 - 0.5 * r for r in RATES]          # holds while 0.9 - 0.5r >= 0.8: r <= 0.2
    x = delivered_at(_size(0.85, 0.5, accs))
    assert x["five"]["verdict"] == "holds" and x["three"]["verdict"] == "fails"
    assert x["writes"] == "0.151321 → 0.245025"
    assert x["fewest"] == 3 and x["monotone"]
    assert fewest_text(x) == "3"


def test_a_write_ladder_that_never_fails_is_said_to_run_off_its_end():
    x = delivered_at(_size(0.85, 0.5, [0.9] * len(RATES), rows=676))
    assert x["writes"] == "holds at every rung to 0.495"
    assert x["fewest"] == 1


def test_no_attempts_that_hold_is_reported_as_none_up_to_the_most_tried():
    x = delivered_at(_size(0.85, 0.5, [0.79] * len(RATES)))
    assert x["fewest"] is None
    assert fewest_text(x) == f"none up to {max(WRITE_ATTEMPTS)}"


def test_a_count_off_the_states_ladder_is_refused_at_a_size_too():
    b = _size(0.85, 0.5, [0.9] * len(RATES))
    b["states_per_device"] = _sweep([65, 33, 17, 9, 7, 4, 2], [0.9] * 7, 0.8)
    with pytest.raises(ValueError, match="not on the states ladder"):
        delivered_at(b)


def test_a_write_source_run_at_another_state_count_is_refused():
    with pytest.raises(ValueError, match="not the 5"):
        delivered_at(_size(0.85, 0.5, [0.9] * len(RATES), states=7))


def test_a_size_budget_that_predates_the_write_source_is_refused():
    b = _size(0.85, 0.5, [0.9] * len(RATES))
    del b["write_error_rate"]
    with pytest.raises(KeyError, match="write_error_rate"):
        delivered_at(b)


# -- the recorded budgets ----------------------------------------------------------


@pytest.fixture(scope="module")
def budgets():
    out = {}
    for g in GRIDS:
        with open(_path(g, "error_budget.json"), encoding="utf-8") as fh:
            out[g] = json.load(fh)
    return out


@sizes_on_disk
def test_every_size_is_the_array_it_was_declared_to_be(budgets):
    for g, b in budgets.items():
        assert (b["nRows"], b["nCols"]) == (g * g, 10)
        assert b["nDevices"] == g * g * 10 * 2, "differential pairs"
        assert b["grid"] == g


@sizes_on_disk
def test_every_pass_mark_is_ninety_five_percent_of_that_sizes_own_ideal(budgets):
    """Declared before the run: no size is graded on another's curve."""
    for b in budgets.values():
        assert b["threshold"] == pytest.approx(0.95 * b["ideal"])


@sizes_on_disk
def test_the_seeds_are_the_rows_at_every_size(budgets):
    assert {b["baseSeed"] for b in budgets.values()} == {20260908}


@sizes_on_disk
def test_the_wire_ladder_in_the_json_is_the_one_declared(budgets):
    """MATLAB builds ``2*10.^(k/3)``; Python declares the same. They must agree."""
    for b in budgets.values():
        got = b["wire_resistance_ohm"]["magnitudes"]
        assert len(got) == len(WIRE_LADDER)
        for m, want in zip(got, WIRE_LADDER):
            assert m == pytest.approx(want, rel=1e-9)
        assert b["exact"]["magnitudes"] == got


@sizes_on_disk
def test_every_size_bracketed_both_ways_on_both_models(budgets):
    """A ladder that never fails has found a too-narrow ladder, not an edge.

    First order brackets at every size. The solved network may not: since the pair
    stores zero as two devices off (2026-10-04) it draws less current, and at 6x6 it
    holds to the top of the declared ladder. That is allowed only in that direction
    -- holding at every rung, which the report says is beyond the ladder -- and never
    as a failure at the bottom, which would mean the ladder started too high.
    """
    for g, b in budgets.items():
        assert b["wire_resistance_ohm"]["bracketed"], f"first order, {g}x{g}"
        ex = b["exact"]
        if not ex["bracketed"]:
            assert all(ex["exactHolds"]), f"solved, {g}x{g}: unbracketed but not by holding"


@sizes_on_disk
def test_only_the_stochastic_sources_have_a_spread(budgets):
    for b in budgets.values():
        assert max(b["states_per_device"]["accStd"]) < 1e-15
        assert max(b["wire_resistance_ohm"]["accStd"]) < 1e-15
        assert max(b["sigma_g_rel"]["accStd"]) > 0
        assert max(b["sigma_area_rel"]["accStd"]) > 0


@sizes_on_disk
def test_first_order_never_holds_where_the_solved_network_fails(budgets):
    """The claim in the source's header, as a fact about every point measured.

    One pass overstates the drop, so it can only turn a design that holds into one
    that appears to fail. The report refuses to render the other way round; this is
    the same check where a failure names the size.
    """
    for g, b in budgets.items():
        ex = b["exact"]
        for m, first, solved in zip(ex["magnitudes"], ex["firstOrderHolds"], ex["exactHolds"]):
            assert not (first and not solved), f"{g}x{g} at {m:g} ohm"


@sizes_on_disk
def test_the_solved_edge_is_above_first_orders_at_every_size(budgets):
    for g, b in budgets.items():
        assert b["exact"]["lastHolding"] > b["wire_resistance_ohm"]["lastHolding"], g


@sizes_on_disk
def test_the_solved_network_never_falls_below_chance_and_first_order_does(budgets):
    """First order leaves the range of a resistor network; the network cannot."""
    exact_min = min(min(b["exact"]["exactAcc"]) for b in budgets.values())
    first_min = min(min(b["exact"]["firstOrderAcc"]) for b in budgets.values())
    assert exact_min > 0.1
    assert first_min < 0.1


@sizes_on_disk
def test_the_worst_cell_only_loses_conductance(budgets):
    for b in budgets.values():
        for f in b["exact"]["worstCellFraction"]:
            assert 0.0 <= f <= 1.0 + 1e-9


@sizes_on_disk
def test_conductance_variation_is_the_binding_of_the_two_at_every_size(budgets):
    """The row's own finding, held at each size rather than only at 36 rows."""
    from apps.report_row import bits_from_sigma, bits_from_states

    for g, b in budgets.items():
        sigma_bits = bits_from_sigma(b["sigma_g_rel"]["lastHolding"])
        state_bits = bits_from_states(int(b["states_per_device"]["lastHolding"]), b["scheme"])
        assert sigma_bits > state_bits, f"{g}x{g}"


# -- the size that is the row --------------------------------------------------------


@sizes_on_disk
@pytest.mark.skipif(not os.path.exists(ROW_BUDGET), reason="no row budget on disk")
def test_the_row_size_reproduces_the_row_on_sources_one_and_two():
    """6x6 through the new training path and the new driver is the row, exactly.

    Sources 1 and 2, and area variation, use the row's own ladders and seeds, so they
    must come back identical. Source 3 is on a different ladder and is compared where
    the two agree: the new first-order bracket has to be consistent with both ends of
    the row's.
    """
    with open(ROW_BUDGET, encoding="utf-8") as fh:
        row = json.load(fh)
    with open(_path(6, "error_budget.json"), encoding="utf-8") as fh:
        new = json.load(fh)

    assert new["ideal"] == row["ideal"]
    assert new["threshold"] == row["threshold"]
    for key in ("sigma_g_rel", "sigma_area_rel", "states_per_device"):
        for field in ("magnitudes", "accMean", "accStd", "holds", "lastHolding", "firstFailing"):
            assert new[key][field] == row[key][field], (key, field)

    # The row's own bracket says where the edge lies; on this ladder nothing at or below
    # the row's holding point may fail, and nothing at or above its failing point may
    # hold. Read from the row's budget rather than typed, so a rerun cannot leave this
    # test checking a bracket the row no longer records.
    held, failed = (row["wire_resistance_ohm"][k] for k in ("lastHolding", "firstFailing"))
    first = new["wire_resistance_ohm"]
    assert first["firstFailing"] > held, f"the row records holding at {held:g} ohm"
    assert first["lastHolding"] < failed, f"and failing at {failed:g} ohm"


@sizes_on_disk
@writes_on_disk
def test_every_size_ran_its_write_source_at_the_delivered_five_levels(budgets):
    """Said in the report: the same five states at every size, whether or not they hold."""
    for g, b in budgets.items():
        assert b["write_error_rate"]["states"] == DELIVERED_LEVELS, g
        assert b["write_error_rate"]["threshold"] == b["threshold"], g


@sizes_on_disk
@writes_on_disk
def test_every_write_bracket_end_is_on_every_sizes_write_ladder(budgets):
    """So each size's verdict is read off ladder points, to the bit."""
    for g, b in budgets.items():
        mags = b["write_error_rate"]["magnitudes"]
        assert mags == sorted(set(mags)), g
        for m in WRITE_ATTEMPTS:
            for end in write_bracket(m):
                assert end in mags, (g, m, end)


@sizes_on_disk
@writes_on_disk
def test_both_delivered_level_counts_are_rungs_of_every_sizes_states_ladder(budgets):
    from apps.report_row import level_verdict

    for g, b in budgets.items():
        for n in (DELIVERED_LEVELS, DELIVERED_LEVELS_TWO_PILLAR):
            assert level_verdict(b["states_per_device"], n)["levels"] == n, (g, n)


@sizes_on_disk
@writes_on_disk
def test_the_write_source_has_a_spread_at_every_size_where_it_ran_to_a_failure(budgets):
    """It draws random neighbours, so its realizations differ -- unlike the states knob."""
    for g, b in budgets.items():
        assert max(b["write_error_rate"]["accStd"]) > 0, g


@sizes_on_disk
def test_the_delivered_bracket_is_on_the_area_ladder_at_every_size(budgets):
    """So each size's verdict on the delivered spread is read off ladder points."""
    for g, b in budgets.items():
        mags = b["sigma_area_rel"]["magnitudes"]
        for end in DELIVERED_SIGMA_AREA:
            assert any(math.isclose(m, end) for m in mags), (g, end)


# -- the committed document --------------------------------------------------------------


@sizes_on_disk
@writes_on_disk
def test_the_committed_document_matches_what_report_size_produces_now():
    """The same bargain ``test_report_row.py`` makes for the row.

    ``docs/array_size.md`` is generated and reads like prose somebody wrote, so the
    natural way to correct a sentence is to edit the file -- and the next run of
    ``python -m apps.report_size`` discards the edit without a word.
    """
    with open(OUT, encoding="utf-8", newline="") as fh:
        on_disk = fh.read()
    assert on_disk == report_size.render(), (
        "docs/array_size.md is not what apps.report_size.render() produces. The prose "
        "lives in apps/report_size.py; edit it there and re-run "
        "`python -m apps.report_size`."
    )
