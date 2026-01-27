from typing import Any, Callable, cast

from japanese_arrows.models import Cell, Puzzle
from japanese_arrows.rules import Conclusion, ExcludeVal, OnlyVal, SetVal
from japanese_arrows.solver.definitions import ConclusionApplicationResult
from japanese_arrows.universe import Universe


def calculate_new_candidates(
    puzzle: Puzzle,
    conclusion: Conclusion,
    witness: dict[str, Any],
    universe: Universe,
) -> tuple[set[int] | None, tuple[int, int] | None, Cell | None, set[int] | None]:
    """
    Calculates the new candidate set for a cell based on a conclusion.
    Returns:
        - (new_candidates, (r,c), cell, current_candidates) if successful/possible progress.
        - (None, (r, c), cell, None) if contradiction found (invalid type or empty result set).
        - (None, None, None, None) if no progress can be made (OOB, empty candidates).
    """
    p_val = universe.eval_term(conclusion.position, witness)
    if p_val == "OOB":
        return None, None, None, None

    r, c = p_val
    cell = puzzle.grid[r][c]

    # Optimization: Check effectively empty candidates early
    if cell.number is not None and cell.candidates is not None and not cell.candidates:
        return None, None, None, None

    current_candidates = cell.candidates
    if cell.number is not None:
        current_candidates = {cell.number}
    elif current_candidates is None:
        return None, None, None, None
    new_candidates = current_candidates.copy()

    conclusion_type = type(conclusion)

    if conclusion_type is ExcludeVal:
        exc_conclusion = cast(ExcludeVal, conclusion)
        val = universe.eval_term(exc_conclusion.value, witness)
        if isinstance(val, int):
            if exc_conclusion.operator == "=":
                new_candidates.discard(val)
            elif exc_conclusion.operator == ">":
                new_candidates = {c for c in new_candidates if not (c > val)}
            elif exc_conclusion.operator == "<":
                new_candidates = {c for c in new_candidates if not (c < val)}
            elif exc_conclusion.operator == ">=":
                new_candidates = {c for c in new_candidates if not (c >= val)}
            elif exc_conclusion.operator == "<=":
                new_candidates = {c for c in new_candidates if not (c <= val)}
            elif exc_conclusion.operator == "!=":
                new_candidates = {c for c in new_candidates if not (c != val)}

    elif conclusion_type is SetVal:
        set_conclusion = cast(SetVal, conclusion)
        val = universe.eval_term(set_conclusion.value, witness)
        if not isinstance(val, int):
            return None, (r, c), cell, None
        new_candidates.intersection_update({val})

    elif conclusion_type is OnlyVal:
        only_conclusion = cast(OnlyVal, conclusion)
        allowed = set()
        for v_term in only_conclusion.values:
            v = universe.eval_term(v_term, witness)
            if isinstance(v, int):
                allowed.add(v)
        new_candidates.intersection_update(allowed)

    if not new_candidates:
        return None, (r, c), cell, None

    return new_candidates, (r, c), cell, current_candidates


def apply_conclusion(
    puzzle: Puzzle,
    conclusion: Conclusion,
    witness: dict[str, Any],
    universe: Universe,
) -> tuple[ConclusionApplicationResult, tuple[int, int] | None]:
    new_candidates, loc, cell, current_candidates = calculate_new_candidates(puzzle, conclusion, witness, universe)

    if loc is None:
        return ConclusionApplicationResult.NO_PROGRESS, None

    if new_candidates is None:  # Contradiction found in calc
        # cell is guaranteed to be not None if loc is not None
        # We rely on type checker or assertion if needed, but logic ensures it.
        cell.candidates = set()  # type: ignore
        cell.number = None  # type: ignore
        return ConclusionApplicationResult.CONTRADICTION, loc

    # We have new_candidates and current_candidates
    if new_candidates != current_candidates:
        cell.candidates = new_candidates  # type: ignore
        if len(new_candidates) == 1:
            cell.number = next(iter(new_candidates))  # type: ignore
        return ConclusionApplicationResult.PROGRESS, None

    return ConclusionApplicationResult.NO_PROGRESS, None


def apply_conclusion_with_undo(
    puzzle: Puzzle,
    conclusion: Conclusion,
    witness: dict[str, Any],
    universe: Universe,
) -> Callable[[], None] | str | None:
    new_candidates, loc, cell, current_candidates = calculate_new_candidates(puzzle, conclusion, witness, universe)

    if loc is None:
        return None

    if new_candidates is None:
        return "CONTRADICTION"

    if new_candidates != current_candidates:
        old_candidates_obj = cell.candidates  # type: ignore
        old_number_obj = cell.number  # type: ignore

        cell.candidates = new_candidates  # type: ignore
        if len(new_candidates) == 1:
            cell.number = next(iter(new_candidates))  # type: ignore

        def undo() -> None:
            cell.candidates = old_candidates_obj  # type: ignore
            cell.number = old_number_obj  # type: ignore

        return undo

    return None
