from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class Direction(str, Enum):
    NORTH = "↑"
    NORTH_EAST = "↗"
    EAST = "→"
    SOUTH_EAST = "↘"
    SOUTH = "↓"
    SOUTH_WEST = "↙"
    WEST = "←"
    NORTH_WEST = "↖"


@dataclass
class Cell:
    direction: Direction
    number: Optional[int] = None

    def __str__(self) -> str:
        num_str = str(self.number) if self.number is not None else "."
        return f"{self.direction.value}{num_str}"

    @classmethod
    def from_string(cls, text: str) -> "Cell":
        if len(text) != 2:
            raise ValueError(f"Invalid cell string: '{text}'")
        direction = Direction(text[0])
        number_char = text[1]
        number = int(number_char) if number_char != "." else None
        return cls(direction=direction, number=number)


@dataclass
class Puzzle:
    rows: int
    cols: int
    grid: List[List[Cell]]

    def __post_init__(self) -> None:
        if len(self.grid) != self.rows:
            raise ValueError(f"Grid has {len(self.grid)} rows, expected {self.rows}")
        for i, row in enumerate(self.grid):
            if len(row) != self.cols:
                raise ValueError(f"Row {i} has {len(row)} cols, expected {self.cols}")

    def to_string(self) -> str:
        res = []
        border = "+" + "+".join(["----"] * self.cols) + "+"
        res.append(border)
        for row in self.grid:
            row_str = "|"
            for cell in row:
                row_str += f" {cell} |"
            res.append(row_str)
            res.append(border)
        return "\n".join(res) + "\n"

    @classmethod
    def from_string(cls, text: str) -> "Puzzle":
        lines = text.strip().splitlines()
        # Filter out border lines (those starting with +)
        content_lines = [line for line in lines if not line.startswith("+")]

        grid = []
        for line in content_lines:
            # line looks like "| ↑. | ←1 |"
            # split by | gives ['', ' ↑. ', ' ←1 ', ''] based on spaces padding
            parts = line.strip("|").split("|")
            row_cells = []
            for part in parts:
                cell_str = part.strip()
                row_cells.append(Cell.from_string(cell_str))
            grid.append(row_cells)

        rows = len(grid)
        cols = len(grid[0]) if grid else 0
        return cls(rows=rows, cols=cols, grid=grid)
