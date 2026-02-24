"""Gate 0 dedicated format violation fixture.

Deliberately uses single quotes throughout so ruff format --check
produces a diff (it normalizes to double quotes).
Do NOT run ruff format on this file — violations are intentional.
"""

x = 'hello'
y = 'world'
z = 'single quotes trigger ruff format'
