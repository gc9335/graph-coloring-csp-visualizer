from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from exp3.run_experiments import run_all


if __name__ == "__main__":
    run_all(timeout_seconds=60.0)
