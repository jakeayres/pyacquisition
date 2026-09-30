from pathlib import Path

import matplotlib.pyplot as plt
from pyacquisition import read_traces

newest = max(Path("data").glob("*.data"))
traces = read_traces(newest, "spectrum")
kelvin = traces.info["row.T"].to_numpy()
print(f"{newest.name}: {len(traces.index)} spectra of {traces.x.size} points")
print(f"from {kelvin[0]:.1f} K to {kelvin[-1]:.1f} K")

for spectrum, t in zip(traces.channels["intensity"][::3], kelvin[::3]):
    plt.plot(traces.x, spectrum, label=f"{t:.1f} K")
plt.xlabel("frequency (GHz)")
plt.ylabel("intensity (V)")
plt.legend()
plt.savefig("spectra.png", dpi=150)
plt.show()
