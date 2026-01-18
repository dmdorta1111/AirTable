"""Formula engine for PyBase.

This module provides a complete formula evaluation system supporting:
- Arithmetic operations (+, -, *, /, %, ^)
- Comparison operations (=, !=, <, >, <=, >=)
- Logical operations (AND, OR, NOT)
- Text functions (CONCAT, LEFT, RIGHT, MID, LEN, TRIM, etc.)
- Numeric functions (SUM, AVG, MIN, MAX, ROUND, ABS, etc.)
- Logical functions (IF, SWITCH, IFS)
- Date functions (TODAY, NOW, DATEADD, DATEDIFF, etc.)
- Field references ({Field Name})
"""

from pybase.formula.parser import FormulaParser
from pybase.formula.evaluator import FormulaEvaluator
from pybase.formula.functions import FORMULA_FUNCTIONS, register_function
from pybase.formula.dependencies import FormulaDependencyGraph

__all__ = [
    "FormulaParser",
    "FormulaEvaluator",
    "FORMULA_FUNCTIONS",
    "register_function",
    "FormulaDependencyGraph",
]
