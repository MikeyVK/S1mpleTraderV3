import re

file_path = r"d:\dev\SimpleTraderV3\tests\unit\scaffolders\test_template_scaffolder.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Fix 1: Line 104-107
content = content.replace(
    """)
        result = scaffolder.scaffold(
            artifact_type=\"dto\",
            name=\"TestDTO\",
            description=\"Test DTO\"
        )

        # Assert on structure""",
    """)
        result = scaffolder.scaffold(
            artifact_type=\"dto\",
            name=\"TestDTO\",
            description=\"Test DTO\",
            frozen=True,
            examples=[{\"id\": \"test-1\", \"name\": \"Test\"}],
            fields=[
                {\"name\": \"id\", \"type\": \"str\", \"description\": \"Unique identifier\"},
                {\"name\": \"name\", \"type\": \"str\", \"description\": \"Test name\"}
            ],
            dependencies=[\"pydantic\"],
            responsibilities=[\"Data validation\", \"Type safety\"]
        )

        # Assert on structure""",
    1
)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("✅ Applied fix 1/5")
