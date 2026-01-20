from japanese_arrows.models import Puzzle


def read_puzzle(file_path: str) -> Puzzle:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    return Puzzle.from_string(content)


def write_puzzle(puzzle: Puzzle, file_path: str) -> None:
    content = puzzle.to_string()
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
