from unittest.mock import MagicMock

from japanese_arrows.generator.constraints import MaxRuleApplicationsOfMaxComplexity, MinRuleApplicationsOfMaxComplexity


def test_min_rule_applications_of_max_complexity() -> None:
    constraint = MinRuleApplicationsOfMaxComplexity(0.4)

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


def test_max_rule_applications_of_max_complexity() -> None:
    constraint = MaxRuleApplicationsOfMaxComplexity(0.5)

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


def test_constraints_with_different_max_complexity() -> None:
    # If the puzzle was solved with max complexity 1
    constraint = MinRuleApplicationsOfMaxComplexity(1.0)

    step1 = MagicMock()
    step1.rule_complexity = 1

    trace = MagicMock()
    trace.steps = [step1]
    trace.max_complexity_used = 1

    assert constraint.check(trace) is True
