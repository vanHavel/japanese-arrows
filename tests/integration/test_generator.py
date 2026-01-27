import pytest

from japanese_arrows.generator.constraints import Constraint, NumberFraction, RuleComplexityFraction
from japanese_arrows.generator.generator import Generator
from japanese_arrows.models import Puzzle
from japanese_arrows.solver import SolverStatus, create_solver

pytestmark = pytest.mark.integration


def test_generator_simple() -> None:
    gen = Generator()
    constraints: list[Constraint] = []
    # Use small grid 3x3
    puzzle, stats = gen.generate(3, 3, False, 3, constraints)

    if puzzle is None:
        print(f"Stats: {stats}")
    assert isinstance(puzzle, Puzzle)
    assert stats.puzzles_successfully_generated == 1
    assert stats.puzzles_rejected_constraints >= 0
    assert stats.puzzles_rejected_no_solution >= 0
    assert puzzle.rows == 3
    assert puzzle.cols == 3

    # Verify valid puzzle by solving it again
    solver = create_solver(max_complexity=3)
    res = solver.solve(puzzle)

    assert res.status == SolverStatus.SOLVED


def test_generator_constraints() -> None:
    # Test that we can generate with constraints
    gen = Generator()
    # Require at least some rule applications of complexity 1
    constraints: list[Constraint] = [RuleComplexityFraction(complexity=1, min_fraction=0.01)]

    # 4x4 with diagonals allowed
    puzzle, stats = gen.generate(4, 4, True, 3, constraints, max_attempts=200)

    if puzzle is None:
        print(f"Stats: {stats}")
    assert isinstance(puzzle, Puzzle)
    assert stats.puzzles_rejected_constraints >= 0
    assert stats.puzzles_rejected_no_solution >= 0
    assert stats.puzzles_successfully_generated == 1

    # Verify it solves
    solver = create_solver(max_complexity=3)
    res = solver.solve(puzzle)
    assert res.status == SolverStatus.SOLVED


def test_generate_many() -> None:
    gen = Generator()
    constraints: list[Constraint] = []

    puzzles, stats = gen.generate_many(3, 3, 3, False, 3, constraints)

    assert len(puzzles) == 3
    assert stats.puzzles_successfully_generated >= 3
    for p in puzzles:
        assert isinstance(p, Puzzle)
        assert p.rows == 3
        assert p.cols == 3


def test_generator_max_attempts() -> None:
    gen = Generator()
    # Use a constraint that is impossible to meet

    constraints: list[Constraint] = [NumberFraction(number=99, min_fraction=0.1)]

    puzzle, stats = gen.generate(3, 3, False, 3, constraints, max_attempts=5)
    assert puzzle is None
