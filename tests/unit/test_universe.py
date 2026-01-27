from typing import Any, Callable

from japanese_arrows.models import Type
from japanese_arrows.rules import (
    Constant,
    Equality,
    ExistsNumber,
    ExistsPosition,
    FunctionCall,
    Relation,
    Variable,
)
from japanese_arrows.universe import Universe


def test_universe_init() -> None:
    domain: dict[Type, set[Any]] = {
        Type.POSITION: {"p1", "p2"},
        Type.NUMBER: {1, 2, 3},
    }
    constants = {"MAX": 3}

    # Predicates on n-tuples
    def is_less(args: tuple[Any, ...]) -> bool:
        return bool(args[0] < args[1])

    relations: dict[str, Callable[[tuple[Any, ...]], bool]] = {"<": is_less}

    # n-ary functions
    def add_one(args: tuple[Any, ...]) -> int:
        return int(args[0] + 1)

    def val_func(args: tuple[Any, ...]) -> int:
        # Map p1->1, p2->2
        if args[0] == "p1":
            return 1
        return 2

    functions: dict[str, Callable[[tuple[Any, ...]], Any]] = {"add_one": add_one, "val": val_func}

    u = Universe(domain, constants, relations, functions)

    assert u.domain == domain
    assert u.constants == constants
    assert u.relations["<"] == is_less
    assert u.functions["add_one"] == add_one

    # Verify we can call them as expected
    assert u.relations["<"]((1, 2)) is True
    assert u.functions["add_one"]((1,)) == 2


def test_universe_check_simple() -> None:
    # Universe with p1=1, p2=2
    domain: dict[Type, set[Any]] = {Type.POSITION: {"p1", "p2"}, Type.NUMBER: {1, 2}}
    constants: dict[str, Any] = {}
    relations: dict[str, Callable[[tuple[Any, ...]], bool]] = {}  # none needed for equality

    def val_func(args: tuple[Any, ...]) -> int:
        if args[0] == "p1":
            return 1
        return 2

    functions: dict[str, Callable[[tuple[Any, ...]], Any]] = {"val": val_func}

    u = Universe(domain, constants, relations, functions)

    v_p = Variable("p")
    t_val_p = FunctionCall("val", [v_p])
    t_1 = Constant(1)

    formula = ExistsPosition([v_p], Equality(t_val_p, t_1))

    witness = u.check(formula)
    assert witness is not None
    assert witness["p"] == "p1"

    # exists p (val(p) = 3) -> Should return None
    t_3 = Constant(3)
    formula_false = ExistsPosition([v_p], Equality(t_val_p, t_3))
    assert u.check(formula_false) is None


def test_universe_check_relation() -> None:
    domain: dict[Type, set[Any]] = {Type.NUMBER: {1, 2, 3}}

    def is_less(args: tuple[Any, ...]) -> bool:
        return bool(args[0] < args[1])

    u = Universe(domain, {}, {"<": is_less}, {})

    # exists x, y (x < y)

    v_x = Variable("x")
    v_y = Variable("y")

    formula = ExistsNumber([v_x, v_y], Relation("<", [v_x, v_y]))

    witness = u.check(formula)
    assert witness is not None
    # Just need one valid pair
    x = witness["x"]
    y = witness["y"]
    assert x < y


def test_universe_quantifier_exclusions() -> None:
    # Domain includes "p1" and "OOB"
    domain: dict[Type, set[Any]] = {Type.POSITION: {"p1", "OOB"}}
    constants = {"OOB": "OOB"}

    # Exclude OOB from quantifiers
    exclusions = {Type.POSITION: {"OOB"}}

    u = Universe(domain, constants, {}, {}, quantifier_exclusions=exclusions)

    v_p = Variable("p")
    c_OOB = Constant("OOB")

    # exists p (p = OOB) -> should be false because OOB is excluded
    formula_false = ExistsPosition([v_p], Equality(v_p, c_OOB))
    assert u.check(formula_false) is None

    # exists p (p != OOB) -> should be true (p=p1)
    formula_true = ExistsPosition([v_p], Equality(v_p, Constant("p1")))

    witness = u.check(formula_true)
    assert witness is not None
    assert witness["p"] == "p1"
