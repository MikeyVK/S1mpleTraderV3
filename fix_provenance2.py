path = r"d:\dev\SimpleTraderV3\tests\integration\test_provenance_e2e.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Fix second occurrence (line 222-223)
old = """        if artifact_type == "dto":
            context["fields"] = [{"name": "id", "type": "int"}]

        file_path = await manager.scaffold_artifact(artifact_type, **context)"""

new = """        if artifact_type == "dto":
            context["fields"] = [
                {"name": "id", "type": "int", "description": "Identifier"},
                {"name": "name", "type": "str", "description": "Name"}
            ]
            context["frozen"] = True
            context["examples"] = [{"id": 1, "name": "Test"}]
            context["dependencies"] = ["pydantic"]
            context["responsibilities"] = ["Data validation", "Type safety"]

        file_path = await manager.scaffold_artifact(artifact_type, **context)"""

content = content.replace(old, new, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("Fixed test_provenance_e2e.py (second occurrence)")
