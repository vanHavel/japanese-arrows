# Copyright (C) 2026 Lukas Huwald
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from pathlib import Path

from japanese_arrows.solver import create_solver

# Path to test-specific rules file
TEST_RULES_FILE = Path(__file__).parent.parent / "config" / "test_rules.yaml"


def test_create_solver_with_complexity_filter() -> None:
    """Test creating a solver with specific complexity level."""
    solver = create_solver(max_complexity=1, rules_file=TEST_RULES_FILE)
    assert len(solver.rules) == 1
    assert solver.rules[0].name == "ARROW-POINTS-OOB"
    assert solver.rules[0].complexity == 1


def test_create_solver_custom_file() -> None:
    """Test creating a solver with a custom rules file."""
    solver = create_solver(max_complexity=1, rules_file=TEST_RULES_FILE)
    assert len(solver.rules) == 1
    assert solver.rules[0].name == "ARROW-POINTS-OOB"


def test_create_solver_filters_by_complexity() -> None:
    """Test that solver filters rules by complexity."""
    # With max_complexity=0, no rules should be loaded
    solver = create_solver(max_complexity=0, rules_file=TEST_RULES_FILE)
    assert len(solver.rules) == 0

    # With max_complexity=1, only complexity 1 rules should be loaded
    solver = create_solver(max_complexity=1, rules_file=TEST_RULES_FILE)
    assert len(solver.rules) == 1
    assert all(rule.complexity <= 1 for rule in solver.rules)

    # With max_complexity=2, both rules should be loaded
    solver = create_solver(max_complexity=2, rules_file=TEST_RULES_FILE)
    assert len(solver.rules) == 2
    assert all(rule.complexity <= 2 for rule in solver.rules)


def test_create_solver_default_loads_all_rules() -> None:
    """Test that default behavior (max_complexity=None) loads all rules."""
    # With max_complexity=None (default), all rules should be loaded
    solver = create_solver(rules_file=TEST_RULES_FILE)
    assert len(solver.rules) == 2  # Both test rules should be loaded

    rule_names = {rule.name for rule in solver.rules}
    assert "ARROW-POINTS-OOB" in rule_names
    assert "TEST-RULE-COMPLEXITY-2" in rule_names
