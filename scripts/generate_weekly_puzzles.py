from japanese_arrows.generator.constraints import (
    FollowingArrowsFraction,
    NumberFraction,
    RuleComplexityFraction,
)

GENERATION_CONFIG = {
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
        "difficulty": "Hard",
    },
}
