# Contributing to PyAcquisition

Thank you for helping. Bug reports, instrument drivers, fixes and improvements
to the documentation are all welcome. For anything more than a small fix, open
an issue first, so that the approach can be agreed before you spend time on it.

## The license of your contribution

PyAcquisition is under the [Mozilla Public License 2.0](LICENSE) (MPL-2.0), and
a contribution to it is under the MPL-2.0 too. You keep the copyright in your
contribution, and the git history records who wrote what.

- A new file under `src/` starts with the same notice as the files beside it:
  the SPDX identifier, the copyright line and the MPL's notice. A test checks
  that every file has it.
- Code in `examples/` is dedicated to the public domain under CC0 1.0 (see
  [examples/LICENSE](examples/LICENSE)), so that users can copy it into their
  own work freely.

## Sign off every commit

Each commit carries a line that certifies the Developer Certificate of Origin
1.1, below: that you wrote the change, or otherwise have the right to submit it
under the project's license.

```text
Signed-off-by: Your Name <you@example.org>
```

`git commit -s` adds it, with the name and email in your git configuration.
For commits you have already made, `git rebase --signoff main` adds it, and
then push again. A pull request with a commit that isn't signed off can't be
taken in.

```text
Developer Certificate of Origin
Version 1.1

Copyright (C) 2004, 2006 The Linux Foundation and its contributors.

Everyone is permitted to copy and distribute verbatim copies of this
license document, but changing it is not allowed.


Developer's Certificate of Origin 1.1

By making a contribution to this project, I certify that:

(a) The contribution was created in whole or in part by me and I
    have the right to submit it under the open source license
    indicated in the file; or

(b) The contribution is based upon previous work that, to the best
    of my knowledge, is covered under an appropriate open source
    license and I have the right under that license to submit that
    work with modifications, whether created in whole or in part
    by me, under the same open source license (unless I am
    permitted to submit under a different license), as indicated
    in the file; or

(c) The contribution was provided directly to me by some other
    person who certified (a), (b) or (c) and I have not modified
    it.

(d) I understand and agree that this project and the contribution
    are public and that a record of the contribution (including all
    personal information I submit with it, including my sign-off) is
    maintained indefinitely and may be redistributed consistent with
    this project or the open source license(s) involved.
```

## Making the change

- Set up with `uv sync --all-groups`.
- Check it with `uv run ruff check .` and `uv run pytest tests`. The browser
  tests in `tests/ui/` need Microsoft Edge.
- Keep a pull request to one change, with a message that says what changed and
  why.

## Previewing the docs

Preview the docs with `uv run zensical serve`. The front page runs the real
interface, from a copy of its files that the docs build makes. Make the copy
yourself before you preview, and again after changing the interface:

```
uv run python -c "import shutil; shutil.copytree('src/pyacquisition/gui/static', 'docs/demo/app', dirs_exist_ok=True)"
```

`docs/demo/app/` is not committed.
