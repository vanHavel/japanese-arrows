import argparse
from pathlib import Path

from japanese_arrows.io import read_puzzle
from japanese_arrows.solver import SolverStatus, create_solver


def deploy(puzzle_path: str, date_str: str) -> None:
    # Parse date YYYY-MM-DD
    try:
        y, m, d = date_str.split("-")
    except ValueError:
        print("Invalid date format. Use YYYY-MM-DD")
        return

    dest_dir = Path(f"web/puzzles/{y}/{m}/{d}")
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Read and Write Puzzle
    print(f"Reading {puzzle_path}...")
    puzzle = read_puzzle(puzzle_path)

    with open(dest_dir / "puzzle.txt", "w", encoding="utf-8") as f:
        f.write(puzzle.to_string())

    # Solve
    print("Solving...")
    solver = create_solver(max_complexity=6)
    result = solver.solve(puzzle)

    if result.status != SolverStatus.SOLVED:
        print(f"Warning: Puzzle status is {result.status}. Deploying anyway.")

    # Write Solution (only numbers needed usually, but text format is standard)
    with open(dest_dir / "solution.txt", "w", encoding="utf-8") as f:
        f.write(result.puzzle.to_string())

    print(f"Deployed to {dest_dir}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("puzzle_path", help="Path to puzzle.txt")
    parser.add_argument("date", help="YYYY-MM-DD")
    args = parser.parse_args()

    deploy(args.puzzle_path, args.date)


if __name__ == "__main__":
    main()
