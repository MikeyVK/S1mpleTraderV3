"""Gate 4 Types dedicated violation fixture (mypy --strict).

Deliberately missing type annotations and contains a type incompatibility
so mypy --strict reports structured errors.
Do NOT fix annotations — violations are intentional.
"""


def add_numbers(x, y):  # missing type annotations (mypy strict: error)
    return x + y


def greet(name: str) -> str:
    return "Hello " + name


result: int = greet("world")  # incompatible type: str assigned to int (mypy strict: error)
