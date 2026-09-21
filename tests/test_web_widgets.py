"""Every widget, at every array size, mounted and taken down again.

The size page rebuilds each instrument when the reader changes the array size, so
a mount has to be undoable. Until that page existed nothing could tell whether it
was: a widget was mounted once and lived as long as the document, and an observer
it never disconnected cost nothing and left no trace anybody could look for.

``tests/widget_runner.js`` mounts each one against ``tests/dom_stub.js``'s counting
window -- which remembers every ResizeObserver, MutationObserver,
IntersectionObserver, media listener, interval and animation frame it hands out --
and then calls ``destroy``. A leak is a count that does not come back.

**The hero is the one that matters.** It holds an interval, an animation frame and
its own IntersectionObserver, none of which stop because the element left the
document. Five size changes leave five intervals repainting five detached canvases,
which is not a memory leak a reader would ever see; it is a hot laptop.

The other half of this module is the size literals. Six widgets carried a ``36``,
a ``360``, a ``720`` or a ``2,000`` in text a reader sees. Mounted at 676 rows,
any of those that stayed behind is a sentence that is now false, and the page would
look entirely fine.
"""
from __future__ import annotations

import os
import re
import shutil

import pytest

from conftest import json_runner

HERE = os.path.dirname(os.path.abspath(__file__))
RUNNER = os.path.join(HERE, "widget_runner.js")

node = shutil.which("node")
pytestmark = pytest.mark.skipif(node is None, reason="node not on PATH")

GRIDS = (6, 8, 12, 18, 26)

#: Every widget the runner mounts, and whether it appears on the index page too.
WIDGETS = ("heroMachine", "deviceExplorer", "wireColumn", "errorBench",
           "budgetLadder", "drawPad", "sizeArray")


@pytest.fixture(scope="module")
def out():
    return json_runner(node, RUNNER)


def runs_of(out, host):
    """Every mount of one widget, keyed as the runner keyed them."""
    return out["widgets"][host]


# ------------------------------------------------------------------- disposal


@pytest.mark.parametrize("host", WIDGETS)
def test_every_widget_returns_a_disposer(out, host):
    """``mount`` returns ``{destroy}``. Without it the page cannot be rebuilt."""
    for key, run in runs_of(out, host).items():
        assert run["hasDestroy"], f"{host} at {key} returned nothing to destroy"


@pytest.mark.parametrize("host", WIDGETS)
def test_destroy_gives_back_everything_it_took(out, host):
    """The counts return to where they started, at every size.

    Named individually in the failure, because "a leak" is not actionable and
    "one ResizeObserver and one interval" is.
    """
    for key, run in runs_of(out, host).items():
        leaked = {k: run["afterDestroy"][k] - run["before"][k]
                  for k in run["before"]
                  if run["afterDestroy"][k] != run["before"][k]}
        assert not leaked, f"{host} at {key} left behind {leaked}"


@pytest.mark.parametrize("host", WIDGETS)
def test_destroy_empties_the_host(out, host):
    """A mount on top of a mount draws the instrument twice, one under the other.

    ``size_page.js`` empties the host itself for a widget with no disposer, so
    this is about the widgets that do have one: theirs is the one that has to.
    """
    for key, run in runs_of(out, host).items():
        assert run["mountedLength"] > 0, f"{host} at {key} mounted nothing"
        assert run["hostLeft"] == 0, f"{host} at {key} left markup in its host"


def test_the_hero_gives_back_its_second_host(out):
    """The readout is outside the widget's container, so emptying it does not reach.

    ``apps/build_site.py`` passes ``#heroReadout`` by id and the hero writes the
    verdict into it. A rebuild that cleared only the container would leave the
    previous array's answer sitting under the new array's machine.
    """
    for key, run in runs_of(out, "heroMachine").items():
        assert run["readoutLeft"] == 0, f"the hero left its readout filled at {key}"


def test_the_heros_animation_is_actually_started_before_it_is_stopped(out):
    """A disposer that was never needed proves nothing.

    Two paths, and both are walked: with motion the hero schedules an animation
    frame, and under reduced motion it starts an interval instead -- but only once
    the reader presses Play, which is why the runner presses it. Its own
    IntersectionObserver is constructed either way.
    """
    lively = runs_of(out, "heroMachine")["g26"]
    assert lively["made"]["frame"] >= 1, "the hero never asked for a frame"
    assert lively["made"]["intersection"] == 1, "the hero never watched its canvas"

    reduced = runs_of(out, "heroMachine")["reducedMotion"]
    assert reduced["made"]["interval"] == 1, (
        "reduced motion plus Play is the path that starts an interval, and this run "
        "did not start one -- so the clearInterval in destroy is untested"
    )
    assert reduced["afterMount"]["interval"] == 1
    assert reduced["afterDestroy"]["interval"] == 0


@pytest.mark.parametrize("host", WIDGETS)
def test_every_widget_uses_the_shared_observers(out, host):
    """Both disposers in ``plot.js`` matter, so both must be reached.

    Every instrument on this site redraws on a width change and on a theme change;
    one that asked for neither would pass the leak test above by doing nothing.
    """
    run = runs_of(out, host)["g26"]
    assert run["made"]["resize"] >= 1, f"{host} does not watch its own width"
    assert run["made"]["mutation"] >= 1, f"{host} does not watch the theme"
    assert run["made"]["media"] >= 1, f"{host} ignores the system colour preference"


# --------------------------------------------------------------- the literals


#: Figures that belong to the 36-row array. A widget mounted at 676 rows that still
#: prints one of these is printing something false.
#:
#: "2,000" is deliberately **not** here. The recorded verdict is over all 2,000
#: digits at every size, so a widget that says so is right; what would be wrong is
#: claiming the *live* number is over them, which
#: :func:`test_the_bench_says_which_digits_its_number_is_over` checks by name.
SIX_BY_SIX = ("36 ", "360 ", "720 ", "6 by 6", "0.7345", "73.45")


@pytest.mark.parametrize("host", WIDGETS)
def test_no_widget_carries_another_size_s_numbers(out, host):
    """The trap Stage 3 is really about.

    Forty-three lines across the six widgets carried a ``36``, ``360``, ``720`` or
    ``2,000``, or read ``model.rows``; fourteen of them sat inside a string a reader
    sees. A missed one is not an error, a crash or a blank panel -- it is a correct
    instrument under a caption about a different machine.
    """
    text = runs_of(out, host)["g26"]["text"]
    found = [lit for lit in SIX_BY_SIX if lit in text]
    assert not found, f"{host} at 676 rows still says {found}: {text[:300]!r}"


@pytest.mark.parametrize("host", WIDGETS)
def test_the_text_moves_when_the_array_does(out, host):
    """Something a reader sees has to differ between the smallest and largest array.

    The inverse of the test above, and the one that catches a widget wired to
    ``opts.data`` everywhere except the place it prints.
    """
    runs = runs_of(out, host)
    small, large = runs["g6"]["text"], runs["g26"]["text"]
    if host == "deviceExplorer":
        pytest.skip("size-independent by design; see the test below")
    assert small != large, f"{host} prints the same thing at 36 rows and at 676"


def test_the_device_explorer_is_the_one_that_does_not_move():
    """A device has the same states at every grid, and that is the point of it.

    Source 2's bracket barely moves across the sweep for exactly this reason, and
    the instrument saying the same thing at 36 rows and at 676 is the honest
    picture rather than an oversight. Stated here so the test above can exempt it
    without the exemption looking like one.
    """
    # Nothing to compute: this is a claim about the design, kept beside the test
    # that would otherwise flag it, so that removing one means answering the other.


def test_the_bench_says_which_digits_its_number_is_over(out):
    """The sample's cost, in the UI, where decision 2 said it had to be.

    The index page computes over all 2,000 frozen digits; the size page computes
    over a 500-digit sample of the same set and a recorded verdict is still over
    2,000. A reader comparing the two has to be told which is which.
    """
    index = runs_of(out, "errorBench")["index"]["text"]
    sized = runs_of(out, "errorBench")["g26"]["text"]
    assert "all 2,000 frozen test digits" in index
    assert "500-digit sample of the frozen set" in sized
    assert "all 2,000 frozen test digits" not in sized


# ----------------------------------------------------------------- the pad


def test_the_pad_grid_is_a_whole_multiple_of_every_array(out):
    """Which is what makes the box average an exact area average.

    At 24 over 18 a target cell would take 1.33 pad cells and ``Math.floor`` would
    tile them unevenly; at 24 over 26 the pad would have fewer cells than the tile
    it fills, and the reader would be shown structure finer than they could draw.
    """
    for entry in out["padGrid"]:
        assert entry["whole"], f"pad {entry['pad']} does not divide by {entry['grid']}"
        assert entry["per"] >= 2, (
            f"a pad cell per {entry['per']} of the array at {entry['grid']}x"
            f"{entry['grid']} is not enough to draw with"
        )


def test_the_shared_task_s_pad_is_the_pad_it_has_always_been(out):
    """6x6 keeps 24.

    The index page's numbers were all produced with a 24-grid pad box-averaged four
    to one. A pad that changed for 6x6 would change what that page shows without
    changing any recorded number, which is the quietest way to break it.
    """
    assert out["padGridAtSix"] == 24
