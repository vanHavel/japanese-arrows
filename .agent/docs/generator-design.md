# Generator Design

The generator creates valid Japanese Arrows puzzles by combining random search, constraint satisfaction, and parallel execution.

## Core Generation Loop

1.  **Initial State**: Create a grid with arrows of random orientation.
2.  **Preprocessing**: Flip arrows that point out of bounds to increase the density of interactions.
3.  **Solver Loop**:
    *   Iteratively run the solver with `max_complexity`.
    *   **Contradiction Handling**: If the solver finds a contradiction, the generator attempts to "fix" the grid by rotating the arrow at the contradiction location. This is limited by `MAX_MODIFICATIONS_FRACTION` (10% of total cells, minimum 3).
    *   **Guessing (Underconstrained)**: If the solver exhausts its rules without finding a solution or contradiction, the generator picks a random unfilled cell and assigns one of its possible candidates. This is recorded as a **guess**.
    *   **Guessing Limit**: To ensure the puzzle remains a "puzzle" and not a "pre-filled solution", guessing is limited to MAX_GUESSES_FRACTION of the total cells (with a minimum of 3). Puzzles exceeding this limit are rejected.
4.  **Verification**: Once solved, the final trace is checked against a list of `Constraints` (e.g., rule complexity fractions, specific rule usage).
5.  **Minimal Clues**: The generator returns a puzzle containing *only* the arrow directions and the explicit **guesses** made during generation. All other numbers are left for the player to deduce.

## Parallel Execution (`generate_many`)

The generator supports high-throughput generation using `ProcessPoolExecutor`:

*   **Iterator Interface**: `generate_many` yields results as soon as any worker process completes a batch, allowing for real-time progress reporting.
*   **Racing Strategy**: Multiple workers can race to find a single complex puzzle.
*   **Early Cancellation**: Once the requested `max_count` of puzzles is reached, remaining futures are cancelled to save resources.

## Statistics and Rejection

The generator tracks detailed statistics to help tune constraints and understand difficulty:
*   `puzzles_successfully_generated`
*   `puzzles_rejected_constraints`: Failed post-solve validation.
*   `puzzles_rejected_no_solution`: Reached a dead end that rotation couldn't fix.
*   `puzzles_rejected_excessive_guessing`: Exceeded the 25% clue threshold.
*   `rejections_per_constraint`: Breakdown of which constraints were most difficult to satisfy.

Current feasible generation limits:
- max complexity: 6 - 6x6
- max_complexity: 5 - 9x9
- max_complexity: 4 - unsuccessful
- max_complexity: 3 - 9x9
  
