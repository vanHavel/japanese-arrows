from abc import ABC, abstractmethod
from typing import Optional

from japanese_arrows.models import Puzzle
from japanese_arrows.solver import SolverResult


class Constraint(ABC):
    @abstractmethod
    def check(self, trace: SolverResult) -> bool:
        pass

    def pre_check(self, puzzle: Puzzle) -> bool:
        return True


class RuleComplexityFraction(Constraint):
    def __init__(
        self,
        complexity: int,
        min_fraction: Optional[float] = None,
        max_fraction: Optional[float] = None,
    ):
        self.complexity = complexity
        self.min_fraction = min_fraction
        self.max_fraction = max_fraction

    def check(self, trace: SolverResult) -> bool:
        steps = trace.steps
        total = len(steps)
        if total == 0:
            if self.min_fraction is not None and self.min_fraction > 0:
                return False
            return True

        comp_apps = sum(1 for s in steps if s.rule_complexity == self.complexity)
        fraction = comp_apps / total

        if self.min_fraction is not None and fraction < self.min_fraction:
            return False
        if self.max_fraction is not None and fraction > self.max_fraction:
            return False

        return True


class NumberFraction(Constraint):
    def __init__(self, number: int, min_fraction: Optional[float] = None, max_fraction: Optional[float] = None):
        self.number = number
        self.min_fraction = min_fraction
        self.max_fraction = max_fraction

    def check(self, trace: SolverResult) -> bool:
        puzzle = trace.puzzle
        total_cells = puzzle.rows * puzzle.cols
        if total_cells == 0:
            return True

        count = 0
        for row in puzzle.grid:
            for cell in row:
                if cell.number == self.number:
                    count += 1

        fraction = count / total_cells

        if self.min_fraction is not None and fraction < self.min_fraction:
            return False
        if self.max_fraction is not None and fraction > self.max_fraction:
            return False

        return True

    def pre_check(self, puzzle: Puzzle) -> bool:
        total_cells = puzzle.rows * puzzle.cols
        if total_cells == 0:
            return True

        # Calculate path lengths
        path_lengths = []
        for r in range(puzzle.rows):
            for c in range(puzzle.cols):
                cell = puzzle.grid[r][c]
                dr, dc = cell.direction.delta
                length = 0
                curr_r, curr_c = r + dr, c + dc
                while 0 <= curr_r < puzzle.rows and 0 <= curr_c < puzzle.cols:
                    length += 1
                    curr_r += dr
                    curr_c += dc
                path_lengths.append(length)

        if self.number == 0:
            # Number of 0s is exactly the number of cells with path_length == 0
            count = sum(1 for length in path_lengths if length == 0)
            fraction = count / total_cells
            if self.min_fraction is not None and fraction < self.min_fraction:
                return False
            if self.max_fraction is not None and fraction > self.max_fraction:
                return False
            return True

        if self.number == 1:
            # Number of 1s:
            # - At least cells with path_length == 1
            # - At most cells with path_length >= 1
            min_count = sum(1 for length in path_lengths if length == 1)
            max_count = sum(1 for length in path_lengths if length >= 1)

            if self.min_fraction is not None and max_count / total_cells < self.min_fraction:
                return False
            if self.max_fraction is not None and min_count / total_cells > self.max_fraction:
                return False
            return True

        # For number >= 2
        # max_count: path_length >= number
        max_count = sum(1 for length in path_lengths if length >= self.number)
        if self.min_fraction is not None and max_count / total_cells < self.min_fraction:
            return False

        return True


class UsesRule(Constraint):
    def __init__(self, rule_name: str, min_count: Optional[int] = None, min_fraction: Optional[float] = None):
        self.rule_name = rule_name
        self.min_count = min_count
        self.min_fraction = min_fraction

    def check(self, trace: SolverResult) -> bool:
        steps = trace.steps
        total = len(steps)

        count = sum(1 for s in steps if s.rule_name == self.rule_name)

        if self.min_count is not None and count < self.min_count:
            return False

        if self.min_fraction is not None:
            if total == 0:
                return self.min_fraction <= 0
            fraction = count / total
            if fraction < self.min_fraction:
                return False

        return True


class FollowingArrowsFraction(Constraint):
    def __init__(self, min_fraction: Optional[float] = None, max_fraction: Optional[float] = None):
        self.min_fraction = min_fraction
        self.max_fraction = max_fraction

    def _get_count(self, puzzle: Puzzle) -> int:
        count = 0
        for r in range(puzzle.rows):
            for c in range(puzzle.cols):
                cell = puzzle.grid[r][c]
                dr, dc = cell.direction.delta
                nr, nc = r + dr, c + dc
                if 0 <= nr < puzzle.rows and 0 <= nc < puzzle.cols:
                    if puzzle.grid[nr][nc].direction == cell.direction:
                        count += 1
        return count

    def check(self, trace: SolverResult) -> bool:
        # Since this only depends on the arrows, pre_check logic applies
        return self.pre_check(trace.puzzle)

    def pre_check(self, puzzle: Puzzle) -> bool:
        total_cells = puzzle.rows * puzzle.cols
        if total_cells == 0:
            return True

        count = self._get_count(puzzle)
        fraction = count / total_cells

        if self.min_fraction is not None and fraction < self.min_fraction:
            return False
        if self.max_fraction is not None and fraction > self.max_fraction:
            return False

        return True


class PrefilledCellsFraction(Constraint):
    def __init__(self, min_fraction: Optional[float] = None, max_fraction: Optional[float] = None):
        self.min_fraction = min_fraction
        self.max_fraction = max_fraction

    def check(self, trace: SolverResult) -> bool:
        puzzle = trace.initial_puzzle
        if puzzle is None:
            # Fallback to current puzzle if initial not stored (should not happen with latest solver)
            puzzle = trace.puzzle

        total_cells = puzzle.rows * puzzle.cols
        if total_cells == 0:
            return True

        count = sum(1 for row in puzzle.grid for cell in row if cell.number is not None)
        fraction = count / total_cells

        if self.min_fraction is not None and fraction < self.min_fraction:
            return False
        if self.max_fraction is not None and fraction > self.max_fraction:
            return False

        return True
