import os
from typing import Any

from japanese_arrows.io import read_puzzle, write_puzzle
from japanese_arrows.models import Cell, Direction, Puzzle


def test_puzzle_io(tmp_path: Any) -> None:
    c1 = Cell(direction=Direction.NORTH, number=1)
    p = Puzzle(rows=1, cols=1, grid=[[c1]])

    file_path = tmp_path / "puzzle.txt"
    write_puzzle(p, str(file_path))

    assert os.path.exists(file_path)

    p2 = read_puzzle(str(file_path))
    assert p == p2


def test_write_puzzle_svg_simple(tmp_path: Any) -> None:
    grid = [[Cell(Direction.EAST, number=3), Cell(Direction.SOUTH, candidates={1, 2})]]
    puzzle = Puzzle(rows=1, cols=2, grid=grid)

    file_path = tmp_path / "test.svg"
    write_puzzle(puzzle, str(file_path))

    assert os.path.exists(file_path)
    content = file_path.read_text(encoding="utf-8")

    # Basic SVG structure
    assert '<svg xmlns="http://www.w3.org/2000/svg"' in content

    # Check rotations
    # East is 0 deg
    assert "rotate(0.0)" in content
    # South is 90 deg
    assert "rotate(90.0)" in content

    # Check content
    # Number 3 should be in a text tag
    assert ">3</text>" in content

    # Candidates 1 and 2
    assert ">1</text>" in content
    assert ">2</text>" in content

    # Check classes
    assert 'class="number"' in content
    assert 'class="candidate"' in content


def test_write_puzzle_svg_large_candidates(tmp_path: Any) -> None:
    grid = [[Cell(Direction.NORTH, candidates={10, 20})]]
    puzzle = Puzzle(rows=1, cols=1, grid=grid)

    file_path = tmp_path / "test_large.svg"
    write_puzzle(puzzle, str(file_path))

    content = file_path.read_text(encoding="utf-8")
    assert ">10,20</text>" in content
