# mypy: disable-error-code="attr-defined, no-any-return, return"
from typing import Any, Callable, Iterator

from japanese_arrows.rules import (
    And,
    ConditionCalculation,
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
    Rule,
)
from japanese_arrows.type_checking import Type
from japanese_arrows.universe import Universe


class RuleCompiler:
    def __init__(self) -> None:
        self.code_lines: list[str] = []
        self.indent_level = 0
        self.bound_vars: list[str] = []

    def add_line(self, line: str) -> None:
        self.code_lines.append("    " * self.indent_level + line)

    def indent(self) -> None:
        self.indent_level += 1

    def dedent(self) -> None:
        self.indent_level -= 1

    def compile(self, rule: Rule) -> Callable[[Universe], Iterator[dict[str, Any]]]:
        self.code_lines = []
        self.indent_level = 0
        self.bound_vars = []

        self.add_line("def compiled_rule(u):")
        self.indent()

        # optimized locals
        self.add_line("pos_domain = u.domain[Type.POSITION]")
        self.add_line("num_domain = u.domain[Type.NUMBER]")
        self.add_line("rels = u.relations")
        self.add_line("funcs = u.functions")

        # Split long lines for linting compliance
        self.add_line("qe = u.quantifier_exclusions")
        self.add_line("excl_pos = qe.get(Type.POSITION, set()) if qe else set()")
        self.add_line("excl_num = qe.get(Type.NUMBER, set()) if qe else set()")

        self.add_line("eff_pos_domain = pos_domain - excl_pos")
        self.add_line("eff_num_domain = num_domain - excl_num")

        # Compile condition with a continuation that yields the result
        def yield_continuation() -> None:
            # Build the witness dict from bound variables
            if not self.bound_vars:
                self.add_line("yield {}")
                return

            dict_content = ", ".join(f"'{v}': {v}" for v in self.bound_vars)
            self.add_line(f"yield {{{dict_content}}}")

        self.compile_cps(rule.condition, yield_continuation)

        self.dedent()
        # The execution context extracts the function from namespace

        full_code = "\n".join(self.code_lines)

        namespace = {
            "Type": Type,
            "Iterator": Iterator,
            "Any": Any,
        }
        try:
            # noqa: S102
            exec(full_code, namespace)
            return namespace["compiled_rule"]
        except Exception as e:
            # print(f"Error compiling rule {rule.name}:")
            # print(full_code) # checking code if error
            raise e

    def compile_cps(self, phi: Formula, continuation: Callable[[], None]) -> None:
        """
        Generates code for 'phi'. If 'phi' is satisfied, executes 'continuation'
        (which generates the next block of code).
        """
        match type(phi):
            case t if t is And:
                # Chain continuations: f1 -> f2 -> ... -> continuation
                def make_chain(formulas: list[Formula]) -> Callable[[], None]:
                    if not formulas:
                        return continuation
                    first, *rest = formulas
                    return lambda: self.compile_cps(first, make_chain(rest))

                make_chain(phi.formulas)()

            case t if t in (ExistsPosition, ExistsNumber):
                domain_var = "eff_pos_domain" if t is ExistsPosition else "eff_num_domain"
                vars_to_bind = phi.variables

                def bind_vars(vars_list: list[ConditionVariable]) -> None:
                    if not vars_list:
                        self.compile_cps(phi.formula, continuation)
                        return

                    v = vars_list[0]
                    self.bound_vars.append(v.name)
                    self.add_line(f"for {v.name} in {domain_var}:")
                    self.indent()

                    bind_vars(vars_list[1:])

                    self.dedent()
                    self.bound_vars.pop()

                bind_vars(vars_to_bind)

            case t if t in (Relation, Equality):
                expr = self.expr_formula(phi)
                self.add_line(f"if {expr}:")
                self.indent()
                continuation()
                self.dedent()

            case t if t is Not:
                if isinstance(phi.formula, (Relation, Equality)):
                    expr = self.expr_formula(phi.formula)
                    self.add_line(f"if not ({expr}):")
                    self.indent()
                    continuation()
                    self.dedent()
                elif isinstance(phi.formula, (ExistsPosition, ExistsNumber)):
                    self.add_line("exists_found = False")

                    def set_found() -> None:
                        self.add_line("exists_found = True")

                    self.compile_cps(phi.formula, set_found)

                    self.add_line("if not exists_found:")
                    self.indent()
                    continuation()
                    self.dedent()
                else:
                    raise NotImplementedError("Complex NOT not supported by compiler")

            case t if t in (ForAllPosition, ForAllNumber):
                domain_var = "eff_pos_domain" if t is ForAllPosition else "eff_num_domain"
                vars_in = phi.variables

                def compile_forall_vars(vars_list: list[ConditionVariable], inner_cont: Any) -> None:
                    if not vars_list:
                        self.add_line("inner_success = False")

                        def set_success() -> None:
                            self.add_line("inner_success = True")

                        self.compile_cps(phi.formula, set_success)

                        self.add_line("if not inner_success:")
                        self.indent()
                        self.add_line("all_ok = False")
                        self.add_line("break")
                        self.dedent()
                        return

                    v = vars_list[0]
                    self.add_line(f"for {v.name} in {domain_var}:")
                    self.indent()
                    compile_forall_vars(vars_list[1:], inner_cont)
                    self.dedent()
                    self.add_line("if not all_ok: break")

                self.add_line("all_ok = True")
                compile_forall_vars(vars_in, None)
                self.add_line("if all_ok:")
                self.indent()
                continuation()
                self.dedent()

            case t if t is Or:
                for sub in phi.formulas:
                    self.compile_cps(sub, continuation)

            case _:
                raise ValueError(f"Unknown formula type: {type(phi)}")

    def expr_formula(self, phi: Formula) -> str:
        """Returns Python expression string for simple formulas."""
        match type(phi):
            case t if t is Relation:
                args = [self.expr_term(a) for a in phi.args]
                return f"rels['{phi.relation}'](({', '.join(args)},))"
            case t if t is Equality:
                return f"{self.expr_term(phi.left)} == {self.expr_term(phi.right)}"
            case _:
                raise ValueError(f"Expressions only supported for atoms, got {type(phi)}")

    def expr_term(self, term: ConditionTerm) -> str:
        match type(term):
            case t if t is ConditionVariable:
                return term.name
            case t if t is ConditionConstant:
                if isinstance(term.value, str):
                    return f"u.constants.get('{term.value}', '{term.value}')"
                return str(term.value)
            case t if t is FunctionCall:
                args = [self.expr_term(a) for a in term.args]
                return f"funcs['{term.name}'](({', '.join(args)},))"
            case t if t is ConditionCalculation:
                op = term.operator
                left = self.expr_term(term.left)
                right = self.expr_term(term.right)
                return f"({left} {op} {right} if isinstance({left}, int) and isinstance({right}, int) else 'nil')"
