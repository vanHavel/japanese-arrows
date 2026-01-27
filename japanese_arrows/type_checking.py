from enum import Enum

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
    Rule,
    SetVal,
    Term,
    Variable,
)


class Type(Enum):
    POSITION = "Position"
    NUMBER = "Number"
    DIRECTION = "Direction"

    # Special types
    UNKNOWN = "Unknown"


# Function Signature: ([ArgType, ...], ReturnType)
FunctionSignature = tuple[list[Type], Type]

# Relation Signature: [ArgType, ...]
RelationSignature = list[Type]


def check_rule(
    rule: Rule,
    constants: dict[str, Type],
    functions: dict[str, FunctionSignature],
    relations: dict[str, RelationSignature],
) -> None:
    """
    Checks if a rule is well-typed.
    """
    if not isinstance(rule, FORule):
        # Only FORules have conditions and conclusions to check
        return

    # 1. Check condition
    check_condition(rule.condition, constants, functions, relations)

    # 2. Gather variables from condition (Exists quantifiers)
    scope: dict[str, Type] = {}
    _gather_condition_variables(rule.condition, scope)

    # 3. Check conclusions
    for conclusion in rule.conclusions:
        _check_conclusion(conclusion, constants, scope, functions)


def check_condition(
    formula: Formula,
    constants: dict[str, Type],
    functions: dict[str, FunctionSignature],
    relations: dict[str, RelationSignature],
) -> None:
    """
    Checks if a condition formula is well-typed.
    Raises TypeError if invalid.
    """
    _check_formula(formula, constants, functions, relations, scope={})


def _gather_condition_variables(formula: Formula, scope: dict[str, Type]) -> None:
    """
    Recursively gathers variables bound by Exists quantifiers in the condition
    into the scope for use in conclusions.
    """
    if isinstance(formula, (And, Or)):
        for sub in formula.formulas:
            _gather_condition_variables(sub, scope)
    elif isinstance(formula, Not):
        _gather_condition_variables(formula.formula, scope)
    elif isinstance(formula, ExistsPosition):
        for v in formula.variables:
            scope[v.name] = Type.POSITION
        _gather_condition_variables(formula.formula, scope)
    elif isinstance(formula, ExistsNumber):
        for v in formula.variables:
            scope[v.name] = Type.NUMBER
        _gather_condition_variables(formula.formula, scope)
    elif isinstance(formula, (ForAllPosition, ForAllNumber)):
        # Stop gathering at ForAll quantifiers.
        # We only care about the existential prefix for conclusion scope.
        return
    # Atoms/Relations/Equality don't introduce new variables


def _check_conclusion(
    conclusion: Conclusion, constants: dict[str, Type], scope: dict[str, Type], functions: dict[str, FunctionSignature]
) -> None:
    if isinstance(conclusion, SetVal):
        pos_type = _infer_term_type(conclusion.position, constants, scope, functions)
        if pos_type != Type.POSITION:
            raise TypeError(f"SetVal position must be Position, got {pos_type.value}")

        val_type = _infer_term_type(conclusion.value, constants, scope, functions)
        if val_type != Type.NUMBER:
            raise TypeError(f"SetVal value must be Number, got {val_type.value}")

    elif isinstance(conclusion, ExcludeVal):
        pos_type = _infer_term_type(conclusion.position, constants, scope, functions)
        if pos_type != Type.POSITION:
            raise TypeError(f"ExcludeVal position must be Position, got {pos_type.value}")

        val_type = _infer_term_type(conclusion.value, constants, scope, functions)
        if val_type != Type.NUMBER:
            raise TypeError(f"ExcludeVal value must be Number, got {val_type.value}")

    elif isinstance(conclusion, OnlyVal):
        pos_type = _infer_term_type(conclusion.position, constants, scope, functions)
        if pos_type != Type.POSITION:
            raise TypeError(f"OnlyVal position must be Position, got {pos_type.value}")

        for val in conclusion.values:
            val_type = _infer_term_type(val, constants, scope, functions)
            if val_type != Type.NUMBER:
                raise TypeError(f"OnlyVal values must be Number, got {val_type.value}")
    else:
        raise TypeError(f"Unknown conclusion type: {type(conclusion)}")


def _infer_term_type(
    term: Term,
    constants: dict[str, Type],
    scope: dict[str, Type],
    functions: dict[str, FunctionSignature] | None = None,
) -> Type:
    if isinstance(term, Variable):
        if term.name not in scope:
            raise TypeError(f"Undefined variable: {term.name}")
        return scope[term.name]

    elif isinstance(term, Constant):
        val = term.value
        if isinstance(val, int):
            return Type.NUMBER
        if str(val) in constants:
            return constants[str(val)]
        return Type.UNKNOWN

    elif isinstance(term, FunctionCall):
        # Built-in arithmetic
        if term.name in ("+", "-"):
            if len(term.args) != 2:
                raise TypeError(f"Function '{term.name}' expects 2 arguments, got {len(term.args)}")

            left_type = _infer_term_type(term.args[0], constants, scope, functions)
            right_type = _infer_term_type(term.args[1], constants, scope, functions)
            if left_type != Type.NUMBER or right_type != Type.NUMBER:
                raise TypeError(
                    f"Function '{term.name}' operands must be Number, got {left_type.value} and {right_type.value}"
                )
            return Type.NUMBER

        if functions is None:
            # In conclusions, functions might not be allowed or we need to pass functions map.
            raise TypeError("FunctionCall usage requires functions map")

        if term.name not in functions:
            raise TypeError(f"Unknown function: {term.name}")

        arg_types, ret_type = functions[term.name]
        if len(term.args) != len(arg_types):
            raise TypeError(f"Function '{term.name}' expects {len(arg_types)} arguments, got {len(term.args)}")

        for i, (arg, expected) in enumerate(zip(term.args, arg_types)):
            actual = _infer_term_type(arg, constants, scope, functions)
            if actual != expected:
                raise TypeError(
                    f"Argument {i + 1} of function '{term.name}' must be {expected.value}, but got {actual.value}"
                )
        return ret_type

    else:
        raise TypeError(f"Unknown term type: {type(term)}")


def _check_formula(
    formula: Formula,
    constants: dict[str, Type],
    functions: dict[str, FunctionSignature],
    relations: dict[str, RelationSignature],
    scope: dict[str, Type],
) -> None:
    if isinstance(formula, (And, Or)):
        for sub in formula.formulas:
            _check_formula(sub, constants, functions, relations, scope)

    elif isinstance(formula, Not):
        _check_formula(formula.formula, constants, functions, relations, scope)

    elif isinstance(formula, (ExistsPosition, ForAllPosition)):
        new_scope = scope.copy()
        for v in formula.variables:
            new_scope[v.name] = Type.POSITION
        _check_formula(formula.formula, constants, functions, relations, new_scope)

    elif isinstance(formula, (ExistsNumber, ForAllNumber)):
        new_scope = scope.copy()
        for v in formula.variables:
            new_scope[v.name] = Type.NUMBER
        _check_formula(formula.formula, constants, functions, relations, new_scope)

    elif isinstance(formula, Equality):
        left_type = _infer_term_type(formula.left, constants, scope, functions)
        right_type = _infer_term_type(formula.right, constants, scope, functions)
        if left_type != right_type:
            raise TypeError(f"Equality mismatch: {left_type.value} != {right_type.value} ({formula})")

    elif isinstance(formula, Relation):
        if formula.relation not in relations:
            raise TypeError(f"Unknown relation: {formula.relation}")

        expected_types = relations[formula.relation]
        if len(formula.args) != len(expected_types):
            raise TypeError(
                f"Relation '{formula.relation}' expects {len(expected_types)} arguments, got {len(formula.args)}"
            )

        for i, (arg, expected) in enumerate(zip(formula.args, expected_types)):
            actual = _infer_term_type(arg, constants, scope, functions)
            if actual != expected:
                raise TypeError(
                    f"Argument {i + 1} of '{formula.relation}' must be {expected.value}, "
                    f"but got {actual.value} (Term: {arg})"
                )
    else:
        raise TypeError(f"Unknown formula type: {type(formula)}")
