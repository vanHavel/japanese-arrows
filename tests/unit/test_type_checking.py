import pytest

from japanese_arrows.rules import (
    Constant,
    Equality,
    ExistsNumber,
    ExistsPosition,
    ForAllPosition,
    FORule,
    FunctionCall,
    Not,
    Relation,
    SetVal,
    Variable,
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
        [Variable("p1"), Variable("p2")],
        Relation("eq_pos", [Variable("p1"), Variable("p2")]),
    )
    check_condition(f1, constants, functions, relations)

    # valid Not
    f2 = Not(f1)
    check_condition(f2, constants, functions, relations)

    # valid Equality (Position = Position)
    f3 = ExistsPosition([Variable("q1"), Variable("q2")], Equality(Variable("q1"), Variable("q2")))
    check_condition(f3, constants, functions, relations)


def test_invalid_relation_argument_type(
    type_context: tuple[dict[str, Type], dict[str, FunctionSignature], dict[str, RelationSignature]],
) -> None:
    constants, functions, relations = type_context

    # eq_pos expects (Position, Position), giving (Position, Number)
    f = ExistsPosition(
        [Variable("p")],
        ExistsNumber([Variable("n")], Relation("eq_pos", [Variable("p"), Variable("n")])),
    )
    with pytest.raises(TypeError, match="Argument 2 of 'eq_pos' must be Position"):
        check_condition(f, constants, functions, relations)


def test_equality_types(
    type_context: tuple[dict[str, Type], dict[str, FunctionSignature], dict[str, RelationSignature]],
) -> None:
    constants, functions, relations = type_context

    # Mismatch: Position = Number
    f_bad = ExistsPosition(
        [Variable("p")],
        ExistsNumber([Variable("n")], Equality(Variable("p"), Variable("n"))),
    )
    with pytest.raises(TypeError, match="Equality mismatch"):
        check_condition(f_bad, constants, functions, relations)


def test_undefined_variable(
    type_context: tuple[dict[str, Type], dict[str, FunctionSignature], dict[str, RelationSignature]],
) -> None:
    constants, functions, relations = type_context
    f = Relation("eq_pos", [Variable("undefined"), Variable("undefined")])
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
        [Variable("p")],
        ExistsNumber(
            [Variable("n")],
            Relation(">", [FunctionCall("row", [Variable("p")]), Variable("n")]),
        ),
    )
    check_condition(f, constants, functions, relations)


def test_constants_type_check(
    type_context: tuple[dict[str, Type], dict[str, FunctionSignature], dict[str, RelationSignature]],
) -> None:
    constants, functions, relations = type_context
    # OOB is Position, ZERO is Number

    # Valid: eq_pos(OOB, OOB)
    f1 = Relation("eq_pos", [Constant("OOB"), Constant("OOB")])
    check_condition(f1, constants, functions, relations)

    # Invalid: eq_pos(OOB, ZERO)
    f2 = Relation("eq_pos", [Constant("OOB"), Constant("ZERO")])
    with pytest.raises(TypeError, match="Argument 2 of 'eq_pos' must be Position"):
        check_condition(f2, constants, functions, relations)


def test_check_rule_valid(
    type_context: tuple[dict[str, Type], dict[str, FunctionSignature], dict[str, RelationSignature]],
) -> None:
    constants, functions, relations = type_context

    # Rule: Exists p (row(p) > ZERO) -> set(p, 5)
    # Condition
    p = Variable("p")
    cond = ExistsPosition(
        [p],
        Relation(">", [FunctionCall("row", [p]), Constant("ZERO")]),
    )

    # Conclusion
    # Variable p refers to the p in ExistsPosition
    concl = SetVal(Variable("p"), Constant(5))

    rule = FORule("test-rule", cond, [concl])
    check_rule(rule, constants, functions, relations)


def test_check_rule_undefined_variable_in_conclusion(
    type_context: tuple[dict[str, Type], dict[str, FunctionSignature], dict[str, RelationSignature]],
) -> None:
    constants, functions, relations = type_context

    # Rule: Exists p (...) -> set(q, 5)  -- q is undefined
    p = Variable("p")
    cond = ExistsPosition([p], Equality(p, p))  # dummy condition

    concl = SetVal(Variable("q"), Constant(5))
    rule = FORule("test-rule", cond, [concl])

    with pytest.raises(TypeError, match="Undefined variable: q"):
        check_rule(rule, constants, functions, relations)


def test_check_rule_type_mismatch_conclusion(
    type_context: tuple[dict[str, Type], dict[str, FunctionSignature], dict[str, RelationSignature]],
) -> None:
    constants, functions, relations = type_context

    # Rule: Exists p -> set(p, OOB) -- OOB is Position, set expects Number value
    p = Variable("p")
    cond = ExistsPosition([p], Equality(p, p))

    concl = SetVal(Variable("p"), Constant("OOB"))
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

    # Rule: Exists p -> set(p, val(p) + 1)
    # Note: Calculation wrapper for +
    # We need a Calculation object.

    p = Variable("p")

    # Let's test binding in condition:
    # Exists p, n (val(p) = n) -> set(p, n + 1)

    n = Variable("n")
    cond_bind = ExistsPosition([p], ExistsNumber([n], Relation("eq_num", [FunctionCall("val", [p]), n])))

    concl_calc = SetVal(Variable("p"), FunctionCall("+", [Variable("n"), Constant(1)]))

    rule = FORule("test-rule", cond_bind, [concl_calc])
    check_rule(rule, constants, functions, relations)


def test_check_rule_forall_scope_exclusion(
    type_context: tuple[dict[str, Type], dict[str, FunctionSignature], dict[str, RelationSignature]],
) -> None:
    constants, functions, relations = type_context

    # Rule: Exists p (ForAll q (p = q)) -> set(q, 5)
    # Variable q is bound by ForAll, so it should NOT be available in conclusion.
    # Rule: Exists p (ForAll q (p = q)) -> set(q, 5)
    # Variable q is bound by ForAll, so it should NOT be available in conclusion.
    p = Variable("p")
    q = Variable("q")

    cond = ExistsPosition([p], ForAllPosition([q], Equality(p, q)))

    concl = SetVal(Variable("q"), Constant(5))
    rule = FORule("test-rule", cond, [concl])

    with pytest.raises(TypeError, match="Undefined variable: q"):
        check_rule(rule, constants, functions, relations)

    # However, 'p' should still be available
    concl_p = SetVal(Variable("p"), Constant(5))
    rule_p = FORule("test-rule", cond, [concl_p])
    check_rule(rule_p, constants, functions, relations)


if __name__ == "__main__":
    pytest.main([__file__])
