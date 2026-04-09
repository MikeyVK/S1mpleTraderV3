with open(r"C:\temp\st3\.st3\config\workflows.yaml", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, l in enumerate(lines, 1):
    print(f"{i:3}: {l}", end="")
