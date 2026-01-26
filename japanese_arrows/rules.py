from abc import ABC
from dataclasses import dataclass
from typing import Any

# --- Terms ---


class Term(ABC):
    pass


@dataclass
class Variable(Term):
    name: str

    def __str__(self) -> str:
        return self.name


@dataclass
class Constant(Term):
    value: Any  # integers, "OOB", "nil", etc.

    def __str__(self) -> str:
        return str(self.value)


@dataclass
class FunctionCall(Term):
    name: str
    args: list[Term]

    def __str__(self) -> str:
        args_str = ", ".join(str(arg) for arg in self.args)
        return f"{self.name}({args_str})"


# --- Formulas (Uses Terms) ---


class Formula(ABC):
    pass


@dataclass
class Not(Formula):
    formula: Formula

    def __str__(self) -> str:
        return f"~({self.formula})"


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


@dataclass
class Equality(Atom):
    left: Term
    right: Term

    def __str__(self) -> str:
        return f"{self.left} = {self.right}"


@dataclass
class And(Formula):
    formulas: list[Formula]

    def __str__(self) -> str:
        return " ^ ".join(f"({f})" for f in self.formulas)


@dataclass
class Or(Formula):
    formulas: list[Formula]

    def __str__(self) -> str:
        return " v ".join(f"({f})" for f in self.formulas)


class Quantifier(Formula):
    pass


@dataclass
class ExistsPosition(Quantifier):
    variables: list[Variable]
    formula: Formula

    def __str__(self) -> str:
        vars_str = ", ".join(str(v) for v in self.variables)
        return f"exists_pos {vars_str} ({self.formula})"


@dataclass
class ExistsNumber(Quantifier):
    variables: list[Variable]
    formula: Formula

    def __str__(self) -> str:
        vars_str = ", ".join(str(v) for v in self.variables)
        return f"exists_num {vars_str} ({self.formula})"


@dataclass
class ForAllPosition(Quantifier):
    variables: list[Variable]
    formula: Formula

    def __str__(self) -> str:
        vars_str = ", ".join(str(v) for v in self.variables)
        return f"forall_pos {vars_str} ({self.formula})"


@dataclass
class ForAllNumber(Quantifier):
    variables: list[Variable]
    formula: Formula

    def __str__(self) -> str:
        vars_str = ", ".join(str(v) for v in self.variables)
        return f"forall_num {vars_str} ({self.formula})"


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
