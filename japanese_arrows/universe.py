import itertools
from dataclasses import dataclass
from typing import Any, Callable

from japanese_arrows.rules import (
    And,
    ConditionConstant,
    ConditionTerm,
    ConditionVariable,
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
        return self._check(phi, {})

    def _check(self, phi: Formula, assignment: dict[str, Any]) -> dict[str, Any] | None:
        if isinstance(phi, And):
            combined_witness: dict[str, Any] = {}
            for sub in phi.formulas:
                w = self._check(sub, assignment)
                if w is None:
                    return None
                combined_witness.update(w)
            return combined_witness

        elif isinstance(phi, Or):
            for sub in phi.formulas:
                w = self._check(sub, assignment)
                if w is not None:
                    return w
            return None

        elif isinstance(phi, Not):
            w = self._check(phi.formula, assignment)
            if w is None:
                return {}
            return None

        elif isinstance(phi, (ExistsPosition, ExistsNumber)):
            domain_type = Type.POSITION if isinstance(phi, ExistsPosition) else Type.NUMBER
            elements = self.domain.get(domain_type, set())
            if self.quantifier_exclusions and domain_type in self.quantifier_exclusions:
                elements = elements - self.quantifier_exclusions[domain_type]

            vars = phi.variables
            names = [v.name for v in vars]

            for values in itertools.product(elements, repeat=len(vars)):
                new_assignment = assignment.copy()
                current_witness = {}
                for name, val in zip(names, values):
                    new_assignment[name] = val
                    current_witness[name] = val

                inner_witness = self._check(phi.formula, new_assignment)
                if inner_witness is not None:
                    return current_witness | inner_witness

            return None

        elif isinstance(phi, (ForAllPosition, ForAllNumber)):
            domain_type = Type.POSITION if isinstance(phi, ForAllPosition) else Type.NUMBER
            elements = self.domain.get(domain_type, set())
            if self.quantifier_exclusions and domain_type in self.quantifier_exclusions:
                elements = elements - self.quantifier_exclusions[domain_type]

            vars = phi.variables
            names = [v.name for v in vars]

            for values in itertools.product(elements, repeat=len(vars)):
                new_assignment = assignment.copy()
                for name, val in zip(names, values):
                    new_assignment[name] = val

                if self._check(phi.formula, new_assignment) is None:
                    return None

            return {}

        elif isinstance(phi, Relation):
            args_values = [self._eval_term(arg, assignment) for arg in phi.args]
            if phi.relation not in self.relations:
                raise ValueError(f"Unknown relation: {phi.relation}")

            is_true = self.relations[phi.relation](tuple(args_values))
            return {} if is_true else None

        elif isinstance(phi, Equality):
            left = self._eval_term(phi.left, assignment)
            right = self._eval_term(phi.right, assignment)
            return {} if left == right else None

        else:
            raise ValueError(f"Unknown formula type: {type(phi)}")

    def _eval_term(self, term: ConditionTerm, assignment: dict[str, Any]) -> Any:
        if isinstance(term, ConditionVariable):
            if term.name not in assignment:
                raise KeyError(f"Variable {term.name} not in assignment")
            return assignment[term.name]

        elif isinstance(term, ConditionConstant):
            if isinstance(term.value, str) and term.value in self.constants:
                return self.constants[term.value]
            return term.value

        elif isinstance(term, FunctionCall):
            if term.name not in self.functions:
                raise ValueError(f"Unknown function: {term.name}")
            args_values = [self._eval_term(arg, assignment) for arg in term.args]
            return self.functions[term.name](tuple(args_values))

        raise ValueError(f"Unknown term type: {type(term)}")
