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


def test_the_contents_card_indexes_sections_and_nothing_else():
    """The regression that arrived the moment the eyebrow stopped being required.

    ``_HEADING`` used to be anchored on ``<p class="eyebrow">``, so making the
    eyebrow optional left it matching every ``h2`` and ``h3`` in the document --
    and the footer has three. They walked straight into the contents card, which
    is not visibly wrong until you read it. The anchor is ``.phase-head`` now, and
    this is what says so.
    """
    html = page_html("index.html")
    labels = re.findall(r'<li[^>]*><a href="#([^"]+)">', html)
    body = html[html.index("<main"):html.index("</main>")]
    for ident in labels:
        assert f'id="{ident}"' in body, f"the card indexes #{ident}, which is not in <main>"
    footer = html[html.index("<footer"):]
    assert "<h3" in footer, "this test is only meaningful while the footer has headings"
    assert not re.search(r'<h3[^>]*\sid="', footer), "a footer heading was given an id"


def test_a_heading_can_carry_its_own_contents_label_and_number():
    """What replaced the eyebrow, asserted rather than assumed.

    The card's number used to be parsed out of the text of a ``<p class="eyebrow">``
    above the heading ("Source 4 of 6" -> 4), which is why a decorative element was
    load bearing. Both overrides are attributes on the heading now, and both are
    stripped before it is emitted -- a heading that shipped a stray ``data-num`` to
    the browser would be the same bug one layer down.
    """
    body = (
        '<div class="phase-head">\n'
        '      <div>\n'
        '        <h2 data-num="3" data-toc="Short">A long heading: with a colon</h2>\n'
        "      </div>\n"
        "    </div>"
    )
    html, entries = build_site.section_index(body)
    assert entries == [{"level": "h2", "id": "short", "label": "Short", "num": "3"}]
    assert "data-num" not in html and "data-toc" not in html
    assert 'id="short"' in html


def test_a_heading_without_either_override_is_labelled_from_its_own_text():
    """``Topic: what it does`` is the page's heading convention; the card takes the
    topic, which is why no separate label has to be authored for the common case."""
    body = ('<div class="phase-head">\n      <div>\n'
            "        <h2>The sum: Kirchhoff's law does the arithmetic</h2>\n"
            "      </div>\n    </div>")
    _, entries = build_site.section_index(body)
    assert entries[0]["label"] == "The sum"
    assert entries[0]["num"] is None


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


# ------------------------------------------------------------------ the widgets
# Six widgets is the first time this generator has emitted any, and the failure
# they can have is silent in every direction: mount_queue.js skips a container it
# cannot find, script_tags emits whatever it is handed in whatever order, and a
# widget whose global is misspelled throws inside a try/catch that exists to stop
# one broken widget stranding the queue. None of that reaches a browser as an
# error. It reaches it as a gap where a machine should be.


def test_every_declared_widget_has_a_host_in_the_page():
    """The check ``Page.widgets`` exists to make possible.

    The tuple is declared rather than inferred precisely so it can be compared
    against the markup. A mistyped id gives a page that silently lacks a widget and
    passes every other test in this file.
    """
    html = page_html("index.html")
    for host in build_site.PAGE_BY_KEY["index"].widgets:
        assert html.count(f'id="{host}"') == 1, f"no unique host for widget {host}"


def test_no_widget_host_in_the_page_is_undeclared():
    """The other direction: a container nobody mounts into is a blank space."""
    body = build_site.page_body("index")
    hosts = set(re.findall(r'<div id="([a-zA-Z][a-zA-Z0-9]*)"></div>', body))
    declared = set(build_site.PAGE_BY_KEY["index"].widgets) | {"heroReadout"}
    assert not hosts - declared, f"empty containers nothing mounts into: {hosts - declared}"


def test_every_widget_module_is_inlined_and_mounted():
    html = page_html("index.html")
    for widget in build_site.WIDGETS:
        assert f'window.SpinnMount("{widget.host}"' in html
        # A marker from each module's own source, so this fails if the module is
        # declared and not emitted rather than only if the mount call is missing.
        assert build_site.read_web_asset(widget.asset)[:60] in html


def test_the_shared_widget_core_loads_before_any_widget_that_reads_it():
    """Order is the whole contract of :func:`script_tags`, and it is silent.

    Every widget reads ``window.SpinnCrossbar`` and ``window.SpinnData`` at module
    scope, and ``xbar_view.js`` reads ``window.SpinnPlot`` the same way. Loaded the
    other way round they get ``undefined`` and throw at mount, inside the queue's
    catch -- which logs to a console nobody has open and leaves a blank page.
    """
    html = page_html("index.html")
    order = [html.index(build_site.read_web_asset(name)[:60])
             for name in ("plot.js",) + build_site.WIDGET_CORE]
    assert order == sorted(order), "the shared modules are emitted out of order"
    first_widget = min(html.index(build_site.read_web_asset(w.asset)[:60])
                       for w in build_site.WIDGETS)
    assert max(order) < first_widget


def test_the_hero_does_not_wait_for_the_reader_to_approach_it():
    """Deferring the first viewport's widget means it starts once it is scrolled past."""
    hero = build_site.WIDGET_BY_HOST["heroMachine"]
    assert hero.defer is False
    html = page_html("index.html")
    assert 'window.SpinnMount("heroMachine", boot);' in html
    assert 'window.SpinnMount("errorBench", boot, {defer: true});' in html


def test_the_page_carries_the_real_data_not_a_placeholder():
    """The page's whole claim is that these are the recorded numbers."""
    html = page_html("index.html")
    assert '"idealAccuracy":0.7345' in html
    assert '"schema":"web-data 1"' in html
    # 2000 samples of 36 pixels, sparse: the block is large, and a page that
    # shipped an empty or truncated one would still render and still classify --
    # just worse, and with no way to tell from the markup.
    assert len(html) > 200_000


def test_no_unsourced_number_is_presented_as_a_measurement():
    """A hole is drawn as a hole. The project's own convention, on the page.

    ``.q.hole`` is the marker; what must not happen is the word UNSOURCED appearing
    in prose without it, which would read as an ordinary emphasis.
    """
    html = page_html("index.html")
    # Prose only. The inlined widget modules discuss UNSOURCED placeholders at
    # length in their own comments, and a source comment is not a claim to a reader.
    body = html[html.index("<main"):html.index("</footer>")]
    plain = re.findall(r"UNSOURCED", body)
    marked = re.findall(r'<span class="q hole">UNSOURCED</span>', body)
    assert plain and len(plain) == len(marked), (
        "every UNSOURCED on the page must be marked as a hole"
    )
