Japanese arrow puzzles can be described using a simple, human readable file format.

Here is an example for a 3 x 2 puzzle.

+----+----+
| ↑. | ←1 |
+----+----+
| ↓1 | →0 |
+----+----+
| ↗1 | ↑2 |
+----+----+

Each cell contains two characters
1. a unicode arrow (U+219x) with x-0..3 for cardinal directions, x=6..9 for diagonals.
2. a number to fill the arrow (potentially .) to signify the arrow is currently empty.