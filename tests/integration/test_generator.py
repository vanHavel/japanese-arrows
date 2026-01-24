from japanese_arrows.generator.constraints import Constraint, MinRuleApplicationsOfMaxComplexity
from japanese_arrows.generator.generator import Generator
from japanese_arrows.models import Puzzle
from japanese_arrows.solver import SolverStatus, create_solver


def test_generator_simple() -> None:
    gen = Generator()
    constraints: list[Constraint] = []
    # Use small grid 3x3
    puzzle, stats = gen.generate(3, 3, False, 1, constraints)

    assert isinstance(puzzle, Puzzle)
    assert stats.total_puzzles_created >= 1
    assert stats.puzzles_rejected_constraints >= 0
    assert puzzle.rows == 3
    assert puzzle.cols == 3

    # Verify valid puzzle by solving it again
    solver = create_solver(max_complexity=1)
    res = solver.solve(puzzle)

    assert res.status == SolverStatus.SOLVED


def test_generator_constraints() -> None:
    # Test that we can generate with constraints
    gen = Generator()
    # Require at least some rule applications of max complexity (which is 1)
    constraints: list[Constraint] = [MinRuleApplicationsOfMaxComplexity(0.01)]

    # 4x4 with diagonals allowed
    puzzle, stats = gen.generate(4, 4, True, 1, constraints)

    assert isinstance(puzzle, Puzzle)
    assert stats.puzzles_rejected_constraints >= 0

    # Verify it solves
    solver = create_solver(max_complexity=1)
    res = solver.solve(puzzle)
    assert res.status == SolverStatus.SOLVED


def test_generate_many() -> None:
    gen = Generator()
    puzzles, stats = gen.generate_many(3, 3, 3, False, 1, [])

    assert len(puzzles) == 3
    assert stats.total_puzzles_created >= 3
    for p in puzzles:
        assert isinstance(p, Puzzle)
        assert p.rows == 3
        assert p.cols == 3
