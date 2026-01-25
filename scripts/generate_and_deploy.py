import argparse
import sys
from pathlib import Path

from japanese_arrows.generator.constraints import Constraint, RuleComplexityFraction
from japanese_arrows.generator.generator import Generator
from japanese_arrows.solver import SolverStatus, create_solver


def generate_and_deploy(
    date_str: str,
    size_r: int,
    size_c: int,
    diagonals: bool,
    max_complexity: int,
    target_complexity: int,
    difficulty_name: str,
) -> None:
    # Parse date
    try:
        y, m, d = date_str.split("-")
    except ValueError:
        print("Invalid date format. Use YYYY-MM-DD")
        sys.exit(1)

    print(f"Generating puzzle for {date_str}...")
    print(f"Size: {size_r}x{size_c}, Diagonals: {diagonals}")
    print(f"Max Complexity: {max_complexity}, Must achieve complexity: {target_complexity}")

    constraints: list[Constraint] = [RuleComplexityFraction(complexity=target_complexity, min_count=1)]

    gen = Generator()

    puzzle = None

    # We loop manually because sometimes a specific random seed gets stuck?
    # Or just rely on generator's internal retries.
    # The generator's generate method takes max_attempts.

    puzzle, stats = gen.generate(
        rows=size_r,
        cols=size_c,
        allow_diagonals=diagonals,
        max_complexity=max_complexity,
        constraints=constraints,
        max_attempts=5000,
    )

    if puzzle is None:
        print("Failed to generate a puzzle satisfying constraints.")
        print(f"Stats: {stats}")
        sys.exit(1)

    print("Puzzle generated successfully!")

    # Setup paths
    dest_dir = Path(f"web/puzzles/{y}/{m}/{d}")
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Save Puzzle
    with open(dest_dir / "puzzle.txt", "w", encoding="utf-8") as f:
        f.write(puzzle.to_string())

    # Solve to get solution string (full grid)
    solver = create_solver(max_complexity=max_complexity)
    res = solver.solve(puzzle)

    if res.status != SolverStatus.SOLVED:
        print(f"Error: Generated puzzle not solvable? Status: {res.status}")
        # this shouldn't happen if generator works, but sanity check
        sys.exit(1)

    with open(dest_dir / "solution.txt", "w", encoding="utf-8") as f:
        f.write(res.puzzle.to_string())

    # Write Metadata
    arrows = "Diagonal" if diagonals else "Straight"
    metadata = f"""difficulty: {difficulty_name}
size: {size_r}x{size_c}
arrows: {arrows}
"""
    with open(dest_dir / "metadata.yaml", "w", encoding="utf-8") as f:
        f.write(metadata)

    print(f"Deployed to {dest_dir} with difficulty {difficulty_name}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("date", help="YYYY-MM-DD")
    parser.add_argument("--size", type=int, default=5, help="Grid size (NxN)")
    parser.add_argument("--diag", action="store_true", help="Allow diagonals")
    parser.add_argument("--max-comp", type=int, required=True, help="Max complexity allowed")
    parser.add_argument("--target-comp", type=int, required=True, help="Target complexity to achieve")
    parser.add_argument("--difficulty", type=str, required=True, help="Difficulty label")

    args = parser.parse_args()

    generate_and_deploy(args.date, args.size, args.size, args.diag, args.max_comp, args.target_comp, args.difficulty)


if __name__ == "__main__":
    main()
