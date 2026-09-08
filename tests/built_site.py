"""The site as ``render()`` produces it, built once per session.

Every site test could read ``site/*.html`` off disk instead. That is the right
thing to measure -- the committed bytes are what Pages serves, so they are what a
visitor gets -- but on its own it leaves two holes.

Nothing would call ``render()``. Edit a body in ``apps/pages/``, forget to run the
build, commit: the suite stays green and the deployed page is the previous one.
And every module would skip when the file was absent, so on a machine without a
build the assertions would not fail, they would quietly not run.

Building once per session and asserting the committed bytes match (see
``test_site_build.py``) closes both: the assertions describe the current source,
and the one test that compares against disk says plainly when the two have
drifted.

Cached rather than rebuilt per module out of habit inherited from photonn, where
the build took ten seconds because every figure was encoded five ways to keep the
smallest. This build has no figures and takes milliseconds; the cache costs
nothing and stays for when it does.
"""
from __future__ import annotations

import functools


@functools.lru_cache(maxsize=None)
def pages() -> dict:
    """``{filename: html}`` for every file the site is made of."""
    from apps.build_site import render

    return render()


def page_html(name: str) -> str:
    """One rendered page by filename."""
    built = pages()
    if name not in built:
        raise AssertionError(
            f"{name} is not one of the files render() produces: {sorted(built)}"
        )
    return built[name]
