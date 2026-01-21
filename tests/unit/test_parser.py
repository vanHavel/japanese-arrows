import pytest

from japanese_arrows.parser import parse_rule, tokenize
from japanese_arrows.rules import (
    And,
    Calculation,
    Equality,
    ExcludeVal,
    ExistsNumber,
    ExistsPosition,
    FunctionCall,
    Not,
    OnlyVal,
    Or,
    Relation,
    SetVal,
)


def test_tokenize() -> None:
    text = "TEST_RULE: exists p (points_at(p, q))"
    tokens = tokenize(text)
    assert len(tokens) == 12
    assert tokens[0].type == "IDENTIFIER"
    assert tokens[0].value == "TEST_RULE"
    assert tokens[1].type == "COLON"
    assert tokens[2].type == "EXISTS"


def test_parse_simple_relation() -> None:
    text = "TEST: points_at(p, q) => set(p, 1)"
    rule = parse_rule(text)
    assert rule.name == "TEST"

    # Implicitly a Relation atom in condition?
    # Actually design says Rules are Condition \n => Conclusion
    # But for "points_at(p, q)" as a condition, it's a Relation.

    assert isinstance(rule.condition, Relation)
    assert rule.condition.relation == "points_at"
    assert len(rule.condition.args) == 2
    assert str(rule.condition.args[0]) == "p"
    assert str(rule.condition.args[1]) == "q"

    assert len(rule.conclusions) == 1
    c = rule.conclusions[0]
    assert isinstance(c, SetVal)
    assert str(c.position) == "p"
    assert str(c.value) == "1"


def test_parse_quantifiers() -> None:
    text = "TEST: exists p,i (val(p) = i) => set(p, i)"
    rule = parse_rule(text)

    # p is Position, i is Number
    # Should be ExistsPos([p], ExistsNum([i], Equality...))

    assert isinstance(rule.condition, ExistsPosition)
    assert len(rule.condition.variables) == 1
    assert rule.condition.variables[0].name == "p"

    assert isinstance(rule.condition, ExistsPosition)
    inner = rule.condition.formula
    assert isinstance(inner, ExistsNumber)
    assert len(inner.variables) == 1
    assert inner.variables[0].name == "i"

    eq = inner.formula
    assert isinstance(eq, Equality)


def test_parse_grouped_quantifiers_same_type() -> None:
    text = "TEST: exists p,q (p = q) => set(p, 0)"
    rule = parse_rule(text)

    assert isinstance(rule.condition, ExistsPosition)
    assert len(rule.condition.variables) == 2
    assert rule.condition.variables[0].name == "p"
    assert rule.condition.variables[1].name == "q"


def test_parse_logic_operators() -> None:
    text = "TEST: exists p ((ahead(p) = 0) ^ (val(p) = 1)) => set(p, 1)"
    rule = parse_rule(text)

    assert isinstance(rule.condition, ExistsPosition)
    inner = rule.condition.formula
    assert isinstance(inner, And)
    assert len(inner.formulas) == 2


def test_parse_implication_desugar() -> None:
    text = "TEST: exists p,q (points_at(p,q) -> val(p)=val(q)) => set(p, 0)"
    rule = parse_rule(text)

    # points_at -> val=val  ==>  !points_at v val=val

    assert isinstance(rule.condition, ExistsPosition)
    inner = rule.condition.formula
    assert isinstance(inner, Or)
    assert len(inner.formulas) == 2
    assert isinstance(inner.formulas[0], Not)
    # inner.formulas[1] is Equality


def test_complex_conclusions() -> None:
    # exclude(p, >i)
    # only(p, [1, 2, i])
    # set(p, i+1)

    text = """
    TEST: exists p,i (val(p) = i)
    => exclude(p, >i)
    => only(p, [1, 2, i])
    => set(p, i+1)
    """
    rule = parse_rule(text)

    assert len(rule.conclusions) == 3

    c1 = rule.conclusions[0]
    assert isinstance(c1, ExcludeVal)
    assert c1.operator == ">"
    assert str(c1.value) == "i"

    c2 = rule.conclusions[1]
    assert isinstance(c2, OnlyVal)
    assert len(c2.values) == 3
    assert str(c2.values[0]) == "1"
    assert str(c2.values[2]) == "i"

    c3 = rule.conclusions[2]
    assert isinstance(c3, SetVal)
    assert isinstance(c3.value, Calculation)
    assert c3.value.operator == "+"
    assert str(c3.value.left) == "i"
    assert str(c3.value.right) == "1"


def test_complex_condition_terms() -> None:
    # next(next(p)) = q
    text = "TEST: exists p,q (next(next(p)) = q) => set(p, 0)"
    rule = parse_rule(text)

    assert isinstance(rule.condition, ExistsPosition)
    inner = rule.condition.formula
    assert isinstance(inner, Equality)

    left = inner.left
    assert isinstance(left, FunctionCall)
    assert left.name == "next"
    assert len(left.args) == 1

    inner_arg = left.args[0]
    assert isinstance(inner_arg, FunctionCall)
    assert inner_arg.name == "next"
    assert str(inner_arg.args[0]) == "p"


def test_neq_sugar() -> None:
    text = "TEST: exists p,q (p != q) => set(p, 0)"
    rule = parse_rule(text)

    assert isinstance(rule.condition, ExistsPosition)
    inner = rule.condition.formula
    # p != q  ==>  !(p = q)
    assert isinstance(inner, Not)
    assert isinstance(inner.formula, Equality)


def test_parse_rule_name() -> None:
    text = "INFER-TOWER: exists p (ahead(p) = 0) => set(p, 0)"
    rule = parse_rule(text)
    assert rule.name == "INFER-TOWER"
    assert isinstance(rule.condition, ExistsPosition)


def test_parse_rule_missing_name_error() -> None:
    text = "exists p (ahead(p) = 0) => set(p, 0)"
    with pytest.raises(ValueError):
        parse_rule(text)
