# Copyright (C) 2026 Lukas Huwald
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import re

from japanese_arrows.rules import (
    And,
    BacktrackRule,
    Conclusion,
    Constant,
    Equality,
    ExcludeVal,
    ExistsNumber,
    ExistsPosition,
    ForAllNumber,
    ForAllPosition,
    Formula,
    FORule,
    FunctionCall,
    Not,
    OnlyVal,
    Or,
    Relation,
    Rule,
    SetVal,
    Term,
    Variable,
)

# Regex patterns for tokens
TOKEN_PATTERNS = [
    (r"\s+", None),  # Whitespace
    (r"//.*", None),  # Comments
    (r"exists\b", "EXISTS"),
    (r"forall\b", "FORALL"),
    (r"set\b", "SET"),
    (r"exclude\b", "EXCLUDE"),
    (r"only\b", "ONLY"),
    (r"->", "IMPLIES"),
    (r"=>", "DOUBLE_ARROW"),
    (r"!=", "NEQ"),
    (r"=", "EQ"),
    (r"<=", "LE"),
    (r">=", "GE"),
    (r"<", "LT"),
    (r">", "GT"),
    (r"!", "NOT"),
    (r"\^", "AND"),
    (r"v\b", "OR"),
    (r"\(", "LPAREN"),
    (r"\)", "RPAREN"),
    (r"\[", "LBRACKET"),
    (r"\]", "RBRACKET"),
    (r":", "COLON"),
    (r",", "COMMA"),
    (r"\+", "PLUS"),
    (r"-", "MINUS"),
    (r"\d+", "NUMBER"),
    (r"[a-zA-Z_]\w*", "IDENTIFIER"),
]


class Token:
    def __init__(self, type: str, value: str, line: int):
        self.type = type
        self.value = value
        self.line = line

    def __repr__(self) -> str:
        return f"Token({self.type}, {self.value!r})"


def tokenize(text: str) -> list[Token]:
    tokens = []
    line_num = 1
    pos = 0
    while pos < len(text):
        match = None
        for pattern, type_ in TOKEN_PATTERNS:
            regex = re.compile(pattern)
            match = regex.match(text, pos)
            if match:
                value = match.group(0)
                if type_:
                    tokens.append(Token(type_, value, line_num))
                # Count newlines in whitespace or comments to update line number
                line_num += value.count("\n")
                pos = match.end()
                break
        if not match:
            raise ValueError(f"Illegal character at line {line_num}: {text[pos]}")
    return tokens


class RuleParser:
    def __init__(self, text: str):
        self.tokens = tokenize(text)
        self.pos = 0

    def parse_rule(self) -> FORule:
        name_token = self.consume("IDENTIFIER")
        name = name_token.value
        self.consume("COLON")

        condition = self.parse_formula()
        conclusions = self.parse_conclusions()
        return FORule(name, condition, conclusions)

    def parse_conclusions(self) -> list[Conclusion]:
        conclusions = []
        while self.pos < len(self.tokens) and self.current_token().type == "DOUBLE_ARROW":
            self.consume("DOUBLE_ARROW")
            conclusions.append(self.parse_conclusion())
        return conclusions

    def parse_conclusion(self) -> Conclusion:
        token = self.consume("IDENTIFIER", "SET", "EXCLUDE", "ONLY")

        if token.type == "SET":
            self.consume("LPAREN")
            pos = self.parse_term()
            self.consume("COMMA")
            val = self.parse_term()
            self.consume("RPAREN")
            return SetVal(pos, val)
        elif token.type == "EXCLUDE":
            self.consume("LPAREN")
            pos = self.parse_term()
            self.consume("COMMA")

            # check for operator
            op = "="
            if self.match("GT", "LT", "GE", "LE", "EQ", "NEQ"):
                op_token = self.advance()
                op = op_token.value

            val = self.parse_term()
            self.consume("RPAREN")
            return ExcludeVal(pos, op, val)
        elif token.type == "ONLY":
            self.consume("LPAREN")
            pos = self.parse_term()
            self.consume("COMMA")
            self.consume("LBRACKET")
            values = []
            if not self.match("RBRACKET"):
                values.append(self.parse_term())
                while self.match("COMMA"):
                    self.consume("COMMA")
                    values.append(self.parse_term())
            self.consume("RBRACKET")
            self.consume("RPAREN")
            return OnlyVal(pos, values)
        else:
            raise ValueError(f"Unknown conclusion type: {token.value}")

    def parse_formula(self) -> Formula:
        return self.parse_implication()

    def parse_implication(self) -> Formula:
        left = self.parse_disjunction()
        if self.match("IMPLIES"):
            self.consume("IMPLIES")
            right = self.parse_implication()
            # Desugar: A -> B becomes !A v B
            return Or([Not(left), right])
        return left

    def parse_disjunction(self) -> Formula:
        formulas = [self.parse_conjunction()]
        while self.match("OR"):
            self.consume("OR")
            formulas.append(self.parse_conjunction())

        if len(formulas) == 1:
            return formulas[0]
        return Or(formulas)

    def parse_conjunction(self) -> Formula:
        formulas = [self.parse_atom()]
        while self.match("AND"):
            self.consume("AND")
            formulas.append(self.parse_atom())

        if len(formulas) == 1:
            return formulas[0]
        return And(formulas)

    def parse_atom(self) -> Formula:
        if self.match("LPAREN"):
            self.consume("LPAREN")
            # Check if it's a parenthesized formula
            f = self.parse_formula()
            self.consume("RPAREN")
            return f
        elif self.match("NOT"):
            self.consume("NOT")
            return Not(self.parse_atom())
        elif self.match("EXISTS", "FORALL"):
            return self.parse_quantifier()
        else:
            # Relation or Equality
            return self.parse_relation_or_equality()

    def parse_quantifier(self) -> Formula:
        is_forall = self.match("FORALL")
        self.advance()

        vars = []
        vars.append(self.consume("IDENTIFIER").value)
        while self.match("COMMA"):
            self.consume("COMMA")
            vars.append(self.consume("IDENTIFIER").value)

        self.consume("LPAREN")
        formula = self.parse_formula()
        self.consume("RPAREN")

        # Group consecutive variables of the same type to minimize AST depth
        grouped_quantifiers = []
        current_type = None
        current_vars: list[Variable] = []

        for v_name in vars:
            v_type = self._infer_var_type(v_name)
            if v_type != current_type:
                if current_type is not None:
                    grouped_quantifiers.append((current_type, current_vars))
                current_type = v_type
                current_vars = []
            current_vars.append(Variable(v_name))

        if current_type is not None:
            grouped_quantifiers.append((current_type, current_vars))

        result = formula
        # Apply in reverse order (rightmost variables are innermost)
        for q_type, q_vars in reversed(grouped_quantifiers):
            if is_forall:
                if q_type == "Position":
                    result = ForAllPosition(q_vars, result)
                else:
                    result = ForAllNumber(q_vars, result)
            else:
                if q_type == "Position":
                    result = ExistsPosition(q_vars, result)
                else:
                    result = ExistsNumber(q_vars, result)

        return result

    def parse_relation_or_equality(self) -> Formula:
        left = self.parse_term()

        if self.match("EQ", "NEQ", "LT", "GT", "LE", "GE"):
            op_token = self.advance()
            op = op_token.value
            right = self.parse_term()

            if op_token.type == "EQ":
                return Equality(left, right)
            elif op_token.type == "NEQ":
                return Not(Equality(left, right))
            else:
                return Relation(op, [left, right])

        if isinstance(left, FunctionCall):
            # Treat as relation if it matches the name(args) pattern in formula context
            return Relation(left.name, left.args)

        raise ValueError(f"Expected relation or equality, got {left}")

    def parse_term(self) -> Term:
        left = self.parse_term_primary()

        while self.match("PLUS", "MINUS"):
            op = self.advance().value
            right = self.parse_term_primary()
            left = FunctionCall(op, [left, right])

        return left

    def parse_term_primary(self) -> Term:
        if self.match("NUMBER"):
            return Constant(int(self.consume("NUMBER").value))

        name_token = self.consume("IDENTIFIER")
        name = name_token.value

        if self.match("LPAREN"):
            self.consume("LPAREN")
            args = []
            if not self.match("RPAREN"):
                args.append(self.parse_term())
                while self.match("COMMA"):
                    self.consume("COMMA")
                    args.append(self.parse_term())
            self.consume("RPAREN")
            return FunctionCall(name, args)

        if name in ["OOB", "nil"]:
            return Constant(name)

        return Variable(name)

    def _infer_var_type(self, name: str) -> str:
        # p,q,r... are Position, i,j,k... are Number
        if name and name[0] in "pqrst":
            return "Position"
        return "Number"  # default or i,j,k

    # Helper methods
    def current_token(self) -> Token:
        if self.pos >= len(self.tokens):
            return Token("EOF", "", -1)
        return self.tokens[self.pos]

    def advance(self) -> Token:
        token = self.current_token()
        self.pos += 1
        return token

    def match(self, *types: str) -> bool:
        if self.pos >= len(self.tokens):
            return False
        return self.current_token().type in types

    def consume(self, *types: str) -> Token:
        if self.match(*types):
            return self.advance()
        raise ValueError(
            f"Expected one of {types}, got {self.current_token()} at pos {self.pos}. "
            f"Previous: {self.tokens[self.pos - 1] if self.pos > 0 else 'None'}"
        )


def parse_rule(rule_dict: dict[str, object]) -> Rule:
    """Parse a rule from a dictionary.

    Expected format for FO rules:
        {
            "name": "RULE-NAME",
            "kind": "FO",
            "condition": "exists p (ahead(p) = 0)",
            "complexity": 1,
            "conclusions": ["set(p, 0)", "exclude(p, >1)"]
        }

    Expected format for Backtrack rules:
        {
            "name": "BACKTRACK_SIMPLE_1",
            "kind": "Backtrack",
            "complexity": 4,
            "backtrack_depth": 1,
            "rule_depth": 1,
            "max_rule_complexity": 2
        }
    """
    if "name" not in rule_dict or not rule_dict["name"]:
        raise ValueError("Rule must have a 'name' field")
    name = str(rule_dict["name"])

    kind = str(rule_dict.get("kind", "FO"))
    complexity_raw = rule_dict.get("complexity", 1)
    complexity = int(complexity_raw) if isinstance(complexity_raw, (int, str)) else 1

    if kind == "Backtrack":
        bd_raw = rule_dict.get("backtrack_depth", 1)
        backtrack_depth = int(bd_raw) if isinstance(bd_raw, (int, str)) else 1

        rd_raw = rule_dict.get("rule_depth", 1)
        rule_depth = int(rd_raw) if isinstance(rd_raw, (int, str)) else 1

        mrc_raw = rule_dict.get("max_rule_complexity", 1)
        max_rule_complexity = int(mrc_raw) if isinstance(mrc_raw, (int, str)) else 1

        return BacktrackRule(
            name=name,
            complexity=complexity,
            backtrack_depth=backtrack_depth,
            rule_depth=rule_depth,
            max_rule_complexity=max_rule_complexity,
        )
    else:
        condition_str = str(rule_dict.get("condition", ""))
        conclusions_list = rule_dict.get("conclusions", [])

        if condition_str.strip():
            condition_parser = RuleParser(condition_str)
            condition = condition_parser.parse_formula()
        else:
            condition = Equality(Constant(0), Constant(0))

        conclusions: list[Conclusion] = []
        if isinstance(conclusions_list, list):
            for conc_str in conclusions_list:
                conc_parser = RuleParser(str(conc_str))
                conclusions.append(conc_parser.parse_conclusion())

        return FORule(name, condition, conclusions, complexity)
