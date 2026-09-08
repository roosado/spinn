"""The builder, and the properties the built page has to keep.

``apps/build_site.py`` is a trimmed extraction of photonn's 1192-line version:
five pages, a figure pipeline, a MathML compiler and nine widgets, cut to the
generic spine plus one page. These are the assertions that say the spine still
works, and they are what makes the next trim safe to attempt.

The self-containment checks matter more than they look. These pages are meant to
be openable from ``file://`` and served under a strict CSP, so a single external
``<script src>`` or webfont ``@import`` is a page that renders differently -- or
not at all -- depending on where it is opened from. That is not visible in a
browser with a network connection, which is every browser the page is developed
in.
"""
from __future__ import annotations

import os
import re

import pytest

from apps import build_site
from built_site import page_html, pages

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(REPO, "site")

#: Only index.html is committed. The Artifact body is a build product for
#: publishing elsewhere and is gitignored, so it has no on-disk copy to compare.
COMMITTED = ("index.html",)


def test_render_produces_the_files_the_module_documents():
    assert sorted(pages()) == ["_artifact_body.html", "index.html"]


@pytest.mark.parametrize("name", COMMITTED)
def test_the_committed_bytes_match_what_render_produces_now(name):
    """The one test that compares against disk. A stale build fails here and only here."""
    path = os.path.join(SITE, name)
    if not os.path.exists(path):
        pytest.fail(f"{name} has never been built; run `python -m apps.build_site`")
    with open(path, encoding="utf-8", newline="") as fh:
        on_disk = fh.read()
    assert on_disk == page_html(name), (
        f"site/{name} is not what render() produces. Run `python -m apps.build_site` "
        "and commit the result -- the committed bytes are what Pages serves."
    )


def test_no_placeholder_token_survives_into_a_built_page():
    """An unsubstituted @@TOKEN@@ renders as literal text and looks like a typo."""
    for name, html in pages().items():
        left = sorted(set(re.findall(r"@@[A-Z_0-9]+@@", html)))
        assert not left, f"{name} still carries {left}"


def test_pages_fetch_no_external_subresource():
    """A request, not a link.

    ``<a href>`` to an absolute URL is navigation and is required of the Artifact
    body, which has no sibling files to link relatively to. What must not appear is
    anything the browser would *fetch*: a script, a stylesheet, an image, a font.
    """
    fetched = re.compile(r'(?:\bsrc="|<link\b[^>]*\bhref=")(https?://[^"]*)"')
    for name, html in pages().items():
        refs = fetched.findall(html)
        assert not refs, f"{name} would fetch {refs}; these pages are self-contained"


def test_every_css_variable_used_is_also_defined():
    """The guard on the rename that lifted photonn's optical palette names.

    ``--beam``, ``--fringe`` and ``--spectral`` became ``--accent``, ``--accent-2``
    and ``--rule-gradient`` when the CSS came across; a spintronics repo has no
    beam and no fringe. An undefined custom property is not an error in CSS -- the
    declaration is simply dropped -- so a half-finished rename is invisible except
    as a colour that quietly stops being applied.
    """
    css = build_site.CSS
    used = set(re.findall(r"var\((--[a-z0-9-]+)", css))
    defined = set(re.findall(r"(--[a-z0-9-]+)\s*:", css))
    assert not used - defined, f"undefined custom properties: {sorted(used - defined)}"


def test_no_optical_palette_name_survives():
    assert not re.search(r"--beam|--fringe|--spectral", build_site.CSS)


def test_the_page_carries_its_own_title_and_description():
    html = page_html("index.html")
    page = build_site.PAGE_BY_KEY["index"]
    assert f"<title>{page.title}</title>" in html
    assert f'content="{page.desc}"' in html


def test_the_contents_card_is_generated_from_the_markup():
    """Every section heading gets an id, and the card lists them in document order."""
    html = page_html("index.html")
    labels = re.findall(r'<li[^>]*><a href="#([^"]+)">', html)
    assert labels, "the page has sections, so it must have a contents card"
    for ident in labels:
        assert f'id="{ident}"' in html, f"card links #{ident}, which no heading carries"
    positions = [html.index(f'id="{i}"') for i in labels]
    assert positions == sorted(positions), "the card must follow document order"


def test_a_single_page_site_has_no_hand_off_card():
    """photonn wraps the last page back to the first; with one page that is a loop.

    ``_hand_off`` returns None below two pages, so the card renders as nothing
    rather than inviting the reader to go where they already are. When a second
    page lands this test should be replaced, not deleted.
    """
    assert build_site._hand_off("index") is None
    assert build_site.next_link(None) == ""
    # The class matched in the stylesheet, which is kept for the pages to come;
    # what must be absent is an element wearing it.
    assert 'class="pagenext' not in page_html("index.html")


def test_the_artifact_body_uses_absolute_links_and_supplies_no_head():
    body = page_html("_artifact_body.html")
    assert "<!doctype html>" not in body.lower()
    assert build_site.SITE_URL in body


def test_the_mount_scheduler_is_inlined_and_names_the_renamed_global():
    """The sixth place the Tier 2 rename had to reach, and the easiest to miss.

    ``mount_script`` was re-homed here from photonn's ``diffraction_explorer.py``,
    a module that was never copied -- so its ``window.PhotonnMount`` reference
    would have gone on calling a global that no longer exists, silently.
    """
    html = page_html("index.html")
    assert "window.SpinnMount = mount" in html, "mount_queue.js must be inlined"
    assert "PhotonnMount" not in html
    emitted = build_site.mount_script("demo", "noop(el);")
    assert "window.SpinnMount" in emitted and "Photonn" not in emitted


def test_the_theme_is_persisted_under_this_repos_key():
    """photonn stores 'photonn-theme'; two sibling sites on one origin would collide."""
    html = page_html("index.html")
    assert "'spinn-theme'" in html
    assert "photonn-theme" not in html
