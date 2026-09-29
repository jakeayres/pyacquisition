"""The docs' walkthroughs (Getting Started's pages and the Usage tutorials): each file
a page builds is the example it is meant to be, and each step is written to the same
rules. docs/javascripts/walkthrough.js is what shows them."""

import re
from dataclasses import dataclass, field
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
EXAMPLES = ROOT / "examples"
TABLE = re.compile(r"\[([^\]]+)\]")

# Titles that say too little to read alone in the contents
VAGUE = {"run it", "measure it", "register it", "do it", "try it", "measure faster", "add a column"}


@dataclass
class Block:
    language: str
    title: str
    body: str  # the text, or the path an include takes it from
    included: bool


@dataclass
class Step:
    title: str
    text: str
    blocks: list = field(default_factory=list)


@dataclass
class Walkthrough:
    page: Path
    files: dict  # name: mode
    steps: list

    @property
    def examples(self) -> Path:
        """Where the page's example files are."""
        name = self.page.relative_to(DOCS).as_posix()
        if name.startswith("getting_started/"):
            return EXAMPLES / "getting_started"
        return EXAMPLES / "usage" / self.page.stem

    def blocks_of(self, name: str) -> list:
        """The blocks that build a file, in order: those it titles, or with no title,
        the first file's."""
        first = next(iter(self.files))
        return [
            (i, block) for i, step in enumerate(self.steps) for block in step.blocks
            if block.language not in ("bash", "text") and (block.title or first) == name
        ]


def walkthrough(page: Path) -> Walkthrough:
    """A page's walkthrough, read from its Markdown as walkthrough.js reads its HTML."""
    text = page.read_text(encoding="utf-8")
    attrs = re.search(r'<div class="gs"([^>]*)>', text)[1]
    declared = re.search(r'data-files="([^"]*)"', attrs)
    if declared:
        files = {}
        for entry in declared[1].split():
            name, _, mode = entry.partition(":")
            files[name] = mode or "versions"
    else:
        name = re.search(r'data-file="([^"]*)"', attrs)
        mode = re.search(r'data-mode="([^"]*)"', attrs)
        files = {name[1] if name else "rig.toml": "versions" if mode and mode[1] == "versions" else "merge"}
    steps = []
    for body in re.findall(r'<section class="gs-step"[^>]*>(.*?)</section>', text, flags=re.S):
        title = re.search(r"^## (.+)$", body, flags=re.M)
        step = Step(title[1].strip() if title else "", body)
        # A step's own blocks start at the line's start. Those in an aside are indented.
        for language, info, content in re.findall(r"^```(\w+)([^\n]*)\n(.*?)^```", body, flags=re.S | re.M):
            name = re.search(r'title="([^"]+)"', info)
            include = re.fullmatch(r'--8<-- "([^"]+)"\s*', content)
            step.blocks.append(Block(language, name[1] if name else "", include[1] if include else content,
                                     bool(include)))
        steps.append(step)
    return Walkthrough(page, files, steps)


PAGES = sorted(p for p in DOCS.rglob("*.md") if '<div class="gs"' in p.read_text(encoding="utf-8"))
WALKTHROUGHS = [walkthrough(p) for p in PAGES]
IDS = [w.page.relative_to(DOCS).as_posix() for w in WALKTHROUGHS]


def merged(snippets: list) -> str:
    """The TOML file a walkthrough builds from its snippets, as walkthrough.js builds it:
    a line under a table that is there already goes at its end, and a new table goes
    after its family ([instruments.lockin] after [instruments]), or at the end."""
    rows = []
    for snippet in snippets:
        blocks = []
        for line in snippet.splitlines():
            line = line.rstrip()
            header = TABLE.fullmatch(line)
            if header:
                blocks.append((header.group(1), line, []))
            elif line and blocks:
                blocks[-1][2].append(line)
        for name, header, lines in blocks:
            tables = []  # each table's name, and the row after its last line
            for i, row in enumerate(rows):
                found = TABLE.fullmatch(row)
                if found:
                    tables.append([found.group(1), i + 1])
                elif row and tables:
                    tables[-1][1] = i + 1
            same = [end for table, end in tables if table == name]
            if same:
                rows[same[0] : same[0]] = lines
                continue
            family = name.split(".")[0]
            ends = [end for table, end in tables if table.split(".")[0] == family]
            at = ends[-1] if ends else len(rows)
            rows[at:at] = ([""] if rows else []) + [header, *lines]
    return "\n".join(rows) + "\n"


def content(block: Block) -> str:
    return (ROOT / block.body).read_text(encoding="utf-8") if block.included else block.body


def test_there_are_walkthroughs_to_check():
    assert {"getting_started/installation.md", "getting_started/config_file.md",
            "getting_started/python_api.md"} <= set(IDS)


# -------------------------------------------------------------- the files
@pytest.mark.parametrize("w", WALKTHROUGHS, ids=IDS)
def test_each_block_is_for_a_file_the_walkthrough_lists(w):
    for step in w.steps:
        for block in step.blocks:
            if block.language in ("bash", "text"):
                continue
            assert w.files, f"{step.title}: a {block.language} block in a walkthrough with no files"
            assert (block.title or next(iter(w.files))) in w.files, f"{step.title}: {block.title}"


@pytest.mark.parametrize("w", WALKTHROUGHS, ids=IDS)
def test_each_merged_file_is_its_example(w):
    for name, mode in w.files.items():
        if mode != "merge":
            continue
        built = merged([content(block) for _, block in w.blocks_of(name)])
        example = name if (w.examples / name).exists() else None
        assert example, f"{w.examples / name} is missing: the file the page builds should be an example"
        assert built == (w.examples / name).read_text(encoding="utf-8")


@pytest.mark.parametrize("w", [w for w in WALKTHROUGHS if "usage/" in w.page.as_posix()],
                         ids=[i for i in IDS if i.startswith("usage/")])
def test_each_version_in_a_usage_tutorial_is_an_example(w):
    """So that each is run by the tests, and none can be broken on the page."""
    folder = w.examples.relative_to(ROOT).as_posix()
    for name, mode in w.files.items():
        if mode != "versions":
            continue
        for _, block in w.blocks_of(name):
            assert block.included, f"{name}: a version written on the page"
            assert block.body.startswith(folder + "/"), f"{block.body} isn't in {folder}"


# -------------------------------------------------------------- the steps
@pytest.mark.parametrize("w", WALKTHROUGHS, ids=IDS)
def test_each_step_has_a_title_a_note_and_a_more_line(w):
    assert w.steps
    for number, step in enumerate(w.steps, 1):
        assert step.title, f"step {number} has no title"
        prose = [p for p in re.split(r"\n\s*\n", step.text) if p.strip() and not p.lstrip().startswith(("```", "#", "<", "{", "?", "!", "**More:**", "--8<--"))]
        assert prose, f"{step.title}: no note"
        assert re.search(r"^\*\*More:\*\* .+\n\{ \.gs-more \}$", step.text, flags=re.M), f"{step.title}: no More line"


@pytest.mark.parametrize("w", WALKTHROUGHS, ids=IDS)
def test_no_step_title_is_vague(w):
    for step in w.steps:
        assert step.title.lower() not in VAGUE, step.title
