import datetime
import os
from typing import TypedDict

import yaml

from japanese_arrows.generator.constraints import (
    Constraint,
    FollowingArrowsFraction,
    NumberFraction,
    RuleComplexityFraction,
)
from japanese_arrows.generator.generator import Generator
from japanese_arrows.solver import SolverStatus, create_solver


class DayConfig(TypedDict):
    size: int
    allow_diagonals: bool
    max_complexity: int
    constraints: list[Constraint]
    difficulty: str


GENERATION_CONFIG: dict[str, DayConfig] = {
    "Monday": {
        "size": 4,
        "allow_diagonals": False,
        "max_complexity": 3,
        "constraints": [
            FollowingArrowsFraction(min_fraction=0.1),
            RuleComplexityFraction(complexity=3, min_count=1, max_count=5),
            NumberFraction(number=1, max_fraction=0.5),
        ],
        "difficulty": "Easy",
    },
    "Tuesday": {
        "size": 5,
        "allow_diagonals": True,
        "max_complexity": 4,
        "constraints": [
            FollowingArrowsFraction(min_fraction=0.05),
            RuleComplexityFraction(complexity=3, min_count=2, max_count=6),
            NumberFraction(number=1, max_fraction=0.5),
        ],
        "difficulty": "Normal",
    },
    "Wednesday": {
        "size": 6,
        "allow_diagonals": False,
        "max_complexity": 5,
        "constraints": [
            FollowingArrowsFraction(min_fraction=0.1),
            RuleComplexityFraction(complexity=5, min_count=1, max_count=4),
            NumberFraction(number=1, max_fraction=0.5),
            NumberFraction(number=4, min_fraction=0.01),
        ],
        "difficulty": "Hard",
    },
    "Thursday": {
        "size": 5,
        "allow_diagonals": True,
        "max_complexity": 5,
        "constraints": [
            FollowingArrowsFraction(min_fraction=0.05),
            RuleComplexityFraction(complexity=5, min_count=1, max_count=4),
            NumberFraction(number=1, max_fraction=0.5),
        ],
        "difficulty": "Hard",
    },
    "Friday": {
        "size": 5,
        "allow_diagonals": False,
        "max_complexity": 4,
        "constraints": [
            FollowingArrowsFraction(min_fraction=0.1),
            RuleComplexityFraction(complexity=3, min_count=3, max_count=8),
            NumberFraction(number=1, max_fraction=0.5),
            NumberFraction(number=4, min_fraction=0.01),
        ],
        "difficulty": "Normal",
    },
    "Saturday": {
        "size": 6,
        "allow_diagonals": True,
        "max_complexity": 6,
        "constraints": [
            FollowingArrowsFraction(min_fraction=0.05),
            RuleComplexityFraction(complexity=6, min_count=1, max_count=4),
            NumberFraction(number=1, max_fraction=0.5),
            NumberFraction(number=4, min_fraction=0.01),
        ],
        "difficulty": "Devious",
    },
    "Sunday": {
        "size": 6,
        "allow_diagonals": False,
        "max_complexity": 6,
        "constraints": [
            FollowingArrowsFraction(min_fraction=0.1),
            RuleComplexityFraction(complexity=6, min_count=1, max_count=4),
            NumberFraction(number=1, max_fraction=0.5),
            NumberFraction(number=4, min_fraction=0.01),
        ],
        "difficulty": "Devious",
    },
}

START_DATE = datetime.date(2026, 1, 26)
END_DATE = datetime.date(2026, 2, 8)


def main() -> None:
    generator = Generator()

    current_date = START_DATE
    while current_date <= END_DATE:
        day_name = current_date.strftime("%A")
        config = GENERATION_CONFIG[day_name]

        path = os.path.join(
            "content",
            current_date.strftime("%Y"),
            current_date.strftime("%m"),
            current_date.strftime("%d"),
        )

        if os.path.exists(os.path.join(path, "puzzle.txt")):
            print(f"Puzzle for {current_date} already exists, skipping.")
            current_date += datetime.timedelta(days=1)
            continue

        print(f"Generating for {current_date} ({day_name})...")

        puzzles, stats = generator.generate_many(
            count=1,
            rows=config["size"],
            cols=config["size"],
            allow_diagonals=config["allow_diagonals"],
            max_complexity=config["max_complexity"],
            constraints=config["constraints"],
            n_jobs=-1,
        )

        if not puzzles:
            print(f"Failed to generate puzzle for {current_date}")
            current_date += datetime.timedelta(days=1)
            continue

        puzzle = puzzles[0]

        # Get solution
        solver = create_solver(max_complexity=config["max_complexity"])
        res = solver.solve(puzzle)
        if res.status != SolverStatus.SOLVED:
            print(f"Generated puzzle for {current_date} is NOT solved (Status: {res.status})")
            current_date += datetime.timedelta(days=1)
            continue

        os.makedirs(path, exist_ok=True)

        with open(os.path.join(path, "puzzle.txt"), "w") as f:
            f.write(puzzle.to_string())

        with open(os.path.join(path, "solution.txt"), "w") as f:
            f.write(res.puzzle.to_string())

        metadata = {
            "difficulty": config["difficulty"],
            "size": f"{config['size']}x{config['size']}",
            "arrows": "Diagonal" if config["allow_diagonals"] else "Straight",
        }
        with open(os.path.join(path, "metadata.yaml"), "w") as f:
            yaml.dump(metadata, f, sort_keys=False)

        print(f"Successfully generated and saved puzzle for {current_date}")
        current_date += datetime.timedelta(days=1)


if __name__ == "__main__":
    main()
