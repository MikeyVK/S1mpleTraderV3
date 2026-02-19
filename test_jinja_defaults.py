from jinja2 import Template

# Test 1: Nested default filters  
t1 = Template('{{ a | default(b | default(\"fallback\")) }}')
print('Test 1 (nested default):', t1.render(a=None, b=None))

# Test 2: Complex expression in default
t2 = Template('{{ a | default(b[:10] if b else \"empty\") }}')
print('Test 2 (complex default):', t2.render(a=None, b='2026-02-14'))

# Test 3: Current or pattern from template
t3 = Template('{{ last_updated or (timestamp[:10] if timestamp else \"\") }}')
print('Test 3 (or pattern):', t3.render(last_updated=None, timestamp='2026-02-14T10:00:00Z'))

# Test 4: Can we replace with nested default?
t4 = Template('{{ last_updated | default((timestamp[:10] if timestamp else \"\")) }}')
print('Test 4 (default replacement):', t4.render(last_updated=None, timestamp='2026-02-14T10:00:00Z'))
