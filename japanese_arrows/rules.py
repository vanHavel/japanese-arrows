import itertools
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Iterator

from japanese_arrows.models import Type

if TYPE_CHECKING:
    from japanese_arrows.universe import Universe

# --- Terms ---


class Term(ABC):
    @abstractmethod
    def eval(self, universe: "Universe", assignment: dict[str, Any]) -> Any:
        pass


@dataclass
class Variable(Term):
    name: str

    def __str__(self) -> str:
        return self.name

    def eval(self, universe: "Universe", assignment: dict[str, Any]) -> Any:
        return assignment[self.name]


@dataclass
class Constant(Term):
    value: Any  # integers, "OOB", "nil", etc.

    def __str__(self) -> str:
        return str(self.value)

    def eval(self, universe: "Universe", assignment: dict[str, Any]) -> Any:
        if isinstance(self.value, str) and self.value in universe.constants:
            return universe.constants[self.value]
        return self.value


@dataclass
class FunctionCall(Term):
    name: str
    args: list[Term]

    def __str__(self) -> str:
        args_str = ", ".join(str(arg) for arg in self.args)
        return f"{self.name}({args_str})"

    def eval(self, universe: "Universe", assignment: dict[str, Any]) -> Any:
        if self.name == "+":
            op_left = self.args[0].eval(universe, assignment)
            op_right = self.args[1].eval(universe, assignment)
            if isinstance(op_left, int) and isinstance(op_right, int):
                return op_left + op_right
            return "nil"
        if self.name == "-":
            op_left = self.args[0].eval(universe, assignment)
            op_right = self.args[1].eval(universe, assignment)
            if isinstance(op_left, int) and isinstance(op_right, int):
                return op_left - op_right
            return "nil"

        if self.name not in universe.functions:
            raise ValueError(f"Unknown function: {self.name}")
        args_values = [arg.eval(universe, assignment) for arg in self.args]
        return universe.functions[self.name](tuple(args_values))


# --- Formulas (Uses Terms) ---


class Formula(ABC):
    @abstractmethod
    def check(self, universe: "Universe", assignment: dict[str, Any]) -> Iterator[dict[str, Any]]:
        pass


@dataclass
class Not(Formula):
    formula: Formula

    def __str__(self) -> str:
        return f"~({self.formula})"

    def check(self, universe: "Universe", assignment: dict[str, Any]) -> Iterator[dict[str, Any]]:
        first_inner = next(self.formula.check(universe, assignment), None)
        if first_inner is None:
            yield {}


class Atom(Formula):
    pass


@dataclass
class Relation(Atom):
    relation: str  # "<", ">", "points_at", etc. (excluding "=")
    args: list[Term]

    def __str__(self) -> str:
        if len(self.args) == 2:
            # Infix notation for binary relations
            return f"{self.args[0]} {self.relation} {self.args[1]}"
        args_str = ", ".join(str(arg) for arg in self.args)
        return f"{self.relation}({args_str})"

    def check(self, universe: "Universe", assignment: dict[str, Any]) -> Iterator[dict[str, Any]]:
        args_values = [arg.eval(universe, assignment) for arg in self.args]
        if self.relation not in universe.relations:
            raise ValueError(f"Unknown relation: {self.relation}")

        is_true = universe.relations[self.relation](tuple(args_values))
        if is_true:
            yield {}


@dataclass
class Equality(Atom):
    left: Term
    right: Term

    def __str__(self) -> str:
        return f"{self.left} = {self.right}"

    def check(self, universe: "Universe", assignment: dict[str, Any]) -> Iterator[dict[str, Any]]:
        left = self.left.eval(universe, assignment)
        right = self.right.eval(universe, assignment)
        if left == right:
            yield {}


@dataclass
class And(Formula):
    formulas: list[Formula]

    def __str__(self) -> str:
        return " ^ ".join(f"({f})" for f in self.formulas)

    def check(self, universe: "Universe", assignment: dict[str, Any]) -> Iterator[dict[str, Any]]:
        return self._check_recursive(universe, self.formulas, assignment, {})

    def _check_recursive(
        self, universe: "Universe", formulas: list[Formula], assignment: dict[str, Any], combined: dict[str, Any]
    ) -> Iterator[dict[str, Any]]:
        if not formulas:
            yield combined
            return

        first, *rest = formulas
        for w in first.check(universe, assignment):
            yield from self._check_recursive(universe, rest, assignment, combined | w)


@dataclass
class Or(Formula):
    formulas: list[Formula]

    def __str__(self) -> str:
        return " v ".join(f"({f})" for f in self.formulas)

    def check(self, universe: "Universe", assignment: dict[str, Any]) -> Iterator[dict[str, Any]]:
        for sub in self.formulas:
            yield from sub.check(universe, assignment)


class Quantifier(Formula):
    pass


@dataclass
class ExistsPosition(Quantifier):
    variables: list[Variable]
    formula: Formula

    def __str__(self) -> str:
        vars_str = ", ".join(str(v) for v in self.variables)
        return f"exists_pos {vars_str} ({self.formula})"

    def check(self, universe: "Universe", assignment: dict[str, Any]) -> Iterator[dict[str, Any]]:
        domain_type = Type.POSITION
        elements = universe.domain.get(domain_type, set())
        if universe.quantifier_exclusions and domain_type in universe.quantifier_exclusions:
            elements = elements - universe.quantifier_exclusions[domain_type]

        names = [v.name for v in self.variables]
        try:
            for values in itertools.product(elements, repeat=len(self.variables)):
                current_witness: dict[str, Any] = {}
                for name, val in zip(names, values):
                    assignment[name] = val
                    current_witness[name] = val

                for inner_witness in self.formula.check(universe, assignment):
                    yield current_witness | inner_witness
        finally:
            for name in names:
                if name in assignment:
                    del assignment[name]


@dataclass
class ExistsNumber(Quantifier):
    variables: list[Variable]
    formula: Formula

    def __str__(self) -> str:
        vars_str = ", ".join(str(v) for v in self.variables)
        return f"exists_num {vars_str} ({self.formula})"

    def check(self, universe: "Universe", assignment: dict[str, Any]) -> Iterator[dict[str, Any]]:
        domain_type = Type.NUMBER
        elements = universe.domain.get(domain_type, set())
        if universe.quantifier_exclusions and domain_type in universe.quantifier_exclusions:
            elements = elements - universe.quantifier_exclusions[domain_type]

        names = [v.name for v in self.variables]
        try:
            for values in itertools.product(elements, repeat=len(self.variables)):
                current_witness: dict[str, Any] = {}
                for name, val in zip(names, values):
                    assignment[name] = val
                    current_witness[name] = val

                for inner_witness in self.formula.check(universe, assignment):
                    yield current_witness | inner_witness
        finally:
            for name in names:
                if name in assignment:
                    del assignment[name]


@dataclass
class ForAllPosition(Quantifier):
    variables: list[Variable]
    formula: Formula

    def __str__(self) -> str:
        vars_str = ", ".join(str(v) for v in self.variables)
        return f"forall_pos {vars_str} ({self.formula})"

    def check(self, universe: "Universe", assignment: dict[str, Any]) -> Iterator[dict[str, Any]]:
        domain_type = Type.POSITION
        elements = universe.domain.get(domain_type, set())
        if universe.quantifier_exclusions and domain_type in universe.quantifier_exclusions:
            elements = elements - universe.quantifier_exclusions[domain_type]

        names = [v.name for v in self.variables]
        try:
            for values in itertools.product(elements, repeat=len(self.variables)):
                for name, val in zip(names, values):
                    assignment[name] = val

                first_inner = next(self.formula.check(universe, assignment), None)
                if first_inner is None:
                    return
        finally:
            for name in names:
                if name in assignment:
                    del assignment[name]

        yield {}


@dataclass
class ForAllNumber(Quantifier):
    variables: list[Variable]
    formula: Formula

    def __str__(self) -> str:
        vars_str = ", ".join(str(v) for v in self.variables)
        return f"forall_num {vars_str} ({self.formula})"

    def check(self, universe: "Universe", assignment: dict[str, Any]) -> Iterator[dict[str, Any]]:
        domain_type = Type.NUMBER
        elements = universe.domain.get(domain_type, set())
        if universe.quantifier_exclusions and domain_type in universe.quantifier_exclusions:
            elements = elements - universe.quantifier_exclusions[domain_type]

        names = [v.name for v in self.variables]
        try:
            for values in itertools.product(elements, repeat=len(self.variables)):
                for name, val in zip(names, values):
                    assignment[name] = val

                first_inner = next(self.formula.check(universe, assignment), None)
                if first_inner is None:
                    return
        finally:
            for name in names:
                if name in assignment:
                    del assignment[name]

        yield {}


# --- Conclusions (Uses Terms) ---


class Conclusion(ABC):
    position: Term


@dataclass
class SetVal(Conclusion):
    position: Term
    value: Term

    def __str__(self) -> str:
        return f"set({self.position}, {self.value})"


@dataclass
class ExcludeVal(Conclusion):
    position: Term
    operator: str
    value: Term

    def __str__(self) -> str:
        if self.operator == "=":
            return f"exclude({self.position}, {self.value})"
        return f"exclude({self.position}, {self.operator}{self.value})"


@dataclass
class OnlyVal(Conclusion):
    position: Term
    values: list[Term]

    def __str__(self) -> str:
        vals = ", ".join(str(v) for v in self.values)
        return f"only({self.position}, [{vals}])"


# --- Rule ---


class Rule(ABC):
    name: str
    complexity: int


@dataclass
class FORule(Rule):
    name: str
    condition: Formula
    conclusions: list[Conclusion]
    complexity: int = 1

    def __str__(self) -> str:
        conclusions_str = "\n    - ".join(str(c) for c in self.conclusions)
        return (
            f"FORule {self.name}:\n"
            f"  Condition: {self.condition}\n"
            f"  Complexity: {self.complexity}\n"
            f"  Conclusions:\n    - {conclusions_str}"
        )


@dataclass
class BacktrackRule(Rule):
    name: str
    complexity: int
    backtrack_depth: int
    rule_depth: int
    max_rule_complexity: int

    def __str__(self) -> str:
        return (
            f"BacktrackRule {self.name}:\n"
            f"  Complexity: {self.complexity}\n"
            f"  Backtrack Depth: {self.backtrack_depth}\n"
            f"  Rule Depth: {self.rule_depth}\n"
            f"  Max Rule Complexity: {self.max_rule_complexity}"
        )
