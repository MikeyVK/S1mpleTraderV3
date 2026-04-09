import re

with open(r"C:\temp\st3\.st3\config\workflows.yaml", "rb") as f:
    raw = f.read()

# Check line endings
print("Has CRLF:", b"\r\n" in raw)
print("Has LF:", b"\n" in raw[:200])

content = raw.decode("utf-8")
# Show lines 18-25 (phases area for feature)
lines = content.splitlines()
for i, l in enumerate(lines[14:26], start=15):
    print(f"{i}: {repr(l)}")
