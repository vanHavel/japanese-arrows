from unittest.mock import MagicMock

from japanese_arrows.generator.constraints import (
    FollowingArrowsFraction,
    NumberFraction,
    PrefilledCellsFraction,
    RuleComplexityFraction,
    UsesRule,
)


def test_rule_complexity_fraction_min() -> None:
    constraint = RuleComplexityFraction(complexity=2, min_fraction=0.4)

    # Case 1: No steps
    trace = MagicMock()
    trace.steps = []
    assert constraint.check(trace) is False

    # Case 2: Meet constraint exactly
    step1 = MagicMock()
    step1.rule_complexity = 2
    step2 = MagicMock()
    step2.rule_complexity = 2
    step3 = MagicMock()
    step3.rule_complexity = 1
    step4 = MagicMock()
    step4.rule_complexity = 1
    step5 = MagicMock()
    step5.rule_complexity = 1

    trace.steps = [step1, step2, step3, step4, step5]
    # 2/5 = 0.4 complexity 2 rules, should pass
    assert constraint.check(trace) is True

    # Case 3: Exceed constraint
    trace.steps = [step1, step2, step1, step3, step4]  # 3/5 = 0.6 complexity 2
    assert constraint.check(trace) is True

    # Case 4: Below constraint
    trace.steps = [step1, step3, step4, step5]  # 1/4 = 0.25 complexity 2
    assert constraint.check(trace) is False


def test_rule_complexity_fraction_max() -> None:
    constraint = RuleComplexityFraction(complexity=2, max_fraction=0.5)

    # Case 1: No steps (default True for Max)
    trace = MagicMock()
    trace.steps = []
    assert constraint.check(trace) is True

    # Case 2: Meet constraint exactly
    step1 = MagicMock()
    step1.rule_complexity = 2
    step2 = MagicMock()
    step2.rule_complexity = 1

    trace.steps = [step1, step2]
    # 1/2 = 0.5 rules are complexity 2, should pass
    assert constraint.check(trace) is True

    # Case 3: Below constraint
    trace.steps = [step1, step2, step2]  # 1/3 = 0.33 are complexity 2
    assert constraint.check(trace) is True

    # Case 4: Above constraint
    trace.steps = [step1, step1, step2]  # 2/3 = 0.66 are complexity 2
    assert constraint.check(trace) is False


def test_rule_complexity_fraction_range() -> None:
    constraint = RuleComplexityFraction(complexity=2, min_fraction=0.2, max_fraction=0.5)

    step1 = MagicMock()
    step1.rule_complexity = 2
    step2 = MagicMock()
    step2.rule_complexity = 1

    trace = MagicMock()

    # 1/4 = 0.25 (in range)
    trace.steps = [step1, step2, step2, step2]
    assert constraint.check(trace) is True

    # 1/10 = 0.1 (below range)
    trace.steps = [step1] + [step2] * 9
    assert constraint.check(trace) is False

    # 3/4 = 0.75 (above range)
    trace.steps = [step1, step1, step1, step2]
    assert constraint.check(trace) is False


def test_rule_complexity_fraction_counts() -> None:
    # Test min_count
    constraint_min = RuleComplexityFraction(complexity=2, min_count=2)

    step1 = MagicMock()
    step1.rule_complexity = 2
    step2 = MagicMock()
    step2.rule_complexity = 1

    trace = MagicMock()

    # 1 rule of complexity 2 -> False
    trace.steps = [step1, step2]
    assert constraint_min.check(trace) is False

    # 2 rules of complexity 2 -> True
    trace.steps = [step1, step1, step2]
    assert constraint_min.check(trace) is True

    # Test max_count
    constraint_max = RuleComplexityFraction(complexity=2, max_count=2)

    # 2 rules of complexity 2 -> True
    trace.steps = [step1, step1, step2]
    assert constraint_max.check(trace) is True

    # 3 rules of complexity 2 -> False
    trace.steps = [step1, step1, step1, step2]
    assert constraint_max.check(trace) is False


def test_number_fraction() -> None:
    # 5x5 grid = 25 cells
    from japanese_arrows.models import Cell, Direction, Puzzle

    grid = [[Cell(Direction.NORTH, number=1) for _ in range(5)] for _ in range(5)]
    puzzle = Puzzle(5, 5, grid)

    trace = MagicMock()
    trace.puzzle = puzzle

    # number 1 is in 25/25 = 1.0 of cells
    constraint = NumberFraction(number=1, min_fraction=0.5, max_fraction=1.0)
    assert constraint.check(trace) is True

    constraint = NumberFraction(number=1, min_fraction=1.1)
    assert constraint.check(trace) is False

    # Change some numbers
    puzzle.grid[0][0].number = 2  # 24/25 = 0.96 are '1's
    constraint = NumberFraction(number=1, max_fraction=0.95)
    assert constraint.check(trace) is False

    constraint = NumberFraction(number=1, min_fraction=0.9)
    assert constraint.check(trace) is True

    # Test number that doesn't exist
    constraint = NumberFraction(number=3, max_fraction=0.0)
    assert constraint.check(trace) is True

    constraint = NumberFraction(number=3, min_fraction=0.01)
    assert constraint.check(trace) is False


def test_following_arrows_fraction() -> None:
    from japanese_arrows.models import Cell, Direction, Puzzle

    # 2x2 grid, (0,0) and (0,1) point EAST, (1,0) and (1,1) point WEST
    # (0,0) points at (0,1), both EAST -> count 1
    # (1,1) points at (1,0), both WEST -> count 1
    # Total count: 2
    # Fraction: 2/4 = 0.5
    grid = [
        [Cell(Direction.EAST), Cell(Direction.EAST)],
        [Cell(Direction.WEST), Cell(Direction.WEST)],
    ]
    puzzle = Puzzle(2, 2, grid)

    trace = MagicMock()
    trace.puzzle = puzzle

    constraint = FollowingArrowsFraction(min_fraction=0.4, max_fraction=0.6)
    assert constraint.check(trace) is True

    constraint_fail = FollowingArrowsFraction(min_fraction=0.6)
    assert constraint_fail.check(trace) is False

    # 2x2 grid, all point NORTH
    # (1,0) points at (0,0), both NORTH -> count 1
    # (1,1) points at (0,1), both NORTH -> count 1
    # Total count: 2
    # Fraction: 2/4 = 0.5
    grid2 = [
        [Cell(Direction.NORTH), Cell(Direction.NORTH)],
        [Cell(Direction.NORTH), Cell(Direction.NORTH)],
    ]
    puzzle2 = Puzzle(2, 2, grid2)
    trace2 = MagicMock()
    trace2.puzzle = puzzle2
    assert FollowingArrowsFraction(min_fraction=0.5).check(trace2) is True

    # 3x1 grid, all point SOUTH
    # (0,0) points at (1,0), both SOUTH -> count 1
    # (1,0) points at (2,0), both SOUTH -> count 1
    # Total count: 2
    # Fraction: 2/3 = 0.66
    grid3 = [[Cell(Direction.SOUTH)], [Cell(Direction.SOUTH)], [Cell(Direction.SOUTH)]]
    puzzle3 = Puzzle(3, 1, grid3)
    trace3 = MagicMock()
    trace3.puzzle = puzzle3
    assert FollowingArrowsFraction(min_fraction=0.6, max_fraction=0.7).check(trace3) is True


def test_uses_rule() -> None:
    step1 = MagicMock()
    step1.rule_name = "RULE_A"
    step2 = MagicMock()
    step2.rule_name = "RULE_B"
    step3 = MagicMock()
    step3.rule_name = "RULE_A"

    trace = MagicMock()
    trace.steps = [step1, step2, step3]

    # Rule A used twice
    constraint = UsesRule(rule_name="RULE_A", min_count=2)
    assert constraint.check(trace) is True

    constraint = UsesRule(rule_name="RULE_A", min_count=3)
    assert constraint.check(trace) is False

    # Rule A fraction = 2/3 = 0.66
    constraint = UsesRule(rule_name="RULE_A", min_fraction=0.6)
    assert constraint.check(trace) is True

    constraint = UsesRule(rule_name="RULE_A", min_fraction=0.7)
    assert constraint.check(trace) is False

    # Both count and fraction
    constraint = UsesRule(rule_name="RULE_A", min_count=2, min_fraction=0.6)
    assert constraint.check(trace) is True

    # Rule B used once
    constraint = UsesRule(rule_name="RULE_B", min_count=1)
    assert constraint.check(trace) is True

    constraint = UsesRule(rule_name="RULE_C", min_count=1)
    assert constraint.check(trace) is False


def test_prefilled_cells_fraction() -> None:
    from japanese_arrows.models import Cell, Direction, Puzzle

    # 2x2 grid
    # (0,0) has a number, others don't -> 1/4 = 0.25
    grid = [[Cell(Direction.NORTH) for _ in range(2)] for _ in range(2)]
    grid[0][0].number = 1
    puzzle = Puzzle(2, 2, grid)

    trace = MagicMock()
    trace.initial_puzzle = puzzle

    constraint = PrefilledCellsFraction(min_fraction=0.2, max_fraction=0.3)
    assert constraint.check(trace) is True

    constraint_fail = PrefilledCellsFraction(min_fraction=0.3)
    assert constraint_fail.check(trace) is False

    # 3/4 = 0.75
    grid[0][1].number = 2
    grid[1][0].number = 3
    puzzle2 = Puzzle(2, 2, grid)
    trace.initial_puzzle = puzzle2
    assert PrefilledCellsFraction(min_fraction=0.7, max_fraction=0.8).check(trace) is True
