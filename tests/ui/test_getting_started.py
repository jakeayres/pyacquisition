"""Getting Started's walkthroughs with the interface (docs/getting_started/,
walkthrough.js): at each step of "1. The Config File" and "2. The Python API", the
interface as the file then makes it, from a recording, with what the step made
outlined; and "What you built", live, with its legend.

On a small site built in a temporary folder from Getting Started's pages alone,
with the real config's theme, extensions, stylesheets and scripts, and the
interface's files copied in as the docs build copies them. Skipped without
Zensical."""

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
PHONE = {"width": 390, "height": 844}
PAGES = ["installation", "config_file", "python_api"]


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    root = tmp_path_factory.mktemp("getting_started")
    docs = root / "docs"
    (docs / "getting_started").mkdir(parents=True)
    for name in PAGES:
        shutil.copy(REPO / "docs" / "getting_started" / f"{name}.md", docs / "getting_started")
    for folder in ("stylesheets", "javascripts"):
        shutil.copytree(REPO / "docs" / folder, docs / folder)
    shutil.copytree(REPO / "docs" / "demo", docs / "demo", ignore=shutil.ignore_patterns("app"))
    copy_interface(docs / "demo" / "app")
    (docs / "index.md").write_text("# Getting Started\n", encoding="utf-8")
    shutil.copytree(
        REPO / "examples" / "getting_started",
        root / "examples" / "getting_started",
        ignore=shutil.ignore_patterns("__pycache__"),
    )

    # The real config, with only these pages in it, no API reference to build,
    # and no repository to ask GitHub about.
    config = (REPO / "zensical.toml").read_text(encoding="utf-8")
    head = config[: config.index("nav = [")]
    head = "\n".join(line for line in head.splitlines() if not line.startswith("repo_"))
    theme = config[config.index("[project.theme]") : config.index("[project.plugins")]
    markdown = config[config.index("[project.markdown_extensions]") :]
    nav = ", ".join(f'{{ "{name}" = "getting_started/{name}.md" }}' for name in PAGES)
    (root / "zensical.toml").write_text(
        f'{head}\nnav = [{{ "Home" = "index.md" }}, {nav}]\n\n{theme}{markdown}',
        encoding="utf-8",
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


def opened(browser, site, name, viewport=WIDE, still=False):
    context = browser.new_context(
        viewport=viewport, reduced_motion="reduce" if still else "no-preference"
    )
    page = Page(context.new_page())
    page.page.goto(f"{site.address}/getting_started/{name}/")
    page.context = context
    return page


def go(page, k):
    """Scrolls to step k (from 0), as the contents' links do."""
    page.page.evaluate(
        """(k) => {
          const root = document.querySelector('.gs'), stage = root.querySelector('.gs-stage');
          const steps = root.querySelectorAll('.gs-notes > .gs-step');
          const pinned = parseFloat(getComputedStyle(stage).top) || 0;
          const travel = root.offsetHeight - stage.offsetHeight;
          window.scrollTo(0, window.scrollY + root.getBoundingClientRect().top - pinned
            + ((k + 0.5) / steps.length) * travel);
        }""",
        k,
    )


def shown(page, session):
    """Waits for the step's recording to be the one shown, live, and settled; gives
    its frame."""
    page.page.wait_for_function(
        """(session) => {
          const frame = document.querySelector('.gs-app__frame.is-on');
          return !!frame && frame.src.endsWith('session=' + session)
            && frame.contentWindow.pyacquisition?.store?.status === 'live';
        }""",
        arg=session,
        timeout=20000,
    )
    page.page.wait_for_timeout(700)
    return page.page.frame_locator(".gs-app__frame.is-on")


def outlined(page, where=".gs-panels"):
    page.page.wait_for_function(
        "(where) => document.querySelectorAll(where + ' .gs-outline .box').length > 0",
        arg=where,
    )


# ------------------------------------------------------------ part 1
STEPS_1 = [
    ("config-1", None, ".brand-name"),
    ("config-2", "Instruments", ".instrument-item"),
    ("config-3", "Values", '[data-column="time"]'),
    ("config-4", "Values", '[data-column="wave"]'),
    ("config-5", "Values", ".rack-control"),
    ("config-6", "Instruments", ".instrument-item"),
    ("config-6", "Values", ".file-control"),
]


@pytest.mark.parametrize(
    "k, step", list(enumerate(STEPS_1)), ids=[f"{i + 1}-{s[0]}" for i, s in enumerate(STEPS_1)]
)
def test_each_step_shows_what_its_file_makes(browser, site, k, step):
    session, view, part = step
    page = opened(browser, site, "config_file")
    go(page, k)
    frame = shown(page, session)
    if view:
        expect(frame.get_by_role("tab", name=view)).to_have_attribute("aria-selected", "true")
    expect(frame.locator(part).first).to_be_visible()
    outlined(page)
    assert page.errors == []
    page.context.close()


def test_a_steps_line_joins_its_new_lines_to_what_they_made(browser, site):
    page = opened(browser, site, "config_file")
    go(page, 2)
    shown(page, "config-3")
    page.page.wait_for_function("!!document.querySelector('.gs-panels .gs-outline .link')")
    page.context.close()


def test_the_hardware_step_shows_the_lockins_menus(browser, site):
    page = opened(browser, site, "config_file")
    go(page, 5)
    frame = shown(page, "config-6")
    # get_x is the lock-in's, not the clock's or the signal generator's
    expect(frame.get_by_role("button", name="get_x", exact=True)).to_be_visible()
    page.context.close()


# ------------------------------------------------------------ part 2
def test_setup_sets_the_frequency_and_the_interface_reads_it(browser, site):
    page = opened(browser, site, "python_api")
    go(page, 1)
    frame = shown(page, "python-2")
    expect(frame.locator(".result-value").first).to_have_text("137")
    page.context.close()


def test_a_calculation_adds_its_column(browser, site):
    page = opened(browser, site, "python_api")
    go(page, 3)
    frame = shown(page, "python-4")
    expect(frame.locator('[data-column="power"]')).to_be_visible()
    expect(frame.locator(".series-chip", has_text="power")).to_be_visible()
    page.context.close()


def test_a_registered_task_is_offered_in_add_task(browser, site):
    page = opened(browser, site, "python_api")
    go(page, 5)
    frame = shown(page, "python-6")
    expect(frame.locator(".task-option", has_text="Record")).to_be_visible()
    expect(frame.locator(".task-form-title")).to_have_text("Record")
    page.context.close()


def test_the_task_runs_into_its_files(browser, site):
    page = opened(browser, site, "python_api")
    go(page, 6)
    frame = shown(page, "python-7")
    expect(frame.locator(".running-task")).to_contain_text("Record")
    expect(frame.locator(".file-control .topbar-chip")).to_contain_text("run")
    page.context.close()


# ------------------------------------------------------------ what you built
@pytest.mark.parametrize("name", ["config_file", "python_api"])
def test_what_you_built_runs_and_its_legend_points(browser, site, name):
    page = opened(browser, site, name)
    built = page.page.locator(".pa-built")
    built.scroll_into_view_if_needed()
    expect(built).to_have_class(re.compile("is-live"), timeout=20000)
    built.locator("li").first.hover()
    expect(built.locator("li").first).to_have_class(re.compile("is-on"))
    outlined(page, ".pa-built")
    assert page.errors == []
    page.context.close()


def test_with_reduced_motion_the_legend_waits_to_be_pointed_at(browser, site):
    page = opened(browser, site, "config_file", still=True)
    built = page.page.locator(".pa-built")
    built.scroll_into_view_if_needed()
    expect(built).to_have_class(re.compile("is-live"), timeout=20000)
    page.page.mouse.move(0, 0)
    page.page.wait_for_timeout(1500)
    expect(built.locator("li.is-on")).to_have_count(0)
    page.context.close()


# ------------------------------------------------------------ a phone
def test_on_a_phone_the_steps_load_no_interface(browser, site):
    page = opened(browser, site, "config_file", viewport=PHONE)
    page.page.wait_for_timeout(1500)
    sources = page.page.evaluate("[...document.querySelectorAll('.gs-app__frame')].map((f) => f.src)")
    assert all(not source for source in sources)
    built = page.page.locator(".pa-built")
    built.scroll_into_view_if_needed()
    expect(built).to_have_class(re.compile("is-live"), timeout=20000)
    page.context.close()


def test_installation_has_no_interface(browser, site):
    page = opened(browser, site, "installation")
    expect(page.page.locator(".gs-panel--app")).to_have_count(0)
    expect(page.page.locator(".pa-built")).to_have_count(0)
    page.context.close()
