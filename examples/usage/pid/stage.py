"""A simulated sample stage, for Hold a temperature with PID. It answers the messages
that the real Lakeshore_350 and SR_830 drivers send, so hold.py uses them as it
would on the rig:

- the Lakeshore's output 1 drives a heater on the stage, which sits over a 4.2 K
  bath and takes about 6 s to follow the heater. At full output, in range 3, it
  settles at about 16 K, and each range is ten times the power of the one below;
- its input A reads the stage's temperature;
- a RuOx thermometer on the sample, of 1000 exp(sqrt(2 K / T)) ohms, carries the
  lock-in's 100 nA, so the lock-in's X is its voltage: about 165 uV at 8 K.
"""

import math
import random
import threading
import time


class SimulatedStage:
    """The stage's temperature, and a connection for each instrument to use in place
    of its address: `stage.lakeshore` and `stage.lockin`."""

    def __init__(self):
        self.lakeshore = _Port("SIM::LAKESHORE", self._lakeshore)
        self.lockin = _Port("SIM::LOCKIN", self._lockin)
        self.lakeshore.settings.update(
            {"*IDN?": "LSCI,MODEL350,SIMULATED,1.0", "OUTMODE? 1": "1,1,0"}
        )
        self.lockin.settings["*IDN?"] = (
            "Stanford_Research_Systems,SR830,SIMULATED,1.0"
        )
        self._temperature = 4.2
        self._last = time.monotonic()
        self._lock = threading.Lock()

    def _heater(self) -> float:
        """The output the heater gets, in percent: the manual output, in open loop
        mode (3) with a range on."""
        settings = self.lakeshore.settings
        mode = int(settings["OUTMODE? 1"].split(",")[0])
        heater_range = int(settings.get("RANGE? 1", "0"))
        if mode != 3 or heater_range == 0:
            return 0.0
        return min(max(float(settings.get("MOUT? 1", "0")), 0.0), 100.0)

    def _advance(self) -> float:
        """The stage's temperature now, having followed the heater since last asked."""
        with self._lock:
            now = time.monotonic()
            dt, self._last = now - self._last, now
            decades = int(self.lakeshore.settings.get("RANGE? 1", "0")) - 3
            settles_at = 4.2 + 12.0 * self._heater() / 100 * 10**decades
            follow = 1 - math.exp(-dt / 6.0)
            self._temperature += (settles_at - self._temperature) * follow
            return self._temperature

    def _lakeshore(self, query: str):
        if query == "KRDG? A":
            return f"{self._advance():.4f}"
        if query == "HTR? 1":
            return f"{self._heater():.1f}"
        return None

    def _lockin(self, query: str):
        if query == "OUTP? 1":
            resistance = 1000.0 * math.exp(math.sqrt(2.0 / self._advance()))
            return f"{100e-9 * resistance * (1 + random.gauss(0, 3e-4)):.6e}"
        if query == "OUTP? 2":
            return f"{random.gauss(0, 5e-8):.6e}"
        return None


class _Port:
    """Stands in for an instrument's connection: it keeps what is written, for the
    queries that read it back, and asks the stage for the rest."""

    def __init__(self, name, answer):
        self.resource_name = name
        self.settings = {}
        self._answer = answer

    def write(self, message: str) -> int:
        header, _, arguments = message.partition(" ")
        first, _, rest = arguments.partition(",")
        if rest:
            self.settings[f"{header}? {first}"] = rest
        else:
            self.settings[f"{header}?"] = first
        return len(message)

    def query(self, message: str) -> str:
        reply = self._answer(message)
        return reply if reply is not None else self.settings.get(message, "0")

    def close(self) -> None:
        pass
