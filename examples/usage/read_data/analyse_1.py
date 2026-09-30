from pathlib import Path

folder = Path("data")
for path in sorted(folder.glob("*.data")):
    print(path.name)
