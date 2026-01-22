import copy
from enum import Enum
from typing import Any, Callable, List, Set, Tuple, Union

from japanese_arrows.models import Puzzle
from japanese_arrows.rules import (
    Calculation,
    Conclusion,
    ConclusionConstant,
    ConclusionTerm,
    ConclusionVariable,
    ExcludeVal,
    OnlyVal,
    Rule,
    SetVal,
)
from japanese_arrows.type_checking import Type
from japanese_arrows.universe import Universe


class SolverResult(Enum):
    SOLVED = "SOLVED"
    NO_SOLUTION = "NO_SOLUTION"
    UNDERCONSTRAINED = "UNDERCONSTRAINED"


class Solver:
    def __init__(self, rules: List[Rule]):
        self.rules = rules

    def solve(self, puzzle: Puzzle) -> Tuple[SolverResult, Puzzle]:
        puzzle = copy.deepcopy(puzzle)
        self._initialize_candidates(puzzle)

        while True:
            progress = self._apply_rules(puzzle)
            if not progress:
                break

        # Check termination status
        if self._is_solved(puzzle):
            return SolverResult.SOLVED, puzzle
        elif self._has_contradiction(puzzle):
            return SolverResult.NO_SOLUTION, puzzle
        else:
            return SolverResult.UNDERCONSTRAINED, puzzle

    def _initialize_candidates(self, puzzle: Puzzle) -> None:
        limit = max(puzzle.rows, puzzle.cols)
        initial_candidates = set(range(limit))

        for row in puzzle.grid:
            for cell in row:
                if cell.number is None:
                    cell.candidates = initial_candidates.copy()
                else:
                    cell.candidates = {cell.number}

    def _apply_rules(self, puzzle: Puzzle) -> bool:
        universe = self._create_universe(puzzle)

        for rule in self.rules:
            # Check condition
            witness = universe.check(rule.condition)
            if witness:
                # Apply conclusions
                rule_progress = False
                for conclusion in rule.conclusions:
                    if self._apply_conclusion(puzzle, conclusion, witness, universe):
                        rule_progress = True

                if rule_progress:
                    return True

        return False

    def _apply_conclusion(
        self, puzzle: Puzzle, conclusion: Conclusion, witness: dict[str, Any], universe: Universe
    ) -> bool:
        p_val = self._eval_conclusion_term(conclusion.position, witness)

        if p_val == "OOB":
            return False

        r, c = p_val
        cell = puzzle.grid[r][c]

        current_candidates = cell.candidates
        if cell.number is not None:
            current_candidates = {cell.number}
        elif current_candidates is None:
            return False

        new_candidates = current_candidates.copy()

        if isinstance(conclusion, SetVal):
            val = self._eval_conclusion_term(conclusion.value, witness)
            if not isinstance(val, int):
                # If set(p, nil), this is a contradiction for valid puzzles or means no solution
                # Mark as contradiction by emptying candidates
                cell.candidates = set()
                cell.number = None
                return True
            new_candidates.intersection_update({val})

        elif isinstance(conclusion, ExcludeVal):
            val = self._eval_conclusion_term(conclusion.value, witness)
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
                    # exclude(p, != val) -> keep only val. Logic: "exclude values that are != val" -> "only val"
                    new_candidates = {c for c in new_candidates if not (c != val)}

        elif isinstance(conclusion, OnlyVal):
            allowed = set()
            for v_term in conclusion.values:
                v = self._eval_conclusion_term(v_term, witness)
                if isinstance(v, int):
                    allowed.add(v)
            new_candidates.intersection_update(allowed)

        # Check if changed
        if new_candidates != current_candidates:
            if not new_candidates:
                cell.candidates = set()
                cell.number = None
                return True

            cell.candidates = new_candidates
            if len(new_candidates) == 1:
                cell.number = next(iter(new_candidates))
            elif cell.number is not None and cell.number not in new_candidates:
                # Existing number removed from candidates -> Contradiction
                cell.number = None
                cell.candidates = set()

            return True

        return False

    def _eval_conclusion_term(self, term: ConclusionTerm, witness: dict[str, Any]) -> Any:
        if isinstance(term, ConclusionVariable):
            return witness[term.name]
        elif isinstance(term, ConclusionConstant):
            return term.value
        elif isinstance(term, Calculation):
            left = self._eval_conclusion_term(term.left, witness)
            right = self._eval_conclusion_term(term.right, witness)
            if isinstance(left, int) and isinstance(right, int):
                if term.operator == "+":
                    return left + right
                if term.operator == "-":
                    return left - right
            return "nil"
        raise AssertionError(f"Unknown conclusion term type: {type(term)}")

    def _create_universe(self, puzzle: Puzzle) -> Universe:
        """
        Creates a Universe for rule evaluation.

        Type guarantees from rule type checking:
        - POSITION variables resolve to (r, c) tuples or "OOB" (never "nil")
        - NUMBER variables resolve to int or "nil" (never "OOB")
        - Variables in conclusions are guaranteed to exist in the witness
        """
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

        # Helper for geometry
        def get_next(p_tuple: Union[Tuple[int, int], str]) -> Any:
            if p_tuple == "OOB":
                return "OOB"
            r, c = p_tuple
            cell = puzzle.grid[r][c]
            dr, dc = cell.direction.delta
            nr, nc = r + dr, c + dc

            if 0 <= nr < rows and 0 <= nc < cols:
                return (nr, nc)
            return "OOB"

        def get_path(p_tuple: Union[Tuple[int, int], str]) -> List[Tuple[int, int]]:
            path = []
            curr = get_next(p_tuple)
            visited = {p_tuple} if isinstance(p_tuple, tuple) else set()

            while curr != "OOB" and curr not in visited:
                path.append(curr)
                visited.add(curr)
                curr = get_next(curr)
            return path

        # Functions
        def func_next(args: Tuple[Any, ...]) -> Any:
            return get_next(args[0])

        def func_val(args: Tuple[Any, ...]) -> Any:
            p = args[0]
            if p == "OOB":
                return "nil"
            r, c = p
            cell = puzzle.grid[r][c]
            return cell.number if cell.number is not None else "nil"

        def func_ahead(args: Tuple[Any, ...]) -> Any:
            p = args[0]
            if p == "OOB":
                return 0
            return len(get_path(p))

        def func_dir(args: Tuple[Any, ...]) -> Any:
            p = args[0]
            if p == "OOB":
                return "nil"
            r, c = p
            return puzzle.grid[r][c].direction

        functions: dict[str, Callable[[Tuple[Any, ...]], Any]] = {
            "next": func_next,
            "val": func_val,
            "ahead": func_ahead,
            "dir": func_dir,
        }

        # Relations
        def rel_points_at(args: Tuple[Any, ...]) -> bool:
            p, q = args[0], args[1]
            if p == "OOB" or q == "OOB":
                return False
            path = get_path(p)
            return q in path

        def safe_compare(args: Tuple[Any, ...], op: str) -> bool:
            a, b = args[0], args[1]
            if a == "nil" or b == "nil":
                return False
            a_int: int = a
            b_int: int = b
            if op == "<":
                return a_int < b_int
            if op == ">":
                return a_int > b_int
            if op == "<=":
                return a_int <= b_int
            if op == ">=":
                return a_int >= b_int
            return False

        relations: dict[str, Callable[[Tuple[Any, ...]], bool]] = {
            "points_at": rel_points_at,
            "<": lambda args: safe_compare(args, "<"),
            ">": lambda args: safe_compare(args, ">"),
            "<=": lambda args: safe_compare(args, "<="),
            ">=": lambda args: safe_compare(args, ">="),
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

    def _has_contradiction(self, puzzle: Puzzle) -> bool:
        for row in puzzle.grid:
            for cell in row:
                if cell.number is None and (cell.candidates is not None and len(cell.candidates) == 0):
                    return True
        return False
