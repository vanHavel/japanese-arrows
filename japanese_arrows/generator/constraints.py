from abc import ABC, abstractmethod
from typing import Optional

from japanese_arrows.models import Puzzle
from japanese_arrows.solver import SolverResult


class Constraint(ABC):
    @abstractmethod
    def check(self, trace: SolverResult) -> bool:
        pass

    @property
    def name(self) -> str:
        return self.__class__.__name__


class RuleComplexityFraction(Constraint):
    def __init__(
        self,
        complexity: int,
        min_fraction: Optional[float] = None,
        max_fraction: Optional[float] = None,
        min_count: Optional[int] = None,
        max_count: Optional[int] = None,
    ):
        self.complexity = complexity
        self.min_fraction = min_fraction
        self.max_fraction = max_fraction
        self.min_count = min_count
        self.max_count = max_count

    def check(self, trace: SolverResult) -> bool:
        steps = trace.steps
        total = len(steps)

        comp_apps = sum(1 for s in steps if s.rule_complexity == self.complexity)

        if self.min_count is not None and comp_apps < self.min_count:
            return False
        if self.max_count is not None and comp_apps > self.max_count:
            return False

        if total == 0:
            if self.min_fraction is not None and self.min_fraction > 0:
                return False
            return True

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
        puzzle = trace.puzzle
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
