from __future__ import annotations

import json
from pathlib import Path


def future_metric_spec() -> dict:
    return {
        "sets": ["C", "N", "P"],
        "required_metrics": [
            "|C|",
            "|N|",
            "|P|",
            "|C ∪ N|",
            "|C ∪ P|",
            "|N ∪ P|",
            "|C ∪ N ∪ P|",
            "NVARC-only rescues",
            "program-only rescues",
            "overlap",
            "Jaccard similarities",
            "cost per incremental solved index",
            "contamination labels",
        ],
    }


def main() -> None:
    print(json.dumps(future_metric_spec(), indent=2))


if __name__ == "__main__":
    main()
