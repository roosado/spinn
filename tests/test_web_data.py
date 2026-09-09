"""The generated data module, and the drift it is allowed to have: none.

``apps/web/data.js`` is committed, because the site is built offline and the page
inlines it. A committed generated file is a file that can go stale, and a stale
one here is worse than a stale build: the page would go on displaying a previous
run's weights and a previous run's budget under this run's prose, and every number
on it would look exactly as authoritative as it does now.

So this makes the same bargain ``test_site_build.py`` makes for the built page --
regenerate in memory, compare against the bytes on disk, and fail with the command
that fixes it.
"""
from __future__ import annotations

import base64
import io
import json
import os
import re

import numpy as np
import pytest

from apps import export_web_data

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_JS = os.path.join(REPO, "apps", "web", "data.js")
IDEAL = os.path.join(REPO, "exports", "crossbar_ideal.npz")
BUDGET = os.path.join(REPO, "exports", "error_budget.json")
TASK = os.path.join(REPO, "tests", "fixtures", "shared_task_6x6.npz")

#: ``exports/`` is gitignored and regenerable; ``apps/web/data.js`` is committed,
#: because the page inlines it and a clone has to be able to build the site without
#: having run the training or the budget first. So every check that compares the
#: generated module against what generated it only runs where both exist. The
#: frozen task fixture *is* committed, so the checks against it always run --
#: which is the half that would catch a corrupted image block.
needs_exports = pytest.mark.skipif(
    not (os.path.exists(IDEAL) and os.path.exists(BUDGET)),
    reason="exports/ is gitignored; run apps.train_crossbar and the budget first",
)


@pytest.fixture(scope="module")
def payload():
    """The JSON object out of the committed module, without running JavaScript."""
    with io.open(DATA_JS, encoding="utf-8", newline="") as fh:
        text = fh.read()
    match = re.search(r"var DATA = (\{.*\});\n", text, re.S)
    assert match, "data.js no longer has the shape this test reads"
    return json.loads(match.group(1))


@needs_exports
def test_the_committed_module_matches_what_the_exporter_produces_now():
    """The one test that compares against disk. A stale export fails here only."""
    with io.open(DATA_JS, encoding="utf-8", newline="") as fh:
        on_disk = fh.read()
    assert on_disk == export_web_data.render(), (
        "apps/web/data.js is not what export_web_data.render() produces. Run "
        "`python -m apps.export_web_data` and rebuild the site -- the page inlines "
        "this file, so a stale copy is a page reporting a previous run's numbers."
    )


@needs_exports
def test_the_weights_are_the_exported_ones_to_the_last_bit(payload):
    ideal = np.load(IDEAL)
    assert np.array_equal(np.asarray(payload["weights"], dtype="f8"), ideal["weights"])
    assert payload["readoutGain"] == float(ideal["readout_gain"])
    assert payload["idealAccuracy"] == float(ideal["ideal_accuracy"])


def test_the_labels_survive_the_crossing(payload):
    task = np.load(TASK)
    got = np.frombuffer(base64.b64decode(payload["labels"]), dtype="u1")
    assert np.array_equal(got, task["test_labels"].astype("u1"))


def test_the_sparse_images_round_trip_within_one_part_in_65535(payload):
    """The precision decision, asserted rather than asserted-about.

    At eight bits the ideal accuracy comes out 0.7340 instead of 0.7345 -- one
    sample, moved by a rounding error in a digit sitting on a knife edge. Sixteen
    bits costs about 13 kB more and loses nothing that any number on the page can
    see, and this is what says the file is still carrying sixteen.
    """
    task = np.load(TASK)
    want = export_web_data.normalise(task["test_images"])

    block = payload["images"]
    counts = np.frombuffer(base64.b64decode(block["counts"]), dtype="u1")
    idx = np.frombuffer(base64.b64decode(block["idx"]), dtype="u1")
    val = np.frombuffer(base64.b64decode(block["val"]), dtype="<u2")

    got = np.zeros((block["n"], block["dim"]), dtype="f8")
    at = 0
    for s, c in enumerate(int(v) for v in counts):
        got[s, idx[at:at + c]] = val[at:at + c] / block["full"]
        at += c
    assert at == len(idx) == len(val), "the three sparse arrays disagree on length"
    assert np.max(np.abs(got - want)) <= 1.0 / block["full"]


def test_an_ideal_forward_pass_over_the_shipped_data_gives_the_recorded_accuracy(payload):
    """The end-to-end check, in Python, over exactly the bytes the browser gets.

    ``test_web_crossbar.py`` proves the JavaScript computes this correctly; this
    proves the data it computes it from is intact, without needing Node. If the
    quantisation of the images ever cost a sample, it fails here first.
    """
    task = np.load(TASK)
    block = payload["images"]
    counts = np.frombuffer(base64.b64decode(block["counts"]), dtype="u1")
    idx = np.frombuffer(base64.b64decode(block["idx"]), dtype="u1")
    val = np.frombuffer(base64.b64decode(block["val"]), dtype="<u2")
    x = np.zeros((block["n"], block["dim"]), dtype="f8")
    at = 0
    for s, c in enumerate(int(v) for v in counts):
        x[s, idx[at:at + c]] = val[at:at + c] / block["full"]
        at += c

    logits = x @ np.asarray(payload["weights"], dtype="f8")
    acc = float(np.mean(np.argmax(logits, axis=1) == task["test_labels"]))
    assert acc == payload["idealAccuracy"]


@needs_exports
def test_the_budget_carries_every_source_and_its_bracket(payload):
    with open(BUDGET, encoding="utf-8") as fh:
        recorded = json.load(fh)
    pairs = (("sigma", "sigma_g_rel"), ("states", "states_per_device"),
             ("wire", "wire_resistance_ohm"))
    for web, src in pairs:
        entry = payload["budget"][web]
        assert entry["magnitudes"] == recorded[src]["magnitudes"]
        assert entry["accMean"] == recorded[src]["accMean"]
        assert entry["lastHolding"] == recorded[src]["lastHolding"]
        assert entry["firstFailing"] == recorded[src]["firstFailing"]
    assert payload["threshold"] == recorded["threshold"]


def test_the_unsourced_operating_point_crossed_with_its_values(payload):
    """It has to cross, because error source 3 needs an absolute conductance.

    Sources 1 and 2 cancel the window exactly, which is why the page can say the
    accuracy does not depend on it. IR drop is ``R * I`` and cannot, so these three
    placeholders are load-bearing for one of the three panels -- and the page has to
    keep saying they are placeholders.
    """
    op = payload["operatingPoint"]
    assert op == {"gMinS": 1.0e-6, "gMaxS": 3.0e-6, "readVoltageV": 0.1}
