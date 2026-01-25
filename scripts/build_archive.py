import json
from pathlib import Path
from typing import Any, Dict, List

import yaml

PUZZLES_DIR = Path("web/puzzles")
OUTPUT_FILE = Path("web/assets/puzzles.json")


def main() -> None:
    puzzles: List[Dict[str, Any]] = []

    # Walk through the directory structure
    # Expected: web/puzzles/YYYY/MM/DD/metadata.yaml

    if not PUZZLES_DIR.exists():
        print(f"Directory {PUZZLES_DIR} does not exist.")
        return

    # Using rglob to find all metadata.yaml files
    for metadata_file in PUZZLES_DIR.rglob("metadata.yaml"):
        # Parent structure should be .../YYYY/MM/DD
        day_dir = metadata_file.parent
        month_dir = day_dir.parent
        year_dir = month_dir.parent

        # Verify structure roughly
        try:
            year = int(year_dir.name)
            month = int(month_dir.name)
            day = int(day_dir.name)
            date_str = f"{year:04d}-{month:02d}-{day:02d}"
        except ValueError:
            print(f"Skipping {metadata_file}: Folder structure does not match YYYY/MM/DD")
            continue

        with open(metadata_file, "r", encoding="utf-8") as f:
            try:
                data = yaml.safe_load(f)
            except yaml.YAMLError as e:
                print(f"Error parsing {metadata_file}: {e}")
                continue

        if not data:
            data = {}

        entry = {
            "date": date_str,
            "difficulty": data.get("difficulty", "Unknown"),
            "size": data.get("size", "Unknown"),
            "arrows": data.get("arrows", "Unknown"),
        }

        puzzles.append(entry)

    # Sort puzzles by date descending
    puzzles.sort(key=lambda x: x["date"], reverse=True)

    # Ensure output directory exists
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(puzzles, f, indent=2)

    print(f"Built archive with {len(puzzles)} puzzles at {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
