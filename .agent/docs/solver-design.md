# Solver
The puzzle solver simulates a human solving the puzzle by deduction.

The solver is initialized with a list of rules. When solving a puzzle, the solver goes through the rules in order. 

If a rule can be applied to make progress in the puzzle, the progress is marked in the puzzle state.

If this leaves all arrows filled, the solver checks the whole puzzle to verify that there is no contradiction and every arrow has a value according to the rules. If yes, the solver then terminates and returns the solved puzzle. On contradiction the solver returns NoSolution.

If a rule does not allow to make progress, the solver continues with the next rule.

If no rule allows to make progress, the solver terminates with Underconstrained result.

For more details on rules, check rules-design.md.

# Puzzle State
The state of the solver is a puzzle instance, where each cell has a direction and a value. The directions are given and immutable. The value can be 
- an integer, which means this cell is already filled
- a list of integers, the options for this cell
Initially, when the solver gets the puzzle, it replaces all cells without a number (free arrows) with an options list. The options contain all numbers from 0 up to the max of rows and cols in the puzzle - 1.
The solver continues by narrowing down options according to rules. When only one option is left for a cell, it is replaced by an integer, signifying the cell is filled.


 # How the solver applies rules
 The solver will try to prove the condition true recursively. While doing so, it will also produce a witness for the existential prefix of the rule. 
 These witnesses will then be replaced in the conclusion. Next, the conclusions will be applied one by one to the current puzzle state.
 If any conclusion contradicts the current puzzle state, the solve returns NoSolution.