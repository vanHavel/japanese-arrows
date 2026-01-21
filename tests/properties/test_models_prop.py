from typing import Any

from hypothesis import given
from hypothesis import strategies as st

from japanese_arrows.models import Cell, Direction, Puzzle

# Strategy for Direction
direction_strategy = st.sampled_from(Direction)

# Strategy for Cell
cell_strategy = st.builds(
    Cell, direction=direction_strategy, number=st.one_of(st.none(), st.integers(min_value=0, max_value=9))
)


# Strategy for Puzzle


@st.composite
def puzzle_strategy(draw: Any) -> Puzzle:
    rows = draw(st.integers(min_value=1, max_value=10))
    cols = draw(st.integers(min_value=1, max_value=10))

    grid = []
    for _ in range(rows):
        row = [draw(cell_strategy) for _ in range(cols)]
        grid.append(row)

    return Puzzle(rows=rows, cols=cols, grid=grid)


@given(cell_strategy)
def test_cell_roundtrip(cell: Cell) -> None:
    assert Cell.from_string(str(cell)) == cell


@given(puzzle_strategy())
def test_puzzle_roundtrip(puzzle: Puzzle) -> None:
    assert Puzzle.from_string(puzzle.to_string()) == puzzle
