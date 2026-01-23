# Rules
Rules have a name and contain a condition and the conclusions. 
The condition is a typed first order formula. The universe contains positions in the grid, numbers (up to the max of rows and cols), as well as special elements OOB and nil. 
There are two types of quantifiers
- exists p / forall p quantifies over positions (not OOB)
- exists i / forall i quantifies over numbers (not nil)
By convention, we use p,q,r... for position variables and i,j,k... for numeric vatiables.
Each condition typically begins with existential quantifiers, the part before the first universal quantifier (if any) is called the existential prefix of the condition.
We allow short form multi quantifications such as exists p,q ...
We allow an empty string as a short form for something always true (e.g. 0=0)

The signature contains 
- unary function next(p): the immediate next position the arrow at p is pointing at, or OOB if out of the grid. 
- binary relation points_at(p, q): the tuples (p, q) such that the arrow at p points at the arrow at q, directly or indirectly, in a straight line
- constants OOB, nil, 0
- unary function val(p): the numeric value of p, or nil if not set
- unary function sees_distinct(p): the number of distinct numbers in arrows that p points at, in a straight line
- binary relation candidate(p, i): the tuple (p, i) such that either the arrow at p has i as one of its options, or val(p) = i
- binary relations <, >, <=, >= on digits with the usual interpretation
- unary function ahead(p): number of cells in the grid in the direction p points at (straight line)
- unary function behind(p): number of cells in the grid before p in the direction p points at (straight line)
- unary function ahead_free(p): number of cells in the direction p points at that are not filled yet
- binary function between_free(p, q): the number of free cells strictly between p and q (exclusive), if q is on the path from p. Otherwise nil.
- binary arithmetic function +

The conclusions are a list. Each conclusion can be one of
- set(p, d): position p must have value d
- exlude(p, d): position p cannot have value d
 - exclude(p, >d) as well as other comparison operators
- only(p, [d1,...,dn]): position p must have a value within d1...dn

In the conclusion, p,d etc. are typically free variables that appear in the existential prefix of the condition. Digits can also be constants.
We also allow terms such as d+1, d-2 for digits.

Here are a few examples of rules to illustrate the concept:

Example 1: An arrow pointing out of the grid has value 0.
Condition: exists p (ahead(p) = 0)
Conclusions:
 - set(p, 0)

 Example 2: Two arrows next two each other, pointing in the same direction, with the arrow in front already marked i -> the arrow behind must be marked i or i+1
 Condition: exists p,q,i (next(p) = q ^ dir(p) = dir(q) ^ val(q) = i)
 Conclusions:
 - only(p, [i, i+1])

 Example 3: The value in an arrow can not be higher than the number of arrows ahead.
 Condition: exists p,i (ahead(p) = i)
 Conclusions:
 - exclude(p, >i)

 # Rule Syntax Details
 This section describes details of the string representation of rules, from which they can be parsed.

 Rules: are written as yaml as
id:
 name: Name
 condition: Condition
 complexity: Complexity
 conclusions:
   - Conclusion1
   - Conclusion2

Conditions:
 - Quantifers can be grouped as in exists p,i (phi). After a (potentially grouped) quantifier, there are always parentheses.
 - The type of quantifiers is infered by convention of variable names. Variables are single characters only
 - Around chains binary operators, there are always parentheses to simplify parsing to avoid ambiguity. Example (phi ^ (psi v tau)). An exception to that are chains of only disjunctions or only conjunctions.
 - Negation is written as !(phi) with parentheses.
 - Implication phi -> tau is syntactic sugar for (!(phi) v tau)
 - t1 != t2 is sugar for !(t1 = t2)

 Full Example: (does not make logical sense, just for syntax)
infer-tower:
 name: Infer Tower
 complexity: 1
 condition: exists p,q ((p != q ^ points_at(p, q)) -> forall i ((val(p) = i) -> val(q) = i))
   conclusions:
   - set(q, 3)
   - exclude(p, >1)