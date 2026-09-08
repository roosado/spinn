"""The suite itself, proven to run.

Nothing inherited from photonn had ever been executed in this repo. The three
tiers of confidence it was sorted into came from ``grep`` and ``diff``, which
establish what *should* work, not what does -- and two files have already turned
out to be misfiled by that metric.

This is the first test that ran here. Its only job is to be the fixed point the
rest of the suite is measured against: if this fails, a failure anywhere else
says nothing about the code it names.
"""
from __future__ import annotations

import numpy as np

import spinn

from conftest import RNG_SEED


def test_the_package_imports_and_declares_a_version():
    assert spinn.__version__ == "0.1.0"


def test_the_seeded_generator_is_actually_seeded(rng):
    """A fixture that quietly reseeded would make every downstream draw unrepeatable."""
    assert np.array_equal(rng.random(4), np.random.default_rng(RNG_SEED).random(4))
