import copy
import time
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, List

import yaml

from japanese_arrows.models import Puzzle
from japanese_arrows.optimizer import optimize
from japanese_arrows.parser import parse_rule
from japanese_arrows.rules import (
    BacktrackRule,
    Conclusion,
    Constant,
    ExcludeVal,
    FORule,
    Rule,
    Variable,
)
from japanese_arrows.solver.definitions import (
    TYPE_CONSTANTS,
    TYPE_FUNCTIONS,
    TYPE_RELATIONS,
    ConclusionApplicationResult,
    compute_all_paths,
    create_universe,
)
from japanese_arrows.solver.utils import (
    apply_conclusion,
    apply_conclusion_with_undo,
)
from japanese_arrows.type_checking import check_rule
from japanese_arrows.universe import Universe


class SolverStatus(Enum):
    SOLVED = "SOLVED"
    NO_SOLUTION = "NO_SOLUTION"
    UNDERCONSTRAINED = "UNDERCONSTRAINED"


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
                        puzzle,
                        hypothesis_rules,
                        universe,
                        path_cache,
                        rule.rule_depth,
                        timing_stats,
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
                                puzzle,
                                rules,
                                universe,
                                path_cache,
                                depth - 1,
                                timing_stats,
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
        return apply_conclusion(puzzle, conclusion, witness, universe)

    def _apply_conclusion_with_undo(
        self,
        puzzle: Puzzle,
        conclusion: Conclusion,
        witness: dict[str, Any],
        universe: Universe,
    ) -> Callable[[], None] | str | None:
        return apply_conclusion_with_undo(puzzle, conclusion, witness, universe)

    def _create_universe(
        self,
        puzzle: Puzzle,
        path_cache: dict[tuple[int, int], list[tuple[int, int]]] | None = None,
    ) -> Universe:
        return create_universe(puzzle, path_cache)

    def _is_solved(self, puzzle: Puzzle) -> bool:
        return puzzle.validate()


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
        project_root = Path(__file__).parent.parent.parent
        rules_file = project_root / "config" / "rules.yaml"
    else:
        rules_file = Path(rules_file)

    # Load rules from YAML file
    with open(rules_file) as f:
        rules_data = yaml.safe_load(f)

    all_rules = []
    for rule_dict in rules_data:
        rule = parse_rule(rule_dict)
        if max_complexity is None or rule.complexity <= max_complexity:
            if isinstance(rule, FORule):
                # Type check before optimization
                check_rule(rule, TYPE_CONSTANTS, TYPE_FUNCTIONS, TYPE_RELATIONS)

                # Optimize the rule condition (miniscoping quantifiers)
                rule.condition = optimize(rule.condition)

                # Type check after optimization
                check_rule(rule, TYPE_CONSTANTS, TYPE_FUNCTIONS, TYPE_RELATIONS)

            all_rules.append(rule)

    return Solver(all_rules)
