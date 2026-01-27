from enum import Enum
from typing import Any, Callable, Set, Tuple

from japanese_arrows.models import Direction, Puzzle
from japanese_arrows.type_checking import Type
from japanese_arrows.universe import Universe


class ConclusionApplicationResult(Enum):
    NO_PROGRESS = "NO_PROGRESS"
    PROGRESS = "PROGRESS"
    CONTRADICTION = "CONTRADICTION"


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


def create_universe(
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


# Type definitions
TYPE_CONSTANTS = {"OOB": Type.POSITION, "nil": Type.NUMBER}
TYPE_FUNCTIONS = {
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
TYPE_RELATIONS = {
    "points_at": [Type.POSITION, Type.POSITION],
    "candidate": [Type.POSITION, Type.NUMBER],
    "sees_value": [Type.POSITION, Type.NUMBER],
    "<": [Type.NUMBER, Type.NUMBER],
    ">": [Type.NUMBER, Type.NUMBER],
    "<=": [Type.NUMBER, Type.NUMBER],
    ">=": [Type.NUMBER, Type.NUMBER],
}
