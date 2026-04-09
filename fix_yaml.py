import re

with open(r"C:\temp\st3\.st3\config\workflows.yaml", "r", encoding="utf-8") as f:
    content = f.read()

result = re.sub(
    r'(      - research\n)(      - planning\n)(      - design\n)',
    r'\1\3\2',
    content
)

orig_lines = content.splitlines()
new_lines = result.splitlines()
print("DIFF PREVIEW:")
changed = 0
for i, (o, n) in enumerate(zip(orig_lines, new_lines)):
    if o != n:
        print(f"Line {i+1}: {repr(o)} -> {repr(n)}")
        changed += 1
print(f"Total lines changed: {changed}")

with open(r"C:\temp\st3\.st3\config\workflows.yaml", "w", encoding="utf-8") as f:
    f.write(result)
print("Done.")
