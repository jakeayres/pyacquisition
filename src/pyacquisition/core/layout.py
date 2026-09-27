"""The GUI's layout (its plots, the dock and the theme chosen), kept by the
experiment so it comes back on the next run.

It lives in a file on the server, not in the browser: the app's window starts
afresh each run, and a file also works in a frozen app. The file is
`.pyacquisition/layout.json` under `root_path`, holding each experiment's
layout by its name, so experiments that share a folder keep their own.
"""

import json
from pathlib import Path

from fastapi import Body, HTTPException

from .logging import logger

MAX_BYTES = 1_000_000  # far more than a layout needs; a guard against mistakes


class Layout:
    """One experiment's layout, in the shared file."""

    def __init__(self, root: Path, name):
        """
        Args:
            root (Path): The experiment's root folder.
            name: Its name, or a function giving it (it can change before the
                experiment runs, as `from_config` names it after its file).
        """
        self.path = Path(root) / ".pyacquisition" / "layout.json"
        self._name = name

    @property
    def name(self) -> str:
        return self._name() if callable(self._name) else self._name

    def _all(self) -> dict:
        try:
            layouts = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except (OSError, ValueError) as error:
            logger.warning(f"[Layout] Can't read {self.path}, so starting afresh: {error}")
            return {}
        return layouts if isinstance(layouts, dict) else {}

    def get(self) -> dict:
        """This experiment's layout, or {} if there is none yet."""
        layout = self._all().get(self.name)
        return layout if isinstance(layout, dict) else {}

    def put(self, layout: dict) -> None:
        """Replaces this experiment's layout, keeping the others'."""
        layouts = self._all()
        layouts[self.name] = layout
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Written aside and then moved, so a crash part way can't leave half a file.
        partial = self.path.with_suffix(".tmp")
        partial.write_text(json.dumps(layouts, indent=2), encoding="utf-8")
        partial.replace(self.path)

    def _register_endpoints(self, api_server):
        @api_server.app.get("/experiment/layout", tags=["experiment"])
        async def get_layout():
            """
            The GUI's layout for this experiment, as it last saved it: an
            object of its own making ({} if there is none yet).
            """
            return {"status": 200, "data": self.get()}

        @api_server.app.put("/experiment/layout", tags=["experiment"])
        async def put_layout(layout: dict = Body(...)):
            """Save the GUI's layout for this experiment (a JSON object)."""
            if len(json.dumps(layout)) > MAX_BYTES:
                raise HTTPException(status_code=413, detail="That layout is too big.")
            try:
                self.put(layout)
            except OSError as error:
                raise HTTPException(
                    status_code=500, detail=f"Couldn't save the layout: {error}"
                ) from error
            return {"status": 200}
