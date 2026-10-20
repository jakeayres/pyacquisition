# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2023-2026 Jake Ayres
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""What PyAcquisition is, as the interface's About (`GET /about`) and a built
app's NOTICE.txt (`pyacquisition build`) say it: its name, the version, its
license, copyright and source, and the libraries its interface uses. Written
once, here, so that the two can't disagree."""

import textwrap

from ..gui import STATIC_DIR
from .news import installed_version

NAME = "PyAcquisition"
LICENSE = "MPL-2.0"
LICENSE_NAME = "Mozilla Public License 2.0"
MPL_URL = "https://mozilla.org/MPL/2.0/"
COPYRIGHT = "Copyright (C) 2023-2026 Jake Ayres"
SOURCE_URL = "https://github.com/jakeayres/pyacquisition"
LICENSE_URL = "https://pyacquisition.readthedocs.io/en/latest/overview/license/"

# The libraries the interface uses, shipped with it in gui/static/vendor/<folder>,
# each with its LICENSE there.
LIBRARIES = (
    {"name": "Preact", "license": "MIT", "folder": "preact"},
    {"name": "uPlot", "license": "MIT", "folder": "uplot"},
    {"name": "htm", "license": "Apache-2.0", "folder": "htm"},
)


def about() -> dict:
    """What `GET /about` answers: the facts above, and the `version` running
    (None when it isn't known)."""
    return {
        "name": NAME,
        "version": installed_version(),
        "license": LICENSE,
        "license_name": LICENSE_NAME,
        "copyright": COPYRIGHT,
        "source_url": SOURCE_URL,
        "license_url": LICENSE_URL,
        "libraries": [{"name": lib["name"], "license": lib["license"]} for lib in LIBRARIES],
    }


def notice(version: str | None) -> str:
    """The text of NOTICE.txt, which `pyacquisition build` writes beside an app,
    for anyone it is given to: the PyAcquisition version it was made with, its
    license and where its source is, that the experiment's own files are its
    author's, and the full licenses of the libraries its interface uses, which
    they ask to go with every copy.

    Args:
        version: The PyAcquisition version the app was made with, or None if
            it isn't known.
    """
    names = [f"{lib['name']} ({lib['license']})" for lib in LIBRARIES]
    libraries = f"{', '.join(names[:-1])} and {names[-1]}"
    rule = "=" * 72
    lines = [
        f"{NAME} {version}" if version else f"{NAME} (version unknown)",
        COPYRIGHT,
        "",
        f"This app was made with {NAME}, which is free software under the",
        f"{LICENSE_NAME} ({LICENSE}): {MPL_URL}",
        f"Its source code is at {SOURCE_URL}",
        "",
        "The experiment's own files (its config file, script and modules) are its",
        "author's, under whatever license they chose.",
        "",
        "The app also contains:",
        "",
        textwrap.fill(
            f"- {libraries}, which draw {NAME}'s interface. Their licenses follow "
            "in full.",
            width=74,
            subsequent_indent="  ",
        ),
        "- Python, and the packages PyAcquisition and the experiment use, each under",
        "  its own license.",
    ]
    for lib in LIBRARIES:
        text = (STATIC_DIR / "vendor" / lib["folder"] / "LICENSE").read_text(encoding="utf-8")
        lines += ["", rule, lib["name"], rule, "", text.strip()]
    return "\n".join(lines) + "\n"
