import copy
import random
from dataclasses import dataclass, field

from joblib import Parallel, delayed, effective_n_jobs

from japanese_arrows.generator.constraints import Constraint
from japanese_arrows.models import Cell, Direction, Puzzle
from japanese_arrows.solver import SolverResult, SolverStatus, compute_all_paths, create_solver


@dataclass
class GenerationStats:
    puzzles_successfully_generated: int = 0
    puzzles_rejected_constraints: int = 0
    puzzles_rejected_no_solution: int = 0
    rejections_per_constraint: dict[str, int] = field(default_factory=dict)


class Generator:
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

        while True:
            total_attempts = (
                stats.puzzles_successfully_generated
                + stats.puzzles_rejected_constraints
                + stats.puzzles_rejected_no_solution
            )
            if total_attempts >= max_attempts and max_attempts != -1:
                return None, stats

            grid = self._create_random_grid(rows, cols, allow_diagonals)

            current_puzzle = Puzzle(rows=rows, cols=cols, grid=grid)

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
            max_modifications = 10

            while True:
                trace = solver.solve(current_puzzle, path_cache=path_cache, reuse_candidates=reuse_candidates)

                if trace.status == SolverStatus.SOLVED:
                    failing_constraint = self._get_failing_constraint(trace, constraints)
                    if failing_constraint is None:
                        stats.puzzles_successfully_generated += 1
                        return current_puzzle, stats
                    else:
                        stats.puzzles_rejected_constraints += 1
                        stats.rejections_per_constraint[failing_constraint.name] = (
                            stats.rejections_per_constraint.get(failing_constraint.name, 0) + 1
                        )
                        break

                elif trace.status == SolverStatus.UNDERCONSTRAINED:
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

                    reuse_candidates = True

                    # Continue inner loop

                else:
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

                        # Recompute paths since arrows changed
                        path_cache = compute_all_paths(current_puzzle)
                        reuse_candidates = False
                        modifications += 1
                        continue

                    stats.puzzles_rejected_no_solution += 1
                    break

    def generate_many(
        self,
        max_count: int,
        rows: int,
        cols: int,
        allow_diagonals: bool,
        max_complexity: int,
        constraints: list[Constraint],
        prefilled_cells_count: int = 0,
        max_attempts: int = 1000,
        n_jobs: int = 1,
    ) -> tuple[list[Puzzle], GenerationStats]:
        n_tasks = max(max_count, effective_n_jobs(n_jobs)) if n_jobs != 1 else 1

        n_workers = effective_n_jobs(n_jobs)
        n_tasks = max(max_count, n_workers) if max_count == 1 else n_workers

        attempts_per_task = max_attempts // n_tasks
        target_puzzles_per_task = (max_count + n_tasks - 1) // n_tasks

        results = Parallel(n_jobs=n_jobs)(
            delayed(self._generate_batch)(
                target_count=target_puzzles_per_task,
                max_attempts=attempts_per_task,
                rows=rows,
                cols=cols,
                allow_diagonals=allow_diagonals,
                max_complexity=max_complexity,
                constraints=constraints,
                prefilled_cells_count=prefilled_cells_count,
            )
            for _ in range(n_tasks)
        )

        puzzles: list[Puzzle] = []
        overall_stats = GenerationStats()

        all_found_puzzles = []
        for task_puzzles, task_stats in results:
            all_found_puzzles.extend(task_puzzles)
            overall_stats.puzzles_rejected_constraints += task_stats.puzzles_rejected_constraints
            overall_stats.puzzles_rejected_no_solution += task_stats.puzzles_rejected_no_solution
            for name, count in task_stats.rejections_per_constraint.items():
                overall_stats.rejections_per_constraint[name] = (
                    overall_stats.rejections_per_constraint.get(name, 0) + count
                )

        puzzles = all_found_puzzles[:max_count]
        overall_stats.puzzles_successfully_generated = len(puzzles)

        return puzzles, overall_stats

    def _generate_batch(
        self,
        target_count: int,
        max_attempts: int,
        rows: int,
        cols: int,
        allow_diagonals: bool,
        max_complexity: int,
        constraints: list[Constraint],
        prefilled_cells_count: int,
    ) -> tuple[list[Puzzle], GenerationStats]:
        batch_puzzles: list[Puzzle] = []
        batch_stats = GenerationStats()

        while len(batch_puzzles) < target_count:
            total_attempts = (
                batch_stats.puzzles_successfully_generated
                + batch_stats.puzzles_rejected_constraints
                + batch_stats.puzzles_rejected_no_solution
            )
            remaining = max_attempts - total_attempts

            if remaining <= 0:
                break

            puzzle, _ = self.generate(
                rows=rows,
                cols=cols,
                allow_diagonals=allow_diagonals,
                max_complexity=max_complexity,
                constraints=constraints,
                prefilled_cells_count=prefilled_cells_count,
                max_attempts=total_attempts + remaining,
                _stats=batch_stats,
            )

            if puzzle is not None:
                batch_puzzles.append(puzzle)
            else:
                break

        return batch_puzzles, batch_stats

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
