import copy
import random
from dataclasses import dataclass
from typing import List

from japanese_arrows.generator.constraints import Constraint
from japanese_arrows.models import Cell, Direction, Puzzle
from japanese_arrows.solver import SolverResult, SolverStatus, create_solver


@dataclass
class GenerationStats:
    puzzles_successfully_generated: int = 0
    puzzles_rejected_constraints: int = 0
    puzzles_rejected_no_solution: int = 0


class Generator:
    def generate(
        self,
        rows: int,
        cols: int,
        allow_diagonals: bool,
        max_complexity: int,
        constraints: list[Constraint],
        max_attempts: int = 100,
        _stats: GenerationStats | None = None,
    ) -> tuple[Puzzle, GenerationStats]:
        solver = create_solver(max_complexity=max_complexity)
        stats = _stats if _stats is not None else GenerationStats()
        start_attempts = stats.puzzles_rejected_constraints + stats.puzzles_rejected_no_solution

        while True:
            if stats.puzzles_rejected_constraints + stats.puzzles_rejected_no_solution - start_attempts >= max_attempts:
                raise RuntimeError(f"Could not generate puzzle within {max_attempts} attempts")

            # 1. Create random grid
            grid = self._create_random_grid(rows, cols, allow_diagonals)

            # current_puzzle holds the base arrows plus any manual inserts (givens)
            current_puzzle = Puzzle(rows=rows, cols=cols, grid=grid)

            # 2. Loop until solved or failed
            while True:
                # 2.1 Run the solver with max_complexity
                # We work on a copy so we don't mess up current_puzzle validation logic
                # (though solve() copies internally, we want explicitly fresh start)
                trace = solver.solve(copy.deepcopy(current_puzzle))

                if trace.status == SolverStatus.SOLVED:
                    # Step 3: verify that the grid lies within the desired constraints
                    if self._check_constraints(trace, constraints):
                        stats.puzzles_successfully_generated += 1
                        return current_puzzle, stats
                    else:
                        # Step 4: Constraints failed, start over (outer loop)
                        stats.puzzles_rejected_constraints += 1
                        break

                elif trace.status == SolverStatus.UNDERCONSTRAINED:
                    # Step 2.3: Choose random unfilled cell from partial solution
                    partial_grid = trace.puzzle.grid

                    empty_cells = []
                    for r in range(rows):
                        for c in range(cols):
                            if partial_grid[r][c].number is None:
                                empty_cells.append((r, c))

                    if not empty_cells:
                        # This shouldn't happen if status is UNDERCONSTRAINED,
                        # but if it does, it's a weird state. Restart.
                        stats.puzzles_rejected_no_solution += 1
                        break

                    # Choose random unfilled cell
                    r, c = random.choice(empty_cells)
                    cell = partial_grid[r][c]

                    if not cell.candidates:
                        # No candidates - effectively a dead end / NO_SOLUTION
                        stats.puzzles_rejected_no_solution += 1
                        break

                    # Fill with one of its candidates
                    val = random.choice(list(cell.candidates))

                    # Record this decision as a manual insert in current_puzzle
                    current_puzzle.grid[r][c].number = val

                    # Continue inner loop

                else:  # NO_SOLUTION
                    # Contradiction. Start over.
                    stats.puzzles_rejected_no_solution += 1
                    break

    def generate_many(
        self,
        count: int,
        rows: int,
        cols: int,
        allow_diagonals: bool,
        max_complexity: int,
        constraints: list[Constraint],
        max_attempts: int = 1000,
    ) -> tuple[list[Puzzle], GenerationStats]:
        puzzles: list[Puzzle] = []
        overall_stats = GenerationStats()

        while len(puzzles) < count:
            remaining_attempts = (
                max_attempts
                - overall_stats.puzzles_successfully_generated
                - overall_stats.puzzles_rejected_constraints
                - overall_stats.puzzles_rejected_no_solution
            )
            if remaining_attempts <= 0:
                break

            try:
                puzzle, _ = self.generate(
                    rows,
                    cols,
                    allow_diagonals,
                    max_complexity,
                    constraints,
                    max_attempts=remaining_attempts,
                    _stats=overall_stats,
                )
                puzzles.append(puzzle)
            except RuntimeError:
                # Reached max_attempts across all generations
                break

        return puzzles, overall_stats

    def _create_random_grid(self, rows: int, cols: int, allow_diagonals: bool) -> List[List[Cell]]:
        grid = []
        directions = [Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST]
        if allow_diagonals:
            directions.extend([Direction.NORTH_EAST, Direction.SOUTH_EAST, Direction.SOUTH_WEST, Direction.NORTH_WEST])

        for _ in range(rows):
            row = []
            for _ in range(cols):
                d = random.choice(directions)
                row.append(Cell(direction=d))
            grid.append(row)
        return grid

    def _check_constraints(self, trace: SolverResult, constraints: List[Constraint]) -> bool:
        for c in constraints:
            if not c.check(trace):
                return False
        return True
