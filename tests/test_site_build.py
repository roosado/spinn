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

#: Every page of the site is committed. The Artifact body is a build product for
#: publishing elsewhere and is gitignored, so it has no on-disk copy to compare.
COMMITTED = tuple(p.file for p in build_site.PAGES)

#: Every page, by filename, for the checks that are about all of them.
EVERY_PAGE = pytest.mark.parametrize("name", COMMITTED)


def test_render_produces_the_files_the_module_documents():
    assert sorted(pages()) == sorted(["_artifact_body.html", *COMMITTED])


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


@EVERY_PAGE
def test_the_page_carries_its_own_title_and_description(name):
    html = page_html(name)
    page = next(p for p in build_site.PAGES if p.file == name)
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
    assert re.search(r"<h[23]\b", footer), (
        "this test is only meaningful while the footer has headings")
    assert not re.search(r'<h[23][^>]*\sid="', footer), "a footer heading was given an id"


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


def test_the_hand_off_card_closes_the_loop_between_the_pages():
    """This replaces, rather than deletes, the assertion that there was no card.

    With one page ``_hand_off`` returned None, because photonn's wrap-to-the-first
    would have invited the reader to go where they already were. With two it is the
    wrap that closes the loop: the index hands off to the size page and the size page
    hands back, and both cards are generated rather than written twice.
    """
    assert build_site._hand_off("index") == ("larger", "Next")
    assert build_site._hand_off("larger") == ("index", "Back to the start")
    assert build_site.next_link(None) == ""
    for page in build_site.PAGES:
        assert 'class="pagenext' in page_html(page.file), f"{page.file} has no hand-off"
    assert "Go larger" in page_html("index.html")


def test_every_page_is_reachable_from_every_other_one():
    """The topbar is generated from PAGES, so this is really a test of the tokens.

    An unresolved ``@@HREF_larger@@`` renders as literal text inside an href and the
    link goes nowhere, which no other check here would notice.
    """
    for page in build_site.PAGES:
        html = page_html(page.file)
        for other in build_site.PAGES:
            href = build_site.href(other.key)
            assert f'href="{href}"' in html, f"{page.file} cannot reach {other.file}"
        nav = re.search(r'<nav class="topbar-nav"[^>]*>(.*?)</nav>', html, re.S).group(1)
        assert nav.count('aria-current="page"') == 1, "one link is the page you are on"
        assert f'>{page.nav}</a>' in nav


def test_every_rule_for_the_headline_matches_the_markup():
    """The regression that shipped, and that nothing else in this file could see.

    The first viewport was rebuilt around the machine and its wrapper renamed from
    ``.hero`` to ``.machine``; the headline's rules kept targeting ``.hero``. So the
    page's one claim rendered in the browser's default bold sans -- no serif, no
    amber emphasis, a spectral underbar zero pixels tall -- while the committed bytes
    matched the generator and every other assertion here passed. A selector naming a
    class the markup does not carry is not an error in CSS. It is simply never applied.
    """
    css = re.sub(r"/\*.*?\*/", "", build_site.CSS, flags=re.S)
    bodies = "".join(build_site.page_body(p.key) for p in build_site.PAGES)
    selectors = [s.strip() for block in re.findall(r"([^{}@]+)\{", css)
                 for s in block.split(",")]
    headline = [s for s in selectors if re.search(r"\bh1\b|\.underbar\b", s)]
    assert headline, "the stylesheet has no rule for the headline at all"
    for sel in headline:
        for cls in re.findall(r"\.([a-zA-Z][\w-]*)", sel):
            assert re.search(rf'class="[^"]*\b{re.escape(cls)}\b', bodies), (
                f"`{sel}` targets .{cls}, which no page carries")


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


@EVERY_PAGE
def test_every_widget_module_is_inlined_and_mounted(name):
    """Each page carries its own widgets, and only its own.

    Only its own matters as much as all of its own: the two widgets the size page
    adds read a megabyte of data, and a page that quietly inlined them would still
    render, still be correct, and take four times as long to arrive.
    """
    page = next(p for p in build_site.PAGES if p.file == name)
    html = page_html(name)
    for widget in build_site.WIDGETS:
        mine = widget.host in page.widgets
        marker = build_site.read_web_asset(widget.asset)[:60]
        # A marker from each module's own source, so this fails if the module is
        # declared and not emitted rather than only if the mount call is missing.
        assert (f'window.SpinnMount("{widget.host}"' in html) is mine
        assert (marker in html) is mine, f"{widget.asset} on {name}: expected {mine}"


@EVERY_PAGE
def test_a_page_inlines_only_the_data_modules_it_declares(name):
    """``size_data.js`` is 957 kB of five trained arrays. The index needs none of it."""
    page = next(p for p in build_site.PAGES if p.file == name)
    html = page_html(name)
    for module, marker in (("data.js", '"schema":"web-data 1"'),
                           ("size_data.js", '"schema":"web-size-data 1"')):
        wanted = module in build_site.WIDGET_CORE or module in page.modules
        assert (marker in html) is wanted, f"{module} on {name}: expected {wanted}"


def test_the_shared_widget_core_loads_before_any_widget_that_reads_it():
    """Order is the whole contract of :func:`script_tags`, and it is silent.

    Every widget reads ``window.SpinnCrossbar`` and ``window.SpinnData`` at module
    scope, and ``xbar_view.js`` reads ``window.SpinnPlot`` the same way. Loaded the
    other way round they get ``undefined`` and throw at mount, inside the queue's
    catch -- which logs to a console nobody has open and leaves a blank page.
    """
    for page in build_site.PAGES:
        html = page_html(page.file)
        shared = ("plot.js",) + build_site.WIDGET_CORE + page.modules
        order = [html.index(build_site.read_web_asset(name)[:60]) for name in shared]
        assert order == sorted(order), f"{page.file}: shared modules out of order"
        first_widget = min(html.index(build_site.read_web_asset(
            build_site.WIDGET_BY_HOST[h].asset)[:60]) for h in page.widgets)
        assert max(order) < first_widget, f"{page.file}: a widget precedes what it reads"


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
    # Prose only. The inlined widget modules may discuss the operating point at
    # length in their own comments, and a source comment is not a claim to a reader.
    body = html[html.index("<main"):html.index("</footer>")]
    plain = re.findall(r"UNSOURCED", body)
    marked = re.findall(r'<span class="q hole">UNSOURCED</span>', body)
    assert plain and len(plain) == len(marked), (
        "every UNSOURCED on the page must be marked as a hole"
    )


# ------------------------------------------------------------------- hardening
# What a reader gets who is not using a mouse, a script, or a screen at all. The
# widgets' own behaviour is checked in a browser; these are the parts that live in
# the markup and can drift out of it without anything else noticing.


@EVERY_PAGE
def test_the_skip_link_is_the_first_stop_and_lands_on_the_page(name):
    """Its target is in the page body and the link is in the generator, so the two can
    drift apart -- and a skip link to an id nothing carries does nothing, silently."""
    html = page_html(name)
    body = html[html.index("<body"):]
    first = re.search(r"<(?:a|button|input|select|textarea)\b[^>]*>", body).group(0)
    assert 'class="skip"' in first, f"the first focusable element is {first}"
    target = re.search(r'class="skip" href="#([^"]+)"', body).group(1)
    assert body.count(f'id="{target}"') == 1, f"the skip link's #{target} is not on the page"


@pytest.mark.parametrize("key", [p.key for p in build_site.PAGES])
def test_instrument_titles_and_sub_headings_are_headings(key):
    """Heading navigation is how a screen reader skims a page, and it skipped all
    seven: they were paragraphs styled to look like headings. The look is kept."""
    body = build_site.page_body(key)
    for cls in ("inst-t", "sub-h"):
        tags = re.findall(rf'<(\w+) class="{cls}"', body)
        # Not every page carries every one of them -- the size page has instruments
        # and no sub-headings. What must hold is that where the look is used, the
        # element under it is a heading, and at the level the page's own outline
        # calls for: an instrument sits under a section heading on the index and is
        # a top-level section of its own on the size page.
        assert set(tags) <= {"h2", "h3"}, f".{cls} is carried by {sorted(set(tags))} on {key}"
    assert re.findall(r'<(\w+) class="inst-t"', body), f"{key} declares no instrument"


def test_each_look_that_stands_in_for_a_heading_is_used_somewhere():
    """The other half of the check above: a rule for a look nothing wears is dead."""
    bodies = "".join(build_site.page_body(p.key) for p in build_site.PAGES)
    for cls in ("inst-t", "sub-h"):
        assert re.findall(rf'<h3 class="{cls}"', bodies), f".{cls} is worn by nothing"


@pytest.mark.parametrize("key", [p.key for p in build_site.PAGES])
def test_every_instrument_says_what_is_missing_without_a_script(key):
    """With scripts off, each host is an empty div under a caption that tells the
    reader to drag or draw something. Each is followed by what would have been there."""
    body = build_site.page_body(key)
    for host in build_site.PAGE_BY_KEY[key].widgets:
        assert re.search(rf'<div id="{host}"></div>\s*<noscript>', body), (
            f"#{host} has no fallback for a reader without scripts")


def test_the_budget_fallback_states_the_recorded_brackets():
    """The ladder is the one widget whose content is recorded rather than computed, so
    without a script its brackets can still be given in words. In words they are a
    second copy of numbers that live in data.js, and this is what keeps them one."""
    body = build_site.page_body("index")
    data = build_site.read_web_asset("data.js")
    block = re.search(r'<div id="budgetLadder"></div>\s*<noscript>(.*?)</noscript>',
                      body, re.S).group(1)
    items = [build_site.strip_tags(li) for li in re.findall(r"<li>(.*?)</li>", block, re.S)]
    assert len(items) == 3, "one bracket per error source"
    for key, text in zip(("sigma", "states", "wire"), items):
        hold, fail = re.search(
            rf'"{key}":\{{"magnitudes".*?"lastHolding":([\d.]+),"firstFailing":([\d.]+)',
            data).groups()
        said = re.search(r"holds at\D*?([\d.]+).*?fails at\D*?([\d.]+)", text).groups()
        assert tuple(map(float, said)) == (float(hold), float(fail)), (key, text)


@EVERY_PAGE
def test_the_saved_theme_is_applied_before_anything_paints(name):
    """At the foot of the body it ran after the whole inline data set, so a reader whose
    saved theme differed from their system's could see the other one first."""
    html = page_html("index.html")
    boot = build_site.THEME_BOOT
    assert html.index(boot) < html.index("<style>") < html.index("<body")
    art = page_html("_artifact_body.html")
    assert art.index(boot) < art.index('<header class="topbar"')


def test_every_class_the_stylesheet_styles_is_emitted_somewhere():
    """The general case of the headline test, and the guard the dead CSS needed.

    A rule for a class nothing emits is not an error in CSS; it is a rule waiting for
    the next edit to reuse it. photonn's stat tiles, stats grid, figure plates and
    tables sat in this stylesheet from the trim that brought the generator across --
    three of the four the card pattern this page refuses -- until a critique counted
    them. A class passes when the page body, the generator outside its stylesheet, or
    a widget module names it. That is loose on purpose: it catches a class nothing
    names at all, not one named by accident. The exceptions are vocabulary a page may
    write and none does yet, and each must still have a rule.
    """
    css = re.sub(r"/\*.*?\*/", "", build_site.CSS, flags=re.S)
    classes = set(re.findall(r"\.([a-zA-Z][\w-]*)", css))
    with open(build_site.__file__, encoding="utf-8") as fh:
        generator = fh.read().replace(build_site.CSS, "")
    widgets = "".join(build_site.read_web_asset(name)
                      for name in sorted(os.listdir(build_site.WEB_DIR)) if name.endswith(".js"))
    bodies = "".join(build_site.page_body(p.key) for p in build_site.PAGES)
    haystack = bodies + generator + widgets
    dormant = {
        "band-b",                 # the note under a band heading; no page groups sections
        "planned", "badge-next",  # a section not built yet (DESIGN.md, under Chips)
    }
    unused = sorted(c for c in classes - dormant
                    if not re.search(rf"(?<![\w-]){re.escape(c)}(?![\w-])", haystack))
    assert not unused, f"rules for classes nothing emits: {unused}"
    assert dormant <= classes, "an exception outlived its rule; take it off the list"


def _top_level_classes(css: str) -> set:
    """Classes a stylesheet defines outside any at-rule block.

    At-rule blocks are excluded because that is where this site's cross-cutting
    rules live and they are cross-cutting on purpose: the touch block in the
    generator grows the hit area of ``.bn-btn`` and ``.dw-btn``, and the
    forced-colours block redraws a track the widget owns. Those reach into a
    widget's vocabulary knowingly. What must not happen is two files claiming the
    same class at the top level, where neither knows about the other.
    """
    stripped = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    # Drop @media / @supports bodies, brace-matched so a nested rule goes with them.
    out, i = [], 0
    while i < len(stripped):
        at = stripped.find("@", i)
        if at < 0:
            out.append(stripped[i:])
            break
        out.append(stripped[i:at])
        brace = stripped.find("{", at)
        if brace < 0:
            break
        depth, j = 1, brace + 1
        while j < len(stripped) and depth:
            if stripped[j] == "{":
                depth += 1
            elif stripped[j] == "}":
                depth -= 1
            j += 1
        i = j
    flat = "".join(out)
    found = set()
    for block in re.findall(r"([^{}]+)\{", flat):
        for sel in block.split(","):
            found.update(re.findall(r"\.([a-zA-Z][\w-]*)", sel))
    return found


def _widget_css(source: str) -> str:
    """A widget's injected stylesheet: every double-quoted literal, joined.

    The modules build their CSS by concatenating string literals, and a selector
    never appears anywhere else in them -- so joining the literals gives the
    stylesheet without needing to parse JavaScript, and without ``P.injectStyle``
    or ``el.className`` reading as a selector.
    """
    return "".join(re.findall(r'"([^"\n]*)"', source))


#: Generated data modules. They are megabytes of base64 inside string literals and
#: carry no CSS, so reading them as a stylesheet is slow and says nothing.
_NOT_A_WIDGET = ("data.js", "size_data.js")

#: Vocabulary more than one file is meant to style, and does.
#:
#: ``.v`` and ``.l`` are the two halves of ``V.readout``, which every widget that
#: prints a labelled number calls; ``.hold`` and ``.fail`` are the verdict colours,
#: and a verdict means the same thing wherever one is drawn. Each is a word the
#: design system owns rather than a widget, and sharing them is what keeps a readout
#: on one instrument looking like a readout on the next.
_SHARED_VOCABULARY = {"v", "l", "hold", "fail"}


def _widget_modules():
    return [n for n in sorted(os.listdir(build_site.WEB_DIR))
            if n.endswith(".js") and n not in _NOT_A_WIDGET]


def test_no_class_is_defined_by_both_the_generator_and_a_widget():
    """Two owners, one name, and the loser is whichever rule loses the cascade.

    ``.sz-facts`` was defined twice for a while: by the generator, for the line of
    facts beside the size control, and by ``size.js``, for its row of readouts. The
    widget's ``display:flex`` won, the control's facts came apart, and nothing
    failed -- each rule was used by something. ``plot.js`` carries the same warning
    one level down about style *ids*; this is the class half of it.
    """
    mine = _top_level_classes(build_site.CSS) - _SHARED_VOCABULARY
    for name in _widget_modules():
        theirs = _top_level_classes(_widget_css(build_site.read_web_asset(name)))
        clash = sorted(mine & theirs)
        assert not clash, f"{name} and the stylesheet both define: {clash}"


def test_no_two_widgets_define_the_same_class():
    """The same hazard between two modules, neither of which can see the other."""
    owner = {}
    for name in _widget_modules():
        found = _top_level_classes(_widget_css(build_site.read_web_asset(name)))
        for cls in sorted(found - _SHARED_VOCABULARY):
            assert cls not in owner, f"{name} and {owner[cls]} both define .{cls}"
            owner[cls] = name


def test_the_shared_vocabulary_is_actually_shared():
    """An allow-list nobody prunes is an allow-list that grows.

    Each name here is exempted because more than one file styles it on purpose. If
    only one file still does, it is not shared vocabulary any more and the exemption
    should go rather than sit there covering the next collision.
    """
    counts = {cls: 0 for cls in _SHARED_VOCABULARY}
    sources = [build_site.CSS] + [_widget_css(build_site.read_web_asset(n))
                                  for n in _widget_modules()]
    for css in sources:
        for cls in _top_level_classes(css):
            if cls in counts:
                counts[cls] += 1
    lonely = sorted(c for c, n in counts.items() if n < 2)
    assert not lonely, f"exempted but styled in only one place: {lonely}"


def test_every_widget_injects_its_styles_under_its_own_id():
    """``injectStyle`` is guarded on the id, so two widgets sharing one means the
    second finds the id taken and runs with none of its own CSS -- silently."""
    ids = {}
    for name in sorted(os.listdir(build_site.WEB_DIR)):
        if not name.endswith(".js"):
            continue
        for found in re.findall(r'injectStyle\("([^"]+)"', build_site.read_web_asset(name)):
            assert found not in ids, f"{name} and {ids[found]} both inject #{found}"
            ids[found] = name


@EVERY_PAGE
def test_a_page_that_declares_a_body_class_gets_one(name):
    """The size page redefines a page-wide offset, and needs somewhere to do it.

    This is the check that was missing when the class first failed to be emitted:
    the stylesheet had the rule, the page had the second sticky bar, and every
    anchor on it jumped 56 px short because ``<body>`` carried no class for the
    rule to match. Nothing rendered wrongly; things simply landed in the wrong
    place, which no other assertion here looks at.
    """
    page = next(p for p in build_site.PAGES if p.file == name)
    html = page_html(name)
    if page.body_class:
        assert f'<body class="{page.body_class}">' in html
    else:
        assert "<body>" in html


def test_the_sticky_offset_is_defined_for_every_body_class_that_asks_for_one():
    """A class on <body> with no rule behind it is decoration.

    The pair is load bearing together: the stylesheet redefines ``--sticky`` under
    ``body.sizepage``, the page script reads it off ``document.body``, and anchor
    targets use it. Any one of the three alone does nothing.
    """
    css = build_site.CSS
    for page in build_site.PAGES:
        if not page.body_class:
            continue
        assert re.search(rf"body\.{page.body_class}\s*\{{[^}}]*--sticky", css), (
            f"body.{page.body_class} is emitted but redefines no --sticky"
        )
    assert "getComputedStyle(document.body)" in build_site.PAGE_SCRIPT, (
        "the scrollspy must read --sticky off the element the class is on"
    )


@EVERY_PAGE
def test_the_heading_outline_never_skips_a_level(name):
    """h1 then h3 is a hole in the document outline, and a screen reader falls in it.

    Heading level is how a page is skimmed without looking at it, and the level has
    to follow the outline rather than the look. ``.inst-t`` is a mono micro-label on
    both pages and is an ``h3`` on the index, where each instrument sits under a
    section heading, and an ``h2`` on the size page, where the instruments *are* the
    sections. Same component, same drawing, different depth.

    The footer's headings are excluded: it is a landmark of its own and its three
    ``h2`` columns do not continue the article's outline.
    """
    html = page_html(name)
    body = html[html.index("<main"):html.index("<footer")]
    levels = [int(m) for m in re.findall(r"<h([1-6])\b", body)]
    assert levels and levels[0] == 1, f"{name} does not open on an h1"
    assert levels.count(1) == 1, f"{name} has {levels.count(1)} h1 elements"
    for before, after in zip(levels, levels[1:]):
        assert after <= before + 1, (
            f"{name} goes h{before} -> h{after}, skipping a level"
        )
