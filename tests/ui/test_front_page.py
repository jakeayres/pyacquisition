"""The docs' front page (docs/index.md, hero.css, hero.js): the script beside the
interface it makes, running, in one pane of glass, and the tour between them; and
the setup page's section, "Or build it in a window", with its switcher.

On a small site built in a temporary folder from the front page alone, with the
real config's theme, extensions, stylesheets and scripts, and the interface's
files copied in as the docs build copies them. Skipped without Zensical."""

import re
import shutil
import subprocess
import sys

import pytest

pytest.importorskip("playwright")
pytest.importorskip("zensical")

from playwright.sync_api import expect  # noqa: E402
from ui_helpers import REPO, Page, StaticSite, copy_interface  # noqa: E402

WIDE = {"width": 1440, "height": 900}
LAPTOP = {"width": 1280, "height": 800}
TABLET = {"width": 1024, "height": 768}
PHONE = {"width": 390, "height": 844}

# The tour's steps: a line each starts at, how many lines, and how many parts of
# the interface it outlines (hero.js).
STEPS = [
    ("class MyExperiment", 1, 1),
    ("data_path", 1, 1),
    ('Clock("clock")', 3, 2),
    ('SR_830("lockin"', 4, 4),
    ('Lakeshore_350("lakeshore"', 10, 2),
    ("if __name__", 2, 2),
]


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    root = tmp_path_factory.mktemp("front_page")
    docs = root / "docs"
    docs.mkdir()
    shutil.copy(REPO / "docs" / "index.md", docs)
    for folder in ("stylesheets", "javascripts"):
        shutil.copytree(REPO / "docs" / folder, docs / folder)
    shutil.copytree(REPO / "docs" / "demo", docs / "demo", ignore=shutil.ignore_patterns("app"))
    copy_interface(docs / "demo" / "app")
    (root / "examples").mkdir()
    for name in ("front_page.py", "front_page.toml"):
        shutil.copy(REPO / "examples" / name, root / "examples")
    shutil.copytree(REPO / "docs" / "images" / "front_page", docs / "images" / "front_page")

    # The real config, with only the front page in it, no API reference to build,
    # and no repository to ask GitHub about.
    config = (REPO / "zensical.toml").read_text(encoding="utf-8")
    head = config[: config.index("nav = [")]
    head = "\n".join(line for line in head.splitlines() if not line.startswith("repo_"))
    theme = config[config.index("[project.theme]") : config.index("[project.plugins")]
    markdown = config[config.index("[project.markdown_extensions]") :]
    (root / "zensical.toml").write_text(
        f'{head}\nnav = [{{ "Overview" = "index.md" }}]\n\n{theme}{markdown}', encoding="utf-8"
    )
    subprocess.run(
        [sys.executable, "-m", "zensical", "build", "--clean"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    served = StaticSite(root / "site")
    yield served
    served.stop()


def front(browser, site, viewport=WIDE, still=False, before=None):
    """The front page, with its interface live. `before(page)` runs before it loads."""
    context = browser.new_context(
        viewport=viewport, reduced_motion="reduce" if still else "no-preference"
    )
    page = Page(context.new_page())
    if before:
        before(page.page)
    page.page.goto(f"{site.address}/")
    page.context = context
    return page


def live(page):
    """Waits for the interface to be live, and the glass to have risen into place."""
    page.page.wait_for_function(
        "document.querySelector('.pa-window__view iframe')"
        "?.contentWindow?.pyacquisition?.store?.status === 'live'"
    )
    page.page.wait_for_function(
        "document.querySelector('.pa-stage').getAnimations()"
        ".every((a) => a.playState === 'finished')"
    )


def frame(page):
    return page.page.frame_locator(".pa-window__view iframe")


def scale(page):
    return float(
        page.page.evaluate(
            "getComputedStyle(document.querySelector('.pa-stage')).getPropertyValue('--pa-scale')"
        )
    )


def boxes(page, selector):
    return page.page.locator(selector).bounding_box()


# ------------------------------------------------------------ the hero
def test_the_hero_runs_the_interface_beside_the_script(browser, site):
    page = front(browser, site)
    live(page)

    expect(page.page.locator("h1")).to_contain_text("Write only the science.")
    expect(page.page.locator(".pa-stage__code")).to_contain_text("class MyExperiment")
    expect(frame(page).locator(".brand-name")).to_have_text("MyExperiment")
    expect(page.page.locator(".pa-window__label")).to_have_text("Simulated instruments")

    code, app = boxes(page, ".pa-stage__code"), boxes(page, ".pa-window")
    assert app["x"] > code["x"] + code["width"], "they should be side by side"
    assert code["y"] < WIDE["height"] and app["y"] < WIDE["height"], "both start in view"
    assert scale(page) >= 0.7
    assert page.errors == []
    page.context.close()


@pytest.mark.parametrize("viewport", [WIDE, LAPTOP], ids=["1440", "1280"])
def test_side_by_side_the_interface_is_never_drawn_below_0_7(browser, site, viewport):
    page = front(browser, site, viewport)
    live(page)
    code, app = boxes(page, ".pa-stage__code"), boxes(page, ".pa-window")
    assert app["x"] > code["x"] + code["width"]
    assert scale(page) >= 0.7
    page.context.close()


def test_all_four_value_tiles_show_in_one_row(browser, site):
    # The tour points at each of them, so none may wrap out of view.
    page = front(browser, site)
    live(page)
    tops = [
        frame(page).locator(f'[data-column="{name}"]').bounding_box()["y"]
        for name in ("time", "x", "y", "T")
    ]
    assert max(tops) - min(tops) < 5, tops  # a tile in a second row is ~100 px lower
    page.context.close()


def test_the_glass_hangs_over_the_page_below_the_band(browser, site):
    page = front(browser, site)
    live(page)
    band = page.page.evaluate(
        """() => {
          const hero = document.querySelector('.pa-live');
          const overhang = parseFloat(getComputedStyle(hero, '::before').bottom);
          return hero.getBoundingClientRect().bottom - overhang;
        }"""
    )
    glass = boxes(page, ".pa-stage")
    assert glass["y"] < band < glass["y"] + glass["height"]
    page.context.close()


def test_narrower_the_interface_comes_first_then_the_script(browser, site):
    page = front(browser, site, TABLET)
    live(page)
    code, app = boxes(page, ".pa-stage__code"), boxes(page, ".pa-window")
    assert app["y"] + app["height"] <= code["y"]
    assert scale(page) >= 0.7
    page.context.close()


def test_on_a_phone_the_interface_is_a_picture_with_a_way_in(browser, site):
    page = front(browser, site, PHONE)
    live(page)
    events = page.page.evaluate(
        "getComputedStyle(document.querySelector('.pa-window__view iframe')).pointerEvents"
    )
    assert events == "none"
    expect(page.page.get_by_role("link", name="Open it full size")).to_be_visible()
    page.context.close()


def test_the_demo_is_held_while_the_hero_is_out_of_view(browser, site):
    page = front(browser, site)
    live(page)
    held = "document.querySelector('.pa-window__view iframe').contentWindow.pyacquisitionDemo.held"

    page.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.page.wait_for_function(held)
    page.page.evaluate("window.scrollTo(0, 0)")
    page.page.wait_for_function(f"!{held}")
    page.context.close()


def test_the_lights_and_the_rows_wait_while_the_page_scrolls(browser, site):
    page = front(browser, site)
    live(page)
    held = "document.querySelector('.pa-window__view iframe').contentWindow.pyacquisitionDemo.held"
    page.page.evaluate("window.scrollBy(0, 40)")
    page.page.wait_for_function(held, polling="raf")  # the scroll event comes a frame later
    expect(page.page.locator(".pa-live")).to_have_attribute("data-scrolling", "")
    page.page.wait_for_function(f"!{held}")  # a moment after it stops
    expect(page.page.locator(".pa-live")).not_to_have_attribute("data-scrolling", "")
    page.context.close()


def test_without_the_interfaces_files_the_hero_says_how_to_copy_them(browser, site):
    def missing(page):
        page.route(
            "**/demo/app/js/main.js",
            lambda route: route.fulfill(status=404)
            if route.request.method == "HEAD"
            else route.continue_(),
        )

    page = front(browser, site, before=missing)
    expect(page.page.locator(".pa-window__missing")).to_contain_text("copytree")
    page.context.close()


# ------------------------------------------------------------ the tour
def shown(page):
    """The tour as drawn: its lit lines, its boxes, and whether its line ends on
    a box."""
    return page.page.evaluate(
        """() => {
          const stage = document.querySelector('.pa-stage');
          const lines = [...stage.querySelectorAll('.pa-stage__code code > span.pa-on')];
          const rects = [...stage.querySelectorAll('.pa-tour .box')].map((r) => ({
            x: +r.getAttribute('x'), y: +r.getAttribute('y'),
            w: +r.getAttribute('width'), h: +r.getAttribute('height'),
          }));
          const link = stage.querySelector('.pa-tour .link');
          let ends = null;
          if (link) {
            const n = link.getAttribute('d').trim().split(/[ ,]+/).map(Number);
            const [x, y] = n.slice(-2);
            ends = rects.some((r) => x >= r.x - 1 && x <= r.x + r.w && y >= r.y && y <= r.y + r.h);
          }
          return {
            first: lines[0]?.textContent ?? null,
            lines: lines.length,
            boxes: rects.length,
            ends,
          };
        }"""
    )


def line(page, text):
    return page.page.locator(".pa-stage__code code > span", has_text=text).first


@pytest.mark.parametrize("start, lines, parts", STEPS, ids=[s[0] for s in STEPS])
def test_each_step_joins_its_lines_to_what_they_make(browser, site, start, lines, parts):
    page = front(browser, site)
    live(page)
    frame(page).locator('[data-column="T"]').wait_for()

    line(page, start).hover()
    page.page.wait_for_timeout(150)
    tour = shown(page)

    assert start in tour["first"]
    assert tour["lines"] == lines
    assert tour["boxes"] == parts
    assert tour["ends"] is True, "the line should end on what the lines make"
    page.context.close()


def use(page):
    """Clicks into the interface, which the page scrolls over until then."""
    page.page.locator(".pa-window__shield").click()
    expect(page.page.locator(".pa-window__view")).to_have_class(re.compile("is-active"))


def test_the_page_scrolls_over_the_interface_until_it_is_clicked(browser, site):
    page = front(browser, site)
    live(page)
    events = "getComputedStyle(document.querySelector('.pa-window__view iframe')).pointerEvents"
    assert page.page.evaluate(events) == "none"
    # The wheel over the interface scrolls the page, not its plots.
    box = boxes(page, ".pa-window__view")
    page.page.mouse.move(box["x"] + box["width"] / 2, box["y"] + 60)
    page.page.mouse.wheel(0, 300)
    page.page.wait_for_function("window.scrollY > 100")

    page.page.evaluate("window.scrollTo(0, 0)")
    use(page)
    assert page.page.evaluate(events) == "auto"
    page.page.mouse.move(5, 5)  # leaving it, it goes back to letting the page scroll
    expect(page.page.locator(".pa-window__view")).not_to_have_class(re.compile("is-active"))
    page.context.close()


def test_hovering_the_interface_lights_the_lines_that_made_it(browser, site):
    page = front(browser, site)
    live(page)
    use(page)
    frame(page).locator('[data-column="T"]').hover()
    page.page.wait_for_timeout(150)
    assert 'Lakeshore_350("lakeshore"' in shown(page)["first"]
    page.context.close()


def test_the_tour_moves_by_itself_and_stops_when_the_interface_is_used(browser, site):
    page = front(browser, site)
    live(page)
    page.page.wait_for_selector(".pa-stage[data-touring]")
    first = shown(page)["first"]
    page.page.wait_for_function(
        "(first) => document.querySelector('.pa-stage__code span.pa-on')?.textContent !== first",
        arg=first,
        timeout=6000,
    )

    use(page)
    expect(page.page.locator(".pa-stage")).not_to_have_attribute("data-touring", "")
    assert shown(page)["lines"] == 0
    page.context.close()


def test_with_reduced_motion_the_tour_waits_to_be_asked(browser, site):
    page = front(browser, site, still=True)
    live(page)
    page.page.wait_for_timeout(3500)
    assert shown(page)["lines"] == 0

    line(page, 'SR_830("lockin"').hover()
    expect(page.page.locator(".pa-stage")).to_have_attribute("data-touring", "")
    page.context.close()


def test_stacked_the_tour_outlines_but_draws_no_lines(browser, site):
    page = front(browser, site, TABLET)
    live(page)
    frame(page).locator('[data-column="T"]').wait_for()
    line(page, 'SR_830("lockin"').hover()
    page.page.wait_for_timeout(150)

    assert shown(page)["boxes"] == 4
    display = page.page.evaluate(
        "getComputedStyle(document.querySelector('.pa-tour .link')).display"
    )
    assert display == "none"
    page.context.close()


# ------------------------------------------------------------ the setup page
def switch_state(page):
    return page.page.evaluate(
        """() => ({
          tab: [...document.querySelectorAll('.pa-switch [role=tab]')]
            .findIndex((t) => t.getAttribute('aria-selected') === 'true'),
          shot: [...document.querySelectorAll('.pa-device img')]
            .findIndex((i) => i.classList.contains('is-on')),
        })"""
    )


def test_the_setup_section_shows_the_setup_page(browser, site):
    page = front(browser, site)
    section = page.page.locator(".pa-setup")
    section.scroll_into_view_if_needed()
    expect(section.locator("h2")).to_have_text("Or build it in a window.")
    expect(section.locator(".pa-setup__cmd")).to_contain_text("uv run pyacquisition new rig.toml")
    expect(section.get_by_role("tab")).to_have_count(3)
    shot = section.locator(".pa-device img.is-on")
    expect(shot).to_be_visible()
    page.page.wait_for_function(
        "document.querySelector('.pa-device img.is-on').naturalWidth > 0"
    )
    page.context.close()


def test_a_tab_shows_its_picture(browser, site):
    page = front(browser, site)
    page.page.locator(".pa-setup").scroll_into_view_if_needed()
    page.page.get_by_role("tab", name="Checked as you type").click()
    assert switch_state(page) == {"tab": 2, "shot": 2}

    page.page.keyboard.press("ArrowUp")
    assert switch_state(page) == {"tab": 1, "shot": 1}
    expect(page.page.get_by_role("tab", name="Choose what to measure")).to_be_focused()
    page.context.close()


def test_the_tabs_go_round_by_themselves_in_view(browser, site):
    page = front(browser, site)
    page.page.mouse.move(0, 0)
    page.page.locator(".pa-switch").scroll_into_view_if_needed()
    expect(page.page.locator(".pa-switch")).to_have_attribute("data-playing", "")
    page.page.wait_for_function(
        "document.querySelector('.pa-switch [aria-selected=true]').id === 'pa-setup-tab-2'",
        timeout=9000,
    )
    page.context.close()


def test_with_reduced_motion_the_tabs_wait_to_be_chosen(browser, site):
    page = front(browser, site, still=True)
    page.page.locator(".pa-switch").scroll_into_view_if_needed()
    page.page.wait_for_timeout(1500)
    expect(page.page.locator(".pa-switch")).not_to_have_attribute("data-playing", "")
    assert switch_state(page) == {"tab": 0, "shot": 0}
    page.context.close()

