import copy
import random
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from dataclasses import dataclass, field

from joblib import effective_n_jobs

from japanese_arrows.generator.constraints import Constraint
from japanese_arrows.models import Cell, Direction, Puzzle
from japanese_arrows.solver import SolverResult, SolverStatus, compute_all_paths, create_solver


@dataclass
class GenerationStats:
    puzzles_successfully_generated: int = 0
    puzzles_rejected_constraints: int = 0
    puzzles_rejected_no_solution: int = 0
    puzzles_rejected_excessive_guessing: int = 0
    rejections_per_constraint: dict[str, int] = field(default_factory=dict)


class Generator:
    OUTWARD_ARROWS_THRESHOLD = 0.1
    MAX_MODIFICATIONS_FRACTION = 0.1
    MAX_GUESSES_FRACTION = 0.15

    def generate(
        self,
        rows: int,
        cols: int,
        allow_diagonals: bool,
        max_complexity: int,
        constraints: list[Constraint],
        prefilled_cells_count: int = 0,
        max_attempts: int = 100,
        _stats: GenerationStats | None = None,
    ) -> tuple[Puzzle | None, GenerationStats]:
        solver = create_solver(max_complexity=max_complexity)
        stats = _stats if _stats is not None else GenerationStats()
        extra_fills = 0
        guesses: list[tuple[int, int, int]] = []

        while True:
            total_attempts = (
                stats.puzzles_successfully_generated
                + stats.puzzles_rejected_constraints
                + stats.puzzles_rejected_no_solution
                + stats.puzzles_rejected_excessive_guessing
            )
            if total_attempts >= max_attempts and max_attempts != -1:
                return None, stats

            grid = self._create_random_grid(rows, cols, allow_diagonals)

            current_puzzle = Puzzle(rows=rows, cols=cols, grid=grid)

            self._flip_outward_arrows(current_puzzle)

            if prefilled_cells_count > 0:
                self._prefill_cells(current_puzzle, prefilled_cells_count)

            failed_pre_check = False
            for constraint in constraints:
                if not constraint.pre_check(current_puzzle):
                    stats.puzzles_rejected_constraints += 1
                    stats.rejections_per_constraint[constraint.name] = (
                        stats.rejections_per_constraint.get(constraint.name, 0) + 1
                    )
                    failed_pre_check = True
                    break
            if failed_pre_check:
                continue

            path_cache = compute_all_paths(current_puzzle)
            reuse_candidates = False
            base_puzzle = copy.deepcopy(current_puzzle)
            modifications = 0

            while True:
                trace = solver.solve(current_puzzle, path_cache=path_cache, reuse_candidates=reuse_candidates)

                if trace.status == SolverStatus.SOLVED:
                    failing_constraint = self._get_failing_constraint(trace, constraints)
                    if failing_constraint is None:
                        stats.puzzles_successfully_generated += 1

                        # Return a puzzle that only has the guesses and prefilled numbers
                        result_puzzle = copy.deepcopy(base_puzzle)

                        # Apply guesses
                        for gr, gc, gval in guesses:
                            result_puzzle.grid[gr][gc].number = gval
                            result_puzzle.grid[gr][gc].candidates = {gval}

                        return result_puzzle, stats
                    else:
                        stats.puzzles_rejected_constraints += 1
                        stats.rejections_per_constraint[failing_constraint.name] = (
                            stats.rejections_per_constraint.get(failing_constraint.name, 0) + 1
                        )
                        break

                elif trace.status == SolverStatus.UNDERCONSTRAINED:
                    import math

                    limit = max(math.ceil(rows * cols * self.MAX_GUESSES_FRACTION), 3)
                    if extra_fills >= limit:
                        stats.puzzles_rejected_excessive_guessing += 1
                        break

                    current_puzzle = trace.puzzle

                    empty_cells = []
                    for r in range(rows):
                        for c in range(cols):
                            if current_puzzle.grid[r][c].number is None:
                                empty_cells.append((r, c))

                    if not empty_cells:
                        stats.puzzles_rejected_no_solution += 1
                        break

                    r, c = random.choice(empty_cells)
                    cell = current_puzzle.grid[r][c]

                    if not cell.candidates:
                        stats.puzzles_rejected_no_solution += 1
                        break

                    val = random.choice(list(cell.candidates))

                    cell.number = val
                    cell.candidates = {val}
                    extra_fills += 1
                    guesses.append((r, c, val))

                    reuse_candidates = True

                    # Continue inner loop

                else:
                    import math

                    max_modifications = max(math.ceil(rows * cols * self.MAX_MODIFICATIONS_FRACTION), 3)
                    if modifications < max_modifications and trace.contradiction_location is not None:
                        # Contradiction found, try to rotate the arrow at the contradiction
                        r, c = trace.contradiction_location

                        # Modify the base puzzle (preserving prefilled numbers but resetting guesses)
                        current_dir = base_puzzle.grid[r][c].direction

                        allowed_dirs = [Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST]
                        if allow_diagonals:
                            allowed_dirs.extend(
                                [Direction.NORTH_EAST, Direction.SOUTH_EAST, Direction.SOUTH_WEST, Direction.NORTH_WEST]
                            )

                        current_idx = allowed_dirs.index(current_dir) if current_dir in allowed_dirs else 0
                        new_dir = allowed_dirs[(current_idx + 1) % len(allowed_dirs)]

                        base_puzzle.grid[r][c].direction = new_dir

                        # Reset current_puzzle to base_puzzle (clears number guesses)
                        current_puzzle = copy.deepcopy(base_puzzle)
                        extra_fills = 0
                        guesses = []

                        # Recompute paths since arrows changed
                        path_cache = compute_all_paths(current_puzzle)
                        reuse_candidates = False
                        modifications += 1
                        continue

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
        prefilled_cells_count: int = 0,
        n_jobs: int = 1,
    ) -> tuple[list[Puzzle], GenerationStats]:
        n_workers = effective_n_jobs(n_jobs)
        puzzles: list[Puzzle] = []
        total_stats = GenerationStats()

        with ProcessPoolExecutor(max_workers=n_workers) as executor:
            # Initial submission of tasks
            futures = set()
            for _ in range(n_workers):
                futures.add(
                    executor.submit(
                        self.generate,
                        rows=rows,
                        cols=cols,
                        allow_diagonals=allow_diagonals,
                        max_complexity=max_complexity,
                        constraints=constraints,
                        prefilled_cells_count=prefilled_cells_count,
                        max_attempts=1,
                    )
                )

            # Loop until we have enough puzzles
            while len(puzzles) < count:
                done, _ = wait(futures, return_when=FIRST_COMPLETED)

                for future in done:
                    futures.remove(future)
                    try:
                        res_puzzle, res_stats = future.result()

                        # Aggregate stats
                        total_stats.puzzles_successfully_generated += res_stats.puzzles_successfully_generated
                        total_stats.puzzles_rejected_constraints += res_stats.puzzles_rejected_constraints
                        total_stats.puzzles_rejected_no_solution += res_stats.puzzles_rejected_no_solution
                        total_stats.puzzles_rejected_excessive_guessing += res_stats.puzzles_rejected_excessive_guessing
                        for name, val in res_stats.rejections_per_constraint.items():
                            total_stats.rejections_per_constraint[name] = (
                                total_stats.rejections_per_constraint.get(name, 0) + val
                            )

                        if res_puzzle is not None:
                            puzzles.append(res_puzzle)

                    except Exception:
                        # Log error if possible, or just continue
                        pass

                    if len(puzzles) < count:
                        futures.add(
                            executor.submit(
                                self.generate,
                                rows=rows,
                                cols=cols,
                                allow_diagonals=allow_diagonals,
                                max_complexity=max_complexity,
                                constraints=constraints,
                                prefilled_cells_count=prefilled_cells_count,
                                max_attempts=1,
                            )
                        )
                    else:
                        break

            # Cancel remaining
            for f in futures:
                f.cancel()

        return puzzles, total_stats

    def _create_random_grid(self, rows: int, cols: int, allow_diagonals: bool) -> list[list[Cell]]:
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

    def _get_failing_constraint(self, trace: SolverResult, constraints: list[Constraint]) -> Constraint | None:
        for c in constraints:
            if not c.check(trace):
                return c
        return None

    def _prefill_cells(self, puzzle: Puzzle, count: int) -> None:
        all_coords = [(r, c) for r in range(puzzle.rows) for c in range(puzzle.cols)]

        count = min(count, len(all_coords))

        selected_coords = random.sample(all_coords, count)

        max_dim = max(puzzle.rows, puzzle.cols)

        for r, c in selected_coords:
            path_len = 0
            cell = puzzle.grid[r][c]
            dr, dc = cell.direction.delta
            curr_r, curr_c = r + dr, c + dc
            while 0 <= curr_r < puzzle.rows and 0 <= curr_c < puzzle.cols:
                path_len += 1
                curr_r += dr
                curr_c += dc

            upper_bound = min(path_len, max_dim - 1)
            val = random.randint(0, upper_bound)
            puzzle.grid[r][c].number = val

    def _flip_outward_arrows(self, puzzle: Puzzle) -> None:
        rows = puzzle.rows
        cols = puzzle.cols
        total_cells = rows * cols
        outward_arrows = []

        for r in range(rows):
            for c in range(cols):
                cell = puzzle.grid[r][c]
                dr, dc = cell.direction.delta
                nr, nc = r + dr, c + dc
                if not (0 <= nr < rows and 0 <= nc < cols):
                    outward_arrows.append((r, c))

        target_count = int(total_cells * self.OUTWARD_ARROWS_THRESHOLD)
        num_to_flip = len(outward_arrows) - target_count

        if num_to_flip > 0:
            opposites = {
                Direction.NORTH: Direction.SOUTH,
                Direction.SOUTH: Direction.NORTH,
                Direction.EAST: Direction.WEST,
                Direction.WEST: Direction.EAST,
                Direction.NORTH_EAST: Direction.SOUTH_WEST,
                Direction.SOUTH_WEST: Direction.NORTH_EAST,
                Direction.SOUTH_EAST: Direction.NORTH_WEST,
                Direction.NORTH_WEST: Direction.SOUTH_EAST,
            }
            to_flip = random.sample(outward_arrows, num_to_flip)
            for r, c in to_flip:
                cell = puzzle.grid[r][c]
                if cell.direction in opposites:
                    cell.direction = opposites[cell.direction]
