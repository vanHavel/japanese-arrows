# V1 Generator

The naive V1 generator accepts these arguments
- grid sizes (n, m)
- flag whether diagonal arrows are allowed
- max_complexity of the puzzle
- constraints:
  - constraints have an ABC with one function that takes a solver trace and returns a boolean
  - implement these constraints:
    - min_rule_applications_of_max_complexity (fraction)
    - max_rule_applications_of_max_complexity (fraction)

The generator then creates a puzzle by
1. creating a grid with arrows of random orientation
2. while the grid is not solved:
    1. run the solver with max_complexity
    2. if the solver solves the grid, return the original arrow grid together with all recorded manual inserts
    3. otherwise, in the partial solution, choose a random unfilled cell and fill it with one of its candidates, record this decision as a manual insert
3. solve the grid, get the solver trace and verify that the grid lies within the desired constraints on rule applications 
4. if the grid does not lie within the desired constraints, start over