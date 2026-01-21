import pytest

from japanese_arrows.rules import (
    Atom,
    ConditionConstant,
    ConditionVariable,
    ExistsNumber,
    ExistsPosition,
    FunctionCall,
)
from japanese_arrows.type_checking import FunctionSignature, RelationSignature, Type, check_condition


@pytest.fixture
def type_context() -> tuple[dict[str, Type], dict[str, FunctionSignature], dict[str, RelationSignature]]:
    constants = {
        "OOB": Type.POSITION,
        "nil": Type.NUMBER,
        # Integers are automatically inferred as Type.NUMBER
    }

    functions: dict[str, FunctionSignature] = {
        "next": ([Type.POSITION], Type.POSITION),
        "ahead": ([Type.POSITION], Type.NUMBER),
        "val": ([Type.POSITION], Type.NUMBER),
        "dir": ([Type.POSITION], Type.DIRECTION),
    }

    relations: dict[str, RelationSignature] = {
        # Removed generic '=' as requested.
        "eq_pos": [Type.POSITION, Type.POSITION],
        "eq_num": [Type.NUMBER, Type.NUMBER],
        "points_at": [Type.POSITION, Type.POSITION],
        ">": [Type.NUMBER, Type.NUMBER],
    }
    return constants, functions, relations


def test_valid_simple_formula(
    type_context: tuple[dict[str, Type], dict[str, FunctionSignature], dict[str, RelationSignature]],
) -> None:
    constants, functions, relations = type_context
    # exists p (next(p) eq_pos OOB)
    p = ConditionVariable("p")
    formula = ExistsPosition(
        variables=[p], formula=Atom("eq_pos", [FunctionCall("next", [p]), ConditionConstant("OOB")])
    )
    # Should not raise exception
    check_condition(formula, constants, functions, relations)


def test_invalid_arg_type(
    type_context: tuple[dict[str, Type], dict[str, FunctionSignature], dict[str, RelationSignature]],
) -> None:
    constants, functions, relations = type_context
    # exists p (ahead(p) eq_pos OOB) -> ahead returns NUMBER, eq_pos expects POSITION
    p = ConditionVariable("p")
    formula = ExistsPosition(
        variables=[p], formula=Atom("eq_pos", [FunctionCall("ahead", [p]), ConditionConstant("OOB")])
    )

    with pytest.raises(TypeError, match="must be Position, but got Number"):
        check_condition(formula, constants, functions, relations)


def test_undefined_variable(
    type_context: tuple[dict[str, Type], dict[str, FunctionSignature], dict[str, RelationSignature]],
) -> None:
    constants, functions, relations = type_context
    # exists p (next(q) eq_pos p) -> q is undefined
    p = ConditionVariable("p")
    q = ConditionVariable("q")
    formula = ExistsPosition(variables=[p], formula=Atom("eq_pos", [FunctionCall("next", [q]), p]))

    with pytest.raises(TypeError, match="Undefined variable: q"):
        check_condition(formula, constants, functions, relations)


def test_nested_quantifiers(
    type_context: tuple[dict[str, Type], dict[str, FunctionSignature], dict[str, RelationSignature]],
) -> None:
    constants, functions, relations = type_context
    # exists p (exists i (val(p) eq_num i))
    p = ConditionVariable("p")
    i = ConditionVariable("i")

    formula = ExistsPosition(
        variables=[p], formula=ExistsNumber(variables=[i], formula=Atom("eq_num", [FunctionCall("val", [p]), i]))
    )
    # Should pass
    check_condition(formula, constants, functions, relations)


def test_type_mismatch_constant(
    type_context: tuple[dict[str, Type], dict[str, FunctionSignature], dict[str, RelationSignature]],
) -> None:
    constants, functions, relations = type_context
    # exists p (val(p) eq_num OOB) -> OOB is POSITION, eq_num expects NUMBER
    p = ConditionVariable("p")
    formula = ExistsPosition(
        variables=[p], formula=Atom("eq_num", [FunctionCall("val", [p]), ConditionConstant("OOB")])
    )

    with pytest.raises(TypeError, match="must be Number, but got Position"):
        check_condition(formula, constants, functions, relations)


if __name__ == "__main__":
    pytest.main([__file__])
