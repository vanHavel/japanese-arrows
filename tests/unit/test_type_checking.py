import pytest

from japanese_arrows.rules import (
    Calculation,
    ConclusionConstant,
    ConclusionVariable,
    ConditionConstant,
    ConditionVariable,
    Equality,
    ExistsNumber,
    ExistsPosition,
    ForAllPosition,
    FORule,
    FunctionCall,
    Not,
    Relation,
    SetVal,
)
from japanese_arrows.type_checking import FunctionSignature, RelationSignature, Type, check_condition, check_rule


@pytest.fixture
def type_context() -> tuple[dict[str, Type], dict[str, FunctionSignature], dict[str, RelationSignature]]:
    constants = {
        "OOB": Type.POSITION,
        "ZERO": Type.NUMBER,
        "nil": Type.NUMBER,  # Used in examples
    }
    functions = {
        "add": ([Type.NUMBER, Type.NUMBER], Type.NUMBER),
        "row": ([Type.POSITION], Type.NUMBER),
        "val": ([Type.POSITION], Type.NUMBER),
    }
    relations = {
        "eq_pos": [Type.POSITION, Type.POSITION],
        "eq_num": [Type.NUMBER, Type.NUMBER],
        "points_at": [Type.POSITION, Type.DIRECTION, Type.POSITION],
        ">": [Type.NUMBER, Type.NUMBER],
    }
    return constants, functions, relations


def test_valid_formulas(
    type_context: tuple[dict[str, Type], dict[str, FunctionSignature], dict[str, RelationSignature]],
) -> None:
    constants, functions, relations = type_context

    # Valid Relation
    # points_at(p1, d1, p2) - assuming we had valid variables or constants
    # Using constants for simplicity in basic test since variables need Quantifiers
    # We don't have DIRECTION constants in the fixture yet, let's add one locally or mock
    # Actually, let's use relations we have fully defined constants for or wrapped in quantifiers

    # Exists p1, p2: eq_pos(p1, p2)
    f1 = ExistsPosition(
        [ConditionVariable("p1"), ConditionVariable("p2")],
        Relation("eq_pos", [ConditionVariable("p1"), ConditionVariable("p2")]),
    )
    check_condition(f1, constants, functions, relations)

    # valid Not
    f2 = Not(f1)
    check_condition(f2, constants, functions, relations)

    # valid Equality (Position = Position)
    f3 = ExistsPosition(
        [ConditionVariable("q1"), ConditionVariable("q2")], Equality(ConditionVariable("q1"), ConditionVariable("q2"))
    )
    check_condition(f3, constants, functions, relations)


def test_invalid_relation_argument_type(
    type_context: tuple[dict[str, Type], dict[str, FunctionSignature], dict[str, RelationSignature]],
) -> None:
    constants, functions, relations = type_context

    # eq_pos expects (Position, Position), giving (Position, Number)
    f = ExistsPosition(
        [ConditionVariable("p")],
        ExistsNumber([ConditionVariable("n")], Relation("eq_pos", [ConditionVariable("p"), ConditionVariable("n")])),
    )
    with pytest.raises(TypeError, match="Argument 2 of 'eq_pos' must be Position"):
        check_condition(f, constants, functions, relations)


def test_equality_types(
    type_context: tuple[dict[str, Type], dict[str, FunctionSignature], dict[str, RelationSignature]],
) -> None:
    constants, functions, relations = type_context

    # Mismatch: Position = Number
    f_bad = ExistsPosition(
        [ConditionVariable("p")],
        ExistsNumber([ConditionVariable("n")], Equality(ConditionVariable("p"), ConditionVariable("n"))),
    )
    with pytest.raises(TypeError, match="Equality mismatch"):
        check_condition(f_bad, constants, functions, relations)


def test_undefined_variable(
    type_context: tuple[dict[str, Type], dict[str, FunctionSignature], dict[str, RelationSignature]],
) -> None:
    constants, functions, relations = type_context
    f = Relation("eq_pos", [ConditionVariable("undefined"), ConditionVariable("undefined")])
    with pytest.raises(TypeError, match="Undefined variable: undefined"):
        check_condition(f, constants, functions, relations)


def test_nested_quantifiers(
    type_context: tuple[dict[str, Type], dict[str, FunctionSignature], dict[str, RelationSignature]],
) -> None:
    constants, functions, relations = type_context

    # ForAll p: (Exists n: row(p) > n)
    # > is (Number, Number)
    # row(p) is Number
    # n is Number
    f = ForAllPosition(
        [ConditionVariable("p")],
        ExistsNumber(
            [ConditionVariable("n")],
            Relation(">", [FunctionCall("row", [ConditionVariable("p")]), ConditionVariable("n")]),
        ),
    )
    check_condition(f, constants, functions, relations)


def test_constants_type_check(
    type_context: tuple[dict[str, Type], dict[str, FunctionSignature], dict[str, RelationSignature]],
) -> None:
    constants, functions, relations = type_context
    # OOB is Position, ZERO is Number

    # Valid: eq_pos(OOB, OOB)
    f1 = Relation("eq_pos", [ConditionConstant("OOB"), ConditionConstant("OOB")])
    check_condition(f1, constants, functions, relations)

    # Invalid: eq_pos(OOB, ZERO)
    f2 = Relation("eq_pos", [ConditionConstant("OOB"), ConditionConstant("ZERO")])
    with pytest.raises(TypeError, match="Argument 2 of 'eq_pos' must be Position"):
        check_condition(f2, constants, functions, relations)


def test_check_rule_valid(
    type_context: tuple[dict[str, Type], dict[str, FunctionSignature], dict[str, RelationSignature]],
) -> None:
    constants, functions, relations = type_context

    # Rule: Exists p (row(p) > ZERO) -> set(p, 5)
    # Condition
    p = ConditionVariable("p")
    cond = ExistsPosition(
        [p],
        Relation(">", [FunctionCall("row", [p]), ConditionConstant("ZERO")]),
    )

    # Conclusion
    # Variable p refers to the p in ExistsPosition
    concl = SetVal(ConclusionVariable("p"), ConclusionConstant(5))

    rule = FORule("test-rule", cond, [concl])
    check_rule(rule, constants, functions, relations)


def test_check_rule_undefined_variable_in_conclusion(
    type_context: tuple[dict[str, Type], dict[str, FunctionSignature], dict[str, RelationSignature]],
) -> None:
    constants, functions, relations = type_context

    # Rule: Exists p (...) -> set(q, 5)  -- q is undefined
    p = ConditionVariable("p")
    cond = ExistsPosition([p], Equality(p, p))  # dummy condition

    concl = SetVal(ConclusionVariable("q"), ConclusionConstant(5))
    rule = FORule("test-rule", cond, [concl])

    with pytest.raises(TypeError, match="Undefined variable in conclusion: q"):
        check_rule(rule, constants, functions, relations)


def test_check_rule_type_mismatch_conclusion(
    type_context: tuple[dict[str, Type], dict[str, FunctionSignature], dict[str, RelationSignature]],
) -> None:
    constants, functions, relations = type_context

    # Rule: Exists p -> set(p, OOB) -- OOB is Position, set expects Number value
    p = ConditionVariable("p")
    cond = ExistsPosition([p], Equality(p, p))

    concl = SetVal(ConclusionVariable("p"), ConclusionConstant("OOB"))
    rule = FORule("test-rule", cond, [concl])

    with pytest.raises(TypeError, match="SetVal value must be Number, got Position"):
        check_rule(rule, constants, functions, relations)


def test_check_rule_calculation_conclusion(
    type_context: tuple[dict[str, Type], dict[str, FunctionSignature], dict[str, RelationSignature]],
) -> None:
    constants, functions, relations = type_context

    # Rule: Exists p -> set(p, val(p) + 1)
    # Note: Calculation wrapper for +
    # We need a Calculation object.

    p = ConditionVariable("p")

    # Let's test binding in condition:
    # Exists p, n (val(p) = n) -> set(p, n + 1)

    n = ConditionVariable("n")
    cond_bind = ExistsPosition([p], ExistsNumber([n], Relation("eq_num", [FunctionCall("val", [p]), n])))

    concl_calc = SetVal(ConclusionVariable("p"), Calculation("+", ConclusionVariable("n"), ConclusionConstant(1)))

    rule = FORule("test-rule", cond_bind, [concl_calc])
    check_rule(rule, constants, functions, relations)


def test_check_rule_forall_scope_exclusion(
    type_context: tuple[dict[str, Type], dict[str, FunctionSignature], dict[str, RelationSignature]],
) -> None:
    constants, functions, relations = type_context

    # Rule: Exists p (ForAll q (p = q)) -> set(q, 5)
    # Variable q is bound by ForAll, so it should NOT be available in conclusion.
    p = ConditionVariable("p")
    q = ConditionVariable("q")

    cond = ExistsPosition([p], ForAllPosition([q], Equality(p, q)))

    concl = SetVal(ConclusionVariable("q"), ConclusionConstant(5))
    rule = FORule("test-rule", cond, [concl])

    with pytest.raises(TypeError, match="Undefined variable in conclusion: q"):
        check_rule(rule, constants, functions, relations)

    # However, 'p' should still be available
    concl_p = SetVal(ConclusionVariable("p"), ConclusionConstant(5))
    rule_p = FORule("test-rule", cond, [concl_p])
    check_rule(rule_p, constants, functions, relations)


if __name__ == "__main__":
    pytest.main([__file__])
