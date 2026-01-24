from abc import ABC, abstractmethod

from japanese_arrows.solver import SolverResult


class Constraint(ABC):
    @abstractmethod
    def check(self, trace: SolverResult) -> bool:
        pass


class MinRuleApplicationsOfMaxComplexity(Constraint):
    def __init__(self, fraction: float):
        self.fraction = fraction

    def check(self, trace: SolverResult) -> bool:
        steps = trace.steps
        total = len(steps)
        if total == 0:
            return False

        max_comp = trace.max_complexity_used
        max_comp_apps = sum(1 for s in steps if s.rule_complexity == max_comp)

        return (max_comp_apps / total) >= self.fraction


class MaxRuleApplicationsOfMaxComplexity(Constraint):
    def __init__(self, fraction: float):
        self.fraction = fraction

    def check(self, trace: SolverResult) -> bool:
        steps = trace.steps
        total = len(steps)
        if total == 0:
            return True

        max_comp = trace.max_complexity_used
        max_comp_apps = sum(1 for s in steps if s.rule_complexity == max_comp)

        return (max_comp_apps / total) <= self.fraction
