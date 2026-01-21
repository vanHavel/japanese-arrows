from abc import ABC
from dataclasses import dataclass
from typing import Any

# --- Condition Terms (LHS) ---


class ConditionTerm(ABC):
    pass


@dataclass
class ConditionVariable(ConditionTerm):
    name: str

    def __str__(self) -> str:
        return self.name


@dataclass
class ConditionConstant(ConditionTerm):
    value: Any  # integers, "OOB", "nil", etc.

    def __str__(self) -> str:
        return str(self.value)


@dataclass
class FunctionCall(ConditionTerm):
    name: str
    args: list[ConditionTerm]

    def __str__(self) -> str:
        args_str = ", ".join(str(arg) for arg in self.args)
        return f"{self.name}({args_str})"


# --- Conclusion Terms (RHS) ---


class ConclusionTerm(ABC):
    pass


@dataclass
class ConclusionVariable(ConclusionTerm):
    name: str

    def __str__(self) -> str:
        return self.name


@dataclass
class ConclusionConstant(ConclusionTerm):
    value: Any

    def __str__(self) -> str:
        return str(self.value)


@dataclass
class Calculation(ConclusionTerm):
    operator: str  # "+", "-"
    left: ConclusionTerm
    right: ConclusionTerm

    def __str__(self) -> str:
        return f"({self.left} {self.operator} {self.right})"


# --- Formulas (Uses ConditionTerms) ---


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
    args: list[ConditionTerm]

    def __str__(self) -> str:
        if len(self.args) == 2:
            # Infix notation for binary relations
            return f"{self.args[0]} {self.relation} {self.args[1]}"
        args_str = ", ".join(str(arg) for arg in self.args)
        return f"{self.relation}({args_str})"


@dataclass
class Equality(Atom):
    left: ConditionTerm
    right: ConditionTerm

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
    variables: list[ConditionVariable]
    formula: Formula

    def __str__(self) -> str:
        vars_str = ", ".join(str(v) for v in self.variables)
        return f"exists_pos {vars_str} ({self.formula})"


@dataclass
class ExistsNumber(Quantifier):
    variables: list[ConditionVariable]
    formula: Formula

    def __str__(self) -> str:
        vars_str = ", ".join(str(v) for v in self.variables)
        return f"exists_num {vars_str} ({self.formula})"


@dataclass
class ForAllPosition(Quantifier):
    variables: list[ConditionVariable]
    formula: Formula

    def __str__(self) -> str:
        vars_str = ", ".join(str(v) for v in self.variables)
        return f"forall_pos {vars_str} ({self.formula})"


@dataclass
class ForAllNumber(Quantifier):
    variables: list[ConditionVariable]
    formula: Formula

    def __str__(self) -> str:
        vars_str = ", ".join(str(v) for v in self.variables)
        return f"forall_num {vars_str} ({self.formula})"


# --- Conclusions (Uses ConclusionTerms) ---


class Conclusion(ABC):
    pass


@dataclass
class SetVal(Conclusion):
    position: ConclusionTerm
    value: ConclusionTerm

    def __str__(self) -> str:
        return f"set({self.position}, {self.value})"


@dataclass
class ExcludeVal(Conclusion):
    position: ConclusionTerm
    operator: str
    value: ConclusionTerm

    def __str__(self) -> str:
        if self.operator == "=":
            return f"exclude({self.position}, {self.value})"
        return f"exclude({self.position}, {self.operator}{self.value})"


@dataclass
class OnlyVal(Conclusion):
    position: ConclusionTerm
    values: list[ConclusionTerm]

    def __str__(self) -> str:
        vals = ", ".join(str(v) for v in self.values)
        return f"only({self.position}, [{vals}])"


# --- Rule ---


@dataclass
class Rule:
    condition: Formula
    conclusions: list[Conclusion]

    def __str__(self) -> str:
        conclusions_str = "\n  - ".join(str(c) for c in self.conclusions)
        return f"Condition: {self.condition}\nConclusions:\n  - {conclusions_str}"
