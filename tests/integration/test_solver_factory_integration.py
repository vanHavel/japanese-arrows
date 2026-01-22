"""Integration tests for the solver factory with default configuration."""

from japanese_arrows.solver import create_solver


def test_create_solver_with_default_config() -> None:
    """Test that solver loads rules from default config/rules.yaml."""
    # Create solver with default settings (all rules from config/rules.yaml)
    solver = create_solver()
    assert len(solver.rules) >= 1
