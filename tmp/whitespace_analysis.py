"""Complete analysis of DTO template inheritance chain."""

# DTO inheritance: dto.py.jinja2 → tier2_base_python → tier1_base_code → tier0_base_artifact

# ===== TIER 0: tier0_base_artifact.jinja2 =====
# {% block content %}
# {%- set comment_start = "#" if format in ["python", "yaml", "shell"] else "<!--" -%}
# {%- set comment_end = "" if format in ["python", "yaml", "shell"] else " -->" -%}
# {{comment_start}} SCAFFOLD: template={{artifact_type}} version={{template_version | default("1.0")}} created={{timestamp}} path={{output_path}}{{comment_end}}{{ "\n" }}
# 
# {#- Child templates extend content here -#}
# {% endblock %}
#
# OUTPUT:
# "# SCAFFOLD: ...\n"
# "\n"                    <-- This empty line after {{ "\n" }} because next line in source is empty
#
# PROBLEM: Explicit "\n" + implicit newline from template source = 2 lines total

# ===== TIER 1: tier1_base_code.jinja2 =====
# {% block content -%}           <-- Trims whitespace AFTER
# {{ super() }}                   <-- Outputs tier0 (SCAFFOLD + 2 newlines)
#                                 <-- This empty line in source
# {%- block module_docstring -%}  <-- Trims whitespace BEFORE and AFTER
# """
# ...
# """
# 
# {%- endblock -%}               <-- Trims BEFORE and AFTER
#                                <-- Empty line
# {%- block imports_section -%}  <-- Trims BEFORE and AFTER
# ...
# {%- endblock -%}
#
# FLOW:
# 1. super() outputs "# SCAFFOLD...\n\n"  
# 2. Empty line in source after super() --> "\n"
# 3. {%- block module_docstring -%} TRIMS the "\n" before it
# 4. Docstring outputs
# 5. {%- endblock -%} TRIMS whitespace after
# 6. Empty line in source --> "\n"
# 7. {%- block imports_section -%} TRIMS the "\n" before it
# 8. Imports output
#
# RESULT: SCAFFOLD sticks to docstring (no newline between)

# ===== THE FIX =====
# Option 1: Remove explicit "\n" from tier0, keep one implicit newline
# Option 2: Use consistent {% block %} without - for boundaries, {%- -%} only internal

print("Analysis complete - see comments above for full breakdown")
print("\nRECOMMENDED FIX:")
print("1. tier0: Remove explicit {{ '\\n' }}, let block boundary provide newline")
print("2. tier1: Use {% block %} (no dash) for section boundaries")
print("3. tier1: Use {%- %} (left dash only) for control flow that shouldn't add newlines")
print("4. tier2: Follow same pattern")
print("5. concrete: Follow same pattern")
