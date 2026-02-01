# Copyright (C) 2026 Lukas Huwald
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from pathlib import Path

from japanese_arrows.models import Puzzle
from japanese_arrows.solver import SolverStatus, create_solver

# Configuration
PUZZLE_PATH = "puzzles/pi.txt"


def main() -> None:
    solver = create_solver(max_complexity=6)

    puzzle_path = Path(PUZZLE_PATH)
    if not puzzle_path.exists():
        print(f"Error: {puzzle_path} not found")
        return

    with open(puzzle_path) as f:
        puzzle = Puzzle.from_string(f.read())

    print(f"Solving {puzzle_path}...")
    result = solver.solve(puzzle)

    print(f"\nStatus: {result.status}")

    print("\n--- Solution Trace ---")

    # We will replay the steps on a fresh puzzle copy to show state evolution if desired,
    # but the result object already contains the steps.
    # To keep it simple, we just list the steps and if there is a contradiction trace, we print it.

    for i, step in enumerate(result.steps, 1):
        print(f"\nStep {i}: Rule '{step.rule_name}'")
        print(f"  Witness: {step.witness}")
        conclusions_str = ", ".join(str(c) for c in step.conclusions_applied)
        print(f"  Applied: {conclusions_str}")

        if step.contradiction_trace:
            print("  Contradiction Trace:")
            for trace_line in step.contradiction_trace:
                print(f"    | {trace_line}")

        print("\n  Resulting Puzzle State:")
        print(step.puzzle_state.to_string_with_candidates())

    print("\n--- Final Result ---")
    if result.status == SolverStatus.SOLVED:
        print("Puzzle solved successfully!")
        print(result.puzzle.to_string())
    else:
        print("Puzzle NOT solved fully.")
        print(result.puzzle.to_string_with_candidates())

    print("\n--- Rule Execution Statistics ---")
    print(f"{'Rule Name':<30} | {'Count':<6} | {'Time (s)':<10}")
    print("-" * 52)
    total_time = 0.0
    # Sort by time spent
    sorted_rules = sorted(result.rule_execution_time.items(), key=lambda x: x[1], reverse=True)
    for name, duration in sorted_rules:
        count = result.rule_application_count.get(name, 0)
        print(f"{name:<30} | {count:<6} | {duration:<10.4f}")
        total_time += duration
    print("-" * 52)
    print(f"{'Total':<30} | {'':<6} | {total_time:<10.4f}")


if __name__ == "__main__":
    main()
