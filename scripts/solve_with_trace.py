from pathlib import Path

from japanese_arrows.models import Puzzle
from japanese_arrows.solver import SolverStatus, create_solver

# Configuration
PUZZLE_PATH = "puzzles/zeiger_2.txt"


def main() -> None:
    # Use max_complexity=6 to include backtracking
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


if __name__ == "__main__":
    main()
