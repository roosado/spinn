"""The browser at five array sizes, pinned to the sweep that measured them.

``tests/test_web_crossbar.py`` is this argument at one size and the docstring there
is the general case: ``apps/web/crossbar.js`` is a third implementation of physics
that already exists in Python and in MATLAB, a third copy is normally where you stop
and share one, and since the seam between the two that matter is one-directional the
copy is pinned instead of trusted.

Two things are new here, and they pin differently.

**The wire network, solved.** ``err.ir_drop_exact`` factors a sparse matrix; the
browser runs a block Thomas sweep over the same matrix, ordered by row. Different
algorithms, so they agree to floating point rather than to the last bit, and what is
compared is ``Geff / G`` -- the fraction of its programmed conductance each cell
keeps -- at all fifteen ladder points of all five sizes, worst and mean. Seventy-five
pairs. This is the pin that holds the solver, the weights' transcription through
base64 and the operating point at once, because a wrong one of any of the three moves
those numbers.

**The 500-digit twins.** The page ships a sample, because five sizes of the full
2,000 test digits is megabytes. ``run_size_sweep.m`` therefore records every ladder
twice, and the sample half was computed on exactly the digits ``size_data.js``
carries -- for source 1, on exactly the same twenty perturbed arrays. So accuracy is
compared sample for sample, and agrees exactly except where a tie falls the other
way.

The one-cell closed form and a dense NumPy solve of a small array are here too. They
are what says the solver is right rather than merely reproducible: a pin against
MATLAB catches a browser that drifted, and catches nothing at all about a mistake
both sides could make from the same description.
"""
from __future__ import annotations

import json
import os
import re
import shutil

import numpy as np
import pytest

from conftest import json_runner

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
RUNNER = os.path.join(HERE, "size_runner.js")
SIZE_JS = os.path.join(REPO, "apps", "web", "size_data.js")
SIZE_DIR = os.path.join(REPO, "exports", "size")

node = shutil.which("node")
pytestmark = pytest.mark.skipif(node is None, reason="node not on PATH")

#: One sample of five hundred. Four times coarser than the main page's tolerance,
#: because the sample is four times smaller -- and it is spent exactly once, at 6x6
#: with five states per device, where two column currents come out equal and MATLAB's
#: matrix multiply and the browser's loop sum them in different orders.
ONE_SAMPLE = 1 / 500 + 1e-12

#: The solver's two implementations are a sparse LU and a block Thomas sweep, so this
#: is a floating-point tolerance and not a physics one. The worst disagreement over
#: all 150 comparisons is 3e-11, at 676 rows, where the sweep is 676 blocks deep.
SOLVE_REL = 1e-9

GRIDS = (6, 8, 12, 18, 26)


def unpack_images(block: dict) -> np.ndarray:
    """Expand the sparse image block, reading the widths it states.

    A third implementation of the format, after the exporter's and the browser's,
    and written here rather than imported for the reason the format needs checking
    at all: at 18x18 and 26x26 the index and the count are two bytes, and a reader
    that assumed one byte would not raise. It would return a different picture.
    """
    import base64

    iw, cw = block["idxBytes"], block["cntBytes"]
    counts = np.frombuffer(base64.b64decode(block["counts"]), dtype=f"<u{cw}")
    idx = np.frombuffer(base64.b64decode(block["idx"]), dtype=f"<u{iw}")
    val = np.frombuffer(base64.b64decode(block["val"]), dtype="<u2")
    n, dim = block["n"], block["dim"]
    assert len(counts) == n, "one count per sample"
    assert len(idx) == len(val) == int(counts.sum()), "the counts do not span the stream"
    x = np.zeros((n, dim))
    at = 0
    for s, raw in enumerate(counts):
        # int(), because `raw` is a one- or two-byte NumPy scalar and a running
        # offset accumulated in its dtype wraps: 88,658 non-zero pixels across the
        # 26x26 sample, in a uint16 that stops at 65,535.
        c = int(raw)
        x[s, idx[at:at + c]] = val[at:at + c] / block["full"]
        at += c
    return x


@pytest.fixture(scope="module")
def out():
    return json_runner(node, RUNNER)


@pytest.fixture(scope="module")
def payload():
    """The JSON object out of the committed module, without running JavaScript."""
    with open(SIZE_JS, encoding="utf-8", newline="") as fh:
        text = fh.read()
    match = re.search(r"var SIZES = (\{.*\});\n", text, re.S)
    assert match, "size_data.js no longer has the shape this test reads"
    return json.loads(match.group(1))


# ---------------------------------------------------------------- the module
# apps/web/size_data.js is committed, because the page inlines it and a clone has to
# be able to build the site without having run the sweep. exports/size/ is gitignored,
# so the checks that compare the two only run where both exist -- and everything the
# pins above need travels inside the committed module, which is the point. A pin that
# skipped on a clone would not be one.

_exports = all(os.path.exists(os.path.join(SIZE_DIR, f"g{g:02d}", "error_budget.json"))
               for g in GRIDS)
needs_exports = pytest.mark.skipif(
    not _exports, reason="exports/size is gitignored; run spinn-hw/run_size_sweep.m first",
)


@needs_exports
def test_the_committed_module_matches_what_the_exporter_produces_now():
    """The one test that compares against disk. A stale export fails here only."""
    from apps import export_size_data

    with open(SIZE_JS, encoding="utf-8", newline="") as fh:
        on_disk = fh.read()
    assert on_disk == export_size_data.render(), (
        "apps/web/size_data.js is not what export_size_data.render() produces. Run "
        "`python -m apps.export_size_data` and rebuild the site -- the page inlines "
        "this file, so a stale copy is a page reporting a previous sweep's numbers."
    )


@needs_exports
@pytest.mark.parametrize("grid", GRIDS)
def test_the_weights_are_the_exported_ones_to_the_last_bit(payload, grid):
    """Base64 float64, so 'to the last bit' is the whole claim of the format."""
    import base64

    ideal = np.load(os.path.join(SIZE_DIR, f"g{grid:02d}", "crossbar_ideal.npz"))
    got = np.frombuffer(base64.b64decode(payload["sizes"][str(grid)]["weights"]), dtype="<f8")
    assert np.array_equal(got.reshape(grid * grid, 10), ideal["weights"])


@needs_exports
@pytest.mark.parametrize("grid", GRIDS)
def test_the_shipped_digits_are_the_ones_matlab_measured(payload, grid):
    """The sample is chosen in MATLAB and read here, not chosen twice.

    If this module picked its own 50-per-class the two would agree today and diverge
    the first time either side changed how it breaks a tie, and the symptom would be
    a page whose live numbers sit a little away from its recorded ones for a reason
    nobody could see.
    """
    from apps.export_web_data import normalise
    from apps.export_size_data import _task_path

    with open(os.path.join(SIZE_DIR, f"g{grid:02d}", "error_budget.json"),
              encoding="utf-8") as fh:
        budget = json.load(fh)
    idx = [int(i) for i in budget["sample"]["indices"]]

    assert payload["sampleIndices"] == idx
    task = np.load(_task_path(grid))
    want = normalise(task["test_images"])[idx]
    got = unpack_images(payload["sizes"][str(grid)]["images"])
    assert got.shape == want.shape
    # uint16 of a value in [0, 1]: half a level is the whole of the error.
    assert np.max(np.abs(got - want)) <= 0.5 / 65535


def test_the_sample_is_the_same_five_hundred_digits_at_every_grid(payload):
    """One index means one digit at every size, which is what the page claims."""
    assert len(payload["sampleIndices"]) == 500
    assert payload["samplePerClass"] == 50
    assert len(set(payload["sampleIndices"])) == 500
    for grid in GRIDS:
        size = payload["sizes"][str(grid)]
        assert size["images"]["n"] == 500
        assert size["sample"]["n"] == 500


def test_the_labels_are_fifty_of_each_class(payload):
    import base64

    for grid in GRIDS:
        labels = np.frombuffer(base64.b64decode(payload["sizes"][str(grid)]["labels"]),
                               dtype="u1")
        counts = np.bincount(labels, minlength=10)
        assert list(counts) == [50] * 10, f"g{grid:02d} sample is lopsided: {counts}"


def test_every_size_states_its_own_operating_point(payload):
    """Identical at every size, and carried per size anyway.

    Error source 3 is the one source that does not cancel the conductance window, so
    it reads the window off the model it is running on. A shared copy would be a
    second place for it to be wrong.
    """
    for grid in GRIDS:
        op = payload["sizes"][str(grid)]["operatingPoint"]
        assert op == {"gMinS": 1.0e-6, "gMaxS": 3.0e-6, "readVoltageV": 0.1}


def test_the_geometry_is_g_squared_rows_and_ten_columns(payload):
    for grid in GRIDS:
        g = payload["sizes"][str(grid)]["geometry"]
        assert g == {"rows": grid * grid, "cols": 10, "side": grid,
                     "devices": grid * grid * 20}


# ------------------------------------------------------------------ the solver


def test_one_cell_is_a_device_in_series_with_its_two_segments(out):
    """``G / (1 + 2RG)``, which is the only case with an answer written down."""
    assert out["oneCell"]["geff"] == pytest.approx(out["oneCell"]["closedForm"], rel=1e-14)


def test_a_small_array_matches_a_dense_nodal_solve(out):
    """The independent check: the same network, built and solved again in NumPy.

    A pin against MATLAB catches a browser that drifted. It catches nothing about a
    mistake both sides could make from the same description, which is why this builds
    the nodal matrix from the geometry in words -- drivers at the column-1 edge,
    amplifiers at the row-1 edge, a segment between neighbours, a device across each
    cell -- and solves it densely.
    """
    s = out["small"]
    n_rows, n_cols, r = s["rows"], s["cols"], s["R"]
    g = np.asarray(s["G"], dtype="f8").reshape(n_rows, n_cols)

    nn = n_rows * n_cols
    row_node = lambda i, j: i * n_cols + j            # noqa: E731
    col_node = lambda i, j: nn + i * n_cols + j       # noqa: E731

    a = np.zeros((2 * nn, 2 * nn))

    def link(p, q, conductance):
        a[p, p] += conductance
        a[q, q] += conductance
        a[p, q] -= conductance
        a[q, p] -= conductance

    def ground(p, conductance):
        """A branch to a node held at zero: the driver's, or the amplifier's."""
        a[p, p] += conductance

    for i in range(n_rows):
        for j in range(n_cols):
            link(row_node(i, j), col_node(i, j), g[i, j])
            if j + 1 < n_cols:
                link(row_node(i, j), row_node(i, j + 1), 1.0 / r)
            if i + 1 < n_rows:
                link(col_node(i, j), col_node(i + 1, j), 1.0 / r)
    for i in range(n_rows):
        ground(row_node(i, 0), 1.0 / r)              # the segment up to driver i
    for j in range(n_cols):
        ground(col_node(0, j), 1.0 / r)              # the segment down to amplifier j

    # Drive one row at a time and read what reaches each amplifier: that is Geff by
    # its definition, current out per volt in.
    geff = np.zeros((n_rows, n_cols))
    for i in range(n_rows):
        b = np.zeros(2 * nn)
        b[row_node(i, 0)] = 1.0 / r                  # one volt behind that segment
        v = np.linalg.solve(a, b)
        for j in range(n_cols):
            geff[i, j] = v[col_node(0, j)] / r

    got = np.asarray(s["Geff"], dtype="f8").reshape(n_rows, n_cols)
    assert got == pytest.approx(geff, rel=1e-12)


def test_a_vanishing_wire_gives_back_the_programmed_array(out):
    """The solved path at 1 nano-ohm must be the ideal path, or it is a third model."""
    assert out["vanishingWire"]["worstWeightDifference"] < 1e-9
    assert out["vanishingWire"]["worstFraction"] == pytest.approx(1.0, abs=1e-9)


@pytest.mark.parametrize("grid", GRIDS)
def test_the_solver_reproduces_the_recorded_cell_fractions(out, grid):
    """Fifteen ladder points, worst and mean, against ``run_size_sweep.m``.

    The worst is one cell -- the corner furthest from both edges -- and on its own it
    would say nothing about the other 13,519 the page draws. The mean is recorded
    beside it for that reason, and both are checked.
    """
    bad = []
    for e in out["sizes"][str(grid)]["fractions"]:
        for got, want, which in ((e["worst"], e["worstRecorded"], "worst"),
                                 (e["mean"], e["meanRecorded"], "mean")):
            if abs(got - want) > SOLVE_REL * want:
                bad.append((which, e["magnitude"], got, want))
    assert not bad, f"g{grid:02d} cell fractions disagree with the sweep: {bad}"


def test_the_starvation_map_covers_every_cell_of_every_size(out):
    """What the picture is drawn from is the array, not a summary of it."""
    for grid in GRIDS:
        m = out["sizes"][str(grid)]["map"]
        assert m["length"] == m["cells"] == grid * grid * 10
        assert 0 < m["lo"] <= m["hi"] <= 1.0
        assert m["worst"] == pytest.approx(m["lo"], rel=1e-15)


# ------------------------------------------------------- the recorded twins


@pytest.mark.parametrize("grid", GRIDS)
def test_the_browser_reproduces_the_sample_ideal(out, grid):
    """No error source, no draw: this one is to the digit."""
    size = out["sizes"][str(grid)]
    assert size["sampleIdealComputed"] == size["sampleIdeal"]


@pytest.mark.parametrize("grid", GRIDS)
@pytest.mark.parametrize("source", ["states", "wire", "solved"])
def test_the_deterministic_ladders_agree_sample_for_sample(out, grid, source):
    """Both wire models and the quantiser, against their 500-digit twins.

    Allowed one sample, and it is spent once: at 6x6 with five states per device, the
    weight lattice is coarse enough that two column currents come out exactly equal
    and the winner is decided by the order the additions happened in. The next
    smallest disagreement any of these ladders produces is zero.
    """
    off = [(e["magnitude"], e["computed"], e["recorded"])
           for e in out["sizes"][str(grid)][source]
           if abs(e["computed"] - e["recorded"]) > ONE_SAMPLE]
    assert not off, f"g{grid:02d} {source} disagrees with the recorded twin: {off}"


def test_only_one_tie_is_spent_across_every_size_and_source(out):
    """The tolerance above is a licence, so this counts how much of it is used.

    A tolerance nobody checks the consumption of is a tolerance that grows.
    """
    ties = []
    for grid in GRIDS:
        for source in ("states", "wire", "solved"):
            for e in out["sizes"][str(grid)][source]:
                if e["computed"] != e["recorded"]:
                    ties.append((grid, source, e["magnitude"],
                                 e["computed"] - e["recorded"]))
    assert len(ties) <= 1, f"more than one ladder point turns on a tie: {ties}"


@pytest.mark.parametrize("grid", GRIDS)
def test_conductance_variation_lands_inside_the_recorded_spread(out, grid):
    """A different generator, so the stream differs and the distribution must not.

    The twin here is the same twenty perturbed arrays MATLAB drew, measured on the
    same 500 digits -- but the browser's own draw comes from a small PRNG rather than
    a Mersenne Twister, so what has to hold is the distribution and never a
    realisation.
    """
    bad = []
    for e in out["sizes"][str(grid)]["sigma"]:
        # One recorded standard deviation, plus a floor for the magnitudes where the
        # sweep's own spread is smaller than a couple of samples of five hundred.
        tol = max(e["recordedStd"], 0.008)
        if abs(e["mean"] - e["recorded"]) > tol:
            bad.append((e["magnitude"], e["mean"], e["recorded"], tol))
    assert not bad, f"g{grid:02d} sigma means outside the recorded spread: {bad}"


@pytest.mark.parametrize("grid", GRIDS)
def test_the_sample_digits_decode_to_normalised_images(out, grid):
    """Every sample keeps a peak of exactly one, which is what the encode assumes.

    At 18x18 and 26x26 the sparse block's index and count are two bytes wide. A
    decoder that assumed one would not fail -- it would return a different picture,
    and this is what notices.
    """
    size = out["sizes"][str(grid)]
    assert size["images"]["peakExactlyOne"] == 500
    assert size["images"]["aboveOne"] == 0
    assert 0.2 < size["images"]["nonZero"] / (500 * grid * grid) < 0.35


def test_the_recorded_ideal_is_the_full_set_and_the_digits_are_a_sample(out):
    """The page's one real hazard, asserted as a property of the data.

    ``model.ideal`` is measured over 2,000 digits and ``model.n`` is 500. They are
    different numbers about different sets and the page has to say so; here, all that
    is checked is that they are indeed different, so a later session cannot quietly
    make the sample the whole story.
    """
    for grid in GRIDS:
        size = out["sizes"][str(grid)]
        assert size["n"] == 500
        assert size["threshold"] == pytest.approx(0.95 * size["recordedIdeal"])
        assert size["sampleIdeal"] != size["recordedIdeal"]


def test_the_runner_stays_inside_its_time_budget(out):
    """Five sizes, both wire models, twenty realisations at eleven magnitudes.

    The suite is forty seconds and most of that is MATLAB starting. This runner is
    the one piece of new work that could quietly double it, so its own measurement of
    itself is an assertion rather than a note.
    """
    total = sum(out["timings"].values())
    assert total < 10_000, f"the size runner took {total} ms: {out['timings']}"
