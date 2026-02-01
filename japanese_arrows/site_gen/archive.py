# Copyright (C) 2026 Lukas Huwald
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import json
from pathlib import Path
from typing import Any, Dict, List

import yaml

DEFAULT_PUZZLES_DIR = Path("web/puzzles")
DEFAULT_OUTPUT_FILE = Path("web/assets/puzzles.json")


def build_puzzle_archive(puzzles_dir: Path = DEFAULT_PUZZLES_DIR, output_file: Path = DEFAULT_OUTPUT_FILE) -> None:
    puzzles: List[Dict[str, Any]] = []

    if not puzzles_dir.exists():
        print(f"Directory {puzzles_dir} does not exist.")
        return

    print(f"Building archive from {puzzles_dir}...")

    # Using rglob to find all metadata.yaml files
    for metadata_file in puzzles_dir.rglob("metadata.yaml"):
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
    if not output_file.parent.exists():
        output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(puzzles, f, indent=2)

    print(f"Built archive with {len(puzzles)} puzzles at {output_file}")
