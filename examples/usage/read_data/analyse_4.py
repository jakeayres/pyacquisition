from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

folder = Path("data")
for path in sorted(folder.glob("03.* run *.data")):
    run = pd.read_csv(path)
    print(f"{path.stem}: {len(run)} rows, from {run['time'].min():.1f} s")
    plt.plot(run["time"], run["wave"], label=path.stem)

plt.xlabel("time (s)")
plt.ylabel("wave")
plt.legend()
plt.savefig("wave.png", dpi=150)
plt.show()
