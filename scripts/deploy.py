# Copyright (C) 2026 Lukas Huwald
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import argparse
import sys
from pathlib import Path

# Add project root to sys path so we can import from japanese_arrows
# Assuming script is run from project root or scripts folder
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from japanese_arrows.site_gen.archive import build_puzzle_archive  # noqa: E402
from japanese_arrows.site_gen.assets import generate_all_arrow_assets  # noqa: E402
from japanese_arrows.site_gen.sync import sync_puzzles  # noqa: E402

# This constant will be updated by a daily cronjob
RELEASE_DATE = "2026-02-01"


def cmd_build(args: argparse.Namespace) -> None:
    print("Building static site assets...")
    sync_puzzles(
        content_dir=project_root / "content",
        web_puzzles_dir=project_root / "web" / "puzzles",
        release_date=RELEASE_DATE,
    )
    generate_all_arrow_assets()
    build_puzzle_archive()
    print("Site build complete.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Japanese Arrows Site Deployment Tool")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Build command (default if no args)
    subparsers.add_parser("build", help="Generate assets and archive index")
    args = parser.parse_args()

    if args.command == "build" or args.command is None:
        cmd_build(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
