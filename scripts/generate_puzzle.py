from collections import defaultdict

from japanese_arrows.generator import (
    FollowingArrowsFraction,
    GenerationStats,
    Generator,
    RuleComplexityFraction,
)
from japanese_arrows.io import write_puzzle
from japanese_arrows.solver import SolverStatus, create_solver


def main() -> None:
    gen = Generator()

    # Configuration for generation
    rows = 5
    cols = 5
    allow_diagonals = False
    max_complexity = 4
    prefilled_cells_count = 0

    constraints = [
        FollowingArrowsFraction(min_fraction=0.05),
        RuleComplexityFraction(complexity=3, min_fraction=0.001),
    ]

    print(f"Generating a {rows}x{cols} puzzle (max complexity {max_complexity})...")

    puzzles = []
    stats = GenerationStats()

    generator_iterator = gen.generate_many(
        max_count=1,
        n_jobs=8,
        rows=rows,
        cols=cols,
        allow_diagonals=allow_diagonals,
        max_complexity=max_complexity,
        constraints=constraints,
        prefilled_cells_count=prefilled_cells_count,
        max_attempts=8,
    )

    for batch_puzzles, batch_stats in generator_iterator:
        puzzles.extend(batch_puzzles)
        stats.puzzles_successfully_generated += len(batch_puzzles)
        stats.puzzles_rejected_constraints += batch_stats.puzzles_rejected_constraints
        stats.puzzles_rejected_no_solution += batch_stats.puzzles_rejected_no_solution
        stats.puzzles_rejected_excessive_guessing += batch_stats.puzzles_rejected_excessive_guessing
        for name, count in batch_stats.rejections_per_constraint.items():
            stats.rejections_per_constraint[name] = stats.rejections_per_constraint.get(name, 0) + count

        puzzle = None
        # We can enable early exit if we found enough puzzles,
        # but for now let's just collect all results as configured by max_count/attempts.
        if puzzles:
            print(f"  Found {len(batch_puzzles)} new puzzles (Total: {len(puzzles)})")
            puzzle = puzzles[0]
            break
        else:
            print("No puzzles generated in this batch.")

    if not puzzle:
        print("\nCould not generate puzzle within max attempts")
    else:
        print("\nGenerated Puzzle:")
        print(puzzle.to_string())
        write_puzzle(puzzle, "scripts/output/generated_puzzle.svg")
        print("Saved problem to scripts/output/generated_puzzle.svg")

    print("Generation Statistics:")
    print(f"  Puzzles successfully generated: {stats.puzzles_successfully_generated}")
    print(f"  Puzzles rejected by no solution: {stats.puzzles_rejected_no_solution}")
    print(f"  Puzzles rejected by excessive guessing: {stats.puzzles_rejected_excessive_guessing}")
    print(f"  Puzzles rejected by constraints: {stats.puzzles_rejected_constraints}")
    for name, count in stats.rejections_per_constraint.items():
        print(f"    - {name}: {count}")

    # Solve the puzzle
    if puzzle is not None:
        print("\nSolving the puzzle...")
        solver = create_solver(max_complexity=max_complexity)
        res = solver.solve(puzzle)

        if res.status == SolverStatus.SOLVED:
            print("\nSolved Puzzle:")
            print(res.puzzle.to_string())
            write_puzzle(res.puzzle, "scripts/output/generated_solution.svg")
            print("Saved solution to scripts/output/generated_solution.svg")

            # Count rule applications by complexity
            complexity_counts: dict[int, int] = defaultdict(int)
            # Count each rule's usage and store its complexity
            rule_details = {}  # rule_name -> (complexity, count)

            for step in res.steps:
                complexity_counts[step.rule_complexity] += 1
                if step.rule_name not in rule_details:
                    rule_details[step.rule_name] = [step.rule_complexity, 0]
                rule_details[step.rule_name][1] += 1

            print("Rule Applications by Complexity:")
            for comp in sorted(complexity_counts.keys()):
                print(f"  Complexity {comp}: {complexity_counts[comp]}")

            print("\nDetailed Rule Usage (sorted by complexity):")
            # Sort by complexity then name
            sorted_rules = sorted(rule_details.items(), key=lambda x: (x[1][0], x[0]))
            for name, (comp, count) in sorted_rules:
                print(f"  [{comp}] {name}: {count}")
        else:
            print(f"Solver failed with status: {res.status}")


if __name__ == "__main__":
    main()
