from japanese_arrows.models import Cell, Direction, Puzzle
from japanese_arrows.rules import (
    ConclusionConstant,
    ConclusionVariable,
    ConditionConstant,
    ConditionVariable,
    Equality,
    ExcludeVal,
    ExistsPosition,
    FunctionCall,
    Rule,
    SetVal,
)
from japanese_arrows.solver import Solver, SolverResult


def create_simple_puzzle() -> Puzzle:
    # 2x2 grid
    # ↓ .
    # → .
    grid = [
        [Cell(Direction.SOUTH, None), Cell(Direction.SOUTH, None)],
        [Cell(Direction.EAST, None), Cell(Direction.EAST, None)],
    ]
    return Puzzle(rows=2, cols=2, grid=grid)


def test_initialization() -> None:
    puzzle = create_simple_puzzle()
    solver = Solver([])
    solver._initialize_candidates(puzzle)

    for r in range(2):
        for c in range(2):
            # Max dimension 2, range(2) -> {0, 1}
            assert puzzle.grid[r][c].candidates == {0, 1}


def test_create_universe_geometry() -> None:
    # 3x1 grid: → → .
    # (0,0) -> (0,1) -> (0,2) -> OOB
    grid = [[Cell(Direction.EAST, None), Cell(Direction.EAST, None), Cell(Direction.EAST, None)]]
    puzzle = Puzzle(rows=1, cols=3, grid=grid)
    solver = Solver([])
    solver._initialize_candidates(puzzle)  # Needed? Not for just creating universe for test, but good practice

    universe = solver._create_universe(puzzle)

    # Test next
    # next((0,0)) should be (0,1)
    func_next = universe.functions["next"]
    assert func_next(((0, 0),)) == (0, 1)
    assert func_next(((0, 1),)) == (0, 2)
    assert func_next(((0, 2),)) == "OOB"

    # Test points_at
    rel_points_at = universe.relations["points_at"]
    assert rel_points_at(((0, 0), (0, 1)))
    assert rel_points_at(((0, 0), (0, 2)))  # Transitive
    assert not rel_points_at(((0, 1), (0, 0)))  # Not backwards

    # Test ahead
    func_ahead = universe.functions["ahead"]
    assert func_ahead(((0, 0),)) == 2  # (0,1), (0,2)
    assert func_ahead(((0, 1),)) == 1  # (0,2)
    assert func_ahead(((0, 2),)) == 0


def test_apply_simple_rule() -> None:
    # Rule: exists p (val(p) = nil) => set(p, 1)
    # Applying this to a puzzle with empty cells should set candidates to {1} (and number to 1)

    p_var = ConditionVariable("p")
    # Condition: exists p (val(p) = nil)
    # Note: val(p) returns "nil" (string) if number is None.
    # Equality check: val(p) == "nil"
    # But wait, ConditionConstant("nil") evaluates to "nil" via Universe lookup if "nil" is in constants?
    # Yes, Solver adds "nil" to constants.

    cond = ExistsPosition([p_var], Equality(FunctionCall("val", [p_var]), ConditionConstant("nil")))

    # Conclusion: set(p, 1)
    concl = SetVal(ConclusionVariable("p"), ConclusionConstant(1))

    rule = Rule(name="fill_one", condition=cond, conclusions=[concl])

    puzzle = create_simple_puzzle()
    solver = Solver([rule])
    solver._initialize_candidates(puzzle)

    # Apply rule
    progress = solver._apply_rules(puzzle)
    assert progress

    # Check if a cell was set to 1.
    # Since the rule finds *a* witness, at least one cell should be 1.
    # Depending on implementation (product iterator order), it might be (0,0).
    found_one = False
    for r in range(2):
        for c in range(2):
            if puzzle.grid[r][c].number == 1:
                found_one = True
    assert found_one


def test_solve_already_solved() -> None:
    # Valid puzzle: 1x2. (0,0) -> (0,1) -> OOB.
    # (0,1) points OOB, so val 0.
    # (0,0) points at (0,1) [0], so val 1.
    grid = [[Cell(Direction.EAST, 1), Cell(Direction.EAST, 0)]]
    puzzle = Puzzle(rows=1, cols=2, grid=grid)
    solver = Solver([])
    result, final_puzzle = solver.solve(puzzle)

    assert result == SolverResult.SOLVED


def test_contradiction() -> None:
    # Puzzle with pre-filled invalid state (no such state in Puzzle object unless we cheat or rule causes it)
    # Let's make a rule that requires set(p, 0) and set(p, 1)
    # Actually simpler: Rule says set(p, 0). Puzzle has p=1 initially.

    grid = [[Cell(Direction.SOUTH, 1)]]
    puzzle = Puzzle(rows=1, cols=1, grid=grid)

    # Rule: exists p (val(p) = 1) => set(p, 0)
    p_var = ConditionVariable("p")
    cond = ExistsPosition([p_var], Equality(FunctionCall("val", [p_var]), ConditionConstant(1)))
    concl = SetVal(ConclusionVariable("p"), ConclusionConstant(0))
    rule = Rule("contradict", cond, [concl])

    solver = Solver([rule])
    result, final_puzzle = solver.solve(puzzle)

    assert result == SolverResult.NO_SOLUTION


def test_contradiction_prefilled_removal() -> None:
    # Test verifying that removing the only candidate from a pre-filled cell results in NO_SOLUTION.
    # Puzzle with 1x1 grid, value 0.
    grid = [[Cell(Direction.SOUTH, 0)]]
    puzzle = Puzzle(rows=1, cols=1, grid=grid)

    # Rule: exists p (val(p) = 0) => exclude(p, =, 0)
    p_var = ConditionVariable("p")
    cond = ExistsPosition([p_var], Equality(FunctionCall("val", [p_var]), ConditionConstant(0)))

    # Conclusion: exclude(p, =, 0)
    concl = ExcludeVal(ConclusionVariable("p"), "=", ConclusionConstant(0))

    rule = Rule("exclude_zero", cond, [concl])

    solver = Solver([rule])
    result, final_puzzle = solver.solve(puzzle)

    assert result == SolverResult.NO_SOLUTION
