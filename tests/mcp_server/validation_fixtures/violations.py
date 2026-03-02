"""Intentional quality violations for Issue #251 live validation testing.

DO NOT FIX these violations — they are deliberate test fixtures used in live
validation of the run_quality_gates MCP tool. Each section targets a specific gate.
"""

# gate2: wrong import order (sys before os — isort expects alphabetical: os, sys)
import sys
import os

# gate1: unused names — F401 (os, sys both unused)

# gate3: E501 — line exceeds 100 chars (threshold = 100, so 101+ triggers it)
THIS_VARIABLE_NAME_IS_INTENTIONALLY_VERY_LONG_TO_EXCEED_THE_LINE_LENGTH_GATE3_E501 = "trigger violation here"


# gate0: ruff format violation — missing spaces after commas
def badly_formatted_function(x,y,z):
    return x


# gate4_types: mypy type error — str passed where int expected
def typed_add(a: int, b: int) -> int:
    return a + b


wrong_call: int = typed_add("hello", "world")  # type: error
