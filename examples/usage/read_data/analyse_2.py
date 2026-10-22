from pathlib import Path

import pandas as pd

folder = Path("data")
run = pd.read_csv(folder / "03.01 0.1 V.data")
print(run.head())
