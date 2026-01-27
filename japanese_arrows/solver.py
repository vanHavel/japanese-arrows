import copy
import time
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, List, Set, Tuple

import yaml

from japanese_arrows.models import Direction, Puzzle
from japanese_arrows.optimizer import optimize
from japanese_arrows.parser import parse_rule
from japanese_arrows.rules import (
    BacktrackRule,
    Conclusion,
    Constant,
    ExcludeVal,
    FORule,
    OnlyVal,
    Rule,
    SetVal,
    Variable,
)
from japanese_arrows.type_checking import Type, check_rule
from japanese_arrows.universe import Universe


class SolverStatus(Enum):
    SOLVED = "SOLVED"
    NO_SOLUTION = "NO_SOLUTION"
    UNDERCONSTRAINED = "UNDERCONSTRAINED"


class ConclusionApplicationResult(Enum):
    NO_PROGRESS = "NO_PROGRESS"
    PROGRESS = "PROGRESS"
    CONTRADICTION = "CONTRADICTION"


@dataclass
class SolverStep:
    """Records a single step where a rule made progress."""

    rule_name: str
    rule_complexity: int
    witness: dict[str, Any]

    conclusions_applied: list[Conclusion]
    puzzle_state: "Puzzle"
    contradiction_trace: list[str] = field(default_factory=list)


@dataclass
class SolverResult:
    """Result of solving a puzzle with detailed tracking."""

    status: SolverStatus
    puzzle: Puzzle
    max_complexity_used: int
    rule_application_count: Counter[str]
    rule_execution_time: dict[str, float] = field(default_factory=dict)
    steps: list[SolverStep] = field(default_factory=list)
    initial_puzzle: Puzzle | None = None
    contradiction_location: tuple[int, int] | None = None


class Solver:
    def __init__(self, rules: List[Rule]):
        self.rules = sorted(rules, key=lambda r: r.complexity)
        self.max_rule_complexity = max((r.complexity for r in rules), default=1)

    def solve(
        self,
        puzzle: Puzzle,
        path_cache: dict[tuple[int, int], list[tuple[int, int]]] | None = None,
        reuse_candidates: bool = False,
    ) -> SolverResult:
        if path_cache is None:
            path_cache = compute_all_paths(puzzle)

        initial_puzzle_copy = copy.deepcopy(puzzle)

        puzzle = copy.deepcopy(puzzle)
        if not reuse_candidates:
            self._initialize_candidates(puzzle)

        steps: list[SolverStep] = []
        max_complexity_used = 0
        rule_application_count: Counter[str] = Counter()
        rule_execution_time: dict[str, float] = {}

        universe = self._create_universe(puzzle, path_cache)

        while True:
            progress_made = False
            for rule in self.rules:
                start_time = time.perf_counter()
                # Capture total time attributed so far to subtract "children" time later
                stats_sum_before = sum(rule_execution_time.values())

                result = self._try_apply_rule(puzzle, rule, universe, path_cache, rule_execution_time)

                end_time = time.perf_counter()
                total_duration = end_time - start_time
                stats_sum_after = sum(rule_execution_time.values())

                # "Self time" is total wall time minus time claimed by inner rules
                children_time = stats_sum_after - stats_sum_before
                self_time = max(0.0, total_duration - children_time)

                rule_execution_time[rule.name] = rule_execution_time.get(rule.name, 0.0) + self_time

                if result.status == SolverStatus.NO_SOLUTION:
                    return SolverResult(
                        status=SolverStatus.NO_SOLUTION,
                        puzzle=puzzle,
                        max_complexity_used=max(max_complexity_used, result.max_complexity_used),
                        rule_application_count=rule_application_count,
                        rule_execution_time=rule_execution_time,
                        steps=steps,
                        initial_puzzle=initial_puzzle_copy,
                        contradiction_location=result.contradiction_location,
                    )

                if result.steps:
                    # Progress made
                    steps.extend(result.steps)
                    rule_application_count[rule.name] += len(result.steps)
                    max_complexity_used = max(max_complexity_used, rule.complexity)
                    progress_made = True
                    break  # Restart from the beginning (simplest rules)

            if not progress_made:
                break

        status = self._determine_final_status(puzzle)

        return SolverResult(
            status=status,
            puzzle=puzzle,
            max_complexity_used=max_complexity_used,
            rule_application_count=rule_application_count,
            rule_execution_time=rule_execution_time,
            steps=steps,
            initial_puzzle=initial_puzzle_copy,
        )

    def _try_apply_rule(
        self,
        puzzle: Puzzle,
        rule: Rule,
        universe: Universe,
        path_cache: dict[tuple[int, int], list[tuple[int, int]]],
        timing_stats: dict[str, float],
    ) -> SolverResult:
        if isinstance(rule, BacktrackRule):
            return self._apply_backtrack_rule(puzzle, rule, universe, path_cache, timing_stats)

        if not isinstance(rule, FORule):
            return SolverResult(
                status=SolverStatus.UNDERCONSTRAINED,
                puzzle=puzzle,
                max_complexity_used=0,
                rule_application_count=Counter(),
                steps=[],
            )

        for witness in universe.check_all(rule.condition):
            applied_conclusions: list[Conclusion] = []

            for conclusion in rule.conclusions:
                result, loc = self._apply_conclusion(puzzle, conclusion, witness, universe)

                if result == ConclusionApplicationResult.CONTRADICTION:
                    return SolverResult(
                        status=SolverStatus.NO_SOLUTION,
                        puzzle=puzzle,
                        max_complexity_used=0,
                        rule_application_count=Counter(),
                        steps=[],
                        contradiction_location=loc,
                    )
                elif result == ConclusionApplicationResult.PROGRESS:
                    applied_conclusions.append(conclusion)

            if applied_conclusions:
                step = SolverStep(
                    rule_name=rule.name,
                    rule_complexity=rule.complexity,
                    witness=witness,
                    conclusions_applied=applied_conclusions,
                    puzzle_state=copy.deepcopy(puzzle),
                )
                return SolverResult(
                    status=SolverStatus.UNDERCONSTRAINED,
                    puzzle=puzzle,
                    max_complexity_used=0,
                    rule_application_count=Counter(),
                    steps=[step],
                )

        return SolverResult(
            status=SolverStatus.UNDERCONSTRAINED,
            puzzle=puzzle,
            max_complexity_used=0,
            rule_application_count=Counter(),
            steps=[],
        )

    def _check_consistency(
        self, puzzle: Puzzle, path_cache: dict[tuple[int, int], list[tuple[int, int]]]
    ) -> tuple[bool, str | None, tuple[int, int] | None]:
        """
        Checks if the current partial state is consistent using precomputed paths.
        Returns (False, Reason, Location) if a contradiction is detected.
        """
        for r in range(puzzle.rows):
            for c in range(puzzle.cols):
                cell = puzzle.grid[r][c]

                if cell.number is None:
                    if not cell.candidates:
                        return False, f"Cell ({r},{c}) has no candidates left", (r, c)

                if cell.number is not None:
                    seen_values = set()

                    path = path_cache.get((r, c), [])

                    for pr, pc in path:
                        target = puzzle.grid[pr][pc]
                        if target.number is not None:
                            seen_values.add(target.number)

                    if len(seen_values) > cell.number:
                        return (
                            False,
                            f"Cell ({r},{c}) sees {len(seen_values)} distinct values (> {cell.number})",
                            (r, c),
                        )

        return True, None, None

    def _apply_backtrack_rule(
        self,
        puzzle: Puzzle,
        rule: BacktrackRule,
        universe: Universe,
        path_cache: dict[tuple[int, int], list[tuple[int, int]]],
        timing_stats: dict[str, float],
    ) -> SolverResult:
        candidates_map: list[tuple[int, int, set[int]]] = []
        for r in range(puzzle.rows):
            for c in range(puzzle.cols):
                cell = puzzle.grid[r][c]
                if cell.number is None:
                    cands = cell.candidates if cell.candidates is not None else set()
                    if cands:
                        candidates_map.append((r, c, cands))

        candidates_map.sort(key=lambda x: len(x[2]))

        hypothesis_rules = [r for r in self.rules if r.complexity <= rule.max_rule_complexity]

        original_grid = puzzle.grid

        for r, c, cands in candidates_map:
            for val in list(cands):
                try:
                    working_grid = copy.deepcopy(original_grid)
                    puzzle.grid = working_grid

                    cell = puzzle.grid[r][c]
                    cell.number = val
                    cell.candidates = {val}

                    contradiction_found = False
                    trace: list[str] | None = None

                    trace = self._find_contradiction_optimized(
                        puzzle, hypothesis_rules, universe, path_cache, rule.rule_depth, timing_stats
                    )
                    if trace is not None:
                        contradiction_found = True

                finally:
                    puzzle.grid = original_grid

                if contradiction_found and trace is not None:
                    backtrack_witness = {"p": (r, c)}
                    conclusion = ExcludeVal(position=Variable("p"), operator="=", value=Constant(val))

                    apply_res, loc = self._apply_conclusion(puzzle, conclusion, backtrack_witness, universe)

                    if apply_res == ConclusionApplicationResult.CONTRADICTION:
                        return SolverResult(
                            status=SolverStatus.NO_SOLUTION,
                            puzzle=puzzle,
                            max_complexity_used=rule.complexity,
                            rule_application_count=Counter({rule.name: 1}),
                            steps=[],
                            contradiction_location=loc,
                        )

                    if apply_res == ConclusionApplicationResult.PROGRESS:
                        step = SolverStep(
                            rule_name=rule.name,
                            rule_complexity=rule.complexity,
                            witness=backtrack_witness,
                            conclusions_applied=[conclusion],
                            contradiction_trace=[f"Assuming {r},{c} is {val}:"] + trace,
                            puzzle_state=copy.deepcopy(puzzle),
                        )
                        return SolverResult(
                            status=SolverStatus.UNDERCONSTRAINED,
                            puzzle=puzzle,
                            max_complexity_used=rule.complexity,
                            rule_application_count=Counter({rule.name: 1}),
                            steps=[step],
                        )

        return SolverResult(
            status=SolverStatus.UNDERCONSTRAINED,
            puzzle=puzzle,
            max_complexity_used=0,
            rule_application_count=Counter(),
            steps=[],
        )

    def _find_contradiction_optimized(
        self,
        puzzle: Puzzle,
        rules: list[Rule],
        universe: Universe,
        path_cache: dict[tuple[int, int], list[tuple[int, int]]],
        depth: int,
        timing_stats: dict[str, float],
    ) -> list[str] | None:
        # Check initial consistency (depth 0 check)
        valid, reason, _ = self._check_consistency(puzzle, path_cache)
        if not valid:
            return [f"Inconsistent state: {reason}"]

        if depth <= 0:
            return None

        # Optimization: Interleave generation and application (Fail Fast)
        for rule in rules:
            if not isinstance(rule, FORule):
                continue

            t0 = time.perf_counter()
            stats0 = sum(timing_stats.values())

            try:
                # Iterate witnesses and apply immediately
                for witness in universe.check_all(rule.condition):
                    for conclusion in rule.conclusions:
                        # Try applying with undo
                        undo_op = self._apply_conclusion_with_undo(puzzle, conclusion, witness, universe)

                        if undo_op is None:
                            continue  # No progress

                        step_desc = f"Applied {rule.name} with {witness} -> {conclusion}"

                        if undo_op == "CONTRADICTION":
                            return [step_desc, "CONTRADICTION"]

                        # If successful progress, check deeper
                        # Optimization: For depth 1, we just need to check consistency of the new state
                        # which happens at the start of the recursive call.
                        # For depth > 1, we recurse fully.

                        trace = None
                        if depth == 1:
                            # Depth 1 specialized: just check consistency of result
                            valid_next, reason_next, _ = self._check_consistency(puzzle, path_cache)
                            if not valid_next:
                                trace = [f"Inconsistent state: {reason_next}"]
                        else:
                            # Depth > 1: Full recursion
                            trace = self._find_contradiction_optimized(
                                puzzle, rules, universe, path_cache, depth - 1, timing_stats
                            )

                        if trace is not None:
                            if callable(undo_op):
                                undo_op()
                            return [step_desc] + trace

                        # Backtrack this step
                        if callable(undo_op):
                            undo_op()
            finally:
                t1 = time.perf_counter()
                stats1 = sum(timing_stats.values())
                children_time = stats1 - stats0
                self_time = max(0.0, (t1 - t0) - children_time)
                timing_stats[rule.name] = timing_stats.get(rule.name, 0.0) + self_time

        return None

    def _determine_final_status(self, puzzle: Puzzle) -> SolverStatus:
        if self._is_solved(puzzle):
            return SolverStatus.SOLVED
        return SolverStatus.UNDERCONSTRAINED

    def _initialize_candidates(self, puzzle: Puzzle) -> None:
        limit = max(puzzle.rows, puzzle.cols)
        initial_candidates = set(range(limit))

        for row in puzzle.grid:
            for cell in row:
                if cell.number is None:
                    cell.candidates = initial_candidates.copy()
                else:
                    cell.candidates = {cell.number}

    def _apply_conclusion(
        self,
        puzzle: Puzzle,
        conclusion: Conclusion,
        witness: dict[str, Any],
        universe: Universe,
    ) -> tuple[ConclusionApplicationResult, tuple[int, int] | None]:
        p_val = universe.eval_term(conclusion.position, witness)

        if p_val == "OOB":
            return ConclusionApplicationResult.NO_PROGRESS, None

        r, c = p_val
        cell = puzzle.grid[r][c]

        if cell.number is not None and cell.candidates is not None and not cell.candidates:
            return ConclusionApplicationResult.NO_PROGRESS, None

        current_candidates = cell.candidates
        if cell.number is not None:
            current_candidates = {cell.number}
        elif current_candidates is None:
            return ConclusionApplicationResult.NO_PROGRESS, None

        new_candidates = current_candidates.copy()

        if isinstance(conclusion, SetVal):
            val = universe.eval_term(conclusion.value, witness)
            if not isinstance(val, int):
                cell.candidates = set()
                cell.number = None
                return ConclusionApplicationResult.CONTRADICTION, (r, c)
            new_candidates.intersection_update({val})

        elif isinstance(conclusion, ExcludeVal):
            val = universe.eval_term(conclusion.value, witness)
            if isinstance(val, int):
                if conclusion.operator == "=":
                    new_candidates.discard(val)
                elif conclusion.operator == ">":
                    new_candidates = {c for c in new_candidates if not (c > val)}
                elif conclusion.operator == "<":
                    new_candidates = {c for c in new_candidates if not (c < val)}
                elif conclusion.operator == ">=":
                    new_candidates = {c for c in new_candidates if not (c >= val)}
                elif conclusion.operator == "<=":
                    new_candidates = {c for c in new_candidates if not (c <= val)}
                elif conclusion.operator == "!=":
                    new_candidates = {c for c in new_candidates if not (c != val)}

        elif isinstance(conclusion, OnlyVal):
            allowed = set()
            for v_term in conclusion.values:
                v = universe.eval_term(v_term, witness)
                if isinstance(v, int):
                    allowed.add(v)
            new_candidates.intersection_update(allowed)

        if new_candidates != current_candidates:
            if not new_candidates:
                cell.candidates = set()
                return ConclusionApplicationResult.CONTRADICTION, (r, c)

            cell.candidates = new_candidates
            if len(new_candidates) == 1:
                cell.number = next(iter(new_candidates))

            return ConclusionApplicationResult.PROGRESS, None

        return ConclusionApplicationResult.NO_PROGRESS, None

    def _apply_conclusion_with_undo(
        self, puzzle: Puzzle, conclusion: Conclusion, witness: dict[str, Any], universe: Universe
    ) -> Callable[[], None] | str | None:
        """
        Applies a conclusion.
        Returns:
          - A callable (undo function) if PROGRESS was made.
          - "CONTRADICTION" string if a contradiction was found.
          - None if NO_PROGRESS.
        """
        p_val = universe.eval_term(conclusion.position, witness)
        if p_val == "OOB":
            return None

        r, c = p_val
        cell = puzzle.grid[r][c]

        if cell.number is not None and cell.candidates is not None and not cell.candidates:
            return None

        current_candidates = cell.candidates
        current_number = cell.number

        if current_number is not None:
            eff_candidates = {current_number}
        elif current_candidates is not None:
            eff_candidates = current_candidates
        else:
            return None  # Should not happen

        new_candidates = eff_candidates.copy()

        if isinstance(conclusion, SetVal):
            val = universe.eval_term(conclusion.value, witness)
            if not isinstance(val, int):
                return "CONTRADICTION"
            new_candidates.intersection_update({val})

        elif isinstance(conclusion, ExcludeVal):
            val = universe.eval_term(conclusion.value, witness)
            if isinstance(val, int):
                if conclusion.operator == "=":
                    new_candidates.discard(val)
                elif conclusion.operator == ">":
                    new_candidates = {c for c in new_candidates if not (c > val)}
                elif conclusion.operator == "<":
                    new_candidates = {c for c in new_candidates if not (c < val)}
                elif conclusion.operator == ">=":
                    new_candidates = {c for c in new_candidates if not (c >= val)}
                elif conclusion.operator == "<=":
                    new_candidates = {c for c in new_candidates if not (c <= val)}
                elif conclusion.operator == "!=":
                    new_candidates = {c for c in new_candidates if not (c != val)}

        elif isinstance(conclusion, OnlyVal):
            allowed = set()
            for v_term in conclusion.values:
                v = universe.eval_term(v_term, witness)
                if isinstance(v, int):
                    allowed.add(v)
            new_candidates.intersection_update(allowed)

        if new_candidates != eff_candidates:
            if not new_candidates:
                return "CONTRADICTION"

            # Apply change
            old_candidates_obj = cell.candidates
            old_number_obj = cell.number

            cell.candidates = new_candidates
            if len(new_candidates) == 1:
                cell.number = next(iter(new_candidates))

            # Undo closure
            def undo() -> None:
                cell.candidates = old_candidates_obj
                cell.number = old_number_obj

            return undo

        return None

    def _create_universe(
        self,
        puzzle: Puzzle,
        path_cache: dict[tuple[int, int], list[tuple[int, int]]] | None = None,
    ) -> Universe:
        """
        Creates a Universe for rule evaluation.

        Type guarantees from rule type checking:
        - POSITION variables resolve to (r, c) tuples or "OOB" (never "nil")
        - NUMBER variables resolve to int or "nil" (never "OOB")
        - Variables in conclusions are guaranteed to exist in the witness
        """
        if path_cache is None:
            path_cache = compute_all_paths(puzzle)

        # Precompute ahead values (purely geometric, never changes)
        ahead_cache: dict[Any, int] = {}
        for r in range(puzzle.rows):
            for c in range(puzzle.cols):
                ahead_cache[(r, c)] = len(path_cache[(r, c)])
        ahead_cache["OOB"] = 0

        # Precompute points_at relations (purely geometric, never changes)
        points_at_cache: dict[tuple[Any, Any], bool] = {}
        for r in range(puzzle.rows):
            for c in range(puzzle.cols):
                p = (r, c)
                path = path_cache[p]
                for q in path:
                    points_at_cache[(p, q)] = True
                # Also cache OOB cases
                points_at_cache[(p, "OOB")] = False
                points_at_cache[("OOB", p)] = False
        points_at_cache[("OOB", "OOB")] = False

        rows = puzzle.rows
        cols = puzzle.cols
        max_dim = max(rows, cols)

        positions: Set[Any] = {(r, c) for r in range(rows) for c in range(cols)}
        positions.add("OOB")
        numbers: Set[Any] = set(range(max_dim))
        numbers.add("nil")

        domain: dict[Type, Set[Any]] = {
            Type.POSITION: positions,
            Type.NUMBER: numbers,
        }

        # Constants
        constants: dict[str, Any] = {
            "OOB": "OOB",
            "nil": "nil",
        }
        for i in numbers:
            if isinstance(i, int):
                constants[str(i)] = i

        # Type alias for position
        Position = tuple[int, int] | str  # (r, c) or "OOB"
        Number = int | str  # int or "nil"

        # Helper for geometry
        def get_next(p: Position) -> Position:
            if p == "OOB":
                return "OOB"
            r, c = p
            cell = puzzle.grid[r][c]
            dr, dc = cell.direction.delta
            nr, nc = r + dr, c + dc

            if 0 <= nr < rows and 0 <= nc < cols:
                return (nr, nc)
            return "OOB"

        def get_path(p: Position) -> list[tuple[int, int]]:
            if p == "OOB":
                return []
            if isinstance(p, tuple):
                return path_cache[p]
            return []

        # Functions with readable types
        def next_pos(p: Position) -> Position:
            return get_next(p)

        def val(p: Position) -> Number:
            if p == "OOB":
                return "nil"
            r, c = p
            cell = puzzle.grid[r][c]
            return cell.number if cell.number is not None else "nil"

        def ahead(p: Position) -> int:
            return ahead_cache.get(p, 0)

        def behind(p: Position) -> int:
            if p == "OOB":
                return 0
            r, c = p
            cell = puzzle.grid[r][c]
            dr, dc = cell.direction.delta
            count = 0
            curr_r, curr_c = r - dr, c - dc
            while 0 <= curr_r < rows and 0 <= curr_c < cols:
                count += 1
                curr_r, curr_c = curr_r - dr, curr_c - dc
            return count

        def dir_of(p: Position) -> Direction | str:
            if p == "OOB":
                return "nil"
            r, c = p
            return puzzle.grid[r][c].direction

        def sees_distinct(p: Position) -> int:
            if p == "OOB":
                return 0
            path = get_path(p)
            distinct_values: set[int] = set()
            for pos in path:
                r, c = pos
                cell = puzzle.grid[r][c]
                if cell.number is not None:
                    distinct_values.add(cell.number)
            return len(distinct_values)

        def sees_distinct_candidates(p: Position) -> int:
            if p == "OOB":
                return 0
            path = get_path(p)
            union_candidates: set[int] = set()
            for pos in path:
                r, c = pos
                cell = puzzle.grid[r][c]
                if cell.number is not None:
                    union_candidates.add(cell.number)
                elif cell.candidates is not None:
                    union_candidates.update(cell.candidates)
            return len(union_candidates)

        def ahead_free(p: Position) -> int:
            if p == "OOB":
                return 0
            path = get_path(p)
            count = 0
            for pos in path:
                r, c = pos
                if puzzle.grid[r][c].number is None:
                    count += 1
            return count

        def between_free(p: Position, q: Position) -> Number:
            if p == "OOB" or q == "OOB":
                return "nil"
            path = get_path(p)
            count = 0
            found = False
            for pos in path:
                if pos == q:
                    found = True
                    break
                r, c = pos
                if puzzle.grid[r][c].number is None:
                    count += 1
            if found:
                return count
            return "nil"

        def min_candidate(p: Position) -> Number:
            if p == "OOB":
                return "nil"
            r, c = p
            cell = puzzle.grid[r][c]
            if cell.number is not None:
                return cell.number
            if cell.candidates:
                return min(cell.candidates)
            return "nil"

        def max_candidate(p: Position) -> Number:
            if p == "OOB":
                return "nil"
            r, c = p
            cell = puzzle.grid[r][c]
            if cell.number is not None:
                return cell.number
            if cell.candidates:
                return max(cell.candidates)
            return "nil"

        functions: dict[str, Callable[[Tuple[Any, ...]], Any]] = {
            "next": lambda args: next_pos(args[0]),
            "val": lambda args: val(args[0]),
            "ahead": lambda args: ahead(args[0]),
            "behind": lambda args: behind(args[0]),
            "between_free": lambda args: between_free(args[0], args[1]),
            "ahead_free": lambda args: ahead_free(args[0]),
            "dir": lambda args: dir_of(args[0]),
            "sees_distinct": lambda args: sees_distinct(args[0]),
            "sees_distinct_candidates": lambda args: sees_distinct_candidates(args[0]),
            "min_candidate": lambda args: min_candidate(args[0]),
            "max_candidate": lambda args: max_candidate(args[0]),
            "add": lambda args: args[0] + args[1] if isinstance(args[0], int) and isinstance(args[1], int) else "nil",
        }

        # Relations with readable types
        def points_at(p: Position, q: Position) -> bool:
            return points_at_cache.get((p, q), False)

        def compare(a: Number, b: Number, op: str) -> bool:
            if a == "nil" or b == "nil":
                return False
            assert isinstance(a, int) and isinstance(b, int)
            if op == "<":
                return a < b
            if op == ">":
                return a > b
            if op == "<=":
                return a <= b
            if op == ">=":
                return a >= b
            return False

        def candidate(p: Position, i: Number) -> bool:
            if p == "OOB":
                return False
            if not isinstance(i, int):
                return False
            r, c = p
            cell = puzzle.grid[r][c]
            if cell.number is not None:
                return cell.number == i
            if cell.candidates is not None:
                return i in cell.candidates
            return False

        def sees_value(p: Position, i: Number) -> bool:
            if p == "OOB" or not isinstance(i, int):
                return False
            path = get_path(p)
            for pos in path:
                r, c = pos
                if puzzle.grid[r][c].number == i:
                    return True
            return False

        relations: dict[str, Callable[[Tuple[Any, ...]], bool]] = {
            "points_at": lambda args: points_at(args[0], args[1]),
            "candidate": lambda args: candidate(args[0], args[1]),
            "sees_value": lambda args: sees_value(args[0], args[1]),
            "<": lambda args: compare(args[0], args[1], "<"),
            ">": lambda args: compare(args[0], args[1], ">"),
            "<=": lambda args: compare(args[0], args[1], "<="),
            ">=": lambda args: compare(args[0], args[1], ">="),
        }

        quantifier_exclusions = {
            Type.POSITION: {"OOB"},
            Type.NUMBER: {"nil"},
        }

        return Universe(
            domain=domain,
            constants=constants,
            relations=relations,
            functions=functions,
            quantifier_exclusions=quantifier_exclusions,
        )

    def _is_solved(self, puzzle: Puzzle) -> bool:
        return puzzle.validate()


def compute_all_paths(puzzle: Puzzle) -> dict[tuple[int, int], list[tuple[int, int]]]:
    """
    Precomputes the straight-line path for every cell in the puzzle grid.
    Returns a dictionary mapping (r, c) to list of (r, c) coordinates in the path.
    """
    path_cache: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for r in range(puzzle.rows):
        for c in range(puzzle.cols):
            dr, dc = puzzle.grid[r][c].direction.delta
            curr_r, curr_c = r + dr, c + dc
            path = []
            while 0 <= curr_r < puzzle.rows and 0 <= curr_c < puzzle.cols:
                path.append((curr_r, curr_c))
                curr_r, curr_c = curr_r + dr, curr_c + dc
            path_cache[(r, c)] = path
    return path_cache


def create_solver(max_complexity: int | None = None, rules_file: str | Path | None = None) -> Solver:
    """
    Create a Solver with rules up to the specified complexity level.

    Args:
        max_complexity: Maximum complexity level of rules to include.
                       If None (default), includes all rules regardless of complexity.
        rules_file: Path to the YAML rules file. If None, uses config/rules.yaml

    Returns:
        A Solver instance with the filtered rules
    """
    if rules_file is None:
        # Default to config/rules.yaml relative to the project root
        # Assuming this file is in japanese_arrows/solver.py
        project_root = Path(__file__).parent.parent
        rules_file = project_root / "config" / "rules.yaml"
    else:
        rules_file = Path(rules_file)

    # Load rules from YAML file
    with open(rules_file) as f:
        rules_data = yaml.safe_load(f)

    # Parse rules and filter by complexity
    # Type definitions
    type_constants = {"OOB": Type.POSITION, "nil": Type.NUMBER}
    type_functions = {
        "next": ([Type.POSITION], Type.POSITION),
        "val": ([Type.POSITION], Type.NUMBER),
        "ahead": ([Type.POSITION], Type.NUMBER),
        "behind": ([Type.POSITION], Type.NUMBER),
        "between_free": ([Type.POSITION, Type.POSITION], Type.NUMBER),
        "ahead_free": ([Type.POSITION], Type.NUMBER),
        "dir": ([Type.POSITION], Type.DIRECTION),
        "sees_distinct": ([Type.POSITION], Type.NUMBER),
        "sees_distinct_candidates": ([Type.POSITION], Type.NUMBER),
        "min_candidate": ([Type.POSITION], Type.NUMBER),
        "max_candidate": ([Type.POSITION], Type.NUMBER),
        "add": ([Type.NUMBER, Type.NUMBER], Type.NUMBER),
    }
    type_relations = {
        "points_at": [Type.POSITION, Type.POSITION],
        "candidate": [Type.POSITION, Type.NUMBER],
        "sees_value": [Type.POSITION, Type.NUMBER],
        "<": [Type.NUMBER, Type.NUMBER],
        ">": [Type.NUMBER, Type.NUMBER],
        "<=": [Type.NUMBER, Type.NUMBER],
        ">=": [Type.NUMBER, Type.NUMBER],
    }

    all_rules = []
    for rule_dict in rules_data:
        rule = parse_rule(rule_dict)
        if max_complexity is None or rule.complexity <= max_complexity:
            if isinstance(rule, FORule):
                # Type check before optimization
                check_rule(rule, type_constants, type_functions, type_relations)

                # Optimize the rule condition (miniscoping quantifiers)
                rule.condition = optimize(rule.condition)

                # Type check after optimization
                check_rule(rule, type_constants, type_functions, type_relations)

            all_rules.append(rule)

    return Solver(all_rules)
