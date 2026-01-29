from japanese_arrows.rules import (
    And,
    Conclusion,
    Constant,
    Equality,
    ExcludeVal,
    ExistsNumber,
    ExistsPosition,
    ForAllNumber,
    ForAllPosition,
    Formula,
    FORule,
    FunctionCall,
    Not,
    OnlyVal,
    Or,
    Relation,
    SetVal,
    Term,
    Variable,
)


def get_free_variables(node: Formula | Term) -> set[str]:
    if isinstance(node, Variable):
        return {node.name}
    elif isinstance(node, Constant):
        return set()
    elif isinstance(node, FunctionCall):
        vars = set()
        for arg in node.args:
            vars.update(get_free_variables(arg))
        return vars

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


def substitute_term(term: Term, var_name: str, replacement: Term) -> Term:
    if isinstance(term, Variable):
        if term.name == var_name:
            return replacement
        return term
    elif isinstance(term, Constant):
        return term
    elif isinstance(term, FunctionCall):
        new_args = [substitute_term(arg, var_name, replacement) for arg in term.args]
        return FunctionCall(term.name, new_args)
    raise ValueError(f"Unknown term type: {type(term)}")


def substitute_formula(formula: Formula, var_name: str, replacement: Term) -> Formula:
    if isinstance(formula, Equality):
        return Equality(
            substitute_term(formula.left, var_name, replacement),
            substitute_term(formula.right, var_name, replacement),
        )
    elif isinstance(formula, Relation):
        new_args = [substitute_term(arg, var_name, replacement) for arg in formula.args]
        return Relation(formula.relation, new_args)
    elif isinstance(formula, Not):
        return Not(substitute_formula(formula.formula, var_name, replacement))
    elif isinstance(formula, And):
        return And([substitute_formula(f, var_name, replacement) for f in formula.formulas])
    elif isinstance(formula, Or):
        return Or([substitute_formula(f, var_name, replacement) for f in formula.formulas])
    elif isinstance(formula, (ExistsPosition, ExistsNumber)):
        if any(v.name == var_name for v in formula.variables):
            return formula
        new_inner = substitute_formula(formula.formula, var_name, replacement)
        return type(formula)(formula.variables, new_inner)
    elif isinstance(formula, (ForAllPosition, ForAllNumber)):
        if any(v.name == var_name for v in formula.variables):
            return formula
        new_inner = substitute_formula(formula.formula, var_name, replacement)
        return type(formula)(formula.variables, new_inner)
    raise ValueError(f"Unknown formula type: {type(formula)}")


def substitute_conclusion(conclusion: Conclusion, var_name: str, replacement: Term) -> Conclusion:
    if isinstance(conclusion, SetVal):
        return SetVal(
            substitute_term(conclusion.position, var_name, replacement),
            substitute_term(conclusion.value, var_name, replacement),
        )
    elif isinstance(conclusion, ExcludeVal):
        return ExcludeVal(
            substitute_term(conclusion.position, var_name, replacement),
            conclusion.operator,
            substitute_term(conclusion.value, var_name, replacement),
        )
    elif isinstance(conclusion, OnlyVal):
        return OnlyVal(
            substitute_term(conclusion.position, var_name, replacement),
            [substitute_term(v, var_name, replacement) for v in conclusion.values],
        )
    raise ValueError(f"Unknown conclusion type: {type(conclusion)}")


def find_equality_substitution(conjuncts: list[Formula], var_name: str) -> Term | None:
    for conjunct in conjuncts:
        if isinstance(conjunct, Equality):
            left_vars = get_free_variables(conjunct.left)
            right_vars = get_free_variables(conjunct.right)

            if isinstance(conjunct.left, Variable) and conjunct.left.name == var_name:
                if var_name not in right_vars:
                    return conjunct.right
            if isinstance(conjunct.right, Variable) and conjunct.right.name == var_name:
                if var_name not in left_vars:
                    return conjunct.left
    return None


def get_position_variables_from_conclusions(conclusions: list[Conclusion]) -> set[str]:
    result = set()
    for c in conclusions:
        result.update(get_free_variables(c.position))
    return result


def eliminate_quantifiers_in_formula(
    formula: Formula, conclusions: list[Conclusion]
) -> tuple[Formula, list[Conclusion]]:
    if isinstance(formula, (ExistsPosition, ExistsNumber)):
        inner, conclusions = eliminate_quantifiers_in_formula(formula.formula, conclusions)

        conjuncts = inner.formulas if isinstance(inner, And) else [inner]

        remaining_vars: list[Variable] = []
        current_conjuncts = list(conjuncts)
        current_conclusions = list(conclusions)

        is_position_quantifier = isinstance(formula, ExistsPosition)

        for v in formula.variables:
            replacement = find_equality_substitution(current_conjuncts, v.name)
            if replacement is not None:
                new_conjuncts = []
                for c in current_conjuncts:
                    should_skip = False
                    if isinstance(c, Equality):
                        left_is_var = isinstance(c.left, Variable) and c.left.name == v.name
                        right_is_var = isinstance(c.right, Variable) and c.right.name == v.name
                        if left_is_var or right_is_var:
                            other_vars = get_free_variables(c.right) if left_is_var else get_free_variables(c.left)
                            if v.name not in other_vars:
                                should_skip = True
                    if not should_skip:
                        new_conjuncts.append(substitute_formula(c, v.name, replacement))

                if not new_conjuncts:
                    remaining_vars.append(v)
                    continue

                if is_position_quantifier:
                    tentative_conclusions = [substitute_conclusion(c, v.name, replacement) for c in current_conclusions]
                    remaining_position_vars = {var.name for var in remaining_vars}
                    for other_v in formula.variables:
                        if other_v.name != v.name:
                            remaining_position_vars.add(other_v.name)

                    pos_vars_after = get_position_variables_from_conclusions(tentative_conclusions)
                    if not (pos_vars_after & remaining_position_vars):
                        remaining_vars.append(v)
                        continue

                    current_conclusions = tentative_conclusions

                current_conjuncts = new_conjuncts
                if not is_position_quantifier:
                    current_conclusions = [substitute_conclusion(c, v.name, replacement) for c in current_conclusions]
            else:
                remaining_vars.append(v)

        body: Formula
        if not current_conjuncts:
            body = And([])
        elif len(current_conjuncts) == 1:
            body = current_conjuncts[0]
        else:
            body = And(current_conjuncts)

        result_formula: Formula
        if remaining_vars:
            result_formula = type(formula)(remaining_vars, body)
        else:
            result_formula = body

        return result_formula, current_conclusions

    elif isinstance(formula, (ForAllPosition, ForAllNumber)):
        inner, conclusions = eliminate_quantifiers_in_formula(formula.formula, conclusions)
        return type(formula)(formula.variables, inner), conclusions
    elif isinstance(formula, And):
        new_formulas = []
        for f in formula.formulas:
            new_f, conclusions = eliminate_quantifiers_in_formula(f, conclusions)
            new_formulas.append(new_f)
        return And(new_formulas), conclusions
    elif isinstance(formula, Or):
        new_formulas = []
        for f in formula.formulas:
            new_f, conclusions = eliminate_quantifiers_in_formula(f, conclusions)
            new_formulas.append(new_f)
        return Or(new_formulas), conclusions
    elif isinstance(formula, Not):
        inner, conclusions = eliminate_quantifiers_in_formula(formula.formula, conclusions)
        return Not(inner), conclusions
    else:
        return formula, conclusions


def minscope(phi: Formula) -> Formula:
    if isinstance(phi, (ExistsPosition, ExistsNumber)):
        inner = minscope(phi.formula)

        conjuncts = []
        if isinstance(inner, And):
            conjuncts = inner.formulas
        else:
            conjuncts = [inner]

        is_position = isinstance(phi, ExistsPosition)
        constructor = ExistsPosition if is_position else ExistsNumber

        current_conjuncts = list(conjuncts)
        retained_vars = []

        for v in phi.variables:
            v_name = v.name

            using_v = []
            not_using_v = []
            for c in current_conjuncts:
                if v_name in get_free_variables(c):
                    using_v.append(c)
                else:
                    not_using_v.append(c)

            if not_using_v and using_v:
                if len(using_v) == 1:
                    sub_formula = using_v[0]
                else:
                    sub_formula = And(using_v)

                pushed_q = constructor([v], sub_formula)

                current_conjuncts = not_using_v + [pushed_q]
            else:
                if not using_v:
                    pass
                else:
                    retained_vars.append(v)

        if not current_conjuncts:
            return And([])

        if len(current_conjuncts) == 1:
            body = current_conjuncts[0]
        else:
            body = And(current_conjuncts)

        if not retained_vars:
            return body

        return constructor(retained_vars, body)

    elif isinstance(phi, (ForAllPosition, ForAllNumber)):
        return type(phi)(phi.variables, minscope(phi.formula))

    elif isinstance(phi, And):
        return And([minscope(f) for f in phi.formulas])
    elif isinstance(phi, Or):
        return Or([minscope(f) for f in phi.formulas])
    elif isinstance(phi, Not):
        return Not(minscope(phi.formula))

    return phi


def optimize_rule(rule: FORule) -> FORule:
    condition, conclusions = eliminate_quantifiers_in_formula(rule.condition, rule.conclusions)
    condition = minscope(condition)
    return FORule(
        name=rule.name,
        condition=condition,
        conclusions=conclusions,
        complexity=rule.complexity,
    )


def optimize(phi: Formula) -> Formula:
    return minscope(phi)
