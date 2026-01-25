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
from japanese_arrows.site_gen.deploy_puzzle import generate_and_save_puzzle  # noqa: E402


def cmd_build(args: argparse.Namespace) -> None:
    print("Building static site assets...")
    generate_all_arrow_assets()
    build_puzzle_archive()
    print("Site build complete.")


def cmd_puzzle(args: argparse.Namespace) -> None:
    generate_and_save_puzzle(
        date_str=args.date,
        size_r=args.size,
        size_c=args.size,
        diagonals=args.diag,
        max_complexity=args.max_comp,
        target_complexity=args.target_comp,
        difficulty_name=args.difficulty,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Japanese Arrows Site Deployment Tool")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Build command (default if no args)
    subparsers.add_parser("build", help="Generate assets and archive index")

    # Puzzle command
    puzzle_parser = subparsers.add_parser("puzzle", help="Generate and deploy a single puzzle")
    puzzle_parser.add_argument("date", help="YYYY-MM-DD")
    puzzle_parser.add_argument("--size", type=int, default=5, help="Grid size (NxN)")
    puzzle_parser.add_argument("--diag", action="store_true", help="Allow diagonals")
    puzzle_parser.add_argument("--max-comp", type=int, required=True, help="Max complexity allowed")
    puzzle_parser.add_argument("--target-comp", type=int, required=True, help="Target complexity to achieve")
    puzzle_parser.add_argument("--difficulty", type=str, required=True, help="Difficulty label")

    args = parser.parse_args()

    if args.command == "build" or args.command is None:
        cmd_build(args)
    elif args.command == "puzzle":
        cmd_puzzle(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
