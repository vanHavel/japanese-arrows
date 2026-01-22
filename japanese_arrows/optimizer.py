from japanese_arrows.rules import (
    And,
    ConditionCalculation,
    ConditionConstant,
    ConditionTerm,
    ConditionVariable,
    Equality,
    ExistsNumber,
    ExistsPosition,
    ForAllNumber,
    ForAllPosition,
    Formula,
    FunctionCall,
    Not,
    Or,
    Relation,
)


def get_free_variables(node: Formula | ConditionTerm) -> set[str]:
    if isinstance(node, ConditionVariable):
        return {node.name}
    elif isinstance(node, ConditionConstant):
        return set()
    elif isinstance(node, FunctionCall):
        vars = set()
        for arg in node.args:
            vars.update(get_free_variables(arg))
        return vars
    elif isinstance(node, ConditionCalculation):
        return get_free_variables(node.left) | get_free_variables(node.right)

    elif isinstance(node, And):
        vars = set()
        for f in node.formulas:
            vars.update(get_free_variables(f))
        return vars
    elif isinstance(node, Or):
        vars = set()
        for f in node.formulas:
            vars.update(get_free_variables(f))
        return vars
    elif isinstance(node, Not):
        return get_free_variables(node.formula)

    elif isinstance(node, (ExistsPosition, ExistsNumber, ForAllPosition, ForAllNumber)):
        bound = {v.name for v in node.variables}
        inner_free = get_free_variables(node.formula)
        return inner_free - bound

    elif isinstance(node, Equality):
        return get_free_variables(node.left) | get_free_variables(node.right)
    elif isinstance(node, Relation):
        vars = set()
        for arg in node.args:
            vars.update(get_free_variables(arg))
        return vars

    raise ValueError(f"Unknown node type: {type(node)}")


def optimize(phi: Formula) -> Formula:
    # Recursively optimize children first?
    # Actually for miniscoping, we process top-down logic but need optimized children.

    if isinstance(phi, (ExistsPosition, ExistsNumber)):
        # 1. Optimize inner formula
        inner = optimize(phi.formula)

        # 2. Flatten inner ANDs if present
        conjuncts = []
        if isinstance(inner, And):
            conjuncts = inner.formulas
        else:
            conjuncts = [inner]

        # 3. Try to push each variable down
        # We need to know the type for reconstruction
        is_position = isinstance(phi, ExistsPosition)
        constructor = ExistsPosition if is_position else ExistsNumber

        current_conjuncts = list(conjuncts)
        retained_vars = []

        for v in phi.variables:
            v_name = v.name

            # Find conjuncts that use this variable
            using_v = []
            not_using_v = []
            for c in current_conjuncts:
                if v_name in get_free_variables(c):
                    using_v.append(c)
                else:
                    not_using_v.append(c)

            # If we split the conjuncts, we can push v down
            if not_using_v and using_v:
                # Push v down to wrap 'using_v'
                # Combine using_v into one formula (And or single)
                if len(using_v) == 1:
                    sub_formula = using_v[0]
                else:
                    sub_formula = And(using_v)

                # Create the pushed quantifier
                pushed_q = constructor([v], sub_formula)

                # Optimistically optimize the new structure recursively?
                # Pushing down might reveal more opportunities (e.g. if we pushed 'i' into 'val(q)=i',
                # maybe 'q' was also waiting). But 'q' is processed in this loop.
                # Actually, the loop processes variables at THIS level.

                # Update current_conjuncts: replace using_v with [pushed_q]
                # But proceed carefully. We modify the pool of conjuncts for subsequent variables.
                current_conjuncts = not_using_v + [pushed_q]
            else:
                # Cannot restrict scope (uses all) or unused (vacuous).
                # If unused, we could drop it? Technically yes, but let's keep it safe or
                # just optimize it out if desired.
                # Standard logic: empty quantifier remains or use strict subset.
                # If using_v is empty, v is unused. We can drop it or keep it.
                # Let's keep it for safety unless we want to prune.
                if not using_v:
                    # Unused variable. Prune?
                    # Let's prune it.
                    pass
                else:
                    retained_vars.append(v)

        # Reconstruct result
        if not current_conjuncts:
            # Empty? Should not happen if original wasn't empty.
            return And([])  # True

        # Combine conjuncts
        if len(current_conjuncts) == 1:
            body = current_conjuncts[0]
        else:
            body = And(current_conjuncts)

        if not retained_vars:
            return body

        return constructor(retained_vars, body)

    elif isinstance(phi, (ForAllPosition, ForAllNumber)):
        # Similar logic for Universal + Or? Or just recursive optimize.
        # Miniscoping universal quantifiers works over AND too!
        # forall x (A ^ B) == forall x A ^ forall x B.
        # So same logic applies for AND.
        # But commonly we see Existential over Conjunction in these rules.
        # Let's apply basic optimization: recurse.
        # (Could implement distribution over AND for ForAll too).

        return type(phi)(phi.variables, optimize(phi.formula))

    elif isinstance(phi, And):
        return And([optimize(f) for f in phi.formulas])
    elif isinstance(phi, Or):
        return Or([optimize(f) for f in phi.formulas])
    elif isinstance(phi, Not):
        return Not(optimize(phi.formula))

    return phi
