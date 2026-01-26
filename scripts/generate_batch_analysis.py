from collections import defaultdict
from typing import TextIO

from japanese_arrows.generator import (
    FollowingArrowsFraction,
    Generator,
    NumberFraction,
    RuleComplexityFraction,
)
from japanese_arrows.models import Puzzle
from japanese_arrows.solver import SolverResult, SolverStatus, create_solver


def write_puzzle_analysis(f: TextIO, i: int, puzzle: Puzzle, solution: Puzzle, result: SolverResult) -> None:
    f.write(f"\n{'=' * 40}\n")
    f.write(f"Puzzle #{i + 1}\n")
    f.write(f"{'=' * 40}\n\n")

    f.write("Puzzle Grid:\n")
    f.write(puzzle.to_string())
    f.write("\n\n")

    f.write("Solution Grid:\n")
    f.write(solution.to_string())
    f.write("\n\n")

    # Analyze rule usage
    complexity_counts: dict[int, int] = defaultdict(int)
    rule_counts: dict[str, int] = defaultdict(int)

    for step in result.steps:
        complexity_counts[step.rule_complexity] += 1
        rule_counts[step.rule_name] += 1

    f.write("Rule Usage Statistics:\n")
    f.write("-" * 20 + "\n")
    for comp in sorted(complexity_counts.keys()):
        f.write(f"Complexity {comp}: {complexity_counts[comp]} applications\n")

    f.write("\nDetailed Rule Counts:\n")
    for rule in sorted(rule_counts.keys()):
        f.write(f"  {rule}: {rule_counts[rule]}\n")


def main() -> None:
    # --- Configuration ---
    ROWS = 6
    COLS = 6
    ALLOW_DIAGONALS = True
    MAX_COMPLEXITY = 6
    COUNT = 5

    CONSTRAINTS = [
        FollowingArrowsFraction(min_fraction=0.05),
        RuleComplexityFraction(complexity=6, min_count=1, max_count=4),
        NumberFraction(number=1, max_fraction=0.5),
        NumberFraction(number=4, min_fraction=0.01),
    ]

    OUTPUT_FILE = "scripts/output/batch_analysis.txt"
    # ---------------------

    gen = Generator()
    solver = create_solver(max_complexity=MAX_COMPLEXITY)

    print(f"Generating {COUNT} puzzles with settings:")
    print(f"  Size: {ROWS}x{COLS}")
    print(f"  Diagonals: {ALLOW_DIAGONALS}")
    print(f"  Max Complexity: {MAX_COMPLEXITY}")
    print(f"Writing to: {OUTPUT_FILE}")

    puzzles, stats = gen.generate_many(
        count=COUNT,
        rows=ROWS,
        cols=COLS,
        allow_diagonals=ALLOW_DIAGONALS,
        max_complexity=MAX_COMPLEXITY,
        constraints=CONSTRAINTS,
        n_jobs=8,
    )

    print(f"\nSuccessfully generated {len(puzzles)} puzzles.")
    print("Analyzing and writing results...")

    with open(OUTPUT_FILE, "w") as f:
        f.write("Batch Analysis Report\n")
        f.write(f"Generated {len(puzzles)} puzzles\n")
        f.write(f"Settings: {ROWS}x{COLS}, Diagonals={ALLOW_DIAGONALS}, Max Complexity={MAX_COMPLEXITY}\n\n")

        f.write("Generator Statistics:\n")
        f.write("-" * 20 + "\n")
        f.write(f"  Puzzles successfully generated: {stats.puzzles_successfully_generated}\n")
        f.write(f"  Puzzles rejected by constraints: {stats.puzzles_rejected_constraints}\n")
        f.write(f"  Puzzles rejected by no solution: {stats.puzzles_rejected_no_solution}\n")
        f.write(f"  Puzzles rejected by excessive guessing: {stats.puzzles_rejected_excessive_guessing}\n")
        if stats.rejections_per_constraint:
            f.write("  Rejections per constraint:\n")
            for name, count in stats.rejections_per_constraint.items():
                f.write(f"    - {name}: {count}\n")
        f.write("\n")

        for i, puzzle in enumerate(puzzles):
            res = solver.solve(puzzle, solve_with_min_complexity=True)
            if res.status == SolverStatus.SOLVED:
                write_puzzle_analysis(f, i, puzzle, res.puzzle, res)
            else:
                f.write(f"\nPuzzle #{i + 1} could not be solved (Status: {res.status})\n")
                f.write(puzzle.to_string())

    print("Generator Statistics:")
    print(f"  Puzzles successfully generated: {stats.puzzles_successfully_generated}")
    print(f"  Puzzles rejected by constraints: {stats.puzzles_rejected_constraints}")
    print(f"  Puzzles rejected by no solution: {stats.puzzles_rejected_no_solution}")
    print(f"  Puzzles rejected by excessive guessing: {stats.puzzles_rejected_excessive_guessing}")
    for name, count in stats.rejections_per_constraint.items():
        print(f"    - {name}: {count}")

    print("\nDone.")


if __name__ == "__main__":
    main()
