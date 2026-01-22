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
from japanese_arrows.solver import Solver, SolverStatus


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
    result = solver.solve(puzzle)

    assert result.status == SolverStatus.SOLVED


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
    result = solver.solve(puzzle)

    assert result.status == SolverStatus.NO_SOLUTION


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
    result = solver.solve(puzzle)

    assert result.status == SolverStatus.NO_SOLUTION


def test_solver_result_steps_trace() -> None:
    """Test that solver result captures step trace correctly."""
    # 1x2 puzzle with empty cells
    grid = [[Cell(Direction.EAST, None), Cell(Direction.EAST, None)]]
    puzzle = Puzzle(rows=1, cols=2, grid=grid)

    # Rule that sets empty cells to 0
    p_var = ConditionVariable("p")
    cond = ExistsPosition([p_var], Equality(FunctionCall("val", [p_var]), ConditionConstant("nil")))
    concl = SetVal(ConclusionVariable("p"), ConclusionConstant(0))
    rule = Rule(name="fill_zero", condition=cond, conclusions=[concl], complexity=1)

    solver = Solver([rule])
    result = solver.solve(puzzle)

    # Should have applied the rule twice (once for each cell)
    assert len(result.steps) == 2
    for step in result.steps:
        assert step.rule_name == "fill_zero"
        assert "p" in step.witness
        assert len(step.conclusions_applied) == 1
        assert isinstance(step.conclusions_applied[0], SetVal)


def test_solver_result_max_complexity_used() -> None:
    """Test that max_complexity_used tracks the highest complexity rule that made progress."""
    grid = [[Cell(Direction.EAST, None), Cell(Direction.EAST, None)]]
    puzzle = Puzzle(rows=1, cols=2, grid=grid)

    p_var = ConditionVariable("p")

    # Low complexity rule: sets first empty cell to 0
    cond1 = ExistsPosition([p_var], Equality(FunctionCall("val", [p_var]), ConditionConstant("nil")))
    concl1 = SetVal(ConclusionVariable("p"), ConclusionConstant(0))
    rule1 = Rule(name="low_complexity", condition=cond1, conclusions=[concl1], complexity=1)

    # Higher complexity rule that will never match (no cell has value 99)
    cond2 = ExistsPosition([p_var], Equality(FunctionCall("val", [p_var]), ConditionConstant(99)))
    concl2 = SetVal(ConclusionVariable("p"), ConclusionConstant(1))
    rule2 = Rule(name="high_complexity", condition=cond2, conclusions=[concl2], complexity=5)

    solver = Solver([rule1, rule2])
    result = solver.solve(puzzle)

    # Only rule1 should have been used
    assert result.max_complexity_used == 1


def test_solver_result_rule_application_count() -> None:
    """Test that rule_application_count is a Counter tracking applications per rule."""
    # 1x3 puzzle
    grid = [[Cell(Direction.EAST, None), Cell(Direction.EAST, None), Cell(Direction.EAST, None)]]
    puzzle = Puzzle(rows=1, cols=3, grid=grid)

    p_var = ConditionVariable("p")
    cond = ExistsPosition([p_var], Equality(FunctionCall("val", [p_var]), ConditionConstant("nil")))
    concl = SetVal(ConclusionVariable("p"), ConclusionConstant(0))
    rule = Rule(name="fill_zero", condition=cond, conclusions=[concl], complexity=1)

    solver = Solver([rule])
    result = solver.solve(puzzle)

    # Rule should have been applied 3 times (once per cell)
    assert result.rule_application_count["fill_zero"] == 3
    assert sum(result.rule_application_count.values()) == 3


def test_solver_result_multiple_rules_count() -> None:
    """Test rule_application_count with multiple rules."""
    # 1x2 puzzle with one cell already 0
    grid = [[Cell(Direction.EAST, 0), Cell(Direction.EAST, None)]]
    puzzle = Puzzle(rows=1, cols=2, grid=grid)

    p_var = ConditionVariable("p")

    # Rule 1: fill empty cells with 0
    cond1 = ExistsPosition([p_var], Equality(FunctionCall("val", [p_var]), ConditionConstant("nil")))
    concl1 = SetVal(ConclusionVariable("p"), ConclusionConstant(0))
    rule1 = Rule(name="fill_nil", condition=cond1, conclusions=[concl1], complexity=1)

    # Rule 2: would exclude 0 from cells with 0 (causes contradiction, but tests counting)
    # Actually let's use a rule that simply doesn't match
    cond2 = ExistsPosition([p_var], Equality(FunctionCall("val", [p_var]), ConditionConstant(99)))
    concl2 = SetVal(ConclusionVariable("p"), ConclusionConstant(1))
    rule2 = Rule(name="never_matches", condition=cond2, conclusions=[concl2], complexity=3)

    solver = Solver([rule1, rule2])
    result = solver.solve(puzzle)

    # Only rule1 should be applied (once for the empty cell)
    assert result.rule_application_count["fill_nil"] == 1
    assert result.rule_application_count["never_matches"] == 0
    assert "never_matches" not in result.rule_application_count  # Counter returns 0 for missing keys


def test_solver_result_no_rules_applied() -> None:
    """Test solver result when no rules are applied (already solved puzzle)."""
    grid = [[Cell(Direction.EAST, 1), Cell(Direction.EAST, 0)]]
    puzzle = Puzzle(rows=1, cols=2, grid=grid)

    solver = Solver([])
    result = solver.solve(puzzle)

    assert result.status == SolverStatus.SOLVED
    assert result.max_complexity_used == 0
    assert len(result.steps) == 0
    assert sum(result.rule_application_count.values()) == 0
