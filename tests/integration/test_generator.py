from japanese_arrows.generator.constraints import Constraint, RuleComplexityFraction
from japanese_arrows.generator.generator import Generator
from japanese_arrows.models import Puzzle
from japanese_arrows.solver import SolverStatus, create_solver


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
    puzzles = []
    from japanese_arrows.generator.generator import GenerationStats

    stats = GenerationStats()

    for batch_puzzles, batch_stats in gen.generate_many(3, 3, 3, False, 3, []):
        puzzles.extend(batch_puzzles)
        stats.puzzles_successfully_generated += batch_stats.puzzles_successfully_generated
        stats.puzzles_rejected_constraints += batch_stats.puzzles_rejected_constraints
        stats.puzzles_rejected_no_solution += batch_stats.puzzles_rejected_no_solution
        stats.puzzles_rejected_excessive_guessing += batch_stats.puzzles_rejected_excessive_guessing

    assert len(puzzles) == 3
    assert stats.puzzles_successfully_generated == 3
    for p in puzzles:
        assert isinstance(p, Puzzle)
        assert p.rows == 3
        assert p.cols == 3


def test_generator_max_attempts() -> None:
    gen = Generator()
    # Use a constraint that is impossible to meet
    from japanese_arrows.generator.constraints import NumberFraction

    constraints: list[Constraint] = [NumberFraction(number=99, min_fraction=0.1)]

    puzzle, stats = gen.generate(3, 3, False, 3, constraints, max_attempts=5)
    assert puzzle is None


def test_generate_many_max_attempts() -> None:
    gen = Generator()
    # High count, low budget. Should return at most budget puzzles.
    puzzles = []
    from japanese_arrows.generator.generator import GenerationStats

    stats = GenerationStats()

    for batch_puzzles, batch_stats in gen.generate_many(10, 3, 3, False, 3, [], max_attempts=5):
        puzzles.extend(batch_puzzles)
        stats.puzzles_successfully_generated += batch_stats.puzzles_successfully_generated
        stats.puzzles_rejected_constraints += batch_stats.puzzles_rejected_constraints
        stats.puzzles_rejected_no_solution += batch_stats.puzzles_rejected_no_solution
        stats.puzzles_rejected_excessive_guessing += batch_stats.puzzles_rejected_excessive_guessing

    assert len(puzzles) <= 5
    assert (
        stats.puzzles_successfully_generated
        + stats.puzzles_rejected_constraints
        + stats.puzzles_rejected_no_solution
        + stats.puzzles_rejected_excessive_guessing
        == 5
    )


def test_generate_many_parallel() -> None:
    gen = Generator()
    # Test parallel generation of 4 puzzles
    puzzles = []
    from japanese_arrows.generator.generator import GenerationStats

    stats = GenerationStats()

    for batch_puzzles, batch_stats in gen.generate_many(4, 3, 3, False, 3, [], n_jobs=2):
        puzzles.extend(batch_puzzles)
        stats.puzzles_successfully_generated += batch_stats.puzzles_successfully_generated

    assert len(puzzles) == 4
    for p in puzzles:
        assert isinstance(p, Puzzle)
        assert p.rows == 3
        assert p.cols == 3
