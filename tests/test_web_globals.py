"""The Tier 2 rename, asserted by name.

Four files came in from photonn with their globals renamed and nothing else
touched: ``PhotonnMount`` -> ``SpinnMount``, ``PhotonnPlot`` -> ``SpinnPlot``,
plus a style id, a log prefix and a title prefix. **The rename is the only thing
that can have broken them**, and a missed occurrence gives an undefined global at
mount time -- which in a browser is silent. No error, no console entry, just a
page whose widgets never start.

The two Node runners do not cover this. ``mount_queue_runner.js`` reads
``env.win.SpinnMount``, so it would catch a missed rename there; but
``plot_runner.js`` pulls the module in with ``require`` and never touches the
window global, so ``plot.js``'s ``window.SpinnPlot = API`` line could say anything
at all and every assertion in ``test_plot.py`` would still pass.

So the export surface is checked statically, against the source. It is a cheap
test for a failure whose only other detector is a reader looking at a blank page.
"""
from __future__ import annotations

import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(os.path.dirname(HERE), "apps", "web")


def _source(name: str) -> str:
    with open(os.path.join(WEB, name), encoding="utf-8") as fh:
        return fh.read()


def test_mount_queue_publishes_spinnmount():
    assert "window.SpinnMount = mount" in _source("mount_queue.js")


def test_plot_publishes_spinnplot():
    """The one the runner cannot see, because it imports the module directly."""
    assert "window.SpinnPlot = API" in _source("plot.js")


def test_the_injected_style_id_was_renamed_too():
    """A stale id collides with nothing here, but it is a residue of a half rename."""
    assert '"spinn-mount-style"' in _source("mount_queue.js")


def test_no_photonn_identifier_survives_in_the_web_layer():
    """Capitalised, so this catches code and not the prose provenance we keep.

    ``plot.js`` deliberately still records in a comment that a third copy of its
    logic lived in ``d2nn_stage.js``. That history is worth keeping in a copied
    file, so lower-case mentions are not what is being tested here.
    """
    offenders = []
    for name in ("mount_queue.js", "plot.js"):
        for n, line in enumerate(_source(name).splitlines(), 1):
            if re.search(r"\bPHOTONN\b|\bPhotonn", line):
                offenders.append(f"{name}:{n}: {line.strip()}")
    assert not offenders, "photonn identifiers left in the web layer:\n" + "\n".join(offenders)
