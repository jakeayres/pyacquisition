import glob

import matplotlib.pyplot as plt
import pandas as pd

temperature, signal, spread = [], [], []
for path in sorted(glob.glob("my_data/*hold.data")):
    data = pd.read_csv(path)
    temperature.append(data["T"].mean())
    signal.append(data["R"].mean())
    spread.append(data["R"].std())

plt.errorbar(temperature, signal, yerr=spread, marker="o", capsize=3)
plt.xlabel("T (K)")
plt.ylabel("R (V)")
plt.show()
