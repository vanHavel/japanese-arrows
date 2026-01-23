from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Set, Tuple


class Direction(str, Enum):
    NORTH = "↑"
    NORTH_EAST = "↗"
    EAST = "→"
    SOUTH_EAST = "↘"
    SOUTH = "↓"
    SOUTH_WEST = "↙"
    WEST = "←"
    NORTH_WEST = "↖"

    @property
    def delta(self) -> Tuple[int, int]:
        mapping = {
            Direction.NORTH: (-1, 0),
            Direction.NORTH_EAST: (-1, 1),
            Direction.EAST: (0, 1),
            Direction.SOUTH_EAST: (1, 1),
            Direction.SOUTH: (1, 0),
            Direction.SOUTH_WEST: (1, -1),
            Direction.WEST: (0, -1),
            Direction.NORTH_WEST: (-1, -1),
        }
        return mapping[self]


@dataclass
class Cell:
    direction: Direction
    number: Optional[int] = None
    candidates: Optional[Set[int]] = None

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

    def validate(self) -> bool:
        """
        Validates if the puzzle solution is correct according to Japanese Arrows rules.
        Every cell's number must equal the count of distinct numbers it points at.
        Returns False if any cell is unfilled or incorrect.
        """
        for r in range(self.rows):
            for c in range(self.cols):
                cell = self.grid[r][c]
                if cell.number is None:
                    return False

                # Count distinct numbers in path
                path_values = set()
                curr_r, curr_c = r, c
                visited = {(r, c)}

                # Traverse
                dr, dc = cell.direction.delta
                next_r, next_c = curr_r + dr, curr_c + dc

                while 0 <= next_r < self.rows and 0 <= next_c < self.cols:
                    if (next_r, next_c) in visited:
                        break  # Cycle
                    visited.add((next_r, next_c))

                    target_cell = self.grid[next_r][next_c]
                    if target_cell.number is not None:
                        path_values.add(target_cell.number)

                    # Move to next
                    curr_r, curr_c = next_r, next_c
                    next_r, next_c = curr_r + dr, curr_c + dc

                if cell.number != len(path_values):
                    return False
        return True

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

    def to_string_with_candidates(self) -> str:
        # Calculate max width for each column
        col_widths = [0] * self.cols
        cell_strs = []

        for row in self.grid:
            row_strs = []
            for c, cell in enumerate(row):
                if cell.number is not None:
                    s = f"{cell.direction.value}{cell.number}"
                elif cell.candidates:
                    cands = "".join(str(x) for x in sorted(cell.candidates))
                    s = f"{cell.direction.value}{cands}"
                else:
                    s = f"{cell.direction.value}."

                col_widths[c] = max(col_widths[c], len(s))
                row_strs.append(s)
            cell_strs.append(row_strs)

        res = []
        # Create border
        border_parts = ["-" * (w + 2) for w in col_widths]
        border = "+" + "+".join(border_parts) + "+"
        res.append(border)

        for row_s in cell_strs:
            line_parts = []
            for c, s in enumerate(row_s):
                width = col_widths[c]
                padded = s.ljust(width)
                line_parts.append(f" {padded} ")

            line = "|" + "|".join(line_parts) + "|"
            res.append(line)
            res.append(border)

        return "\n".join(res) + "\n"
