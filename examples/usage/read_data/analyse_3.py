from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

folder = Path("data")
run = pd.read_csv(folder / "03.01 run 1.data")
print(run.head())

plt.plot(run["time"], run["wave"])
plt.xlabel("time (s)")
plt.ylabel("wave")
plt.show()
