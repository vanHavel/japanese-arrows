from enum import Enum

from japanese_arrows.rules import (
    And,
    Atom,
    ConditionConstant,
    ConditionTerm,
    ConditionVariable,
    ExistsNumber,
    ExistsPosition,
    ForAllNumber,
    ForAllPosition,
    Formula,
    FunctionCall,
    Or,
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

    elif isinstance(formula, Atom):
        if formula.relation not in relations:
            raise TypeError(f"Unknown relation: {formula.relation}")

        expected_types = relations[formula.relation]
        if len(formula.args) != len(expected_types):
            raise TypeError(
                f"Relation '{formula.relation}' expects {len(expected_types)} arguments, got {len(formula.args)}"
            )

        for i, (arg, expected) in enumerate(zip(formula.args, expected_types)):
            actual = _infer_term_type(arg, constants, functions, scope)
            if actual != expected:
                raise TypeError(
                    f"Argument {i + 1} of '{formula.relation}' must be {expected.value}, "
                    f"but got {actual.value} (Term: {arg})"
                )
    else:
        raise TypeError(f"Unknown formula type: {type(formula)}")


def _infer_term_type(
    term: ConditionTerm, constants: dict[str, Type], functions: dict[str, FunctionSignature], scope: dict[str, Type]
) -> Type:
    if isinstance(term, ConditionVariable):
        if term.name not in scope:
            raise TypeError(f"Undefined variable: {term.name}")
        return scope[term.name]

    elif isinstance(term, ConditionConstant):
        # Constants map check
        val = term.value
        if isinstance(val, int):
            return Type.NUMBER
        if str(val) in constants:
            return constants[str(val)]
        return Type.UNKNOWN

    elif isinstance(term, FunctionCall):
        if term.name not in functions:
            raise TypeError(f"Unknown function: {term.name}")

        arg_types, ret_type = functions[term.name]
        if len(term.args) != len(arg_types):
            raise TypeError(f"Function '{term.name}' expects {len(arg_types)} arguments, got {len(term.args)}")

        for i, (arg, expected) in enumerate(zip(term.args, arg_types)):
            actual = _infer_term_type(arg, constants, functions, scope)
            if actual != expected:
                raise TypeError(
                    f"Argument {i + 1} of function '{term.name}' must be {expected.value}, but got {actual.value}"
                )
        return ret_type

    else:
        raise TypeError(f"Unknown term type: {type(term)}")
