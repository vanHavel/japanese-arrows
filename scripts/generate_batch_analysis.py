# Copyright (C) 2026 Lukas Huwald
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import multiprocessing
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


def solve_puzzle_worker(args: tuple[Puzzle, int]) -> tuple[Puzzle, SolverResult]:
    puzzle, max_complexity = args
    solver = create_solver(max_complexity=max_complexity)
    res = solver.solve(puzzle)
    return puzzle, res


def main() -> None:
    # --- Configuration ---
    ROWS = 6
    COLS = 6
    ALLOW_DIAGONALS = False
    MAX_COMPLEXITY = 7
    COUNT = 1

    CONSTRAINTS = [
        FollowingArrowsFraction(min_fraction=0.1),
        RuleComplexityFraction(complexity=7, min_count=1),
        NumberFraction(number=1, max_fraction=0.4),
    ]

    OUTPUT_FILE = "scripts/output/batch_analysis.txt"
    # ---------------------

    gen = Generator()

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
    print("Analyzing results in parallel...")

    # Solve puzzles in parallel
    solve_args = [(p, MAX_COMPLEXITY) for p in puzzles]
    with multiprocessing.Pool(processes=8) as pool:
        solved_results = pool.map(solve_puzzle_worker, solve_args)

    print("Writing results to file...")

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
        f.write(f"  Puzzles rejected by timeout: {stats.puzzles_rejected_timeout}\n")
        if stats.rejections_per_constraint:
            f.write("  Rejections per constraint:\n")
            for name, count in stats.rejections_per_constraint.items():
                f.write(f"    - {name}: {count}\n")
        f.write("\n")

        for i, (puzzle, res) in enumerate(solved_results):
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
    print(f"  Puzzles rejected by timeout: {stats.puzzles_rejected_timeout}")
    for name, count in stats.rejections_per_constraint.items():
        print(f"    - {name}: {count}")

    print("\nDone.")


if __name__ == "__main__":
    main()
