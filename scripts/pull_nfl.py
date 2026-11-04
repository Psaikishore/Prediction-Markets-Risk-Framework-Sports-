"""Pull nflverse schedules (scores + closing lines) for 2015-2026 into data/raw."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pmrisk.nfl import pull_schedules

if __name__ == "__main__":
    df = pull_schedules()
    done = df.dropna(subset=["home_score"])
    print(f"{len(df)} scheduled games, {len(done)} completed, seasons {df.season.min()}-{df.season.max()}")
