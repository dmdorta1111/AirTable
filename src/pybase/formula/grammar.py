"""Lark grammar definition for PyBase formulas.

This grammar supports Airtable-like formula syntax including:
- Arithmetic: +, -, *, /, %, ^ (power)
- Comparison: =, !=, <>, <, >, <=, >=
- String concatenation: &
- Logical: AND, OR, NOT
- Field references: {Field Name}
- Function calls: FUNCTION(arg1, arg2, ...)
- Literals: numbers, strings, booleans
"""

# Lark grammar for formula parsing
FORMULA_GRAMMAR = r"""
    ?start: expression

    ?expression: or_expr

    ?or_expr: and_expr
        | or_expr "OR"i and_expr -> or_op

    ?and_expr: not_expr
        | and_expr "AND"i not_expr -> and_op

    ?not_expr: comparison
        | "NOT"i not_expr -> not_op

    ?comparison: concat
        | comparison "=" concat -> eq
        | comparison "!=" concat -> ne
        | comparison "<>" concat -> ne
        | comparison "<" concat -> lt
        | comparison ">" concat -> gt
        | comparison "<=" concat -> le
        | comparison ">=" concat -> ge

    ?concat: additive
        | concat "&" additive -> string_concat

    ?additive: multiplicative
        | additive "+" multiplicative -> add
        | additive "-" multiplicative -> sub

    ?multiplicative: power
        | multiplicative "*" power -> mul
        | multiplicative "/" power -> div
        | multiplicative "%" power -> mod

    ?power: unary
        | unary "^" power -> pow

    ?unary: atom
        | "-" unary -> neg
        | "+" unary -> pos

    ?atom: NUMBER -> number
        | STRING -> string
        | BOOLEAN -> boolean
        | FIELD_REF -> field_ref
        | function_call
        | "(" expression ")"

    function_call: FUNCTION_NAME "(" [arguments] ")"

    arguments: expression ("," expression)*

    // Boolean literals (must come before FUNCTION_NAME for priority)
    BOOLEAN.2: "TRUE"i | "FALSE"i | "BLANK"i

    // Field reference: {Field Name} or {Field Name with spaces}
    FIELD_REF.1: "{" /[^}]+/ "}"

    // Function names (case-insensitive) - lower priority
    FUNCTION_NAME: /(?!TRUE|FALSE|BLANK)[A-Za-z_][A-Za-z0-9_]*/i

    // String literals (single or double quotes)
    STRING: /"[^"]*"/ | /'[^']*'/

    // Number literals (integer or decimal, with optional scientific notation)
    // Note: negative sign is handled by unary operator, not here
    NUMBER: /(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?/

    // Whitespace handling
    %import common.WS
    %ignore WS
"""
