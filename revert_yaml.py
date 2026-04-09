import re

with open(r"C:\temp\st3\.st3\config\workflows.yaml", "r", encoding="utf-8") as f:
    content = f.read()

# Revert: swap research, design, planning -> research, planning, design
result = re.sub(
    r'(      - research\n)(      - design\n)(      - planning\n)',
    r'\1\3\2',
    content
)

orig_lines = content.splitlines()
new_lines = result.splitlines()
print("REVERT DIFF:")
for i, (o, n) in enumerate(zip(orig_lines, new_lines)):
    if o != n:
        print(f"Line {i+1}: {repr(o)} -> {repr(n)}")

with open(r"C:\temp\st3\.st3\config\workflows.yaml", "w", encoding="utf-8") as f:
    f.write(result)
print("Reverted.")
