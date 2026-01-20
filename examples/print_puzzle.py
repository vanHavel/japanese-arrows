from japanese_arrows.models import Cell, Direction, Puzzle


def main() -> None:
    # Create a sample 4x4 grid with various directions and numbers
    grid = [
        [Cell(Direction.SOUTH, 1), Cell(Direction.EAST, 2), Cell(Direction.SOUTH_WEST, 0), Cell(Direction.WEST, 1)],
        [
            Cell(Direction.NORTH, 0),
            Cell(Direction.SOUTH_EAST, 3),
            Cell(Direction.NORTH_WEST, 1),
            Cell(Direction.EAST, 2),
        ],
        [Cell(Direction.NORTH_EAST, 1), Cell(Direction.SOUTH, 2), Cell(Direction.NORTH, 0), Cell(Direction.WEST, 3)],
        [
            Cell(Direction.SOUTH_WEST, 2),
            Cell(Direction.NORTH_WEST, 1),
            Cell(Direction.EAST, 0),
            Cell(Direction.SOUTH, 1),
        ],
    ]

    puzzle = Puzzle(rows=4, cols=4, grid=grid)

    print("Example 4x4 Japanese Arrows Puzzle:")
    print(puzzle.to_string())


if __name__ == "__main__":
    main()
