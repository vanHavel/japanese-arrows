# mypy: disable-error-code="attr-defined"
import itertools
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Callable

from japanese_arrows.rules import (
    And,
    Constant,
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
    Term,
    Variable,
)
from japanese_arrows.type_checking import Type


@dataclass
class Universe:
    domain: dict[Type, set[Any]]
    constants: dict[str, Any]
    relations: dict[str, Callable[[tuple[Any, ...]], bool]]
    functions: dict[str, Callable[[tuple[Any, ...]], Any]]
    quantifier_exclusions: dict[Type, set[Any]] | None = None

    def __post_init__(self) -> None:
        if self.quantifier_exclusions is None:
            self.quantifier_exclusions = {}

    def check(self, phi: Formula) -> dict[str, Any] | None:
        """
        Checks if the sentence phi is true in the universe.
        If true, returns a witness assignment for the existential prefix.
        If false, returns None.
        """
        return next(self._check_all(phi, {}), None)

    def check_all(self, phi: Formula) -> Iterator[dict[str, Any]]:
        """
        Returns a generator yielding all witness assignments for which phi is true.
        """
        return self._check_all(phi, {})

    def _check_all(self, phi: Formula, assignment: dict[str, Any]) -> Iterator[dict[str, Any]]:
        match type(phi):
            case t if t is And:
                yield from self._check_and(phi.formulas, assignment, {})

            case t if t is Or:
                for sub in phi.formulas:
                    yield from self._check_all(sub, assignment)

            case t if t is Not:
                first_inner = next(self._check_all(phi.formula, assignment), None)
                if first_inner is None:
                    yield {}

            case t if t is ExistsPosition or t is ExistsNumber:
                domain_type = Type.POSITION if t is ExistsPosition else Type.NUMBER
                elements = self.domain.get(domain_type, set())
                if self.quantifier_exclusions and domain_type in self.quantifier_exclusions:
                    elements = elements - self.quantifier_exclusions[domain_type]

                vars = phi.variables
                names = [v.name for v in vars]

                for values in itertools.product(elements, repeat=len(vars)):
                    new_assignment = assignment.copy()
                    current_witness: dict[str, Any] = {}
                    for name, val in zip(names, values):
                        new_assignment[name] = val
                        current_witness[name] = val

                    for inner_witness in self._check_all(phi.formula, new_assignment):
                        yield current_witness | inner_witness

            case t if t is ForAllPosition or t is ForAllNumber:
                domain_type = Type.POSITION if t is ForAllPosition else Type.NUMBER
                elements = self.domain.get(domain_type, set())
                if self.quantifier_exclusions and domain_type in self.quantifier_exclusions:
                    elements = elements - self.quantifier_exclusions[domain_type]

                vars = phi.variables
                names = [v.name for v in vars]

                for values in itertools.product(elements, repeat=len(vars)):
                    new_assignment = assignment.copy()
                    for name, val in zip(names, values):
                        new_assignment[name] = val

                    first_inner = next(self._check_all(phi.formula, new_assignment), None)
                    if first_inner is None:
                        return

                yield {}

            case t if t is Relation:
                args_values = [self.eval_term(arg, assignment) for arg in phi.args]
                if phi.relation not in self.relations:
                    raise ValueError(f"Unknown relation: {phi.relation}")

                is_true = self.relations[phi.relation](tuple(args_values))
                if is_true:
                    yield {}

            case t if t is Equality:
                left = self.eval_term(phi.left, assignment)
                right = self.eval_term(phi.right, assignment)
                if left == right:
                    yield {}

            case t:
                raise ValueError(f"Unknown formula type: {t}")

    def _check_and(
        self, formulas: list[Formula], assignment: dict[str, Any], combined: dict[str, Any]
    ) -> Iterator[dict[str, Any]]:
        """Helper to yield all witness combinations for AND formulas."""
        if not formulas:
            yield combined
            return

        first, *rest = formulas
        for w in self._check_all(first, assignment):
            yield from self._check_and(rest, assignment, combined | w)

    def eval_term(self, term: Term, assignment: dict[str, Any]) -> Any:
        match type(term):
            case t if t is Variable:
                if term.name not in assignment:
                    raise KeyError(f"Variable {term.name} not in assignment")
                return assignment[term.name]

            case t if t is Constant:
                if type(term.value) is str and term.value in self.constants:
                    return self.constants[term.value]
                return term.value

            case t if t is FunctionCall:
                # Handle arithmetic built-ins
                if term.name == "+":
                    op_left = self.eval_term(term.args[0], assignment)
                    op_right = self.eval_term(term.args[1], assignment)
                    if type(op_left) is int and type(op_right) is int:
                        return op_left + op_right
                    return "nil"
                if term.name == "-":
                    op_left = self.eval_term(term.args[0], assignment)
                    op_right = self.eval_term(term.args[1], assignment)
                    if type(op_left) is int and type(op_right) is int:
                        return op_left - op_right
                    return "nil"

                if term.name not in self.functions:
                    raise ValueError(f"Unknown function: {term.name}")
                args_values = [self.eval_term(arg, assignment) for arg in term.args]
                return self.functions[term.name](tuple(args_values))

            case t:
                raise ValueError(f"Unknown term type: {t}")
