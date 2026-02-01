# Copyright (C) 2026 Lukas Huwald
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from japanese_arrows.models import Cell, Direction, Puzzle
from japanese_arrows.rules import (
    BacktrackRule,
    Constant,
    Equality,
    ExcludeVal,
    ExistsPosition,
    FORule,
    FunctionCall,
    Variable,
)
from japanese_arrows.solver import Solver, SolverStatus


def test_backtrack_rule_application() -> None:
    # 1x2 puzzle, Cell A -> Cell B.
    # Cell A has candidates {0, 1}.
    # Cell B is fixed 0.
    # Rule 1 (FO): "suicide rule" -> if value is 1, exclude 1.
    #   exists p (val(p)=1) => exclude(p, =, 1)
    #   When A=1 tentatively, this rule applies, leaving A={} -> Contradiction.
    # Backtrack rule: depth 1, mock apply rule 1.

    # Grid: Cell A (SOUTH, None), Cell B (EAST, 0)
    grid = [[Cell(Direction.SOUTH, None), Cell(Direction.EAST, 0)]]
    puzzle = Puzzle(rows=1, cols=2, grid=grid)

    # Rule 1: Suicide rule
    # condition: exists p (val(p)=1)
    p_var = Variable("p")
    cond = ExistsPosition([p_var], Equality(FunctionCall("val", [p_var]), Constant(1)))
    # conclusion: exclude(p, =, 1)
    concl = ExcludeVal(Variable("p"), "=", Constant(1))

    fo_rules = [FORule(name="suicide_if_one", condition=cond, conclusions=[concl], complexity=1)]

    # Backtrack Rule
    bt_rule = BacktrackRule(
        name="backtrack_check", complexity=2, backtrack_depth=1, rule_depth=1, max_rule_complexity=1
    )

    solver = Solver(fo_rules + [bt_rule])
    solver._initialize_candidates(puzzle)
    # Initially A candidates: {0, 1}. B candidates: {0} (or fixed 0).

    # A=1 -> apply suicide rule -> A!=1 -> A={} -> Contradiction.
    # Thus, backtracking should eliminate 1 from A.
    # A should become 0.

    result = solver.solve(puzzle)

    assert result.status == SolverStatus.SOLVED
    assert result.puzzle.grid[0][0].number == 0

    # Verify we used the backtracking rule
    assert result.rule_application_count["backtrack_check"] > 0
    # Steps should show elimination of 1
    # Note: result.steps contains successful application of backtracking
    found_bt = False
    for step in result.steps:
        if step.rule_name == "backtrack_check":
            found_bt = True
            # Check conclusion
            assert len(step.conclusions_applied) == 1
            c = step.conclusions_applied[0]
            assert isinstance(c, ExcludeVal)
            assert isinstance(c.value, Constant)
            assert c.value.value == 1
    assert found_bt
