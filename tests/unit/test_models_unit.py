# Copyright (C) 2026 Lukas Huwald
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from japanese_arrows.models import Cell, Direction, Puzzle


def test_puzzle_init() -> None:
    c1 = Cell(direction=Direction.NORTH)
    c2 = Cell(direction=Direction.SOUTH)
    grid = [[c1, c2]]
    p = Puzzle(rows=1, cols=2, grid=grid)

    assert p.rows == 1
    assert p.cols == 2
    assert len(p.grid) == 1
    assert len(p.grid[0]) == 2
    assert p.grid[0][0] == c1
    assert p.grid[0][1] == c2


def test_cell_string() -> None:
    c = Cell(direction=Direction.NORTH, number=1)
    assert str(c) == "↑1"

    c_empty = Cell(direction=Direction.WEST, number=None)
    assert str(c_empty) == "←."

    assert Cell.from_string("↑1") == c
    assert Cell.from_string("←.") == c_empty


def test_puzzle_string() -> None:
    c1 = Cell(direction=Direction.NORTH)
    c2 = Cell(direction=Direction.EAST, number=1)
    grid = [[c1, c2]]
    p = Puzzle(rows=1, cols=2, grid=grid)

    expected_str = """+----+----+
| ↑. | →1 |
+----+----+
"""
    assert p.to_string() == expected_str
    assert Puzzle.from_string(expected_str) == p
