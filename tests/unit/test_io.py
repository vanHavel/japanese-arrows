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
