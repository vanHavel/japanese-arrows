# Copyright (C) 2026 Lukas Huwald
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import shutil
from pathlib import Path


def sync_puzzles(content_dir: Path, web_puzzles_dir: Path, release_date: str) -> None:
    """
    Syncs puzzles from content_dir to web_puzzles_dir that were released on or before release_date.
    """
    if not content_dir.exists():
        print("Content directory not found skip syncing.")
        return

    print(f"Syncing puzzles released on or before {release_date}...")

    # Clean web/puzzles first to ensure we don't have stale files
    if web_puzzles_dir.exists():
        shutil.rmtree(web_puzzles_dir)
    web_puzzles_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    # Search for metadata.yaml in content/YYYY/MM/DD
    for metadata_file in content_dir.rglob("metadata.yaml"):
        day_dir = metadata_file.parent
        month_dir = day_dir.parent
        year_dir = month_dir.parent

        try:
            year = year_dir.name
            month = month_dir.name
            day = day_dir.name
            # Validate they are numeric and look like a date
            int(year)
            int(month)
            int(day)
            date_str = f"{year}-{month:0>2}-{day:0>2}"
        except ValueError:
            continue

        if date_str <= release_date:
            dest = web_puzzles_dir / year / month / day
            dest.mkdir(parents=True, exist_ok=True)
            for item in day_dir.iterdir():
                if item.is_file():
                    shutil.copy2(item, dest / item.name)
            count += 1

    print(f"Synced {count} puzzles.")
