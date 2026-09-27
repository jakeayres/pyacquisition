"""Finding instruments (roadmap 11, `specs/discovery.md` in the repository).

For now, only what the setup page's Test button needs: each hardware driver's
identity, the words its reply to `*IDN?` contains.
"""

from ..instruments import instrument_map
from ..verify.spec import load_spec
from .instrument import SoftwareInstrument
from .logging import logger


def identities() -> dict[str, tuple]:
    """The words each hardware driver's reply to `*IDN?` contains, by its name
    in `instrument_map`, from the `[identity]` of its verification spec. A
    driver without one is left out, and so is one whose spec fails to load,
    which is logged."""
    found = {}
    for name, cls in instrument_map.items():
        if issubclass(cls, SoftwareInstrument):
            continue
        try:
            spec = load_spec(cls)
        except Exception as e:  # noqa: BLE001 - a broken spec never stops anything
            logger.warning(f"[Discovery] {name}'s verification spec can't be read: {e}")
            continue
        if spec is not None and spec.identity:
            found[name] = tuple(spec.identity)
    return found
