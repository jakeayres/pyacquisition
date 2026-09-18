# Contribute to `pyacquisition`

`pyacquisition` will **always be free**. Contributions of all kinds are welcome. These can include contibutions to the main code base, improving the documentation (including tranlators), and other kinds. Contributions from beginners are equally welcomed.


## Forking workflow

Fork away.

## Bug reports

Raise an issue on github. If possible, please provide a minimal example that reproduces the bug.


## Building the documentation

The documentation is built with [Zensical](https://zensical.org/) and configured in `zensical.toml`. Set up the environment (this installs the documentation tools along with everything else you need to develop `pyacquisition`):

```
uv sync
```

Then preview the site while you edit. It rebuilds and reloads whenever you save a file:

```
uv run zensical serve
```

The preview is served at [http://localhost:8000](http://localhost:8000). If an experiment is already using that port, pick another with `uv run zensical serve -a localhost:8001`.

To build the site once, into the `site/` folder, run `uv run zensical build`.

The pages under **Experiment API** and **Instruments** are generated from the docstrings in the source code, so the best way to improve them is to improve the docstrings.


## Releasing a new version

The version number comes from the git tag, so there is nothing to edit in `pyproject.toml`. To release, make sure your changes are on `main` and pushed, then tag the latest commit and push the tag:

```
git tag v0.2.0
git push origin v0.2.0
```

Pushing the tag starts the **Publish to PyPI** workflow. It builds the package with that version, refuses to continue if the version is not a clean release number, and uploads it to PyPI using [Trusted Publishing](https://docs.pypi.org/trusted-publishers/), so no token is stored anywhere. Follow it under the **Actions** tab on GitHub.

- The tag must start with `v` and must be higher than the last release. PyPI never accepts the same version twice.
- Tag the latest commit of `main`. A tag on an older commit, or a build with uncommitted changes, would produce a development version such as `0.2.1.dev3+g1a2b3c4`, and the workflow stops rather than publish it.
- Between releases, the version you see locally is a development version. That is expected.

