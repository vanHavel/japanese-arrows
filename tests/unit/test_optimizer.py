# Copyright (C) 2026 Lukas Huwald
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import pytest

from japanese_arrows.optimizer import (
    eliminate_quantifiers_in_formula,
    find_equality_substitution,
    get_free_variables,
    minscope,
    optimize_rule,
    substitute_conclusion,
    substitute_formula,
    substitute_term,
)
from japanese_arrows.parser import RuleParser
from japanese_arrows.rules import (
    And,
    Conclusion,
    Constant,
    Equality,
    ExcludeVal,
    ExistsPosition,
    Formula,
    FORule,
    FunctionCall,
    OnlyVal,
    Relation,
    SetVal,
    Variable,
)


class TestSubstituteTerm:
    def test_substitute_variable_match(self) -> None:
        term = Variable("q")
        result = substitute_term(term, "q", FunctionCall("next", [Variable("p")]))
        assert isinstance(result, FunctionCall)
        assert result.name == "next"

    def test_substitute_variable_no_match(self) -> None:
        term = Variable("q")
        result = substitute_term(term, "x", Constant(1))
        assert isinstance(result, Variable)
        assert result.name == "q"

    def test_substitute_constant(self) -> None:
        term = Constant(5)
        result = substitute_term(term, "x", Variable("y"))
        assert isinstance(result, Constant)
        assert result.value == 5

    def test_substitute_in_function(self) -> None:
        term = FunctionCall("val", [Variable("q")])
        replacement = FunctionCall("next", [Variable("p")])
        result = substitute_term(term, "q", replacement)
        assert isinstance(result, FunctionCall)
        assert result.name == "val"
        assert isinstance(result.args[0], FunctionCall)
        assert result.args[0].name == "next"


class TestSubstituteFormula:
    def test_substitute_in_equality(self) -> None:
        formula = Equality(FunctionCall("val", [Variable("q")]), Constant("nil"))
        replacement = FunctionCall("next", [Variable("p")])
        result = substitute_formula(formula, "q", replacement)
        assert isinstance(result, Equality)
        assert isinstance(result.left, FunctionCall)
        inner_arg = result.left.args[0]
        assert isinstance(inner_arg, FunctionCall)
        assert inner_arg.name == "next"

    def test_substitute_in_and(self) -> None:
        formula = And(
            [
                Equality(Variable("q"), Constant(1)),
                Equality(Variable("r"), Constant(2)),
            ]
        )
        result = substitute_formula(formula, "q", Variable("x"))
        assert isinstance(result, And)
        assert len(result.formulas) == 2


class TestSubstituteConclusion:
    def test_substitute_in_setval(self) -> None:
        conclusion = SetVal(Variable("p"), Variable("q"))
        result = substitute_conclusion(conclusion, "q", FunctionCall("next", [Variable("p")]))
        assert isinstance(result, SetVal)
        assert isinstance(result.value, FunctionCall)
        assert result.value.name == "next"

    def test_substitute_in_excludeval(self) -> None:
        conclusion = ExcludeVal(Variable("p"), "=", Variable("q"))
        result = substitute_conclusion(conclusion, "q", Constant(5))
        assert isinstance(result, ExcludeVal)
        assert isinstance(result.value, Constant)

    def test_substitute_in_onlyval(self) -> None:
        conclusion = OnlyVal(Variable("p"), [Variable("q"), FunctionCall("+", [Variable("q"), Constant(1)])])
        replacement = FunctionCall("val", [Variable("r")])
        result = substitute_conclusion(conclusion, "q", replacement)
        assert isinstance(result, OnlyVal)
        assert len(result.values) == 2
        assert isinstance(result.values[0], FunctionCall)
        assert result.values[0].name == "val"


class TestFindEqualitySubstitution:
    def test_find_simple_equality_lhs(self) -> None:
        conjuncts: list[Formula] = [
            Equality(Variable("q"), FunctionCall("next", [Variable("p")])),
            Equality(FunctionCall("dir", [Variable("p")]), FunctionCall("dir", [Variable("q")])),
        ]
        result = find_equality_substitution(conjuncts, "q")
        assert result is not None
        assert isinstance(result, FunctionCall)
        assert result.name == "next"

    def test_find_simple_equality_rhs(self) -> None:
        conjuncts: list[Formula] = [
            Equality(FunctionCall("next", [Variable("p")]), Variable("q")),
        ]
        result = find_equality_substitution(conjuncts, "q")
        assert result is not None
        assert isinstance(result, FunctionCall)
        assert result.name == "next"

    def test_no_substitution_when_var_in_term(self) -> None:
        conjuncts: list[Formula] = [
            Equality(Variable("q"), FunctionCall("f", [Variable("q")])),
        ]
        result = find_equality_substitution(conjuncts, "q")
        assert result is None

    def test_no_substitution_when_no_equality(self) -> None:
        conjuncts: list[Formula] = [
            Relation("points_at", [Variable("p"), Variable("q")]),
        ]
        result = find_equality_substitution(conjuncts, "q")
        assert result is None


class TestQuantifierElimination:
    def test_basic_elimination(self) -> None:
        formula = ExistsPosition(
            [Variable("q"), Variable("p")],
            And(
                [
                    Relation("!=", [FunctionCall("val", [Variable("q")]), Constant("nil")]),
                    Equality(FunctionCall("next", [Variable("p")]), Variable("q")),
                    Equality(FunctionCall("dir", [Variable("p")]), FunctionCall("dir", [Variable("q")])),
                ]
            ),
        )
        conclusions: list[Conclusion] = [
            OnlyVal(
                Variable("p"),
                [
                    FunctionCall("val", [Variable("q")]),
                    FunctionCall("+", [FunctionCall("val", [Variable("q")]), Constant(1)]),
                ],
            ),
        ]

        new_formula, new_conclusions = eliminate_quantifiers_in_formula(formula, conclusions)

        assert "q" not in get_free_variables(new_formula)

        if isinstance(new_formula, ExistsPosition):
            var_names = [v.name for v in new_formula.variables]
            assert "q" not in var_names

        assert len(new_conclusions) == 1
        only_conclusion = new_conclusions[0]
        assert isinstance(only_conclusion, OnlyVal)

    def test_no_elimination_when_equality_negated(self) -> None:
        from japanese_arrows.rules import ExistsNumber, Not

        formula = ExistsPosition(
            [Variable("p")],
            ExistsNumber(
                [Variable("i")],
                And(
                    [
                        Not(Equality(FunctionCall("val", [Variable("p")]), Variable("i"))),
                        Relation("candidate", [Variable("p"), Variable("i")]),
                    ]
                ),
            ),
        )
        conclusions: list[Conclusion] = [ExcludeVal(Variable("p"), "=", Variable("i"))]

        new_formula, new_conclusions = eliminate_quantifiers_in_formula(formula, conclusions)

        if isinstance(new_formula, ExistsPosition):
            inner = new_formula.formula
            if isinstance(inner, ExistsNumber):
                var_names = [v.name for v in inner.variables]
                assert "i" in var_names, "Variable 'i' should NOT be eliminated when equality is negated"
        else:
            pytest.fail(f"Expected ExistsPosition, got {type(new_formula)}")

        conclusion = new_conclusions[0]
        assert isinstance(conclusion, ExcludeVal)
        conclusion_vars = get_free_variables(conclusion.value)
        assert "i" in conclusion_vars, "Conclusion should still reference 'i'"


class TestMinscope:
    def test_minscope_pushes_quantifier(self) -> None:
        formula = ExistsPosition(
            [Variable("p"), Variable("q")],
            And(
                [
                    Equality(FunctionCall("val", [Variable("p")]), Constant(1)),
                    Equality(FunctionCall("val", [Variable("q")]), Constant(2)),
                ]
            ),
        )
        result = minscope(formula)
        assert isinstance(result, And)
        assert len(result.formulas) == 2


class TestOptimizeRule:
    def test_next_arrow_same_direction_rule(self) -> None:
        parser = RuleParser("""
            exists q,p (
              val(q) != nil ^
              next(p) = q ^
              dir(p) = dir(q)
            )
        """)
        condition = parser.parse_formula()

        parser2 = RuleParser("only(p, [val(q), val(q)+1])")
        conclusions = [parser2.parse_conclusion()]

        rule = FORule(
            name="NEXT_ARROW_SAME_DIRECTION",
            condition=condition,
            conclusions=conclusions,
            complexity=2,
        )

        optimized = optimize_rule(rule)

        free_in_condition = get_free_variables(optimized.condition)
        assert "q" not in free_in_condition

        only_conclusion = optimized.conclusions[0]
        assert isinstance(only_conclusion, OnlyVal)

        def contains_next_p(term: object) -> bool:
            if isinstance(term, FunctionCall):
                if term.name == "next" and len(term.args) == 1:
                    if isinstance(term.args[0], Variable) and term.args[0].name == "p":
                        return True
                for arg in term.args:
                    if contains_next_p(arg):
                        return True
            return False

        has_next_p = any(contains_next_p(v) for v in only_conclusion.values)
        assert has_next_p, "Expected conclusion to contain next(p) after substitution"
