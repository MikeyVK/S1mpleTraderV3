path = r"d:\dev\SimpleTraderV3\tests\integration\test_provenance_e2e.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = """        if artifact_type == "dto":
            context["fields"] = [{"name": "id", "type": "int"}]"""

new = """        if artifact_type == "dto":
            context["fields"] = [
                {"name": "id", "type": "int", "description": "Identifier"},
                {"name": "name", "type": "str", "description": "Name"}
            ]
            context["frozen"] = True
            context["examples"] = [{"id": 1, "name": "Test"}]
            context["dependencies"] = ["pydantic"]
            context["responsibilities"] = ["Data validation", "Type safety"]"""

content = content.replace(old, new, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("Fixed test_provenance_e2e.py (first occurrence)")
