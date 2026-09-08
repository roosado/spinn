"""The standalone shell one widget is previewed on.

``apps/preview.py`` came across as Tier 2 -- copied, globals and prefixes renamed,
nothing else touched -- and the open question against it was whether a page it
produces actually carries the ``spinn —`` title prefix rather than photonn's. Plan
01 could only establish that the module imports. This closes it.

There are no widgets to preview yet. The shell is kept anyway: it is 89 lines, it
is the thing five demo modules would otherwise each grow their own copy of, and
photonn's note on it records that this is exactly what happened there before it
was extracted.
"""
from __future__ import annotations

from apps import preview


def _page(**kw):
    args = dict(
        title="a widget",
        heading="A widget",
        standfirst="What it shows.",
        hosts="host",
        bundle="<script>/* bundle */</script>",
        mount="<script>/* mount */</script>",
    )
    args.update(kw)
    return preview.preview_page(**args)


def test_the_title_carries_this_repos_prefix():
    assert "<title>spinn &mdash; a widget</title>" in _page()


def test_no_photonn_prefix_survives():
    assert "photonn" not in _page().lower()


def test_each_host_gets_a_container_in_document_order():
    html = _page(hosts=("first", "second"))
    assert html.index('id="first"') < html.index('id="second"')


def test_a_single_host_may_be_given_as_a_bare_string():
    """The commonest case, and the one where a bare string would otherwise iterate."""
    html = _page(hosts="solo")
    assert '<div id="solo"></div>' in html
    assert '<div id="s"></div>' not in html


def test_the_optional_note_is_absent_unless_asked_for():
    assert 'class="note"' not in _page()
    assert "a caveat" in _page(note="a caveat")


def test_the_page_is_self_contained():
    html = _page()
    assert "http://" not in html and "https://" not in html
