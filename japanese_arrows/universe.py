# mypy: disable-error-code="attr-defined"
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Callable

from japanese_arrows.rules import (
    Formula,
    Term,
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
        return phi.check(self, assignment)

    def eval_term(self, term: Term, assignment: dict[str, Any]) -> Any:
        return term.eval(self, assignment)
