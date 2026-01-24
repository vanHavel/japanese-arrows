from unittest.mock import MagicMock

from japanese_arrows.generator.constraints import NumberFraction, RuleApplicationsOfMaxComplexity, UsesRule


def test_rule_applications_of_max_complexity_min() -> None:
    constraint = RuleApplicationsOfMaxComplexity(min_fraction=0.4)

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
    trace.max_complexity_used = 2
    # 2/5 = 0.4, should pass
    assert constraint.check(trace) is True

    # Case 3: Exceed constraint
    trace.steps = [step1, step2, step1, step3, step4]  # 3/5 = 0.6
    assert constraint.check(trace) is True

    # Case 4: Below constraint
    trace.steps = [step1, step3, step4, step5]  # 1/4 = 0.25
    assert constraint.check(trace) is False


def test_rule_applications_of_max_complexity_max() -> None:
    constraint = RuleApplicationsOfMaxComplexity(max_fraction=0.5)

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
    trace.max_complexity_used = 2
    # 1/2 = 0.5, should pass
    assert constraint.check(trace) is True

    # Case 3: Below constraint
    trace.steps = [step1, step2, step2]  # 1/3 = 0.33
    assert constraint.check(trace) is True

    # Case 4: Above constraint
    trace.steps = [step1, step1, step2]  # 2/3 = 0.66
    assert constraint.check(trace) is False


def test_rule_applications_of_max_complexity_range() -> None:
    constraint = RuleApplicationsOfMaxComplexity(min_fraction=0.2, max_fraction=0.5)

    step1 = MagicMock()
    step1.rule_complexity = 2
    step2 = MagicMock()
    step2.rule_complexity = 1

    trace = MagicMock()
    trace.max_complexity_used = 2

    # 1/4 = 0.25 (in range)
    trace.steps = [step1, step2, step2, step2]
    assert constraint.check(trace) is True

    # 1/10 = 0.1 (below range)
    trace.steps = [step1] + [step2] * 9
    assert constraint.check(trace) is False

    # 3/4 = 0.75 (above range)
    trace.steps = [step1, step1, step1, step2]
    assert constraint.check(trace) is False


def test_constraints_with_different_max_complexity() -> None:
    # If the puzzle was solved with max complexity 1
    constraint = RuleApplicationsOfMaxComplexity(min_fraction=1.0)

    step1 = MagicMock()
    step1.rule_complexity = 1

    trace = MagicMock()
    trace.steps = [step1]
    trace.max_complexity_used = 1

    assert constraint.check(trace) is True


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
